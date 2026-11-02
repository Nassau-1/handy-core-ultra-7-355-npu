//! Build-time owner policy. User settings and local model discovery cannot expand it.
use once_cell::sync::Lazy;
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::path::Path;

#[derive(Deserialize)]
struct Policy {
    managed: bool,
    default_model: String,
    allowed_models: Vec<String>,
}

static POLICY: Lazy<Policy> = Lazy::new(|| {
    serde_json::from_str(include_str!("../../packaging/managed-policy.json"))
        .expect("invalid embedded managed model policy")
});

pub fn enabled() -> bool {
    POLICY.managed
}

pub fn allows(id: &str) -> bool {
    !enabled() || POLICY.allowed_models.iter().any(|allowed| allowed == id)
}

pub fn require_allowed(id: &str) -> Result<(), String> {
    if allows(id) {
        Ok(())
    } else {
        Err("This model is not enabled in your organization's Handy distribution.".into())
    }
}

pub fn default_model() -> &'static str {
    &POLICY.default_model
}

#[derive(Deserialize, Clone)]
pub struct ModelFile {
    pub path: String,
    pub size: u64,
    pub sha256: String,
}

#[derive(Deserialize, Clone)]
pub struct ModelLock {
    pub model_id: String,
    pub repo: Option<String>,
    pub revision: Option<String>,
    pub storage_precision: String,
    pub files: Vec<ModelFile>,
}

pub const MODEL_LOCK_JSON: &str = include_str!("../../packaging/managed-model-lock.json");
pub static MODEL_LOCK: Lazy<ModelLock> =
    Lazy::new(|| serde_json::from_str(MODEL_LOCK_JSON).expect("invalid embedded model lock"));

pub fn payload_id() -> String {
    format!("{:x}", Sha256::digest(MODEL_LOCK_JSON.as_bytes()))
}

impl ModelLock {
    pub fn source(&self) -> Result<(&str, &str), String> {
        let repo = self
            .repo
            .as_deref()
            .ok_or("The approved model is awaiting publication on Hugging Face.")?;
        let revision = self
            .revision
            .as_deref()
            .ok_or("The approved Hugging Face revision has not been configured.")?;
        let parts: Vec<_> = repo.split('/').collect();
        if parts.len() != 2
            || parts.iter().any(|part| {
                part.is_empty()
                    || *part == "."
                    || *part == ".."
                    || !part
                        .chars()
                        .all(|c| c.is_ascii_alphanumeric() || "-_.".contains(c))
            })
            || revision.len() != 40
            || !revision.chars().all(|c| c.is_ascii_hexdigit())
        {
            return Err("Invalid approved model repository/revision".into());
        }
        if self.storage_precision != "FP32"
            || self.model_id != default_model()
            || self.files.is_empty()
        {
            return Err("Unexpected approved model format".into());
        }
        let mut paths = std::collections::HashSet::new();
        for file in &self.files {
            let parts: Vec<_> = file.path.split('/').collect();
            let notice = matches!(
                file.path.as_str(),
                "LICENSE.txt"
                    | "NVIDIA-MODEL-CARD.md"
                    | "TRANSFORMERS-LICENSE.txt"
                    | "source-manifest.json"
            );
            let component = parts.len() == 2
                && matches!(parts[0], "artifact" | "tokenizer")
                && !parts[1].is_empty()
                && parts[1] != "."
                && parts[1] != ".."
                && parts[1]
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || "-_.".contains(c));
            if !(notice || component)
                || file.size == 0
                || file.sha256.len() != 64
                || !file.sha256.chars().all(|c| c.is_ascii_hexdigit())
                || !paths.insert(file.path.as_str())
            {
                return Err("Invalid approved model file manifest".into());
            }
        }
        let required = [
            "artifact/encoder_stream.xml",
            "artifact/encoder_stream.bin",
            "artifact/subsampler_first.xml",
            "artifact/subsampler_first.bin",
            "artifact/subsampler_step.xml",
            "artifact/subsampler_step.bin",
            "artifact/predictor.xml",
            "artifact/predictor.bin",
            "artifact/joint.xml",
            "artifact/joint.bin",
            "artifact/frontend.npz",
            "artifact/metadata.json",
            "tokenizer/tokenizer.json",
            "tokenizer/tokenizer_config.json",
            "tokenizer/processor_config.json",
            "LICENSE.txt",
            "NVIDIA-MODEL-CARD.md",
            "TRANSFORMERS-LICENSE.txt",
            "source-manifest.json",
        ];
        if paths.len() != required.len() || !required.iter().all(|path| paths.contains(path)) {
            return Err("Approved model manifest is missing required components".into());
        }
        Ok((repo, revision))
    }
}

/// Only an atomically finalized, hash-verified download is considered installed.
/// Sizes are checked cheaply at startup; SHA256 is checked before finalization.
pub fn payload_complete(root: &Path) -> bool {
    payload_complete_with(root, &MODEL_LOCK, &payload_id())
}

fn payload_complete_with(root: &Path, manifest: &ModelLock, expected_id: &str) -> bool {
    manifest.source().is_ok()
        && std::fs::read_to_string(root.join("verified-manifest.sha256"))
            .is_ok_and(|id| id == expected_id)
        && manifest.files.iter().all(|file| {
            root.join(&file.path)
                .metadata()
                .is_ok_and(|metadata| metadata.is_file() && metadata.len() == file.size)
        })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn managed_policy_denies_retired_downloaded_and_injected_models() {
        assert!(enabled());
        assert!(allows(default_model()));
        assert_eq!(POLICY.allowed_models.len(), 1);
        for id in [
            "openvino-turbo-int8-npu",
            "nemotron-35-npu-pilot",
            "turbo",
            "custom-model",
            "../model",
            "",
        ] {
            assert!(require_allowed(id).is_err(), "{id}");
        }
    }

    #[test]
    fn immutable_hf_source_and_paths_are_required() {
        let mut model = MODEL_LOCK.clone();
        model.repo = Some("owner/approved-model".into());
        model.revision = Some("a".repeat(40));
        assert!(model.source().is_ok());
        model.revision = Some("main".into());
        assert!(model.source().is_err());
        model.revision = Some("b".repeat(40));
        for path in [
            "../model.bin",
            "artifact/../../file",
            "artifact/C:\\file",
            "/absolute",
            "artifact/..",
        ] {
            model.files[0].path = path.into();
            assert!(model.source().is_err(), "{path}");
        }
        assert!(!payload_complete(Path::new(
            "missing-managed-model-test-directory"
        )));
    }

    #[test]
    fn incomplete_or_wrong_snapshot_is_never_ready() {
        let root = tempfile::tempdir().unwrap();
        let mut model = MODEL_LOCK.clone();
        model.repo = Some("owner/approved-model".into());
        model.revision = Some("a".repeat(40));
        for file in &mut model.files {
            file.size = 1;
            let path = root.path().join(&file.path);
            std::fs::create_dir_all(path.parent().unwrap()).unwrap();
            std::fs::write(path, [1]).unwrap();
        }
        assert!(!payload_complete_with(root.path(), &model, "approved"));
        std::fs::write(root.path().join("verified-manifest.sha256"), "different").unwrap();
        assert!(!payload_complete_with(root.path(), &model, "approved"));
        std::fs::write(root.path().join("verified-manifest.sha256"), "approved").unwrap();
        assert!(payload_complete_with(root.path(), &model, "approved"));
        std::fs::write(root.path().join(&model.files[0].path), []).unwrap();
        assert!(!payload_complete_with(root.path(), &model, "approved"));
        model.files.pop();
        assert!(model.source().is_err());
    }
}
