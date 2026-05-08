use std::collections::VecDeque;
use std::io::{BufRead, BufReader, Read};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use tauri::Emitter;

use crate::vib_path;

use super::platform::augmented_vib_path;

const WATCH_BUFFER_LIMIT: usize = 200;

struct WatchRuntime {
    child: Option<std::process::Child>,
    logs: VecDeque<String>,
    errors: VecDeque<String>,
}

impl WatchRuntime {
    fn new() -> Self {
        Self {
            child: None,
            logs: VecDeque::with_capacity(WATCH_BUFFER_LIMIT),
            errors: VecDeque::with_capacity(WATCH_BUFFER_LIMIT),
        }
    }
}

pub(crate) struct WatchState(Arc<Mutex<WatchRuntime>>);

pub(crate) struct WatchShutdownHandle(Arc<Mutex<WatchRuntime>>);

pub(crate) fn new_state_pair() -> (WatchState, WatchShutdownHandle) {
    let inner = Arc::new(Mutex::new(WatchRuntime::new()));
    (WatchState(Arc::clone(&inner)), WatchShutdownHandle(inner))
}

pub(crate) fn stop_for_exit(handle: &WatchShutdownHandle) {
    if let Ok(mut guard) = handle.0.lock() {
        if let Some(mut child) = guard.child.take() {
            kill_watch_child(&mut child);
        }
    }
}

fn push_watch_line(buffer: &mut VecDeque<String>, line: String) {
    if line.is_empty() {
        return;
    }
    if buffer.len() >= WATCH_BUFFER_LIMIT {
        let _ = buffer.pop_front();
    }
    buffer.push_back(line);
}

#[cfg(target_os = "windows")]
fn emit_watch_log(app: &tauri::AppHandle, state: &Arc<Mutex<WatchRuntime>>, bytes: &[u8]) {
    let line = String::from_utf8_lossy(bytes).trim().to_string();
    if !line.is_empty() {
        if let Ok(mut guard) = state.lock() {
            push_watch_line(&mut guard.logs, line.clone());
        }
        let _ = app.emit("watch_log", line);
    }
}

#[cfg(target_os = "windows")]
fn emit_watch_error(app: &tauri::AppHandle, state: &Arc<Mutex<WatchRuntime>>, bytes: &[u8]) {
    let line = String::from_utf8_lossy(bytes).trim().to_string();
    if !line.is_empty() {
        if let Ok(mut guard) = state.lock() {
            push_watch_line(&mut guard.errors, line.clone());
        }
        let _ = app.emit("watch_error", line);
    }
}

#[cfg(target_os = "windows")]
fn spawn_watch_log_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        let mut reader = BufReader::new(reader);
        let mut buf = Vec::new();
        let mut byte = [0_u8; 1];

        loop {
            match reader.read(&mut byte) {
                Ok(0) => {
                    emit_watch_log(&app, &state, &buf);
                    break;
                }
                Ok(_) => match byte[0] {
                    b'\n' | b'\r' => {
                        emit_watch_log(&app, &state, &buf);
                        buf.clear();
                    }
                    b => buf.push(b),
                },
                Err(_) => {
                    emit_watch_log(&app, &state, &buf);
                    break;
                }
            }
        }
    });
}

#[cfg(not(target_os = "windows"))]
fn spawn_watch_log_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            if let Ok(line) = line {
                let trimmed = line.trim().to_string();
                if let Ok(mut guard) = state.lock() {
                    push_watch_line(&mut guard.logs, trimmed);
                }
                let _ = app.emit("watch_log", line);
            }
        }
    });
}

#[cfg(not(target_os = "windows"))]
fn spawn_watch_error_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            if let Ok(line) = line {
                let trimmed = line.trim().to_string();
                if !trimmed.is_empty() {
                    if let Ok(mut guard) = state.lock() {
                        push_watch_line(&mut guard.errors, trimmed.clone());
                    }
                    let _ = app.emit("watch_error", trimmed);
                }
            }
        }
    });
}

#[cfg(target_os = "windows")]
fn spawn_watch_error_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        let mut reader = BufReader::new(reader);
        let mut buf = Vec::new();
        let mut byte = [0_u8; 1];

        loop {
            match reader.read(&mut byte) {
                Ok(0) => {
                    emit_watch_error(&app, &state, &buf);
                    break;
                }
                Ok(_) => match byte[0] {
                    b'\n' | b'\r' => {
                        emit_watch_error(&app, &state, &buf);
                        buf.clear();
                    }
                    b => buf.push(b),
                },
                Err(_) => {
                    emit_watch_error(&app, &state, &buf);
                    break;
                }
            }
        }
    });
}

fn kill_watch_child(child: &mut std::process::Child) {
    #[cfg(unix)]
    unsafe {
        let pgid = child.id() as i32;
        libc::killpg(pgid, libc::SIGKILL);
    }
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;

        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let pid = child.id().to_string();
        let killed_tree = std::process::Command::new("taskkill")
            .args(["/PID", pid.as_str(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW)
            .status()
            .map(|status| status.success())
            .unwrap_or(false);

        if !killed_tree {
            let _ = child.kill();
        }
    }
    #[cfg(all(not(unix), not(target_os = "windows")))]
    { let _ = child.kill(); }
    let _ = child.wait();
}

impl Drop for WatchState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.child.take() {
                kill_watch_child(&mut child);
            }
        }
    }
}

#[tauri::command]
pub(crate) fn start_watch(app: tauri::AppHandle, state: tauri::State<WatchState>, cwd: String) -> Result<(), String> {
    let vib = vib_path::find_watch_vib().ok_or("watch에 사용할 vib 실행 파일을 찾을 수 없습니다")?;
    // 기존 watch가 있으면 먼저 중지
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(ref mut child) = guard.child {
        kill_watch_child(child);
    }
    guard.child = None;
    guard.logs.clear();
    guard.errors.clear();
    let mut watch_cmd = std::process::Command::new(&vib);
    watch_cmd.arg("watch").current_dir(PathBuf::from(&cwd));
    watch_cmd.stdin(std::process::Stdio::piped());
    watch_cmd.stdout(std::process::Stdio::piped());
    watch_cmd.stderr(std::process::Stdio::piped());
    watch_cmd.env("PATH", augmented_vib_path());
    watch_cmd.env("PYTHONUNBUFFERED", "1");
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        watch_cmd.env("VIBELIGN_ASK_PLAIN", "1");
        watch_cmd.env("NO_COLOR", "1");
        watch_cmd.env("PYTHONUTF8", "1");
        watch_cmd.env("PYTHONIOENCODING", "utf-8");
        watch_cmd.creation_flags(CREATE_NO_WINDOW);
    }
    // Unix: 새 프로세스 그룹 생성 → 자식까지 전체 kill 가능
    #[cfg(unix)]
    unsafe {
        use std::os::unix::process::CommandExt;
        watch_cmd.pre_exec(|| { libc::setpgid(0, 0); Ok(()) });
    }
    let mut child = watch_cmd.spawn().map_err(|e| e.to_string())?;
    // watchdog 설치 프롬프트(y/N)에 자동으로 "y" 응답
    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        let _ = stdin.write_all(b"y\n");
    }
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    guard.child = Some(child);
    let watch_state = Arc::clone(&state.0);
    drop(guard);

    if let Some(out) = stdout {
        let app2 = app.clone();
        spawn_watch_log_thread(out, app2, Arc::clone(&watch_state));
    }
    if let Some(err) = stderr {
        spawn_watch_error_thread(err, app, watch_state);
    }
    Ok(())
}

#[tauri::command]
pub(crate) fn stop_watch(state: tauri::State<WatchState>) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.child.take() {
        kill_watch_child(&mut child);
    }
    Ok(())
}

#[tauri::command]
pub(crate) fn watch_status(state: tauri::State<WatchState>) -> bool {
    state.0.lock()
        .map(|g| g.child.is_some())
        .unwrap_or(false)
}

#[tauri::command]
pub(crate) fn get_watch_logs(state: tauri::State<WatchState>) -> Vec<String> {
    state
        .0
        .lock()
        .map(|g| g.logs.iter().cloned().collect())
        .unwrap_or_default()
}

#[tauri::command]
pub(crate) fn get_watch_errors(state: tauri::State<WatchState>) -> Vec<String> {
    state
        .0
        .lock()
        .map(|g| g.errors.iter().cloned().collect())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::{new_state_pair, stop_for_exit};

    #[test]
    fn state_pair_shares_runtime_between_managed_state_and_exit_handle() {
        let (state, shutdown) = new_state_pair();

        {
            let mut guard = state.0.lock().expect("watch state lock");
            guard.logs.push_back("started".to_string());
            guard.errors.push_back("warning".to_string());
        }

        let guard = shutdown.0.lock().expect("watch shutdown lock");
        assert_eq!(guard.logs.iter().cloned().collect::<Vec<_>>(), vec!["started"]);
        assert_eq!(guard.errors.iter().cloned().collect::<Vec<_>>(), vec!["warning"]);
    }

    #[cfg(unix)]
    #[test]
    fn stop_for_exit_kills_child_registered_in_shared_runtime() {
        let (state, shutdown) = new_state_pair();
        let child = std::process::Command::new("sleep")
            .arg("30")
            .spawn()
            .expect("spawn sleep child");

        {
            let mut guard = state.0.lock().expect("watch state lock");
            guard.child = Some(child);
        }

        stop_for_exit(&shutdown);

        let guard = state.0.lock().expect("watch state lock");
        assert!(guard.child.is_none());
    }
}
