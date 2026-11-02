//! The single approved multi-file Hugging Face export, with resumable verified IO.
use super::{DownloadCleanup, HttpDownloadOutcome, ModelManager};
use crate::managed::{payload_complete, payload_id, MODEL_LOCK};
use anyhow::{anyhow, Result};
use hf_hub::api::tokio::CancellationToken;
use std::fs;
use tauri::Emitter;

impl ModelManager {
    pub(super) async fn download_managed_model(&self, model_id: &str) -> Result<()> {
        crate::managed::require_allowed(model_id).map_err(anyhow::Error::msg)?;
        let (repo, revision) = MODEL_LOCK.source().map_err(anyhow::Error::msg)?;
        let root = crate::windows_npu::nemotron_dir_for(&self.app_handle, model_id)
            .map_err(anyhow::Error::msg)?;
        if payload_complete(&root) {
            self.update_download_status()?;
            let _ = self.app_handle.emit("model-download-complete", model_id);
            return Ok(());
        }
        let cancel = CancellationToken::new();
        {
            let mut flags = self.cancel_flags.lock().unwrap();
            if flags.contains_key(model_id) {
                return Err(anyhow!(
                    "This model is already downloading; wait for cancellation to finish."
                ));
            }
            flags.insert(model_id.into(), cancel.clone());
        }
        let _cleanup = DownloadCleanup {
            available_models: &self.available_models,
            cancel_flags: &self.cancel_flags,
            model_id: model_id.into(),
            disarmed: false,
        };
        if let Some(model) = self.available_models.lock().unwrap().get_mut(model_id) {
            model.is_downloading = true;
        }
        // The target is derived only from the embedded manifest digest. Individual
        // paths and the immutable HF commit have been validated before filesystem IO.
        let staging = root.with_extension("partial");
        let total: u64 = MODEL_LOCK.files.iter().map(|file| file.size).sum();
        let mut completed = 0;
        for file in &MODEL_LOCK.files {
            if cancel.is_cancelled() {
                return Ok(());
            }
            let destination = staging.join(&file.path);
            fs::create_dir_all(
                destination
                    .parent()
                    .ok_or_else(|| anyhow!("Invalid model path"))?,
            )?;
            // Completed files from an interrupted earlier attempt are re-hashed.
            // The HTTP helper also verifies a complete .partial without re-fetching.
            let verified = if destination.is_file() {
                let path = destination.clone();
                let expected = file.sha256.clone();
                let size = file.size;
                tokio::task::spawn_blocking(move || {
                    path.metadata().is_ok_and(|m| m.len() == size)
                        && ModelManager::compute_sha256(&path).is_ok_and(|hash| hash == expected)
                })
                .await?
            } else {
                false
            };
            if !verified {
                let partial = destination.with_extension(format!(
                    "{}.partial",
                    destination
                        .extension()
                        .and_then(|s| s.to_str())
                        .unwrap_or("file")
                ));
                let url = format!(
                    "https://huggingface.co/{repo}/resolve/{revision}/{}",
                    file.path
                );
                match self
                    .download_managed_file(
                        model_id, &url, &partial, file, completed, total, &cancel,
                    )
                    .await?
                {
                    HttpDownloadOutcome::Cancelled => return Ok(()),
                    HttpDownloadOutcome::Completed => {
                        if cancel.is_cancelled() {
                            return Ok(());
                        }
                        // Only this known staging file is replaced, never the active model.
                        if destination.exists() {
                            fs::remove_file(&destination)?;
                        }
                        fs::rename(partial, &destination)?;
                    }
                }
            }
            completed += file.size;
        }
        if cancel.is_cancelled() {
            return Ok(());
        }
        fs::write(staging.join("verified-manifest.sha256"), payload_id())?;
        if root.exists() {
            // Preserve a damaged previous directory for diagnosis; never merge
            // verified files with unverified leftovers or overwrite a loaded model.
            let backup = root.with_extension(format!(
                "invalid-{}",
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)?
                    .as_nanos()
            ));
            fs::rename(&root, backup)?;
        }
        fs::rename(staging, &root)?;
        drop(_cleanup);
        self.update_download_status()?;
        let _ = self.app_handle.emit("model-download-complete", model_id);
        Ok(())
    }
}
