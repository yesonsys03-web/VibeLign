// === ANCHOR: GUI_ERROR_START ===
use std::collections::{HashMap, VecDeque};
use std::io::Write;
use std::path::PathBuf;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};

use crate::vib_path;

use super::platform::{augmented_vib_path, hide_console};

const GUI_ERROR_BUFFER_LIMIT: usize = 1000;
const GUI_ERROR_FLUSH_BATCH_SIZE: usize = 10;
const GUI_ERROR_FLUSH_DELAY_MS: u64 = 5_000;

static REPORTING_IN_PROGRESS: AtomicBool = AtomicBool::new(false);

struct ReportingGuard;

impl ReportingGuard {
    fn enter() -> Option<Self> {
        REPORTING_IN_PROGRESS
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .ok()
            .map(|_| Self)
    }
}

impl Drop for ReportingGuard {
    fn drop(&mut self) {
        REPORTING_IN_PROGRESS.store(false, Ordering::SeqCst);
    }
}

#[derive(Clone)]
struct GuiErrorEntry {
    project_dir: String,
    payload: serde_json::Value,
}

struct GuiErrorRuntime {
    queue: VecDeque<GuiErrorEntry>,
    flush_scheduled: bool,
}

impl GuiErrorRuntime {
    fn new() -> Self {
        Self {
            queue: VecDeque::with_capacity(GUI_ERROR_BUFFER_LIMIT),
            flush_scheduled: false,
        }
    }
}

pub(crate) struct GuiErrorState(Arc<Mutex<GuiErrorRuntime>>);

impl GuiErrorState {
    pub(crate) fn new() -> Self {
        Self(Arc::new(Mutex::new(GuiErrorRuntime::new())))
    }
}

fn push_gui_error(runtime: &mut GuiErrorRuntime, entry: GuiErrorEntry) -> bool {
    if runtime.queue.len() >= GUI_ERROR_BUFFER_LIMIT {
        let _ = runtime.queue.pop_front();
    }
    runtime.queue.push_back(entry);
    runtime.queue.len() >= GUI_ERROR_FLUSH_BATCH_SIZE
}

fn drain_gui_error_batch(runtime: &mut GuiErrorRuntime) -> Vec<GuiErrorEntry> {
    runtime.flush_scheduled = false;
    runtime.queue.drain(..).collect()
}

#[tauri::command]
pub(crate) fn record_gui_error(
    state: tauri::State<GuiErrorState>,
    project_dir: String,
    payload: serde_json::Value,
) {
    let state = Arc::clone(&state.0);
    let _ = std::panic::catch_unwind(move || {
        if project_dir.trim().is_empty() {
            return;
        }
        let Some(_guard) = ReportingGuard::enter() else {
            return;
        };
        let flush_now = match state.lock() {
            Ok(mut guard) => {
                let flush_now = push_gui_error(
                    &mut guard,
                    GuiErrorEntry {
                        project_dir,
                        payload,
                    },
                );
                if !guard.flush_scheduled {
                    guard.flush_scheduled = true;
                    schedule_gui_error_flush(Arc::clone(&state), GUI_ERROR_FLUSH_DELAY_MS);
                }
                flush_now
            }
            Err(_) => false,
        };
        if flush_now {
            schedule_gui_error_flush(state, 0);
        }
    });
}

fn schedule_gui_error_flush(state: Arc<Mutex<GuiErrorRuntime>>, delay_ms: u64) {
    tauri::async_runtime::spawn_blocking(move || {
        if delay_ms > 0 {
            std::thread::sleep(std::time::Duration::from_millis(delay_ms));
        }
        let batch = match state.lock() {
            Ok(mut guard) => drain_gui_error_batch(&mut guard),
            Err(_) => Vec::new(),
        };
        flush_gui_error_entries(batch);
    });
}

fn flush_gui_error_entries(entries: Vec<GuiErrorEntry>) {
    let mut grouped: HashMap<String, Vec<serde_json::Value>> = HashMap::new();
    for entry in entries {
        grouped
            .entry(entry.project_dir)
            .or_default()
            .push(entry.payload);
    }
    for (project_dir, payloads) in grouped {
        flush_gui_error_batch(&project_dir, &payloads);
    }
}

fn flush_gui_error_batch(project_dir: &str, payloads: &[serde_json::Value]) {
    let vib = vib_path::find_runtime_vib();
    let _ = flush_gui_error_batch_with_vib(vib, project_dir, payloads);
}

fn flush_gui_error_batch_with_vib(
    vib: Option<PathBuf>,
    project_dir: &str,
    payloads: &[serde_json::Value],
) -> bool {
    if payloads.is_empty() {
        return false;
    }
    let Some(vib) = vib else {
        return false;
    };
    let Ok(stdin_payload) = serde_json::to_vec(payloads) else {
        return false;
    };
    let mut cmd = std::process::Command::new(&vib);
    cmd.args(["log-gui-error", "--batch", "--root", project_dir])
        .current_dir(project_dir)
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .env("PATH", augmented_vib_path())
        .env("VIBELIGN_PROJECT_ROOT", project_dir)
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8");
    hide_console(&mut cmd);
    let Ok(mut child) = cmd.spawn() else {
        return false;
    };
    if let Some(mut stdin) = child.stdin.take() {
        let _ = stdin.write_all(&stdin_payload);
    }
    child.wait().map(|status| status.success()).unwrap_or(false)
}

#[cfg(test)]
mod error_reporter_tests {
    use std::sync::atomic::Ordering;

    use super::{
        drain_gui_error_batch, flush_gui_error_batch_with_vib, push_gui_error, GuiErrorEntry,
        GuiErrorRuntime, ReportingGuard, GUI_ERROR_BUFFER_LIMIT, GUI_ERROR_FLUSH_BATCH_SIZE,
        REPORTING_IN_PROGRESS,
    };

    #[test]
    fn gui_error_buffer_drops_oldest_beyond_cap() {
        let mut runtime = GuiErrorRuntime::new();
        for index in 0..(GUI_ERROR_BUFFER_LIMIT + 1) {
            let _ = push_gui_error(
                &mut runtime,
                GuiErrorEntry {
                    project_dir: "root".to_string(),
                    payload: serde_json::json!({"index": index}),
                },
            );
        }

        assert_eq!(runtime.queue.len(), GUI_ERROR_BUFFER_LIMIT);
        assert_eq!(
            runtime
                .queue
                .front()
                .and_then(|entry| entry.payload["index"].as_u64()),
            Some(1)
        );
    }

    #[test]
    fn gui_error_batch_drain_clears_scheduled_flag() {
        let mut runtime = GuiErrorRuntime::new();
        runtime.flush_scheduled = true;
        let _ = push_gui_error(
            &mut runtime,
            GuiErrorEntry {
                project_dir: "root".to_string(),
                payload: serde_json::json!({"message": "boom"}),
            },
        );

        let batch = drain_gui_error_batch(&mut runtime);

        assert_eq!(batch.len(), 1);
        assert!(!runtime.flush_scheduled);
        assert!(runtime.queue.is_empty());
    }

    #[test]
    fn gui_error_flush_threshold_is_batch_sized() {
        let mut runtime = GuiErrorRuntime::new();
        for index in 0..(GUI_ERROR_FLUSH_BATCH_SIZE - 1) {
            let flush_now = push_gui_error(
                &mut runtime,
                GuiErrorEntry {
                    project_dir: "root".to_string(),
                    payload: serde_json::json!({"index": index}),
                },
            );
            assert!(!flush_now);
        }

        let flush_now = push_gui_error(
            &mut runtime,
            GuiErrorEntry {
                project_dir: "root".to_string(),
                payload: serde_json::json!({"index": GUI_ERROR_FLUSH_BATCH_SIZE}),
            },
        );

        assert!(flush_now);
    }

    #[test]
    fn reporting_guard_resets_after_drop_and_blocks_reentry() {
        REPORTING_IN_PROGRESS.store(false, Ordering::SeqCst);
        {
            let _guard =
                ReportingGuard::enter().expect("first reporter entry should acquire guard");
            assert!(ReportingGuard::enter().is_none());
        }
        assert!(ReportingGuard::enter().is_some());
        REPORTING_IN_PROGRESS.store(false, Ordering::SeqCst);
    }

    #[test]
    fn missing_vib_path_drops_batch_silently() {
        let payloads = vec![serde_json::json!({"message": "boom"})];

        let flushed = flush_gui_error_batch_with_vib(None, "/tmp/project", &payloads);

        assert!(!flushed);
    }

    #[test]
    fn gui_error_state_constructor_wraps_queue_runtime() {
        let state = super::GuiErrorState::new();

        {
            let mut runtime = state.0.lock().expect("gui error state lock");
            let flush_now = push_gui_error(
                &mut runtime,
                GuiErrorEntry {
                    project_dir: "root".to_string(),
                    payload: serde_json::json!({"message": "boom"}),
                },
            );
            assert!(!flush_now);
            assert_eq!(runtime.queue.len(), 1);
        }

        let mut runtime = state.0.lock().expect("gui error state lock");
        let batch = drain_gui_error_batch(&mut runtime);
        assert_eq!(batch.len(), 1);
        assert!(runtime.queue.is_empty());
    }
}
// === ANCHOR: GUI_ERROR_END ===
