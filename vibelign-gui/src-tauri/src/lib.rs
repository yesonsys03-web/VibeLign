// === ANCHOR: LIB_START ===
mod vib_path;

use std::collections::HashMap;
use std::collections::VecDeque;
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::Emitter;

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
struct OnboardingLastError {
    code: String,
    summary: String,
    detail: Option<String>,
    suggested_action: Option<String>,
}

#[derive(Serialize, Clone, Default)]
#[serde(rename_all = "camelCase")]
struct OnboardingDiagnostics {
    git_installed: Option<bool>,
    wsl_available: Option<bool>,
    claude_on_path: Option<bool>,
    claude_version_ok: Option<bool>,
    claude_doctor_ok: Option<bool>,
    login_status_known: Option<bool>,
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
struct OnboardingSnapshot {
    state: String,
    os: String,
    install_path_kind: String,
    shell_targets: Vec<String>,
    next_action: String,
    headline: String,
    detail: Option<String>,
    primary_button_label: Option<String>,
    logs_available: bool,
    diagnostics: OnboardingDiagnostics,
    last_error: Option<OnboardingLastError>,
}

#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
struct OnboardingProgressEvent {
    phase: String,
    state: String,
    step_id: String,
    status: String,
    message: String,
    stream_chunk: Option<String>,
    shell_target: Option<String>,
    observed_path: Option<String>,
    error_code: Option<String>,
}

#[derive(Default)]
struct OnboardingRuntime {
    snapshot: Option<OnboardingSnapshot>,
    logs: String,
}

struct OnboardingState(Arc<Mutex<OnboardingRuntime>>);

#[derive(Clone, Copy, Deserialize)]
#[serde(rename_all = "kebab-case")]
enum StartNativeInstallPathKind {
    NativePowershell,
    NativeCmd,
}

impl StartNativeInstallPathKind {
    fn as_contract_value(&self) -> &'static str {
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

fn contract_shell_targets(os: &str) -> Vec<String> {
    match os {
        "windows" => vec!["powershell".into(), "cmd".into(), "wsl".into()],
        "macos" => vec!["zsh".into(), "bash".into()],
        _ => vec!["bash".into()],
    }
}

fn onboarding_logs_available() -> bool {
    false
}

#[cfg(target_os = "windows")]
fn push_onboarding_log(runtime: &mut OnboardingRuntime, title: &str, text: &str) {
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

fn store_onboarding_snapshot(state: &Arc<Mutex<OnboardingRuntime>>, snapshot: &OnboardingSnapshot) {
    if let Ok(mut runtime) = state.lock() {
        runtime.snapshot = Some(snapshot.clone());
    }
}

fn build_initial_onboarding_snapshot() -> OnboardingSnapshot {
    let mut snapshot = build_onboarding_snapshot();
    snapshot.logs_available = false;
    snapshot
}

#[cfg(target_os = "windows")]
fn clear_onboarding_logs(state: &Arc<Mutex<OnboardingRuntime>>) {
    if let Ok(mut runtime) = state.lock() {
        runtime.logs.clear();
    }
}

#[cfg(target_os = "windows")]
fn append_onboarding_log(state: &Arc<Mutex<OnboardingRuntime>>, title: &str, text: &str) {
    if let Ok(mut runtime) = state.lock() {
        push_onboarding_log(&mut runtime, title, text);
    }
}

#[cfg(target_os = "windows")]
fn onboarding_logs_available_from_state(state: &Arc<Mutex<OnboardingRuntime>>) -> bool {
    state
        .lock()
        .ok()
        .map(|runtime| !runtime.logs.trim().is_empty())
        .unwrap_or(false)
}

fn build_onboarding_snapshot() -> OnboardingSnapshot {
    let os = current_onboarding_os().to_string();
    let shell_targets = contract_shell_targets(&os);
    #[cfg(target_os = "windows")]
    let git_installed = Some(check_git_installed());
    #[cfg(not(target_os = "windows"))]
    let git_installed = None;

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
            wsl_available: None,
            claude_on_path: None,
            claude_version_ok: None,
            claude_doctor_ok: None,
            login_status_known: None,
        },
        last_error,
    }
}

fn emit_onboarding_progress(app: &tauri::AppHandle, event: OnboardingProgressEvent) {
    let _ = app.emit("onboarding_progress", event);
}

#[cfg(target_os = "windows")]
#[derive(Clone)]
struct CommandCapture {
    ok: bool,
    stdout: String,
    stderr: String,
    exit_code: i32,
}

#[cfg(target_os = "windows")]
fn run_command_capture(
    program: &str,
    args: &[&str],
    env_overrides: &[(&str, String)],
) -> Result<CommandCapture, String> {
    run_command_capture_with_options(program, args, env_overrides, |_, _| {}, None)
}

#[cfg(target_os = "windows")]
fn run_command_capture_with_timeout(
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
#[cfg(target_os = "windows")]
fn run_command_capture_streamed<F>(
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

#[cfg(target_os = "windows")]
fn run_command_capture_with_options<F>(
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

#[cfg(target_os = "windows")]
fn read_windows_user_path() -> Option<String> {
    let output = run_command_capture("reg", &["query", r"HKCU\Environment", "/v", "Path"], &[]).ok()?;
    if !output.ok {
        return None;
    }
    output.stdout.lines().find_map(|line| {
        let marker = line.find("REG_")?;
        let after_marker = &line[marker..];
        let value_start = after_marker.find(char::is_whitespace)?;
        let value = after_marker[value_start..].trim();
        if value.is_empty() {
            return None;
        }
        Some(value.to_string())
    })
}

#[cfg(target_os = "windows")]
fn merge_windows_path() -> Option<String> {
    let current = std::env::var("PATH").ok().unwrap_or_default();
    let user = read_windows_user_path().unwrap_or_default();
    if user.is_empty() {
        return if current.is_empty() { None } else { Some(current) };
    }
    if current.is_empty() {
        return Some(user);
    }
    Some(format!("{};{}", current, user))
}

#[cfg(target_os = "windows")]
fn windows_user_profile() -> Option<PathBuf> {
    std::env::var("USERPROFILE").ok().map(PathBuf::from)
}

#[cfg(target_os = "windows")]
fn windows_placeholder_artifact() -> Option<PathBuf> {
    windows_user_profile().map(|p| p.join("claude"))
}

#[cfg(target_os = "windows")]
fn windows_placeholder_artifact_exists() -> bool {
    let Some(path) = windows_placeholder_artifact() else {
        return false;
    };
    std::fs::metadata(path).map(|m| m.is_file() && m.len() == 0).unwrap_or(false)
}

#[cfg(target_os = "windows")]
fn windows_expected_claude_path() -> Option<PathBuf> {
    windows_user_profile().map(|p| p.join(".local").join("bin").join("claude.exe"))
}

#[cfg(target_os = "windows")]
fn windows_expected_claude_exists() -> bool {
    windows_expected_claude_path()
        .map(|path| path.exists())
        .unwrap_or(false)
}

#[cfg(target_os = "windows")]
fn verify_windows_shells(state: &Arc<Mutex<OnboardingRuntime>>, app: &tauri::AppHandle, install_path_kind: &str) -> OnboardingSnapshot {
    let mut snapshot = build_onboarding_snapshot();
    snapshot.state = "verifying_shells".to_string();
    snapshot.install_path_kind = install_path_kind.to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "새 셸에서 Claude 설치를 검증하는 중이에요".to_string();
    snapshot.detail = Some("PowerShell과 CMD에서 `claude` 실행 가능 여부를 확인하고 있어요.".to_string());
    snapshot.primary_button_label = None;
    snapshot.logs_available = onboarding_logs_available_from_state(state);
    emit_onboarding_progress(app, OnboardingProgressEvent {
        phase: "verify".to_string(),
        state: snapshot.state.clone(),
        step_id: "verify_version".to_string(),
        status: "started".to_string(),
        message: "새 셸에서 `claude --version` 과 `claude doctor` 를 확인하는 중이에요.".to_string(),
        stream_chunk: None,
        shell_target: None,
        observed_path: None,
        error_code: None,
    });

    let merged_path = merge_windows_path();
    let env_overrides: Vec<(&str, String)> = merged_path.clone().map(|p| vec![("PATH", p)]).unwrap_or_default();

    append_onboarding_log(state, "[verify] running", "cmd /C where.exe claude");
    let where_result = run_command_capture("cmd", &["/C", "where.exe claude"], &env_overrides).ok();
    if let Some(result) = &where_result {
        append_onboarding_log(state, "[verify where.exe claude stdout]", &result.stdout);
        append_onboarding_log(state, "[verify where.exe claude stderr]", &result.stderr);
    } else {
        append_onboarding_log(state, "[verify where.exe claude]", "spawn error");
    }
    let claude_on_path = where_result.as_ref().map(|r| r.ok && !r.stdout.trim().is_empty()).unwrap_or(false);
    let observed_path = where_result
        .as_ref()
        .and_then(|r| r.stdout.lines().next())
        .map(|s| s.trim().to_string())
        .or_else(|| windows_expected_claude_path().map(|p| p.to_string_lossy().to_string()));

    append_onboarding_log(state, "[verify] running", "cmd /C claude --version");
    let cmd_version = run_command_capture("cmd", &["/C", "claude --version"], &env_overrides).ok();
    if let Some(result) = &cmd_version {
        append_onboarding_log(state, "[verify cmd claude --version stdout]", &result.stdout);
        append_onboarding_log(state, "[verify cmd claude --version stderr]", &result.stderr);
    } else {
        append_onboarding_log(state, "[verify cmd claude --version]", "spawn error");
    }
    append_onboarding_log(state, "[verify] running", "powershell claude --version");
    let ps_version = run_command_capture("powershell", &["-NoProfile", "-Command", "claude --version"], &env_overrides).ok();
    if let Some(result) = &ps_version {
        append_onboarding_log(state, "[verify powershell claude --version stdout]", &result.stdout);
        append_onboarding_log(state, "[verify powershell claude --version stderr]", &result.stderr);
    } else {
        append_onboarding_log(state, "[verify powershell claude --version]", "spawn error");
    }
    append_onboarding_log(state, "[verify] running", "cmd /C claude doctor (timeout 20s)");
    let doctor_result = run_command_capture_with_timeout("cmd", &["/C", "claude doctor"], &env_overrides, 20).ok();
    if let Some(result) = &doctor_result {
        append_onboarding_log(state, "[verify claude doctor stdout]", &result.stdout);
        append_onboarding_log(state, "[verify claude doctor stderr]", &result.stderr);
    } else {
        append_onboarding_log(state, "[verify claude doctor]", "spawn error");
    }

    let direct_version = windows_expected_claude_path().and_then(|path| {
        let path_str = path.to_string_lossy().to_string();
        append_onboarding_log(state, "[verify] running direct", &format!("{} --version (timeout 15s)", path_str));
        run_command_capture_with_timeout(&path_str, &["--version"], &[], 15).ok().map(|result| (path_str, result))
    });
    if let Some((_, result)) = &direct_version {
        append_onboarding_log(state, "[verify direct claude.exe --version stdout]", &result.stdout);
        append_onboarding_log(state, "[verify direct claude.exe --version stderr]", &result.stderr);
    }

    let direct_doctor = windows_expected_claude_path().and_then(|path| {
        let path_str = path.to_string_lossy().to_string();
        append_onboarding_log(state, "[verify] running direct", &format!("{} doctor (timeout 20s)", path_str));
        run_command_capture_with_timeout(&path_str, &["doctor"], &[], 20).ok().map(|result| (path_str, result))
    });
    if let Some((_, result)) = &direct_doctor {
        append_onboarding_log(state, "[verify direct claude.exe doctor stdout]", &result.stdout);
        append_onboarding_log(state, "[verify direct claude.exe doctor stderr]", &result.stderr);
    }

    let claude_version_ok = cmd_version.as_ref().map(|r| r.ok).unwrap_or(false)
        || ps_version.as_ref().map(|r| r.ok).unwrap_or(false);
    let claude_doctor_ok = doctor_result.as_ref().map(|r| r.ok).unwrap_or(false);
    let direct_version_ok = direct_version.as_ref().map(|(_, r)| r.ok).unwrap_or(false);
    let direct_doctor_ok = direct_doctor.as_ref().map(|(_, r)| r.ok).unwrap_or(false);

    snapshot.logs_available = onboarding_logs_available_from_state(state);
    snapshot.diagnostics.git_installed = Some(check_git_installed());
    snapshot.diagnostics.wsl_available = None;
    snapshot.diagnostics.claude_on_path = Some(claude_on_path);
    snapshot.diagnostics.claude_version_ok = Some(claude_version_ok);
    snapshot.diagnostics.claude_doctor_ok = Some(claude_doctor_ok);
    snapshot.diagnostics.login_status_known = Some(false);

    // doctor 는 interactive prompt 대기로 종종 hang/timeout 되므로,
    // 직접 --version 만 통과해도 설치 성공 + PATH 미설정 으로 분류한다.
    let _ = direct_doctor_ok;
    if !claude_on_path && windows_expected_claude_exists() && direct_version_ok {
        let install_path = windows_expected_claude_path()
            .map(|path| path.to_string_lossy().to_string())
            .unwrap_or_else(|| "C:\\Users\\<user>\\.local\\bin\\claude.exe".to_string());
        let path_dir = windows_expected_claude_path()
            .and_then(|path| path.parent().map(|dir| dir.to_string_lossy().to_string()))
            .unwrap_or_else(|| "C:\\Users\\<user>\\.local\\bin".to_string());
        snapshot.state = "needs_manual_step".to_string();
        snapshot.next_action = "add_to_path".to_string();
        snapshot.headline = "Claude는 설치됐지만 PATH 연결이 아직 안 됐어요".to_string();
        snapshot.detail = Some(format!(
            "설치 자체는 성공했고 `{}` 직접 실행도 통과했어요. `{}` 을 사용자 PATH 에 자동으로 추가해 드릴게요.",
            install_path, path_dir
        ));
        snapshot.primary_button_label = Some("PATH 자동 추가".to_string());
        snapshot.last_error = Some(OnboardingLastError {
            code: "path_not_configured".to_string(),
            summary: "Claude Code는 설치됐지만 새 셸 PATH에는 아직 잡히지 않았어요.".to_string(),
            detail: Some(path_dir.clone()),
            suggested_action: Some("open_manual_steps".to_string()),
        });
        store_onboarding_snapshot(state, &snapshot);
        emit_onboarding_progress(app, OnboardingProgressEvent {
            phase: "verify".to_string(),
            state: snapshot.state.clone(),
            step_id: "verify_doctor".to_string(),
            status: "failed".to_string(),
            message: "설치는 성공했지만 PATH 미설정 상태로 분류했어요.".to_string(),
            stream_chunk: None,
            shell_target: None,
            observed_path: Some(install_path),
            error_code: Some("path_not_configured".to_string()),
        });
        return snapshot;
    }

    if windows_placeholder_artifact_exists() {
        snapshot.state = "needs_manual_step".to_string();
        snapshot.next_action = "none".to_string();
        snapshot.headline = "설치가 비정상 placeholder 파일을 남겼어요".to_string();
        snapshot.detail = Some("0-byte `claude` artifact 가 감지되어 자동 설치를 신뢰할 수 없어요. 더 큰 Windows 환경이나 수동 정리 후 재시도가 필요해요.".to_string());
        snapshot.last_error = Some(OnboardingLastError {
            code: "placeholder_artifact".to_string(),
            summary: "`claude` 실행 파일 대신 0-byte placeholder artifact 가 남았어요.".to_string(),
            detail: windows_placeholder_artifact().map(|p| p.to_string_lossy().to_string()),
            suggested_action: None,
        });
        store_onboarding_snapshot(state, &snapshot);
        emit_onboarding_progress(app, OnboardingProgressEvent {
            phase: "verify".to_string(),
            state: snapshot.state.clone(),
            step_id: "verify_version".to_string(),
            status: "failed".to_string(),
            message: "0-byte placeholder artifact 가 감지되어 설치를 실패로 분류했어요.".to_string(),
            stream_chunk: None,
            shell_target: None,
            observed_path,
            error_code: Some("placeholder_artifact".to_string()),
        });
        return snapshot;
    }

    if claude_on_path && claude_version_ok && claude_doctor_ok {
        snapshot.state = "login_required".to_string();
        snapshot.next_action = "start_login".to_string();
        snapshot.headline = "Claude Code 설치 검증이 끝났어요".to_string();
        snapshot.detail = Some("새 셸에서 `claude --version` 과 `claude doctor` 가 통과했어요. 이제 로그인만 하면 돼요.".to_string());
        snapshot.primary_button_label = Some("로그인 확인 시작".to_string());
        store_onboarding_snapshot(state, &snapshot);
        emit_onboarding_progress(app, OnboardingProgressEvent {
            phase: "verify".to_string(),
            state: snapshot.state.clone(),
            step_id: "verify_doctor".to_string(),
            status: "succeeded".to_string(),
            message: "새 셸 검증이 통과했어요.".to_string(),
            stream_chunk: None,
            shell_target: None,
            observed_path,
            error_code: None,
        });
        return snapshot;
    }

    let doctor_failed = !claude_doctor_ok;
    snapshot.state = if !claude_on_path || !claude_version_ok {
        "needs_cmd_fallback".to_string()
    } else {
        "needs_manual_step".to_string()
    };
    snapshot.next_action = if snapshot.state == "needs_cmd_fallback" {
        "retry_with_cmd".to_string()
    } else {
        "none".to_string()
    };
    snapshot.headline = if snapshot.state == "needs_cmd_fallback" {
        "PowerShell 경로 검증이 불안정했어요".to_string()
    } else {
        "설치 검증이 완전히 통과하지 않았어요".to_string()
    };
    snapshot.detail = Some(if doctor_failed {
        "`claude --version` 또는 `claude doctor` 가 새 셸에서 실패했어요. 자동 설치 성공 문자열만으로는 완료 처리하지 않아요.".to_string()
    } else {
        "새 셸에서 `claude` 실행 가능 여부를 확인하지 못했어요. CMD fallback 이나 수동 점검이 필요해요.".to_string()
    });
    snapshot.primary_button_label = if snapshot.state == "needs_cmd_fallback" {
        Some("CMD로 다시 시도".to_string())
    } else {
        None
    };
    snapshot.last_error = Some(OnboardingLastError {
        code: "installer_false_success".to_string(),
        summary: "설치 스크립트가 끝났지만 새 셸 검증은 통과하지 못했어요.".to_string(),
        detail: Some(format!(
            "claudeOnPath={}, claudeVersionOk={}, claudeDoctorOk={}",
            claude_on_path, claude_version_ok, claude_doctor_ok
        )),
        suggested_action: if snapshot.state == "needs_cmd_fallback" {
            Some("retry_with_cmd".to_string())
        } else {
            None
        },
    });
    store_onboarding_snapshot(state, &snapshot);
    emit_onboarding_progress(app, OnboardingProgressEvent {
        phase: "verify".to_string(),
        state: snapshot.state.clone(),
        step_id: if doctor_failed { "verify_doctor".to_string() } else { "verify_version".to_string() },
        status: "failed".to_string(),
        message: "새 셸 검증이 실패해 설치를 false-success 로 분류했어요.".to_string(),
        stream_chunk: None,
        shell_target: None,
        observed_path,
        error_code: Some("installer_false_success".to_string()),
    });
    snapshot
}

#[cfg(not(target_os = "windows"))]
fn verify_windows_shells(_state: &Arc<Mutex<OnboardingRuntime>>, _app: &tauri::AppHandle, _install_path_kind: &str) -> OnboardingSnapshot {
    let mut snapshot = build_onboarding_snapshot();
    snapshot.state = "blocked".to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "이 구현 slice는 Windows native 설치 전용이에요".to_string();
    snapshot.detail = Some("macOS/Linux onboarding install execution 은 다음 단계에서 별도로 연결합니다.".to_string());
    snapshot.last_error = Some(OnboardingLastError {
        code: "unsupported_environment".to_string(),
        summary: "현재 환경에서는 Windows native install runner 를 실행할 수 없어요.".to_string(),
        detail: None,
        suggested_action: None,
    });
    snapshot
}

// ─── 폴더 열기 ────────────────────────────────────────────────────────────────

#[tauri::command]
fn open_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    std::process::Command::new("open")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    #[cfg(target_os = "windows")]
    std::process::Command::new("explorer")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    #[cfg(target_os = "linux")]
    std::process::Command::new("xdg-open")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    Ok(())
}

#[derive(Serialize)]
struct ReadFileResult {
    path: String,
    content: String,
    source_hash: String,
}

#[derive(Serialize, Deserialize)]
struct DocsIndexEntry {
    category: String,
    path: String,
    title: String,
    modified_at_ms: i64,
}

#[derive(Serialize, Deserialize)]
struct DocsVisualContract {
    schema_version: i64,
    generator_version: String,
}

#[derive(Serialize)]
struct DocsVisualReadResult {
    path: String,
    artifact: serde_json::Value,
    contract: DocsVisualContract,
}

fn normalize_markdown_content(bytes: &[u8]) -> Result<String, String> {
    let bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(bytes);
    let text = std::str::from_utf8(bytes)
        .map_err(|_| "UTF-8 markdown 파일만 읽을 수 있어요".to_string())?;
    Ok(text.replace("\r\n", "\n").replace('\r', "\n"))
}

fn hash_markdown_content(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn normalize_relative_doc_path(path: &std::path::Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

fn is_allowed_doc_path(relative_path: &str) -> bool {
    let lower = relative_path.to_ascii_lowercase();
    if !lower.ends_with(".md") && !lower.ends_with(".markdown") {
        return false;
    }
    // 경로 탈출 차단
    if relative_path.contains("..") {
        return false;
    }
    // docs/ 하위 markdown 전부 허용
    if relative_path.starts_with("docs/") {
        return true;
    }
    // 루트 직속 .md 허용 (서브디렉터리 X)
    !relative_path.contains('/')
}

fn resolve_doc_path(root: &str, path: PathBuf) -> Result<(PathBuf, String), String> {
    let root_path = PathBuf::from(root)
        .canonicalize()
        .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?;
    let joined = if path.is_absolute() {
        path
    } else {
        root_path.join(path)
    };
    let canonical = joined
        .canonicalize()
        .map_err(|e| format!("문서를 찾을 수 없어요: {e}"))?;
    let relative = canonical
        .strip_prefix(&root_path)
        .map_err(|_| "프로젝트 루트 밖 파일은 읽을 수 없어요".to_string())?;
    let relative_path = normalize_relative_doc_path(relative);
    if !is_allowed_doc_path(&relative_path) {
        return Err("허용된 markdown 문서만 읽을 수 있어요".into());
    }
    Ok((canonical, relative_path))
}

#[tauri::command]
fn read_file(root: String, path: PathBuf) -> Result<ReadFileResult, String> {
    let (resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    let bytes = std::fs::read(&resolved_path).map_err(|e| format!("문서를 읽을 수 없어요: {e}"))?;
    let content = normalize_markdown_content(&bytes)?;
    Ok(ReadFileResult {
        path: relative_path,
        source_hash: hash_markdown_content(&content),
        content,
    })
}

/// Windows `canonicalize()` 가 반환하는 `\\?\` 접두사를 벗겨서
/// 외부 프로세스가 경로를 올바르게 해석하도록 한다.
fn strip_unc_prefix(p: PathBuf) -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        let s = p.to_string_lossy();
        if let Some(stripped) = s.strip_prefix(r"\\?\") {
            return PathBuf::from(stripped);
        }
    }
    p
}

/// `vib docs-index` 명령으로 docs index/visual contract를 받는다.
/// vib sidecar에는 vibelign 패키지가 self-contained 되어 있어 별도 Python 환경이 없어도 동작한다.
fn run_vib_docs_index(root: &Path, extra_args: &[&str]) -> Option<Result<String, String>> {
    let vib = vib_path::find_vib()?;
    let mut command = std::process::Command::new(&vib);
    command.arg("docs-index");
    // 기존 호출자가 넘기던 `--print-visual-contract` 를 새 CLI 플래그로 변환.
    let mut visual_contract = false;
    for arg in extra_args {
        if *arg == "--print-visual-contract" {
            visual_contract = true;
        }
    }
    if visual_contract {
        command.arg("--visual-contract");
    } else {
        command.arg(root.as_os_str());
    }
    command
        .current_dir(root)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8");

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    match command.output() {
        Ok(output) if output.status.success() => {
            Some(Ok(String::from_utf8_lossy(&output.stdout).into_owned()))
        }
        Ok(output) => {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
            let msg = if !stderr.is_empty() { stderr } else if !stdout.is_empty() { stdout } else { "vib docs-index 실행 실패".into() };
            Some(Err(format!("[vib docs-index] {msg}")))
        }
        Err(err) => Some(Err(format!("[vib docs-index] 실행 실패: {err}"))),
    }
}

fn run_docs_cache_helper(root: &str, extra_args: &[&str]) -> Result<String, String> {
    let root_path = strip_unc_prefix(
        PathBuf::from(root)
            .canonicalize()
            .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?,
    );

    match run_vib_docs_index(&root_path, extra_args) {
        Some(Ok(s)) => Ok(s),
        Some(Err(e)) => Err(format!(
            "{e}\n\nvib이 오래된 버전일 수 있어요. GUI를 재설치해 주세요."
        )),
        None => Err("vib을 찾을 수 없어요. GUI를 재설치해 주세요.".into()),
    }
}

#[tauri::command]
fn list_docs_index(root: String) -> Result<Vec<DocsIndexEntry>, String> {
    let raw = run_docs_cache_helper(&root, &[])?;
    serde_json::from_str::<Vec<DocsIndexEntry>>(raw.trim())
        .map_err(|e| format!("docs index 결과를 해석할 수 없어요: {e}"))
}

fn read_docs_visual_contract(root: &str) -> Result<DocsVisualContract, String> {
    let raw = run_docs_cache_helper(root, &["--print-visual-contract"])?;
    let payload: serde_json::Value = serde_json::from_str(raw.trim())
        .map_err(|e| format!("docs visual contract를 해석할 수 없어요: {e}"))?;
    let contract = payload
        .get("contract")
        .ok_or_else(|| "docs visual contract 항목이 없어요".to_string())?
        .clone();
    serde_json::from_value::<DocsVisualContract>(contract)
        .map_err(|e| format!("docs visual contract 형식이 올바르지 않아요: {e}"))
}

#[tauri::command]
fn read_docs_visual(root: String, path: PathBuf) -> Result<Option<DocsVisualReadResult>, String> {
    let (resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    let root_path = PathBuf::from(&root)
        .canonicalize()
        .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?;
    let relative = resolved_path
        .strip_prefix(&root_path)
        .map_err(|_| "프로젝트 루트 밖 파일은 읽을 수 없어요".to_string())?;
    let artifact_path = root_path
        .join(".vibelign")
        .join("docs_visual")
        .join(format!("{}.json", normalize_relative_doc_path(relative)));

    if !artifact_path.exists() {
        return Ok(None);
    }

    let artifact_text = std::fs::read_to_string(&artifact_path)
        .map_err(|e| format!("docs visual artifact를 읽을 수 없어요: {e}"))?;
    let artifact: serde_json::Value = serde_json::from_str(&artifact_text)
        .map_err(|e| format!("docs visual artifact JSON이 손상되었어요: {e}"))?;
    let contract = read_docs_visual_contract(&root)?;

    Ok(Some(DocsVisualReadResult {
        path: relative_path,
        artifact,
        contract,
    }))
}

// ─── Watch 프로세스 State ──────────────────────────────────────────────────────

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

struct WatchState(Arc<Mutex<WatchRuntime>>);

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
fn start_watch(app: tauri::AppHandle, state: tauri::State<WatchState>, cwd: String) -> Result<(), String> {
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
fn stop_watch(state: tauri::State<WatchState>) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.child.take() {
        kill_watch_child(&mut child);
    }
    Ok(())
}

#[tauri::command]
fn watch_status(state: tauri::State<WatchState>) -> bool {
    state.0.lock()
        .map(|g| g.child.is_some())
        .unwrap_or(false)
}

#[tauri::command]
fn get_watch_logs(state: tauri::State<WatchState>) -> Vec<String> {
    state
        .0
        .lock()
        .map(|g| g.logs.iter().cloned().collect())
        .unwrap_or_default()
}

#[tauri::command]
fn get_watch_errors(state: tauri::State<WatchState>) -> Vec<String> {
    state
        .0
        .lock()
        .map(|g| g.errors.iter().cloned().collect())
        .unwrap_or_default()
}

// ─── 타입 정의 ─────────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub struct VibResult {
    pub ok: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

// ─── Tauri Commands ────────────────────────────────────────────────────────────

/// vib 실행 파일 경로를 반환한다. 없으면 None.
#[tauri::command]
fn get_vib_path() -> Option<String> {
    vib_path::find_vib().map(|p| p.to_string_lossy().into_owned())
}

/// vib CLI를 터미널 PATH에 설치한다 (앱 시작 시 자동 호출).
#[tauri::command]
fn setup_cli_path() -> Result<String, String> {
    vib_path::install_cli_to_path()
}

#[tauri::command]
fn get_onboarding_snapshot(state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
    state
        .0
        .lock()
        .ok()
        .and_then(|runtime| runtime.snapshot.clone())
        .unwrap_or_else(build_initial_onboarding_snapshot)
}

#[tauri::command]
fn start_native_install(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
    path_kind: StartNativeInstallPathKind,
) -> OnboardingSnapshot {
    let mut snapshot = build_initial_onboarding_snapshot();
    snapshot.state = "installing_native".to_string();
    snapshot.install_path_kind = path_kind.as_contract_value().to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "Claude Code 설치를 시작하는 중이에요".to_string();
    snapshot.detail = Some("공식 설치 스크립트를 실행한 뒤 새 셸에서 바로 검증합니다.".to_string());
    snapshot.primary_button_label = None;
    store_onboarding_snapshot(&state.0, &snapshot);

    let step_id = match path_kind {
        StartNativeInstallPathKind::NativePowershell => "run_powershell_installer",
        StartNativeInstallPathKind::NativeCmd => "run_cmd_installer",
    };
    let shell_target = match path_kind {
        StartNativeInstallPathKind::NativePowershell => Some("powershell".to_string()),
        StartNativeInstallPathKind::NativeCmd => Some("cmd".to_string()),
    };

    emit_onboarding_progress(&app, OnboardingProgressEvent {
        phase: "install".to_string(),
        state: snapshot.state.clone(),
        step_id: step_id.to_string(),
        status: "started".to_string(),
        message: "공식 설치 스크립트를 실행하는 중이에요.".to_string(),
        stream_chunk: None,
        shell_target: shell_target.clone(),
        observed_path: None,
        error_code: None,
    });

    #[cfg(not(target_os = "windows"))]
    {
        let mut unsupported = build_initial_onboarding_snapshot();
        unsupported.state = "blocked".to_string();
        unsupported.install_path_kind = path_kind.as_contract_value().to_string();
        unsupported.next_action = "none".to_string();
        unsupported.headline = "이 구현 slice는 Windows native install 전용이에요".to_string();
        unsupported.detail = Some("macOS/Linux install execution 은 다음 slice 에서 연결합니다.".to_string());
        unsupported.primary_button_label = None;
        unsupported.last_error = Some(OnboardingLastError {
            code: "unsupported_environment".to_string(),
            summary: "현재 OS 에서는 Windows native install 경로를 실행할 수 없어요.".to_string(),
            detail: None,
            suggested_action: None,
        });
        store_onboarding_snapshot(&state.0, &unsupported);
        return unsupported;
    }

    #[cfg(target_os = "windows")]
    {
        if !check_git_installed() {
            let missing = build_initial_onboarding_snapshot();
            store_onboarding_snapshot(&state.0, &missing);
            return missing;
        }

        let state_arc = Arc::clone(&state.0);
        let app_handle = app.clone();
        std::thread::spawn(move || {
            clear_onboarding_logs(&state_arc);
            let env_overrides: Vec<(&str, String)> = merge_windows_path().map(|p| vec![("PATH", p)]).unwrap_or_default();
            let installer = match path_kind {
                StartNativeInstallPathKind::NativePowershell => {
                    append_onboarding_log(&state_arc, "[installer] running", "powershell -NoProfile -Command irm https://claude.ai/install.ps1 | iex");
                    let state_for_sink = Arc::clone(&state_arc);
                    run_command_capture_streamed(
                        "powershell",
                        &["-NoProfile", "-Command", "irm https://claude.ai/install.ps1 | iex"],
                        &env_overrides,
                        |title, line| append_onboarding_log(&state_for_sink, title, line),
                    )
                }
                StartNativeInstallPathKind::NativeCmd => {
                    append_onboarding_log(&state_arc, "[installer] running", "cmd /C curl -fsSL https://claude.ai/install.cmd -o %TEMP%\\vibelign-claude-install.cmd && %TEMP%\\vibelign-claude-install.cmd");
                    let state_for_sink = Arc::clone(&state_arc);
                    run_command_capture_streamed(
                        "cmd",
                        &[
                            "/C",
                            "curl -fsSL https://claude.ai/install.cmd -o \"%TEMP%\\vibelign-claude-install.cmd\" && \"%TEMP%\\vibelign-claude-install.cmd\" && del \"%TEMP%\\vibelign-claude-install.cmd\"",
                        ],
                        &env_overrides,
                        |title, line| append_onboarding_log(&state_for_sink, title, line),
                    )
                }
            };

            let final_snapshot = match installer {
                Ok(result) => {
                    append_onboarding_log(&state_arc, "[installer stdout]", &result.stdout);
                    append_onboarding_log(&state_arc, "[installer stderr]", &result.stderr);
                    let combined = format!("{}\n{}", result.stdout, result.stderr).to_ascii_lowercase();
                    if combined.contains("out of memory") || combined.contains("bun has run out of memory") {
                        let mut failed = build_initial_onboarding_snapshot();
                        failed.state = "needs_manual_step".to_string();
                        failed.install_path_kind = path_kind.as_contract_value().to_string();
                        failed.next_action = "none".to_string();
                        failed.headline = "Windows 설치가 메모리 부족으로 중단됐어요".to_string();
                        failed.detail = Some("Bun out-of-memory 가 감지되어 이 장비에서는 native install 을 신뢰할 수 없어요. 더 큰 VM 이나 다른 Windows 환경에서 다시 시도해야 해요.".to_string());
                        failed.primary_button_label = None;
                        failed.logs_available = onboarding_logs_available_from_state(&state_arc);
                    failed.last_error = Some(OnboardingLastError {
                        code: "installer_oom".to_string(),
                        summary: "설치 중 Bun out-of-memory 가 발생했어요.".to_string(),
                        detail: Some(format!("exit_code={}", result.exit_code)),
                        suggested_action: None,
                    });
                    store_onboarding_snapshot(&state_arc, &failed);
                    emit_onboarding_progress(&app_handle, OnboardingProgressEvent {
                            phase: "install".to_string(),
                            state: failed.state.clone(),
                            step_id: step_id.to_string(),
                            status: "failed".to_string(),
                            message: "설치 중 메모리 부족이 감지되어 실패로 처리했어요.".to_string(),
                            stream_chunk: None,
                            shell_target: shell_target.clone(),
                            observed_path: None,
                            error_code: Some("installer_oom".to_string()),
                        });
                        failed
                    } else {
                        emit_onboarding_progress(&app_handle, OnboardingProgressEvent {
                            phase: "install".to_string(),
                            state: "verifying_shells".to_string(),
                            step_id: step_id.to_string(),
                            status: if result.ok { "succeeded".to_string() } else { "failed".to_string() },
                            message: "설치 실행이 끝나서 새 셸 검증 단계로 넘어가요.".to_string(),
                            stream_chunk: None,
                            shell_target: shell_target.clone(),
                            observed_path: None,
                            error_code: None,
                        });
                        let mut verified = verify_windows_shells(&state_arc, &app_handle, path_kind.as_contract_value());
                        verified.install_path_kind = path_kind.as_contract_value().to_string();
                        verified
                    }
                }
                Err(err) => {
                    let mut failed = build_initial_onboarding_snapshot();
                    failed.state = "blocked".to_string();
                    failed.install_path_kind = path_kind.as_contract_value().to_string();
                    failed.next_action = "none".to_string();
                    failed.headline = "설치 프로세스를 시작하지 못했어요".to_string();
                    failed.detail = Some(err.clone());
                    failed.primary_button_label = None;
                    failed.logs_available = onboarding_logs_available_from_state(&state_arc);
                    failed.last_error = Some(OnboardingLastError {
                        code: "unknown".to_string(),
                        summary: "설치 프로세스 spawn 자체가 실패했어요.".to_string(),
                        detail: Some(err),
                        suggested_action: None,
                    });
                    store_onboarding_snapshot(&state_arc, &failed);
                    emit_onboarding_progress(&app_handle, OnboardingProgressEvent {
                        phase: "install".to_string(),
                        state: failed.state.clone(),
                        step_id: step_id.to_string(),
                        status: "failed".to_string(),
                        message: "설치 프로세스 실행 자체가 실패했어요.".to_string(),
                        stream_chunk: None,
                        shell_target,
                        observed_path: None,
                        error_code: Some("unknown".to_string()),
                    });
                    failed
                }
            };

            store_onboarding_snapshot(&state_arc, &final_snapshot);
        });

        snapshot
    }
}

#[tauri::command]
fn retry_verification(app: tauri::AppHandle, state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        let install_path_kind = state
            .0
            .lock()
            .ok()
            .and_then(|runtime| runtime
                .snapshot
            .as_ref()
            .map(|snapshot| snapshot.install_path_kind.clone()))
            .unwrap_or_else(|| "unknown".to_string());

        let mut snapshot = build_initial_onboarding_snapshot();
        snapshot.state = "verifying_shells".to_string();
        snapshot.install_path_kind = install_path_kind.clone();
        snapshot.next_action = "none".to_string();
        snapshot.headline = "설치 결과를 다시 확인하는 중이에요".to_string();
        snapshot.detail = Some("새 셸 검증을 백그라운드에서 다시 실행하고 있어요.".to_string());
        snapshot.primary_button_label = None;
        store_onboarding_snapshot(&state.0, &snapshot);

        let state_arc = Arc::clone(&state.0);
        let app_handle = app.clone();
        std::thread::spawn(move || {
            let final_snapshot = verify_windows_shells(&state_arc, &app_handle, &install_path_kind);
            store_onboarding_snapshot(&state_arc, &final_snapshot);
        });

        return snapshot;
    }

    #[cfg(not(target_os = "windows"))]
    {
        let snapshot = verify_windows_shells(&state.0, &app, "unknown");
        store_onboarding_snapshot(&state.0, &snapshot);
        snapshot
    }
}

#[tauri::command]
fn add_claude_to_user_path(app: tauri::AppHandle, state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
    #[cfg(target_os = "windows")]
    {
        let bin_dir = windows_expected_claude_path()
            .and_then(|p| p.parent().map(|d| d.to_string_lossy().to_string()))
            .unwrap_or_else(|| String::from("C:\\Users\\%USERNAME%\\.local\\bin"));

        append_onboarding_log(&state.0, "[path-fix] target", &bin_dir);

        // PowerShell 로 사용자 Path 레지스트리에 bin_dir 을 추가한다. REG_EXPAND_SZ 를
        // 그대로 유지하며 WM_SETTINGCHANGE 도 함께 브로드캐스트된다.
        let ps_script = format!(
            "$target = '{}'; $current = [Environment]::GetEnvironmentVariable('Path','User'); if ([string]::IsNullOrEmpty($current)) {{ $current = '' }}; $parts = $current -split ';' | Where-Object {{ $_ -ne '' }}; if ($parts -notcontains $target) {{ $new = if ($parts) {{ (($parts + $target) -join ';') }} else {{ $target }}; [Environment]::SetEnvironmentVariable('Path', $new, 'User'); Write-Output 'PATH_UPDATED' }} else {{ Write-Output 'PATH_ALREADY_PRESENT' }}",
            bin_dir.replace('\'', "''")
        );
        let state_for_sink = Arc::clone(&state.0);
        let result = run_command_capture_streamed(
            "powershell",
            &["-NoProfile", "-Command", &ps_script],
            &[],
            |title, line| append_onboarding_log(&state_for_sink, title, line),
        );

        // PowerShell 경로가 실패하면 cmd + reg add 로 폴백.
        // 기존 Path 를 read_windows_user_path 로 읽은 뒤 bin_dir 이 없으면 append.
        let result = match &result {
            Ok(capture) if capture.ok => result,
            _ => {
                append_onboarding_log(&state.0, "[path-fix] fallback", "powershell 경로 실패 → cmd + reg add 로 재시도");
                let current = read_windows_user_path().unwrap_or_default();
                let already_present = current.split(';').any(|p| p.eq_ignore_ascii_case(&bin_dir));
                if already_present {
                    append_onboarding_log(&state.0, "[path-fix] fallback", "PATH_ALREADY_PRESENT");
                    Ok(CommandCapture { ok: true, stdout: "PATH_ALREADY_PRESENT".to_string(), stderr: String::new(), exit_code: 0 })
                } else {
                    let new_value = if current.is_empty() { bin_dir.clone() } else { format!("{};{}", current.trim_end_matches(';'), bin_dir) };
                    let state_for_sink2 = Arc::clone(&state.0);
                    run_command_capture_streamed(
                        "reg",
                        &["add", r"HKCU\Environment", "/v", "Path", "/t", "REG_EXPAND_SZ", "/d", &new_value, "/f"],
                        &[],
                        |title, line| append_onboarding_log(&state_for_sink2, title, line),
                    )
                }
            }
        };

        let mut snapshot = build_initial_onboarding_snapshot();
        snapshot.install_path_kind = state
            .0
            .lock()
            .ok()
            .and_then(|runtime| runtime.snapshot.as_ref().map(|s| s.install_path_kind.clone()))
            .unwrap_or_else(|| "native-powershell".to_string());
        snapshot.logs_available = onboarding_logs_available_from_state(&state.0);

        match result {
            Ok(capture) if capture.ok => {
                append_onboarding_log(&state.0, "[path-fix] result", capture.stdout.trim());
                snapshot.state = "login_required".to_string();
                snapshot.next_action = "start_login".to_string();
                snapshot.headline = "PATH 를 사용자 환경 변수에 추가했어요".to_string();
                snapshot.detail = Some(format!(
                    "`{}` 을 사용자 PATH 에 넣었어요. 새 터미널을 여는 순간 `claude` 가 바로 잡혀요. 이제 로그인만 남았어요.",
                    bin_dir
                ));
                snapshot.primary_button_label = Some("로그인 확인 시작".to_string());
                snapshot.diagnostics.claude_on_path = Some(true);
                snapshot.diagnostics.claude_version_ok = Some(true);
                snapshot.last_error = None;
                store_onboarding_snapshot(&state.0, &snapshot);
                emit_onboarding_progress(&app, OnboardingProgressEvent {
                    phase: "verify".to_string(),
                    state: snapshot.state.clone(),
                    step_id: "verify_doctor".to_string(),
                    status: "succeeded".to_string(),
                    message: "PATH 자동 추가 완료.".to_string(),
                    stream_chunk: None,
                    shell_target: None,
                    observed_path: Some(bin_dir),
                    error_code: None,
                });
                return snapshot;
            }
            Ok(capture) => {
                append_onboarding_log(&state.0, "[path-fix] stderr", &capture.stderr);
                snapshot.state = "needs_manual_step".to_string();
                snapshot.next_action = "open_manual_steps".to_string();
                snapshot.headline = "PATH 자동 추가가 실패했어요".to_string();
                snapshot.detail = Some("권한 문제로 레지스트리 기록이 실패했어요. 수동 안내를 따라 주세요.".to_string());
                snapshot.primary_button_label = Some("PATH 추가 방법 보기".to_string());
                snapshot.last_error = Some(OnboardingLastError {
                    code: "path_not_configured".to_string(),
                    summary: "PowerShell SetEnvironmentVariable 이 실패했어요.".to_string(),
                    detail: Some(format!("exit_code={}", capture.exit_code)),
                    suggested_action: Some("open_manual_steps".to_string()),
                });
                store_onboarding_snapshot(&state.0, &snapshot);
                return snapshot;
            }
            Err(err) => {
                append_onboarding_log(&state.0, "[path-fix] spawn error", &err);
                snapshot.state = "needs_manual_step".to_string();
                snapshot.next_action = "open_manual_steps".to_string();
                snapshot.headline = "PATH 자동 추가가 실패했어요".to_string();
                snapshot.detail = Some("PowerShell 실행에 실패했어요. 수동 안내를 따라 주세요.".to_string());
                snapshot.primary_button_label = Some("PATH 추가 방법 보기".to_string());
                snapshot.last_error = Some(OnboardingLastError {
                    code: "path_not_configured".to_string(),
                    summary: err,
                    detail: None,
                    suggested_action: Some("open_manual_steps".to_string()),
                });
                store_onboarding_snapshot(&state.0, &snapshot);
                return snapshot;
            }
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = (app, state);
        build_onboarding_snapshot()
    }
}

#[tauri::command]
fn start_login_probe(app: tauri::AppHandle, state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
    emit_onboarding_progress(
        &app,
        OnboardingProgressEvent {
            phase: "login".to_string(),
            state: "probing_login".to_string(),
            step_id: "probe_login".to_string(),
            status: "started".to_string(),
            message: "로그인 probe 스캐폴드를 시작했어요. 실제 probe는 다음 단계에서 연결됩니다.".to_string(),
            stream_chunk: None,
            shell_target: None,
            observed_path: None,
            error_code: None,
        },
    );

    let mut snapshot = build_onboarding_snapshot();
    snapshot.state = "probing_login".to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "Claude 로그인 상태를 확인하는 중이에요".to_string();
    snapshot.detail = Some("실제 login probe execution은 다음 구현 단계에서 연결됩니다.".to_string());
    snapshot.primary_button_label = None;
    store_onboarding_snapshot(&state.0, &snapshot);
    snapshot
}

#[tauri::command]
fn get_onboarding_logs(state: tauri::State<OnboardingState>) -> serde_json::Value {
    let text = state
        .0
        .lock()
        .ok()
        .map(|runtime| runtime.logs.clone())
        .unwrap_or_default();
    serde_json::json!({ "text": text })
}

/// vib CLI를 실행하고 결과를 반환한다.
///
/// - `args`: `["doctor", "--json"]` 등
/// - `cwd`: 프로젝트 루트 경로 (없으면 현재 디렉터리)
/// - `env`: 추가 환경변수 (`{"ANTHROPIC_API_KEY": "..."}` 등)
#[tauri::command]
async fn run_vib(
    args: Vec<String>,
    cwd: Option<String>,
    env: Option<HashMap<String, String>>,
) -> VibResult {
    let vib = match vib_path::find_vib() {
        Some(p) => p,
        None => {
            return VibResult {
                ok: false,
                stdout: String::new(),
                stderr: "vib 실행 파일을 찾을 수 없습니다. 설치 후 재시작하세요.".into(),
                exit_code: -1,
            };
        }
    };

    tauri::async_runtime::spawn_blocking(move || {
        let mut cmd = std::process::Command::new(&vib);
        cmd.args(&args);
        cmd.stdin(std::process::Stdio::null());

        if let Some(dir) = cwd {
            cmd.current_dir(PathBuf::from(dir));
        }

        // Windows에서 Python 서브프로세스의 stdout 인코딩을 UTF-8로 강제 설정 + 콘솔 창 숨김
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.env("PYTHONUTF8", "1");
            cmd.env("PYTHONIOENCODING", "utf-8");
            cmd.creation_flags(CREATE_NO_WINDOW);
        }

        if let Some(env_map) = env {
            for (k, v) in env_map {
                cmd.env(k, v);
            }
        }

        match cmd.output() {
            Ok(output) => VibResult {
                ok: output.status.success(),
                stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
                stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
                exit_code: output.status.code().unwrap_or(-1),
            },
            Err(e) => VibResult {
                ok: false,
                stdout: String::new(),
                stderr: e.to_string(),
                exit_code: -1,
            },
        }
    })
    .await
    .unwrap_or(VibResult {
        ok: false,
        stdout: String::new(),
        stderr: "spawn_blocking 실패".into(),
        exit_code: -1,
    })
}

// ─── API 키 저장소 ─────────────────────────────────────────────────────────────

/// 플랫폼별 api_keys.json 경로.
/// macOS/Linux: ~/.config/vibelign/api_keys.json
/// Windows:     %APPDATA%\vibelign\api_keys.json
fn keys_file_path() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        let appdata = std::env::var("APPDATA").ok()?;
        let dir = PathBuf::from(appdata).join("vibelign");
        std::fs::create_dir_all(&dir).ok()?;
        return Some(dir.join("api_keys.json"));
    }
    #[cfg(not(target_os = "windows"))]
    {
        let xdg_config = std::env::var("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                let home = std::env::var("HOME")
                    .or_else(|_| std::env::var("USERPROFILE"))
                    .unwrap_or_default();
                PathBuf::from(home).join(".config")
            });
        let dir = xdg_config.join("vibelign");
        std::fs::create_dir_all(&dir).ok()?;
        Some(dir.join("api_keys.json"))
    }
}

fn read_keys_file() -> HashMap<String, String> {
    let path = match keys_file_path() { Some(p) => p, None => return HashMap::new() };
    let text = match std::fs::read_to_string(&path) { Ok(t) => t, Err(_) => return HashMap::new() };
    let val: serde_json::Value = match serde_json::from_str(&text) { Ok(v) => v, Err(_) => return HashMap::new() };
    let mut out = HashMap::new();
    if let Some(obj) = val.as_object() {
        for (k, v) in obj {
            if let Some(s) = v.as_str() {
                if !s.is_empty() { out.insert(k.clone(), s.to_string()); }
            }
        }
    }
    out
}

fn write_keys_file(keys: &HashMap<String, String>) -> Result<(), String> {
    let path = keys_file_path().ok_or("keys 파일 경로를 찾을 수 없습니다")?;
    let val = serde_json::to_string_pretty(keys).map_err(|e| e.to_string())?;
    std::fs::write(&path, val + "\n").map_err(|e| e.to_string())
}

fn provider_to_env_key(provider: &str) -> &'static str {
    match provider {
        "ANTHROPIC" => "ANTHROPIC_API_KEY",
        "OPENAI"    => "OPENAI_API_KEY",
        "GEMINI"    => "GEMINI_API_KEY",
        "GLM"       => "GLM_API_KEY",
        "MOONSHOT"  => "MOONSHOT_API_KEY",
        _           => "",
    }
}

fn migrate_legacy_keys() {
    let new_path = match keys_file_path() { Some(p) => p, None => return };
    if new_path.exists() { return; }
    let legacy = read_gui_config();
    let pairs: &[(&str, &str)] = &[
        ("ANTHROPIC", "ANTHROPIC_API_KEY"),
        ("OPENAI",    "OPENAI_API_KEY"),
        ("GEMINI",    "GEMINI_API_KEY"),
        ("GLM",       "GLM_API_KEY"),
        ("MOONSHOT",  "MOONSHOT_API_KEY"),
    ];
    let mut migrated: HashMap<String, String> = HashMap::new();
    if let Some(obj) = legacy.get("provider_api_keys").and_then(|v| v.as_object()) {
        for (short, env_name) in pairs {
            if let Some(v) = obj.get(*short).and_then(|v| v.as_str()) {
                if !v.is_empty() { migrated.insert(env_name.to_string(), v.to_string()); }
            }
        }
    }
    if let Some(s) = legacy.get("anthropic_api_key").and_then(|v| v.as_str()) {
        if !s.is_empty() { migrated.entry("ANTHROPIC_API_KEY".into()).or_insert_with(|| s.to_string()); }
    }
    if !migrated.is_empty() { let _ = write_keys_file(&migrated); }
}

fn config_path() -> Option<PathBuf> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .ok()?;
    let dir = PathBuf::from(home).join(".vibelign");
    std::fs::create_dir_all(&dir).ok()?;
    Some(dir.join("gui_config.json"))
}

#[tauri::command]
fn save_recent_projects(dirs: Vec<String>) -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    let existing = std::fs::read_to_string(&path)
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .unwrap_or(serde_json::json!({}));
    let mut data = existing;
    data["recent_projects"] = serde_json::Value::Array(
        dirs.into_iter().map(serde_json::Value::String).collect(),
    );
    std::fs::write(&path, data.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_recent_projects() -> Vec<String> {
    let path = match config_path() { Some(p) => p, None => return vec![] };
    let text = match std::fs::read_to_string(&path) { Ok(t) => t, Err(_) => return vec![] };
    let data: serde_json::Value = match serde_json::from_str(&text) { Ok(v) => v, Err(_) => return vec![] };
    data["recent_projects"]
        .as_array()
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default()
}

fn read_gui_config() -> serde_json::Value {
    let path = match config_path() {
        Some(p) => p,
        None => return serde_json::json!({}),
    };
    let text = std::fs::read_to_string(&path).unwrap_or_default();
    match serde_json::from_str::<serde_json::Value>(&text) {
        Ok(v) if v.is_object() => v,
        _ => serde_json::json!({}),
    }
}

fn write_gui_config(data: &serde_json::Value) -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    std::fs::write(&path, data.to_string()).map_err(|e| e.to_string())
}

/// `provider_api_keys` + 레거시 `anthropic_api_key`를 합친 맵.
fn provider_keys_from_config(data: &serde_json::Value) -> HashMap<String, String> {
    let mut out = HashMap::new();
    if let Some(obj) = data.get("provider_api_keys").and_then(|v| v.as_object()) {
        for (k, v) in obj {
            if let Some(s) = v.as_str() {
                if !s.is_empty() {
                    out.insert(k.to_uppercase(), s.to_string());
                }
            }
        }
    }
    if let Some(s) = data.get("anthropic_api_key").and_then(|v| v.as_str()) {
        if !s.is_empty() {
            out.entry("ANTHROPIC".into()).or_insert_with(|| s.to_string());
        }
    }
    out
}

#[tauri::command]
fn save_api_key(key: String) -> Result<(), String> {
    save_provider_api_key("ANTHROPIC".to_string(), key)
}

#[tauri::command]
fn load_api_key() -> Option<String> {
    let data = read_gui_config();
    provider_keys_from_config(&data)
        .get("ANTHROPIC")
        .cloned()
        .or_else(|| data["anthropic_api_key"].as_str().map(String::from))
}

#[tauri::command]
fn delete_api_key() -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    if !path.exists() {
        return Ok(());
    }
    let mut data = read_gui_config();
    if let Some(obj) = data.as_object_mut() {
        obj.remove("anthropic_api_key");
    }
    if let Some(obj) = data
        .get_mut("provider_api_keys")
        .and_then(|v| v.as_object_mut())
    {
        obj.remove("ANTHROPIC");
    }
    write_gui_config(&data)
}

#[tauri::command]
fn save_provider_api_key(provider: String, key: String) -> Result<(), String> {
    let provider = provider.to_uppercase();
    let key = key.trim().to_string();
    if key.is_empty() {
        return Err("키가 비어 있습니다".into());
    }
    let env_key = provider_to_env_key(&provider);
    if env_key.is_empty() {
        return Err(format!("알 수 없는 provider: {provider}"));
    }
    let mut keys = read_keys_file();
    keys.insert(env_key.to_string(), key);
    write_keys_file(&keys)
}

#[tauri::command]
fn delete_provider_api_key(provider: String) -> Result<(), String> {
    let provider = provider.to_uppercase();
    let env_key = provider_to_env_key(&provider);
    if env_key.is_empty() {
        return Ok(());
    }
    let mut keys = read_keys_file();
    keys.remove(env_key);
    write_keys_file(&keys)
}

#[tauri::command]
fn load_provider_api_keys() -> HashMap<String, String> {
    let raw = read_keys_file();
    let pairs: &[(&str, &str)] = &[
        ("ANTHROPIC_API_KEY", "ANTHROPIC"),
        ("OPENAI_API_KEY",    "OPENAI"),
        ("GEMINI_API_KEY",    "GEMINI"),
        ("GLM_API_KEY",       "GLM"),
        ("MOONSHOT_API_KEY",  "MOONSHOT"),
    ];
    let mut out = HashMap::new();
    for (env_name, short_name) in pairs {
        if let Some(v) = raw.get(*env_name) {
            out.insert(short_name.to_string(), v.clone());
        }
    }
    out
}

// ─── 환경변수 + 키 파일 API 키 상태 ───────────────────────────────────────────

#[tauri::command]
fn get_env_key_status() -> HashMap<String, bool> {
    let keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GLM_API_KEY",
        "MOONSHOT_API_KEY",
    ];
    let stored = read_keys_file();
    keys.iter()
        .map(|k| {
            let from_env = !std::env::var(k).unwrap_or_default().is_empty();
            let from_file = stored.get(*k).map(|v| !v.is_empty()).unwrap_or(false);
            (k.to_string(), from_env || from_file)
        })
        .collect()
}

// ─── Git 설치 확인 ────────────────────────────────────────────────────────────

#[tauri::command]
fn check_git_installed() -> bool {
    // 1. PATH에서 git 시도
    if std::process::Command::new("git")
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
    {
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

// ─── 프로젝트 요약 ─────────────────────────────────────────────────────────────

/// Windows에서 PATH에 git이 없을 때도 기본 설치 경로에서 찾아 반환
fn git_cmd() -> std::process::Command {
    // PATH에서 찾히면 바로 사용
    if std::process::Command::new("git").arg("--version").output().map(|o| o.status.success()).unwrap_or(false) {
        return std::process::Command::new("git");
    }
    #[cfg(target_os = "windows")]
    {
        let candidates = [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (Arm)\Git\cmd\git.exe",
        ];
        for path in &candidates {
            if std::path::Path::new(path).exists() {
                return std::process::Command::new(path);
            }
        }
    }
    std::process::Command::new("git") // 최후 수단 — 실패해도 에러는 호출부에서 처리
}

fn trunc(s: &str, max: usize) -> String {
    let mut chars = s.chars();
    let result: String = chars.by_ref().take(max).collect();
    if chars.next().is_some() { format!("{}…", result) } else { result }
}

fn parse_checkpoints_from_ctx(content: &str) -> Vec<[String; 2]> {
    let mut in_section = false;
    let mut results = Vec::new();
    for line in content.lines() {
        if line.starts_with("## 4.") { in_section = true; continue; }
        if in_section && line.starts_with("## ") { break; }
        if !in_section || !line.starts_with('|') { continue; }
        let cols: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if cols.len() < 3 { continue; }
        let ts = cols[1];
        let msg = cols[2];
        if msg.is_empty() || msg == "작업 내용" || msg.starts_with('-') || msg == "(메시지 없음)" { continue; }
        let detail = format!("{} — {}", ts, msg);
        results.push([trunc(msg, 20), detail]);
        if results.len() >= 2 { break; }
    }
    results
}

#[derive(Serialize)]
struct SummaryLine {
    display: String,
    detail: String,
}

#[derive(Serialize)]
struct ProjectSummary {
    project_name: String,
    checkpoints: Vec<SummaryLine>,
    git_commits: Vec<SummaryLine>,
}

#[tauri::command]
fn read_project_summary(dir: String) -> ProjectSummary {
    let path = std::path::Path::new(&dir);
    let project_name = path.file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "프로젝트".to_string());

    // git log: hash|subject|date (최근 3개)
    let git_commits = git_cmd()
        .args(["log", "-3", "--pretty=format:%h|%s|%ad", "--date=short"])
        .current_dir(path)
        .output()
        .ok()
        .map(|o| {
            String::from_utf8_lossy(&o.stdout).lines()
                .filter_map(|l| {
                    let parts: Vec<&str> = l.splitn(3, '|').collect();
                    if parts.len() < 2 { return None; }
                    let hash = parts[0].trim();
                    let subject = parts[1].trim();
                    if subject.is_empty() { return None; }
                    let date = parts.get(2).copied().unwrap_or("").trim();

                    // git show --stat: 변경 파일 목록 (on-load 프리페치)
                    let stat = git_cmd()
                        .args(["show", "--stat", "--pretty=format:%b", hash])
                        .current_dir(path)
                        .output()
                        .ok()
                        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                        .unwrap_or_default();

                    let mut detail = format!("{} — {}", date, subject);
                    if !stat.is_empty() {
                        detail.push_str(&format!("\n\n{}", stat));
                    }

                    Some(SummaryLine { display: trunc(subject, 20), detail })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let content = std::fs::read_to_string(path.join("PROJECT_CONTEXT.md")).unwrap_or_default();
    let checkpoints = parse_checkpoints_from_ctx(&content)
        .into_iter()
        .map(|[display, detail]| SummaryLine { display, detail })
        .collect();

    ProjectSummary { project_name, checkpoints, git_commits }
}

// ─── 앱 진입점 ─────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let watch_inner: Arc<Mutex<WatchRuntime>> = Arc::new(Mutex::new(WatchRuntime::new()));
    let watch_inner_for_exit = Arc::clone(&watch_inner);
    let onboarding_inner: Arc<Mutex<OnboardingRuntime>> = Arc::new(Mutex::new(OnboardingRuntime {
        snapshot: Some(build_initial_onboarding_snapshot()),
        logs: String::new(),
    }));

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .setup(|_app| {
            // 기존 gui_config.json 키를 api_keys.json으로 마이그레이션 (최초 1회)
            migrate_legacy_keys();
            // 앱 시작 시 vib CLI를 터미널 PATH에 자동 설치
            if let Err(e) = vib_path::install_cli_to_path() {
                eprintln!("VibeLign: CLI PATH 설치 실패 — {e}");
            }
            Ok(())
        })
        .manage(WatchState(watch_inner))
        .manage(OnboardingState(onboarding_inner))
        .invoke_handler(tauri::generate_handler![
            get_vib_path,
            setup_cli_path,
            get_onboarding_snapshot,
            start_native_install,
            retry_verification,
            add_claude_to_user_path,
            start_login_probe,
            get_onboarding_logs,
            run_vib,
            save_api_key,
            load_api_key,
            delete_api_key,
            save_provider_api_key,
            delete_provider_api_key,
            load_provider_api_keys,
            save_recent_projects,
            load_recent_projects,
            start_watch,
            stop_watch,
            watch_status,
            get_watch_logs,
            get_watch_errors,
            open_folder,
            read_file,
            list_docs_index,
            read_docs_visual,
            get_env_key_status,
            read_project_summary,
            check_git_installed,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            match event {
                tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. } => {
                    if let Ok(mut guard) = watch_inner_for_exit.lock() {
                        if let Some(mut child) = guard.child.take() {
                            kill_watch_child(&mut child);
                        }
                    }
                }
                _ => {}
            }
        });
}
// === ANCHOR: LIB_END ===
