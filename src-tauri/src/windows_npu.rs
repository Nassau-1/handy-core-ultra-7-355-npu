//! Bundled, explicit Intel NPU backend. Errors never select a different device.
use log::info;
use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Write};
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Mutex, OnceLock};
use std::time::Duration;
use tauri::{AppHandle, Manager};

pub const MODEL_ID: &str = "openvino-turbo-int8-npu";
const MAX_AUDIO_SAMPLES: usize = 16_000 * 600;
const LOAD_TIMEOUT: Duration = Duration::from_secs(20 * 60);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(120);
static WORKER: OnceLock<Mutex<Option<Worker>>> = OnceLock::new();
static READY: AtomicBool = AtomicBool::new(false);

fn slot() -> &'static Mutex<Option<Worker>> {
    WORKER.get_or_init(|| Mutex::new(None))
}

pub fn model_dir(app: &AppHandle) -> Result<PathBuf, String> {
    app.path()
        .resource_dir()
        .map(|p| p.join("resources/npu/model"))
        .map_err(|e| e.to_string())
}

pub fn bundled_model_available(app: &AppHandle) -> bool {
    model_dir(app).is_ok_and(|p| {
        [
            "openvino_encoder_model.xml",
            "openvino_encoder_model.bin",
            "openvino_decoder_model.xml",
            "openvino_decoder_model.bin",
            "generation_config.json",
        ]
        .iter()
        .all(|f| p.join(f).is_file())
    })
}

pub fn is_ready() -> bool {
    READY.load(Ordering::Acquire)
}

struct Worker {
    child: Child,
    requests: mpsc::Sender<Vec<u8>>,
    responses: mpsc::Receiver<Result<Value, String>>,
}

impl Drop for Worker {
    fn drop(&mut self) {
        READY.store(false, Ordering::Release);
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

impl Worker {
    fn spawn(app: &AppHandle) -> Result<Self, String> {
        let resources = app.path().resource_dir().map_err(|e| e.to_string())?;
        let exe = resources.join("resources/npu/worker/handy-npu-worker.exe");
        if !exe.is_file() || !bundled_model_available(app) {
            return Err(
                "Bundled NPU runtime/model missing. Repair the installation from Company Portal."
                    .into(),
            );
        }
        let cache = app
            .path()
            .app_local_data_dir()
            .map_err(|e| e.to_string())?
            .join("npu-cache/2026.2.1-turbo-4929ae83");
        std::fs::create_dir_all(&cache).map_err(|e| e.to_string())?;
        let mut child = Command::new(exe)
            .args([model_dir(app)?, cache])
            .creation_flags(0x08000000)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Cannot launch NPU runtime: {e}"))?;
        let mut stdin = child.stdin.take().ok_or("Missing worker stdin")?;
        let (requests, frames) = mpsc::channel::<Vec<u8>>();
        std::thread::spawn(move || {
            for frame in frames {
                if stdin.write_all(&frame).and_then(|_| stdin.flush()).is_err() {
                    break;
                }
            }
        });
        let stdout = child.stdout.take().ok_or("Missing worker stdout")?;
        let (tx, rx) = mpsc::channel();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let response = line
                    .map_err(|e| e.to_string())
                    .and_then(|s| serde_json::from_str(&s).map_err(|e| e.to_string()));
                if tx.send(response).is_err() {
                    break;
                }
            }
        });
        let worker = Self {
            child,
            requests,
            responses: rx,
        };
        let ready = worker.response(LOAD_TIMEOUT)?;
        if ready.get("ready").and_then(Value::as_bool) != Some(true)
            || ready.get("device").and_then(Value::as_str) != Some("NPU")
        {
            return Err(format!(
                "Intel NPU initialization failed: {}",
                ready
                    .get("error")
                    .and_then(Value::as_str)
                    .unwrap_or("invalid device response")
            ));
        }
        READY.store(true, Ordering::Release);
        info!("Whisper Turbo INT8 ready: OpenVINO device=NPU (no fallback)");
        Ok(worker)
    }

    fn response(&self, timeout: Duration) -> Result<Value, String> {
        self.responses.recv_timeout(timeout).map_err(|e| {
            format!("Intel NPU worker timed out or exited ({e}); retry to restart it")
        })?
    }

    fn transcribe(&mut self, audio: &[f32], language: Option<&str>) -> Result<String, String> {
        let header = json!({"samples": audio.len(), "language": language_token(language), "translate": false});
        let mut frame = header.to_string().into_bytes();
        frame.push(b'\n');
        for sample in audio {
            frame.extend_from_slice(&sample.to_le_bytes());
        }
        // Writing large audio frames must not bypass the inference deadline.
        self.requests
            .send(frame)
            .map_err(|e| format!("NPU worker write failed: {e}"))?;
        let response = self.response(REQUEST_TIMEOUT)?;
        if response.get("ok").and_then(Value::as_bool) != Some(true) {
            return Err(response
                .get("error")
                .and_then(Value::as_str)
                .unwrap_or("NPU inference failed")
                .to_string());
        }
        response
            .get("text")
            .and_then(Value::as_str)
            .map(str::to_owned)
            .ok_or_else(|| "NPU worker returned no text".into())
    }
}

fn language_token(language: Option<&str>) -> Option<String> {
    language
        .filter(|s| s.len() == 2 && s.bytes().all(|b| b.is_ascii_lowercase()))
        .map(|s| format!("<|{s}|>"))
}

pub fn load(app: &AppHandle) -> Result<(), String> {
    let mut guard = slot().lock().map_err(|_| "NPU worker lock poisoned")?;
    if guard.is_none() {
        *guard = Some(Worker::spawn(app)?);
    }
    Ok(())
}

pub fn unload() {
    if let Ok(mut guard) = slot().lock() {
        *guard = None;
    }
}

pub fn transcribe(audio: &[f32], language: Option<&str>) -> Result<String, String> {
    if audio.is_empty() {
        return Ok(String::new());
    }
    if audio.len() > MAX_AUDIO_SAMPLES || audio.iter().any(|x| !x.is_finite() || x.abs() > 1.01) {
        return Err("NPU audio must be normalized 16 kHz PCM, at most 10 minutes".into());
    }
    let mut guard = slot().lock().map_err(|_| "NPU worker lock poisoned")?;
    let result = guard
        .as_mut()
        .ok_or("NPU model is not loaded")?
        .transcribe(audio, language);
    if result.is_err() {
        *guard = None;
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn languages_are_validated() {
        assert_eq!(language_token(Some("fr")), Some("<|fr|>".into()));
        assert_eq!(language_token(Some("auto")), None);
        assert_eq!(language_token(Some("fr\n")), None);
    }
    #[test]
    fn invalid_audio_is_rejected_before_worker_access() {
        assert!(transcribe(&[f32::NAN], Some("fr")).is_err());
        assert!(transcribe(&[2.0], Some("fr")).is_err());
    }
}
