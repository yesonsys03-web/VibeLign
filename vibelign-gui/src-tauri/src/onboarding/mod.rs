//! Cross-platform onboarding scaffold. Shared types/helpers live here; the
//! per-OS runners live in `windows` and `macos` sub-modules. During the
//! refactor (Task 0), macOS still uses stubs, so some helpers appear dead on
//! macOS builds — they're still needed by `windows.rs` and by the Task 1+
//! macOS implementation.
#![allow(dead_code)]

use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use tauri::Emitter;

pub mod macos;
pub mod windows;

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub(crate) struct OnboardingLastError {
    pub(crate) code: String,
    pub(crate) summary: String,
    pub(crate) detail: Option<String>,
    pub(crate) suggested_action: Option<String>,
}

#[derive(Serialize, Clone, Default)]
#[serde(rename_all = "camelCase")]
pub(crate) struct OnboardingDiagnostics {
    pub(crate) git_installed: Option<bool>,
    pub(crate) wsl_available: Option<bool>,
    pub(crate) claude_on_path: Option<bool>,
    pub(crate) claude_version_ok: Option<bool>,
    pub(crate) claude_doctor_ok: Option<bool>,
    pub(crate) login_status_known: Option<bool>,
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct OnboardingSnapshot {
    pub(crate) state: String,
    pub(crate) os: String,
    pub(crate) install_path_kind: String,
    pub(crate) shell_targets: Vec<String>,
    pub(crate) next_action: String,
    pub(crate) headline: String,
    pub(crate) detail: Option<String>,
    pub(crate) primary_button_label: Option<String>,
    pub(crate) logs_available: bool,
    pub(crate) diagnostics: OnboardingDiagnostics,
    pub(crate) last_error: Option<OnboardingLastError>,
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub(crate) struct OnboardingProgressEvent {
    pub(crate) phase: String,
    pub(crate) state: String,
    pub(crate) step_id: String,
    pub(crate) status: String,
    pub(crate) message: String,
    pub(crate) stream_chunk: Option<String>,
    pub(crate) shell_target: Option<String>,
    pub(crate) observed_path: Option<String>,
    pub(crate) error_code: Option<String>,
}

#[derive(Default)]
pub(crate) struct OnboardingRuntime {
    pub(crate) snapshot: Option<OnboardingSnapshot>,
    pub(crate) logs: String,
}

pub struct OnboardingState(pub Arc<Mutex<OnboardingRuntime>>);

#[derive(Clone, Copy, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub(crate) enum StartNativeInstallPathKind {
    NativePowershell,
    NativeCmd,
}

impl StartNativeInstallPathKind {
    pub(crate) fn as_contract_value(&self) -> &'static str {
        match self {
            Self::NativePowershell => "native-powershell",
            Self::NativeCmd => "native-cmd",
        }
    }
}

fn current_onboarding_os() -> &'static str {
    if cfg!(target_os = "macos") {
        "macos"
    } else if cfg!(target_os = "windows") {
        "windows"
    } else {
        "linux"
    }
}

pub(crate) fn contract_shell_targets(os: &str) -> Vec<String> {
    match os {
        "windows" => vec!["powershell".into(), "cmd".into(), "wsl".into()],
        "macos" => vec!["zsh".into(), "bash".into()],
        _ => vec!["bash".into()],
    }
}

fn onboarding_logs_available() -> bool {
    false
}

pub(crate) fn push_onboarding_log(runtime: &mut OnboardingRuntime, title: &str, text: &str) {
    if text.trim().is_empty() {
        return;
    }
    if !runtime.logs.is_empty() {
        runtime.logs.push_str("\n\n");
    }
    runtime.logs.push_str(title);
    runtime.logs.push_str("\n");
    runtime.logs.push_str(text.trim());
}

pub(crate) fn store_onboarding_snapshot(
    state: &Arc<Mutex<OnboardingRuntime>>,
    snapshot: &OnboardingSnapshot,
) {
    if let Ok(mut runtime) = state.lock() {
        runtime.snapshot = Some(snapshot.clone());
    }
}

pub(crate) fn build_initial_onboarding_snapshot() -> OnboardingSnapshot {
    let mut snapshot = build_onboarding_snapshot();
    snapshot.logs_available = false;
    snapshot
}

pub(crate) fn clear_onboarding_logs(state: &Arc<Mutex<OnboardingRuntime>>) {
    if let Ok(mut runtime) = state.lock() {
        runtime.logs.clear();
    }
}

pub(crate) fn append_onboarding_log(
    state: &Arc<Mutex<OnboardingRuntime>>,
    title: &str,
    text: &str,
) {
    if let Ok(mut runtime) = state.lock() {
        push_onboarding_log(&mut runtime, title, text);
    }
}

pub(crate) fn onboarding_logs_available_from_state(state: &Arc<Mutex<OnboardingRuntime>>) -> bool {
    state
        .lock()
        .ok()
        .map(|runtime| !runtime.logs.trim().is_empty())
        .unwrap_or(false)
}

pub(crate) fn build_onboarding_snapshot() -> OnboardingSnapshot {
    let os = current_onboarding_os().to_string();
    let shell_targets = contract_shell_targets(&os);
    #[cfg(target_os = "windows")]
    let git_installed = Some(check_git_installed());
    #[cfg(not(target_os = "windows"))]
    let git_installed = None;
    #[cfg(target_os = "windows")]
    let wsl_available = Some(check_wsl_available());
    #[cfg(not(target_os = "windows"))]
    let wsl_available = None;

    let (state, next_action, headline, detail, primary_button_label, last_error) =
        if os == "windows" && git_installed == Some(false) {
            (
                "needs_git".to_string(),
                "install_git".to_string(),
                "Git for Windows가 먼저 필요해요".to_string(),
                Some("Windows native Claude Code 설치를 시작하기 전에 Git for Windows를 설치한 뒤 다시 확인해야 해요.".to_string()),
                Some("Git 설치 후 다시 확인".to_string()),
                Some(OnboardingLastError {
                    code: "missing_git".to_string(),
                    summary: "Git for Windows가 설치되어 있지 않아요.".to_string(),
                    detail: Some("공식 Claude Code Windows native 설치는 Git for Windows를 전제로 해요.".to_string()),
                    suggested_action: Some("install_git".to_string()),
                }),
            )
        } else {
            (
                "ready_to_install".to_string(),
                "start_install".to_string(),
                "Claude Code 자동 설치를 시작할 수 있어요".to_string(),
                Some("공식 설치 경로를 먼저 시도하고, 실패하면 다음 성공 경로로 안내할게요.".to_string()),
                Some("자동 설치 시작".to_string()),
                None,
            )
        };

    OnboardingSnapshot {
        state,
        os,
        install_path_kind: "unknown".to_string(),
        shell_targets,
        next_action,
        headline,
        detail,
        primary_button_label,
        logs_available: onboarding_logs_available(),
        diagnostics: OnboardingDiagnostics {
            git_installed,
            wsl_available,
            claude_on_path: None,
            claude_version_ok: None,
            claude_doctor_ok: None,
            login_status_known: None,
        },
        last_error,
    }
}

pub(crate) fn emit_onboarding_progress(app: &tauri::AppHandle, event: OnboardingProgressEvent) {
    let _ = app.emit("onboarding_progress", event);
}

#[derive(Clone)]
pub(crate) struct CommandCapture {
    pub(crate) ok: bool,
    pub(crate) stdout: String,
    pub(crate) stderr: String,
    pub(crate) exit_code: i32,
}

pub(crate) fn run_command_capture(
    program: &str,
    args: &[&str],
    env_overrides: &[(&str, String)],
) -> Result<CommandCapture, String> {
    run_command_capture_with_options(program, args, env_overrides, |_, _| {}, None)
}

pub(crate) fn run_command_capture_with_timeout(
    program: &str,
    args: &[&str],
    env_overrides: &[(&str, String)],
    timeout_secs: u64,
) -> Result<CommandCapture, String> {
    run_command_capture_with_options(program, args, env_overrides, |_, _| {}, Some(timeout_secs))
}

/// cmd.output()은 프로세스 종료 전까지 stdout/stderr을 버퍼링해서
/// GUI에서는 hang 상태에 중간 로그가 보이지 않아요. 이 함수는 stdout/stderr을
/// 라인 단위로 읽으며 sink 콜백을 호출해 실시간으로 로그가 쌓이게 해요.
pub(crate) fn run_command_capture_streamed<F>(
    program: &str,
    args: &[&str],
    env_overrides: &[(&str, String)],
    sink: F,
) -> Result<CommandCapture, String>
where
    F: FnMut(&str, &str),
{
    run_command_capture_with_options(program, args, env_overrides, sink, None)
}

pub(crate) fn run_command_capture_with_options<F>(
    program: &str,
    args: &[&str],
    env_overrides: &[(&str, String)],
    mut sink: F,
    timeout_secs: Option<u64>,
) -> Result<CommandCapture, String>
where
    F: FnMut(&str, &str),
{
    use std::io::{BufRead, BufReader};
    use std::sync::mpsc;
    use std::sync::{Arc as StdArc, Mutex as StdMutex};
    use std::time::{Duration, Instant};
    let mut cmd = std::process::Command::new(program);
    cmd.args(args);
    cmd.stdin(std::process::Stdio::null());
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());
    for (key, value) in env_overrides {
        cmd.env(key, value);
    }

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    let child = cmd.spawn().map_err(|e| e.to_string())?;
    let child = StdArc::new(StdMutex::new(child));
    let stdout = child.lock().unwrap().stdout.take().ok_or_else(|| "stdout pipe missing".to_string())?;
    let stderr = child.lock().unwrap().stderr.take().ok_or_else(|| "stderr pipe missing".to_string())?;

    let (tx, rx) = mpsc::channel::<(&'static str, String)>();
    let tx_out = tx.clone();
    let out_thread = std::thread::spawn(move || {
        let reader = BufReader::new(stdout);
        let mut collected = String::new();
        for line in reader.lines().flatten() {
            let _ = tx_out.send(("stdout", line.clone()));
            collected.push_str(&line);
            collected.push('\n');
        }
        collected
    });
    let tx_err = tx.clone();
    let err_thread = std::thread::spawn(move || {
        let reader = BufReader::new(stderr);
        let mut collected = String::new();
        for line in reader.lines().flatten() {
            let _ = tx_err.send(("stderr", line.clone()));
            collected.push_str(&line);
            collected.push('\n');
        }
        collected
    });
    drop(tx);

    let deadline = timeout_secs.map(|s| Instant::now() + Duration::from_secs(s));
    let mut timed_out = false;
    loop {
        let remaining = match deadline {
            Some(d) => match d.checked_duration_since(Instant::now()) {
                Some(r) => r,
                None => {
                    timed_out = true;
                    break;
                }
            },
            None => Duration::from_secs(3600),
        };
        match rx.recv_timeout(remaining) {
            Ok((stream, line)) => {
                let title = if stream == "stdout" { "[stream stdout]" } else { "[stream stderr]" };
                sink(title, &line);
            }
            Err(mpsc::RecvTimeoutError::Disconnected) => break,
            Err(mpsc::RecvTimeoutError::Timeout) => {
                timed_out = true;
                break;
            }
        }
    }

    if timed_out {
        sink("[stream timeout]", &format!("command exceeded {}s, killing", timeout_secs.unwrap_or(0)));
        let _ = child.lock().unwrap().kill();
    }

    let stdout_text = out_thread.join().unwrap_or_default();
    let stderr_text = err_thread.join().unwrap_or_default();
    let status = child.lock().unwrap().wait().map_err(|e| e.to_string())?;
    Ok(CommandCapture {
        ok: status.success() && !timed_out,
        stdout: stdout_text,
        stderr: stderr_text,
        exit_code: status.code().unwrap_or(if timed_out { -2 } else { -1 }),
    })
}

// ─── Tauri Commands (cross-platform routers) ──────────────────────────────────

#[tauri::command]
pub fn get_onboarding_snapshot(state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
    state
        .0
        .lock()
        .ok()
        .and_then(|runtime| runtime.snapshot.clone())
        .unwrap_or_else(build_initial_onboarding_snapshot)
}

#[tauri::command]
pub fn start_native_install(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
    path_kind: StartNativeInstallPathKind,
) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        return windows::start_install(app, state, path_kind);
    }

    #[cfg(target_os = "macos")]
    {
        let _ = path_kind;
        return macos::start_install(app, state);
    }

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    {
        let _ = (app, state, path_kind);
        let mut unsupported = build_initial_onboarding_snapshot();
        unsupported.state = "blocked".to_string();
        unsupported.next_action = "none".to_string();
        unsupported.headline = "이 OS 에서는 자동 설치가 아직 지원되지 않아요".to_string();
        unsupported.last_error = Some(OnboardingLastError {
            code: "unsupported_environment".to_string(),
            summary: "현재 OS 에서는 자동 설치 runner 가 없어요.".to_string(),
            detail: None,
            suggested_action: None,
        });
        return unsupported;
    }
}

#[tauri::command]
pub fn start_wsl_install(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        return windows::start_wsl_install(app, state);
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = app;
        let mut snapshot = build_initial_onboarding_snapshot();
        snapshot.state = "blocked".to_string();
        snapshot.install_path_kind = "wsl".to_string();
        snapshot.next_action = "none".to_string();
        snapshot.headline = "이 환경에서는 WSL 트랙을 사용할 수 없어요".to_string();
        snapshot.last_error = Some(OnboardingLastError {
            code: "unsupported_environment".to_string(),
            summary: "WSL 은 Windows 전용이에요.".to_string(),
            detail: None,
            suggested_action: None,
        });
        store_onboarding_snapshot(&state.0, &snapshot);
        snapshot
    }
}

#[tauri::command]
pub fn retry_verification(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        return windows::retry_verification(app, state);
    }

    #[cfg(target_os = "macos")]
    {
        return macos::retry_verification(app, state);
    }

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    {
        let _ = (app, state);
        build_onboarding_snapshot()
    }
}

#[tauri::command]
pub fn add_claude_to_user_path(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        return windows::add_to_user_path(app, state);
    }

    #[cfg(target_os = "macos")]
    {
        return macos::add_to_user_path(app, state);
    }

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    {
        let _ = (app, state);
        build_onboarding_snapshot()
    }
}

#[tauri::command]
pub fn uninstall_claude_code(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
    track: Option<String>,
) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        return windows::uninstall(app, state, track);
    }

    #[cfg(target_os = "macos")]
    {
        let _ = track;
        return macos::uninstall(app, state);
    }

    #[cfg(all(not(target_os = "windows"), not(target_os = "macos")))]
    {
        let _ = (app, state, track);
        build_onboarding_snapshot()
    }
}

#[tauri::command]
pub fn start_login_probe(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        return windows::start_login_probe(app, state);
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = (app, state);
        build_onboarding_snapshot()
    }
}

#[tauri::command]
pub fn get_onboarding_logs(state: tauri::State<OnboardingState>) -> serde_json::Value {
    let text = state
        .0
        .lock()
        .ok()
        .map(|runtime| runtime.logs.clone())
        .unwrap_or_default();
    serde_json::json!({ "text": text })
}

#[tauri::command]
pub fn check_git_installed() -> bool {
    // 1. PATH에서 git 시도
    let mut probe = std::process::Command::new("git");
    probe.arg("--version");
    hide_console(&mut probe);
    if probe.output().map(|o| o.status.success()).unwrap_or(false) {
        return true;
    }
    // 2. Windows 기본 설치 경로 직접 확인
    #[cfg(target_os = "windows")]
    {
        let candidates = [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (Arm)\Git\cmd\git.exe",
        ];
        for path in &candidates {
            if std::path::Path::new(path).exists() {
                return true;
            }
        }
    }
    false
}

#[tauri::command]
pub fn check_wsl_available() -> bool {
    #[cfg(target_os = "windows")]
    {
        return windows::check_wsl_available();
    }
    #[cfg(not(target_os = "windows"))]
    {
        false
    }
}

#[tauri::command]
pub fn check_xcode_clt() -> bool {
    #[cfg(target_os = "macos")]
    {
        return macos::check_xcode_clt();
    }
    #[cfg(not(target_os = "macos"))]
    {
        true
    }
}

// ─── console hiding (for check_git_installed) ─────────────────────────────────

#[cfg(target_os = "windows")]
fn hide_console(cmd: &mut std::process::Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(target_os = "windows"))]
fn hide_console(_cmd: &mut std::process::Command) {}

// ─── testing shim ────────────────────────────────────────────────────────────
// Integration tests (`tests/*.rs`) compile the library without `cfg(test)`,
// so the shim can't be gated with `#[cfg(test)]`. It's a thin wrapper that
// adds zero runtime cost when unused.
pub mod testing {
    use super::{run_command_capture_streamed, CommandCapture};

    pub struct CommandCaptureForTest {
        pub ok: bool,
        pub stdout: String,
        pub stderr: String,
        pub exit_code: i32,
    }

    impl From<CommandCapture> for CommandCaptureForTest {
        fn from(c: CommandCapture) -> Self {
            Self {
                ok: c.ok,
                stdout: c.stdout,
                stderr: c.stderr,
                exit_code: c.exit_code,
            }
        }
    }

    pub fn run_command_capture_streamed_for_test<F>(
        program: &str,
        args: &[&str],
        env_overrides: &[(&str, String)],
        sink: F,
    ) -> Result<CommandCaptureForTest, String>
    where
        F: FnMut(&str, &str),
    {
        run_command_capture_streamed(program, args, env_overrides, sink).map(Into::into)
    }

    #[cfg(target_os = "macos")]
    pub fn ensure_macos_path_marker_at(
        home: &std::path::Path,
    ) -> Result<Vec<std::path::PathBuf>, String> {
        super::macos::ensure_macos_path_marker_in_home(home)
    }

    #[cfg(target_os = "macos")]
    pub fn check_xcode_clt_for_test() -> bool {
        super::macos::check_xcode_clt()
    }

    #[cfg(target_os = "macos")]
    pub fn uninstall_macos_track_at(home: &std::path::Path) -> Result<(), String> {
        super::macos::uninstall_macos_track_in_home(home)
    }
}
