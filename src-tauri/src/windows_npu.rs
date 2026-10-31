//! Bundled, explicit Intel NPU backend. Errors never select a different device.
use crate::commands::transcription::NpuLoadStatus;
use log::{info, warn};
use serde_json::{json, Value};
use std::io::{BufRead, BufReader, Read, Write};
use std::os::windows::process::CommandExt;
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{mpsc, Arc, Mutex, OnceLock};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, Manager};

pub const MODEL_ID: &str = "openvino-turbo-int8-npu";
const MAX_AUDIO_SAMPLES: usize = 16_000 * 600;
const LOAD_TIMEOUT: Duration = Duration::from_secs(20 * 60);
const REQUEST_TIMEOUT: Duration = Duration::from_secs(120);
static WORKER: OnceLock<Mutex<Option<Worker>>> = OnceLock::new();
static READY: AtomicBool = AtomicBool::new(false);
static ACTIVE_LOAD: Mutex<Option<Arc<AtomicBool>>> = Mutex::new(None);
static LOAD_STATUS: OnceLock<Mutex<Option<NpuLoadStatus>>> = OnceLock::new();

pub fn load_status() -> Option<NpuLoadStatus> {
    LOAD_STATUS
        .get_or_init(|| Mutex::new(None))
        .lock()
        .map(|status| status.clone())
        .unwrap_or(None)
}

fn progress(app: &AppHandle, stage: &str, started: Instant, active: bool, error: Option<&str>) {
    let status = NpuLoadStatus {
        stage: stage.to_string(),
        elapsed_ms: started.elapsed().as_millis().min(u32::MAX as u128) as u32,
        active,
        error: error.map(str::to_string),
    };
    if let Ok(mut stored) = LOAD_STATUS.get_or_init(|| Mutex::new(None)).lock() {
        *stored = Some(status.clone());
    }
    let _ = app.emit("npu-load-progress", status);
}

/// Independent of WORKER: cancellation must be possible while its mutex is busy.
pub fn cancel_load() -> bool {
    if let Ok(active) = ACTIVE_LOAD.lock() {
        if let Some(cancel) = active.as_ref() {
            cancel.store(true, Ordering::Release);
            return true;
        }
    }
    false
}

struct ActiveLoad;
impl Drop for ActiveLoad {
    fn drop(&mut self) {
        if let Ok(mut active) = ACTIVE_LOAD.lock() {
            *active = None;
        }
    }
}

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
        // Do not wait indefinitely if Windows refuses termination.
        if self.child.kill().is_ok() {
            let _ = self.child.wait();
        }
    }
}

impl Worker {
    fn spawn(app: &AppHandle, cancel: &AtomicBool, started: Instant) -> Result<Self, String> {
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
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Cannot launch NPU runtime: {e}"))?;
        if let Some(mut stderr) = child.stderr.take() {
            std::thread::spawn(move || {
                let mut buffer = [0u8; 2048];
                let mut logged = 0;
                while let Ok(count) = stderr.read(&mut buffer) {
                    if count == 0 {
                        break;
                    }
                    // Drain continuously, but cap native diagnostics at 64 KiB per worker.
                    let keep = count.min(65536usize.saturating_sub(logged));
                    if keep > 0 {
                        warn!("NPU runtime: {}", String::from_utf8_lossy(&buffer[..keep]));
                        logged += keep;
                    }
                }
            });
        }
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
        let mut stage = "starting".to_string();
        let mut tick = Instant::now();
        let ready = wait_response(&worker.responses, LOAD_TIMEOUT, Some(cancel), |message| {
            if let Some(next) = message
                .and_then(|value| value.get("stage"))
                .and_then(Value::as_str)
            {
                stage = next.to_string();
                info!(
                    "NPU load stage={} elapsed_ms={}",
                    stage,
                    started.elapsed().as_millis()
                );
                tick = Instant::now() - Duration::from_secs(1);
            }
            if tick.elapsed() >= Duration::from_secs(1) {
                progress(app, &stage, started, true, None);
                tick = Instant::now();
            }
        })?;
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
        info!("Whisper Turbo INT8 ready: OpenVINO device=NPU (no fallback)");
        Ok(worker)
    }

    fn response(&self, timeout: Duration) -> Result<Value, String> {
        wait_response(&self.responses, timeout, None, |_| {})
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

fn wait_response(
    responses: &mpsc::Receiver<Result<Value, String>>,
    timeout: Duration,
    cancel: Option<&AtomicBool>,
    mut on_progress: impl FnMut(Option<&Value>),
) -> Result<Value, String> {
    let started = Instant::now();
    loop {
        if cancel.is_some_and(|flag| flag.load(Ordering::Acquire)) {
            return Err("NPU model loading cancelled".into());
        }
        let remaining = timeout.checked_sub(started.elapsed()).ok_or(
            "Intel NPU worker timed out; see the NPU runtime diagnostics in the application log",
        )?;
        match responses.recv_timeout(remaining.min(Duration::from_millis(100))) {
            Ok(value) => {
                let value = value?;
                if value.get("stage").is_some() {
                    on_progress(Some(&value));
                } else {
                    if cancel.is_some_and(|flag| flag.load(Ordering::Acquire)) {
                        return Err("NPU model loading cancelled".into());
                    }
                    return Ok(value);
                }
            }
            Err(mpsc::RecvTimeoutError::Timeout) => on_progress(None),
            Err(mpsc::RecvTimeoutError::Disconnected) => return Err(
                "Intel NPU worker exited before replying; see the NPU runtime diagnostics in the application log".into()),
        }
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
        let cancel = Arc::new(AtomicBool::new(false));
        *ACTIVE_LOAD
            .lock()
            .map_err(|_| "NPU cancellation lock poisoned")? = Some(cancel.clone());
        let _active_load = ActiveLoad;
        let started = Instant::now();
        progress(app, "starting", started, true, None);
        let result = Worker::spawn(app, &cancel, started);
        // Serialize the final ready commit with cancellation; never publish a cancelled worker.
        let mut active = ACTIVE_LOAD
            .lock()
            .map_err(|_| "NPU cancellation lock poisoned")?;
        let result = if cancel.load(Ordering::Acquire) {
            drop(result);
            Err("NPU model loading cancelled".to_string())
        } else {
            result
        };
        *active = None;
        drop(active);
        match result {
            Ok(worker) => {
                *guard = Some(worker);
                READY.store(true, Ordering::Release);
                progress(app, "ready", started, false, None);
            }
            Err(error) => {
                let stage = if cancel.load(Ordering::Acquire) {
                    "cancelled"
                } else {
                    "failed"
                };
                progress(app, stage, started, false, Some(&error));
                return Err(error);
            }
        }
    }
    Ok(())
}

pub fn unload() {
    cancel_load();
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
    fn cancellation_interrupts_a_silent_worker() {
        let (_tx, rx) = mpsc::channel();
        let flag = Arc::new(AtomicBool::new(false));
        let other = flag.clone();
        let started = Instant::now();
        let thread = std::thread::spawn(move || {
            std::thread::sleep(Duration::from_millis(30));
            other.store(true, Ordering::Release);
        });
        let error = wait_response(&rx, Duration::from_secs(30), Some(&flag), |_| {}).unwrap_err();
        thread.join().unwrap();
        assert!(error.contains("cancelled"));
        assert!(started.elapsed() < Duration::from_secs(2));
    }

    #[test]
    fn progress_does_not_replace_ready_or_extend_deadline() {
        let (tx, rx) = mpsc::channel();
        tx.send(Ok(json!({"stage":"compiling"}))).unwrap();
        tx.send(Ok(json!({"ready":true,"device":"NPU"}))).unwrap();
        let mut stages = 0;
        let result = wait_response(&rx, Duration::from_secs(1), None, |event| {
            if event.is_some() {
                stages += 1;
            }
        })
        .unwrap();
        assert_eq!(stages, 1);
        assert_eq!(result["ready"], true);
        let started = Instant::now();
        let error = wait_response(&rx, Duration::from_millis(60), None, |_| {
            let _ = tx.send(Ok(json!({"stage":"compiling"})));
        })
        .unwrap_err();
        assert!(error.contains("timed out"));
        assert!(started.elapsed() < Duration::from_secs(2));
    }

    #[test]
    fn exited_worker_and_bad_json_are_errors() {
        let (tx, rx) = mpsc::channel();
        tx.send(Err("invalid JSON".into())).unwrap();
        assert!(wait_response(&rx, Duration::from_secs(1), None, |_| {})
            .unwrap_err()
            .contains("invalid JSON"));
        drop(tx);
        assert!(wait_response(&rx, Duration::from_secs(1), None, |_| {})
            .unwrap_err()
            .contains("exited"));
    }
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
