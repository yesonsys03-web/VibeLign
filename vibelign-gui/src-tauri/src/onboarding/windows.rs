#![cfg(target_os = "windows")]

use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use super::{
    append_onboarding_log, build_initial_onboarding_snapshot, build_onboarding_snapshot,
    clear_onboarding_logs, emit_onboarding_progress, onboarding_logs_available_from_state,
    run_command_capture, run_command_capture_streamed, run_command_capture_with_timeout,
    store_onboarding_snapshot, CommandCapture, OnboardingLastError, OnboardingProgressEvent,
    OnboardingRuntime, OnboardingSnapshot, OnboardingState, StartNativeInstallPathKind,
};

use super::check_git_installed;

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

fn windows_user_profile() -> Option<PathBuf> {
    std::env::var("USERPROFILE").ok().map(PathBuf::from)
}

fn windows_placeholder_artifact() -> Option<PathBuf> {
    windows_user_profile().map(|p| p.join("claude"))
}

fn windows_placeholder_artifact_exists() -> bool {
    let Some(path) = windows_placeholder_artifact() else {
        return false;
    };
    std::fs::metadata(path).map(|m| m.is_file() && m.len() == 0).unwrap_or(false)
}

fn windows_expected_claude_path() -> Option<PathBuf> {
    windows_user_profile().map(|p| p.join(".local").join("bin").join("claude.exe"))
}

fn windows_expected_claude_exists() -> bool {
    windows_expected_claude_path()
        .map(|path| path.exists())
        .unwrap_or(false)
}

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
    let where_found = where_result.as_ref().map(|r| r.ok && !r.stdout.trim().is_empty()).unwrap_or(false);
    // `where.exe` 를 우리가 주입한 merged PATH 로 실행하기 때문에,
    // install.ps1 이 HKCU\Environment\Path 를 건드리지 않은 경우에도
    // GUI 프로세스 env 만으로 claude.exe 가 잡힐 수 있다.
    // 사용자가 새로 여는 cmd/PowerShell 은 HKCU 영구 PATH 만 본다.
    // 따라서 bin_dir 이 HKCU User PATH 에 실제로 들어있는지 별도로 확인해
    // 그것도 통과해야만 claude_on_path 를 참으로 인정한다.
    let bin_dir_for_check: Option<String> = windows_expected_claude_path()
        .and_then(|p| p.parent().map(|d| d.to_string_lossy().to_string()));
    let user_path_snapshot: String = read_windows_user_path().unwrap_or_default();
    let bin_dir_in_user_path = match bin_dir_for_check.as_deref() {
        Some(bin) => user_path_snapshot
            .split(';')
            .any(|part| part.trim().eq_ignore_ascii_case(bin)),
        None => false,
    };
    if where_found && !bin_dir_in_user_path {
        append_onboarding_log(
            state,
            "[verify] user-path missing",
            "where.exe 는 성공했지만 HKCU Path 에 .local\\bin 이 없어요. PATH 미설정으로 분류해요.",
        );
    }
    let claude_on_path = where_found && bin_dir_in_user_path;
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
    // claude doctor 는 Ink raw-mode TTY 가 필요해서 GUI 자식 프로세스에선 항상 timeout.
    // 진단 가치가 없어 검증 단계에서 생략한다.
    append_onboarding_log(state, "[verify] skip", "claude doctor (non-TTY 한계로 생략)");
    let doctor_result: Option<CommandCapture> = None;

    let direct_version = windows_expected_claude_path().and_then(|path| {
        let path_str = path.to_string_lossy().to_string();
        append_onboarding_log(state, "[verify] running direct", &format!("{} --version (timeout 15s)", path_str));
        run_command_capture_with_timeout(&path_str, &["--version"], &[], 15).ok().map(|result| (path_str, result))
    });
    if let Some((_, result)) = &direct_version {
        append_onboarding_log(state, "[verify direct claude.exe --version stdout]", &result.stdout);
        append_onboarding_log(state, "[verify direct claude.exe --version stderr]", &result.stderr);
    }

    let direct_doctor: Option<(String, CommandCapture)> = None;

    let claude_version_ok = cmd_version.as_ref().map(|r| r.ok).unwrap_or(false)
        || ps_version.as_ref().map(|r| r.ok).unwrap_or(false);
    let claude_doctor_ok = doctor_result.as_ref().map(|r| r.ok).unwrap_or(false);
    let direct_version_ok = direct_version.as_ref().map(|(_, r)| r.ok).unwrap_or(false);
    let direct_doctor_ok = direct_doctor.as_ref().map(|(_, r)| r.ok).unwrap_or(false);

    snapshot.logs_available = onboarding_logs_available_from_state(state);
    snapshot.diagnostics.git_installed = Some(check_git_installed());
    snapshot.diagnostics.wsl_available = Some(check_wsl_available());
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

    // claude doctor 는 non-TTY 에서 Ink raw-mode 에러로 실패하거나 타임아웃되는 게
    // 정상 동작이라 성공 조건에서 뺀다. where.exe + claude --version 이 통과하면
    // 설치·PATH 가 모두 정상이라 판단 가능.
    let _ = claude_doctor_ok;
    if claude_on_path && claude_version_ok {
        snapshot.state = "login_required".to_string();
        snapshot.next_action = "start_login".to_string();
        snapshot.headline = "설치가 잘 끝났어요!".to_string();
        snapshot.detail = Some("이제 터미널에서 `claude` 를 실행하면 로그인 화면이 뜨고, 로그인만 한 번 하면 바로 쓸 수 있어요.".to_string());
        snapshot.primary_button_label = Some("다음으로".to_string());
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

/// WSL 트랙: 네이티브 설치/검증이 끝난 상태에서 WSL 안에 Linux 버전 Claude Code 를
/// 추가로 설치한다. 기존 네이티브 실행은 유지되며 WSL 터미널에서도 `claude` 가 동작하도록
/// 하는 것이 목표다. 반환되는 스냅샷은 cmd/powershell 검증과 WSL 검증 모두를 반영한다.
fn run_wsl_install_flow(
    state: &Arc<Mutex<OnboardingRuntime>>,
    app: &tauri::AppHandle,
    previous_snapshot: OnboardingSnapshot,
) -> OnboardingSnapshot {
    let mut snapshot = previous_snapshot.clone();
    snapshot.state = "installing_wsl".to_string();
    snapshot.install_path_kind = "wsl".to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "WSL 쪽에도 Claude Code 를 설치하는 중이에요".to_string();
    snapshot.detail = Some("PowerShell·CMD 설치는 이미 끝났고, 이어서 WSL 터미널에서도 바로 쓸 수 있도록 Linux 버전을 설치해요.".to_string());
    snapshot.primary_button_label = None;
    store_onboarding_snapshot(state, &snapshot);
    emit_onboarding_progress(app, OnboardingProgressEvent {
        phase: "install".to_string(),
        state: snapshot.state.clone(),
        step_id: "run_wsl_installer".to_string(),
        status: "started".to_string(),
        message: "WSL 안에서 공식 install.sh 를 실행하는 중이에요.".to_string(),
        stream_chunk: None,
        shell_target: Some("wsl".to_string()),
        observed_path: None,
        error_code: None,
    });

    append_onboarding_log(state, "[wsl installer] running", "wsl.exe -- bash -lc 'curl -fsSL https://claude.ai/install.sh | bash'");
    let state_for_sink = Arc::clone(state);
    let install_result = run_command_capture_streamed(
        "wsl.exe",
        &["--", "bash", "-lc", "curl -fsSL https://claude.ai/install.sh | bash"],
        &[],
        |title, line| append_onboarding_log(&state_for_sink, title, line),
    );

    let install_ok = match &install_result {
        Ok(r) => {
            append_onboarding_log(state, "[wsl installer stdout]", &r.stdout);
            append_onboarding_log(state, "[wsl installer stderr]", &r.stderr);
            r.ok
        }
        Err(err) => {
            append_onboarding_log(state, "[wsl installer error]", err);
            false
        }
    };

    snapshot.logs_available = onboarding_logs_available_from_state(state);

    if !install_ok {
        // 네이티브 트랙은 이미 성공했으므로 WSL 실패를 soft-fail 로 취급한다.
        // 프론트에서 '나중에 다시 시도' 재시도 버튼으로 연결한다.
        snapshot.state = "needs_wsl_fallback".to_string();
        snapshot.next_action = "continue_with_wsl".to_string();
        snapshot.headline = "WSL 트랙 설치만 실패했어요".to_string();
        snapshot.detail = Some("PowerShell·CMD 에서는 Claude 가 잘 동작해요. WSL 설치는 나중에 다시 시도할 수 있어요.".to_string());
        snapshot.primary_button_label = Some("WSL 설치 다시 시도".to_string());
        snapshot.last_error = Some(OnboardingLastError {
            code: "unknown".to_string(),
            summary: "WSL 안에서 Claude Code 설치가 완료되지 않았어요.".to_string(),
            detail: install_result.err().map(|e| e).or(Some("install.sh 가 비정상 종료했어요.".to_string())),
            suggested_action: Some("continue_with_wsl".to_string()),
        });
        store_onboarding_snapshot(state, &snapshot);
        emit_onboarding_progress(app, OnboardingProgressEvent {
            phase: "install".to_string(),
            state: snapshot.state.clone(),
            step_id: "run_wsl_installer".to_string(),
            status: "failed".to_string(),
            message: "WSL 트랙 설치가 실패했어요. 네이티브 트랙은 그대로 사용할 수 있어요.".to_string(),
            stream_chunk: None,
            shell_target: Some("wsl".to_string()),
            observed_path: None,
            error_code: Some("unknown".to_string()),
        });
        return snapshot;
    }

    // WSL 검증: `claude --version`
    append_onboarding_log(state, "[wsl verify] running", "wsl.exe -- bash -lc 'claude --version'");
    let verify = run_command_capture(
        "wsl.exe",
        &["--", "bash", "-lc", "claude --version"],
        &[],
    )
    .ok();
    if let Some(r) = &verify {
        append_onboarding_log(state, "[wsl verify stdout]", &r.stdout);
        append_onboarding_log(state, "[wsl verify stderr]", &r.stderr);
    }
    let wsl_version_ok = verify.as_ref().map(|r| r.ok).unwrap_or(false);
    snapshot.logs_available = onboarding_logs_available_from_state(state);

    if wsl_version_ok {
        // 이전 네이티브 검증에서 login_required 까지 갔던 상태를 유지하고,
        // WSL 까지 끝났다는 사실만 헤드라인/디테일에 반영한다.
        snapshot.state = "login_required".to_string();
        snapshot.next_action = "start_login".to_string();
        snapshot.headline = "모든 터미널에서 Claude 를 쓸 수 있어요!".to_string();
        snapshot.detail = Some("PowerShell·CMD 뿐 아니라 WSL 터미널에서도 `claude` 가 실행돼요. 이제 로그인만 하면 바로 사용할 수 있어요.".to_string());
        snapshot.primary_button_label = Some("다음으로".to_string());
        snapshot.last_error = None;
        store_onboarding_snapshot(state, &snapshot);
        emit_onboarding_progress(app, OnboardingProgressEvent {
            phase: "install".to_string(),
            state: snapshot.state.clone(),
            step_id: "run_wsl_installer".to_string(),
            status: "succeeded".to_string(),
            message: "WSL 트랙 설치와 검증이 모두 통과했어요.".to_string(),
            stream_chunk: None,
            shell_target: Some("wsl".to_string()),
            observed_path: None,
            error_code: None,
        });
        return snapshot;
    }

    snapshot.state = "needs_wsl_fallback".to_string();
    snapshot.next_action = "continue_with_wsl".to_string();
    snapshot.headline = "WSL 설치는 끝났지만 `claude` 실행 확인이 안 됐어요".to_string();
    snapshot.detail = Some("네이티브 트랙은 정상이에요. WSL 재시도는 선택사항이에요.".to_string());
    snapshot.primary_button_label = Some("WSL 검증 재시도".to_string());
    snapshot.last_error = Some(OnboardingLastError {
        code: "installer_false_success".to_string(),
        summary: "WSL 안 install.sh 는 성공했지만 `claude --version` 이 실패했어요.".to_string(),
        detail: None,
        suggested_action: Some("continue_with_wsl".to_string()),
    });
    store_onboarding_snapshot(state, &snapshot);
    emit_onboarding_progress(app, OnboardingProgressEvent {
        phase: "verify".to_string(),
        state: snapshot.state.clone(),
        step_id: "verify_version".to_string(),
        status: "failed".to_string(),
        message: "WSL 쪽 검증이 통과하지 못했어요.".to_string(),
        stream_chunk: None,
        shell_target: Some("wsl".to_string()),
        observed_path: None,
        error_code: Some("installer_false_success".to_string()),
    });
    snapshot
}

pub(crate) fn start_wsl_install(app: tauri::AppHandle, state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
    if !check_wsl_available() {
        let mut blocked = build_initial_onboarding_snapshot();
        blocked.state = "blocked".to_string();
        blocked.install_path_kind = "wsl".to_string();
        blocked.next_action = "none".to_string();
        blocked.headline = "WSL 을 감지하지 못했어요".to_string();
        blocked.detail = Some("WSL 배포판이 설치되어 있어야 이 트랙을 사용할 수 있어요.".to_string());
        blocked.last_error = Some(OnboardingLastError {
            code: "unsupported_environment".to_string(),
            summary: "WSL 이 사용 가능한 상태가 아니에요.".to_string(),
            detail: None,
            suggested_action: None,
        });
        store_onboarding_snapshot(&state.0, &blocked);
        return blocked;
    }

    let previous = state
        .0
        .lock()
        .ok()
        .and_then(|runtime| runtime.snapshot.clone())
        .unwrap_or_else(build_initial_onboarding_snapshot);

    let mut in_progress = previous.clone();
    in_progress.state = "installing_wsl".to_string();
    in_progress.install_path_kind = "wsl".to_string();
    in_progress.next_action = "none".to_string();
    in_progress.headline = "WSL 쪽에도 Claude Code 를 설치하는 중이에요".to_string();
    in_progress.detail = Some("공식 install.sh 를 WSL 안에서 실행하고 있어요.".to_string());
    in_progress.primary_button_label = None;
    store_onboarding_snapshot(&state.0, &in_progress);

    let state_arc = Arc::clone(&state.0);
    let app_handle = app.clone();
    let baseline = previous;
    std::thread::spawn(move || {
        let final_snapshot = run_wsl_install_flow(&state_arc, &app_handle, baseline);
        store_onboarding_snapshot(&state_arc, &final_snapshot);
    });

    in_progress
}

pub(crate) fn start_install(
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
                if combined.contains("out of memory")
                    || combined.contains("bun has run out of memory")
                    || combined.contains("allocation failed")
                {
                    let mut failed = build_initial_onboarding_snapshot();
                    failed.state = "needs_manual_step".to_string();
                    failed.install_path_kind = path_kind.as_contract_value().to_string();
                    failed.next_action = "none".to_string();
                    failed.headline = "메모리 부족으로 설치가 중단됐어요".to_string();
                    failed.detail = Some("RAM을 늘리거나 실행 중인 다른 프로그램을 종료한 뒤 다시 시도해 주세요.".to_string());
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
                    // 네이티브 검증이 login_required(성공) 상태이고 WSL 이 감지되면
                    // '코알못' 사용자도 WSL 터미널에서 곧장 `claude` 를 쓸 수 있도록
                    // 병렬 트랙 설치를 자동으로 이어서 실행한다. 네이티브 결과는
                    // 이미 저장되어 있어 WSL 실패가 네이티브 성공을 덮어쓰지 않는다.
                    if verified.state == "login_required" && check_wsl_available() {
                        run_wsl_install_flow(&state_arc, &app_handle, verified)
                    } else {
                        verified
                    }
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

pub(crate) fn retry_verification(app: tauri::AppHandle, state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
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

    snapshot
}

pub(crate) fn add_to_user_path(app: tauri::AppHandle, state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
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
            snapshot.primary_button_label = Some("다음으로".to_string());
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

            // PATH 자동 추가로 native 트랙이 login_required 에 도달한 직후,
            // WSL 이 감지되면 Ubuntu 터미널에서도 `claude` 가 바로 잡히도록
            // Linux 트랙 설치를 이어서 실행한다. 초기 설치 직후 verify 가
            // login_required 로 바로 통과한 경우에는 run_claude_code_installer
            // 쪽 (라인 1589 근처) 에서 같은 로직이 이미 돌고 있지만, PATH
            // 미등록 → add_claude_to_user_path 경로로 빠진 사용자에게는
            // 자동 트리거가 누락되어 있던 것을 여기서 메운다. 실패하더라도
            // run_wsl_install_flow 는 needs_wsl_fallback soft-fail 만 기록하고
            // native 성공 스냅샷 위에 덮어쓰지 않는다.
            if check_wsl_available() {
                let baseline = snapshot.clone();
                let mut in_progress = snapshot.clone();
                in_progress.state = "installing_wsl".to_string();
                in_progress.install_path_kind = "wsl".to_string();
                in_progress.next_action = "none".to_string();
                in_progress.headline = "WSL 쪽에도 Claude Code 를 설치하는 중이에요".to_string();
                in_progress.detail = Some("PATH 연결은 끝났어요. 이어서 Ubuntu 터미널에서도 `claude` 가 동작하도록 공식 install.sh 를 실행해요.".to_string());
                in_progress.primary_button_label = None;
                store_onboarding_snapshot(&state.0, &in_progress);

                let state_arc = Arc::clone(&state.0);
                let app_handle = app.clone();
                std::thread::spawn(move || {
                    let final_snapshot = run_wsl_install_flow(&state_arc, &app_handle, baseline);
                    store_onboarding_snapshot(&state_arc, &final_snapshot);
                });

                return in_progress;
            }

            snapshot
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
            snapshot
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
            snapshot
        }
    }
}

/// track: "all" | "native" | "wsl"
/// - "native": cmd/PowerShell 측 claude.exe + .claude 설정 + PATH 항목
/// - "wsl":    WSL 안의 ~/.local/bin/claude + ~/.claude
/// - "all":    native + wsl 동시
pub(crate) fn uninstall(app: tauri::AppHandle, state: tauri::State<OnboardingState>, track: Option<String>) -> OnboardingSnapshot {
    let track = track.as_deref().unwrap_or("all");

    clear_onboarding_logs(&state.0);
    let track_label = match track {
        "native" => "네이티브(cmd/PowerShell)",
        "wsl" => "WSL",
        _ => "전체",
    };
    append_onboarding_log(&state.0, "[uninstall] start", &format!("{} 트랙 삭제를 시작해요", track_label));

    let do_native = track == "all" || track == "native";
    let do_wsl = track == "all" || track == "wsl";

    let mut native_incomplete = false;

    if do_native {
        native_incomplete = uninstall_native_track(&state.0);
    }

    if do_wsl && check_wsl_available() {
        uninstall_wsl_track(&state.0);
    } else if do_wsl {
        append_onboarding_log(&state.0, "[uninstall wsl] skip", "WSL 이 감지되지 않아 건너뜀");
    }

    if native_incomplete {
        append_onboarding_log(&state.0, "[uninstall] incomplete", "claude.exe 를 지우지 못했어요. 열려 있는 터미널·VS Code·에이전트를 모두 닫고 다시 시도해 주세요.");
    } else {
        append_onboarding_log(&state.0, "[uninstall] done", &format!("{} 삭제가 끝났어요.", track_label));
    }

    let mut snapshot = build_initial_onboarding_snapshot();
    if native_incomplete {
        snapshot.headline = "삭제를 완료하지 못했어요".to_string();
        snapshot.detail = Some("claude.exe 가 다른 프로세스(열린 터미널 등)에서 잠겨 있어요. 모두 닫고 다시 삭제 버튼을 눌러 주세요.".to_string());
    } else {
        snapshot.headline = format!("{} Claude Code 를 삭제했어요", track_label);
        snapshot.detail = Some(match track {
            "native" => "네이티브 바이너리·설정·PATH 항목을 정리했어요. WSL 쪽은 그대로에요.".to_string(),
            "wsl" => "WSL 안의 바이너리·설정을 정리했어요. cmd/PowerShell 쪽은 그대로에요.".to_string(),
            _ => "네이티브 + WSL 양쪽 모두 정리했어요. 다시 설치하려면 '자동 설치 시작' 을 눌러 주세요.".to_string(),
        });
    }
    snapshot.logs_available = onboarding_logs_available_from_state(&state.0);
    store_onboarding_snapshot(&state.0, &snapshot);
    emit_onboarding_progress(&app, OnboardingProgressEvent {
        phase: "install".to_string(),
        state: snapshot.state.clone(),
        step_id: "complete".to_string(),
        status: "succeeded".to_string(),
        message: format!("{} Claude Code 삭제 완료.", track_label),
        stream_chunk: None,
        shell_target: None,
        observed_path: None,
        error_code: None,
    });
    snapshot
}

/// 네이티브 트랙 삭제 (claude.exe + .claude + PATH). 반환값: exe 가 아직 남아 있으면 true.
fn uninstall_native_track(state: &Arc<Mutex<OnboardingRuntime>>) -> bool {
    let profile = windows_user_profile();
    let bin_dir = profile.as_ref().map(|p| p.join(".local").join("bin"));
    let claude_exe = windows_expected_claude_path();
    let claude_data_dir = profile.as_ref().map(|p| p.join(".claude"));
    let placeholder = windows_placeholder_artifact();

    // 1) claude.exe 삭제 — 실행 중이면 먼저 프로세스를 종료
    if let Some(path) = &claude_exe {
        if path.exists() {
            for image in ["claude.exe"] {
                let state_for_sink = Arc::clone(state);
                let _ = run_command_capture_streamed(
                    "taskkill",
                    &["/F", "/IM", image, "/T"],
                    &[],
                    |title, line| append_onboarding_log(&state_for_sink, title, line),
                );
            }

            let mut removed = false;
            let mut last_err: Option<String> = None;
            for attempt in 0..5 {
                match std::fs::remove_file(path) {
                    Ok(_) => { removed = true; break; }
                    Err(e) => {
                        last_err = Some(e.to_string());
                        std::thread::sleep(std::time::Duration::from_millis(200 + 200 * attempt));
                    }
                }
            }
            if removed {
                append_onboarding_log(state, "[uninstall native] removed", &path.to_string_lossy());
            } else {
                let msg = last_err.unwrap_or_else(|| "unknown".to_string());
                append_onboarding_log(
                    state,
                    "[uninstall native] remove claude.exe failed",
                    &format!("{}: {} — 실행 중인 터미널/에이전트를 모두 닫고 다시 시도하세요.", path.to_string_lossy(), msg),
                );
            }
        } else {
            append_onboarding_log(state, "[uninstall native] skip", &format!("{} 가 이미 없음", path.to_string_lossy()));
        }
    }

    // 2) placeholder artifact (%USERPROFILE%\claude 0-byte 파일) 정리
    if let Some(path) = &placeholder {
        if path.exists() && path.is_file() {
            if let Err(e) = std::fs::remove_file(path) {
                append_onboarding_log(state, "[uninstall native] remove placeholder failed", &format!("{}: {}", path.to_string_lossy(), e));
            } else {
                append_onboarding_log(state, "[uninstall native] removed placeholder", &path.to_string_lossy());
            }
        }
    }

    // 3) %USERPROFILE%\.claude 디렉터리 (설정·세션·크리덴셜) 삭제
    if let Some(path) = &claude_data_dir {
        if path.exists() {
            match std::fs::remove_dir_all(path) {
                Ok(_) => append_onboarding_log(state, "[uninstall native] removed", &path.to_string_lossy()),
                Err(e) => append_onboarding_log(state, "[uninstall native] remove .claude failed", &format!("{}: {}", path.to_string_lossy(), e)),
            }
        }
    }

    // 4) PATH 에서 .local\bin 제거 — 단, 디렉터리가 완전히 비었을 때만.
    if let Some(dir) = &bin_dir {
        let is_empty = std::fs::read_dir(dir)
            .map(|mut it| it.next().is_none())
            .unwrap_or(false);
        if is_empty {
            let dir_str = dir.to_string_lossy().to_string();
            let ps_script = format!(
                "$target = '{}'; $current = [Environment]::GetEnvironmentVariable('Path','User'); if ([string]::IsNullOrEmpty($current)) {{ Write-Output 'PATH_EMPTY'; exit }}; $parts = $current -split ';' | Where-Object {{ $_ -ne '' -and $_ -ne $target }}; $new = ($parts -join ';'); [Environment]::SetEnvironmentVariable('Path', $new, 'User'); Write-Output 'PATH_UPDATED'",
                dir_str.replace('\'', "''")
            );
            let state_for_sink = Arc::clone(state);
            let ps_result = run_command_capture_streamed(
                "powershell",
                &["-NoProfile", "-Command", &ps_script],
                &[],
                |title, line| append_onboarding_log(&state_for_sink, title, line),
            );
            if ps_result.as_ref().map(|c| c.ok).unwrap_or(false) {
                append_onboarding_log(state, "[uninstall native] removed from PATH", &dir_str);
            } else {
                append_onboarding_log(state, "[uninstall native] PATH 제거 실패", "(PowerShell 경로). 필요하면 환경 변수에서 수동 제거하세요.");
            }
            let _ = std::fs::remove_dir(dir);
        } else {
            append_onboarding_log(state, "[uninstall native] keep PATH", &format!("{} 에 다른 파일이 남아 있어 PATH 에서 제거하지 않음", dir.to_string_lossy()));
        }
    }

    claude_exe.as_ref().map(|p| p.exists()).unwrap_or(false)
}

/// WSL 트랙 삭제: WSL 안의 ~/.local/bin/claude + ~/.claude 제거
fn uninstall_wsl_track(state: &Arc<Mutex<OnboardingRuntime>>) {
    append_onboarding_log(state, "[uninstall wsl] running", "wsl -- bash -lc 'rm -f ~/.local/bin/claude'");
    let state_for_sink = Arc::clone(state);
    let rm_bin = run_command_capture_streamed(
        "wsl.exe",
        &["--", "bash", "-lc", "rm -f ~/.local/bin/claude"],
        &[],
        |title, line| append_onboarding_log(&state_for_sink, title, line),
    );
    match &rm_bin {
        Ok(r) if r.ok => append_onboarding_log(state, "[uninstall wsl] removed", "~/.local/bin/claude"),
        Ok(r) => append_onboarding_log(state, "[uninstall wsl] rm failed", &format!("exit={} stderr={}", r.exit_code, r.stderr.trim())),
        Err(e) => append_onboarding_log(state, "[uninstall wsl] rm failed", e),
    }

    append_onboarding_log(state, "[uninstall wsl] running", "wsl -- bash -lc 'rm -rf ~/.claude'");
    let state_for_sink2 = Arc::clone(state);
    let rm_data = run_command_capture_streamed(
        "wsl.exe",
        &["--", "bash", "-lc", "rm -rf ~/.claude"],
        &[],
        |title, line| append_onboarding_log(&state_for_sink2, title, line),
    );
    match &rm_data {
        Ok(r) if r.ok => append_onboarding_log(state, "[uninstall wsl] removed", "~/.claude"),
        Ok(r) => append_onboarding_log(state, "[uninstall wsl] rm .claude failed", &format!("exit={} stderr={}", r.exit_code, r.stderr.trim())),
        Err(e) => append_onboarding_log(state, "[uninstall wsl] rm .claude failed", e),
    }
}

pub(crate) fn start_login_probe(app: tauri::AppHandle, state: tauri::State<OnboardingState>) -> OnboardingSnapshot {
    emit_onboarding_progress(
        &app,
        OnboardingProgressEvent {
            phase: "login".to_string(),
            state: "probing_login".to_string(),
            step_id: "probe_login".to_string(),
            status: "started".to_string(),
            message: "설치는 모두 끝났어요. 터미널에서 `claude` 를 실행해 주세요.".to_string(),
            stream_chunk: None,
            shell_target: None,
            observed_path: None,
            error_code: None,
        },
    );

    let mut snapshot = build_onboarding_snapshot();
    snapshot.state = "success".to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "설치가 모두 끝났어요!".to_string();
    snapshot.detail = Some("새 터미널을 열고 `claude` 를 실행하면 로그인 화면이 떠요. 한 번 로그인하면 이후엔 그냥 바로 쓰시면 돼요.".to_string());
    snapshot.primary_button_label = None;
    store_onboarding_snapshot(&state.0, &snapshot);
    snapshot
}

// ─── WSL availability probing ────────────────────────────────────────────────

/// `wsl.exe --status` 는 드물게 수 초 이상 블록될 수 있어서, 프로세스 단위로 한 번만
/// 계산하고 재사용한다. 사용자가 onboarding 중에 WSL 을 새로 설치/제거하는 일은 거의 없기
/// 때문에 이 단순 캐시로도 UI freeze 를 막으면서 정확도를 유지할 수 있다.
static WSL_AVAILABLE_CACHE: std::sync::OnceLock<bool> = std::sync::OnceLock::new();

fn detect_wsl_available_inner() -> bool {
    let mut status_cmd = std::process::Command::new("wsl.exe");
    status_cmd.arg("--status");
    hide_console(&mut status_cmd);
    let status_ok = status_cmd
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false);
    if !status_ok {
        return false;
    }
    let mut list_cmd = std::process::Command::new("wsl.exe");
    list_cmd.args(["-l", "-q"]);
    hide_console(&mut list_cmd);
    let list_output = match list_cmd.output() {
        Ok(out) if out.status.success() => out.stdout,
        _ => return false,
    };
    let utf8_text = String::from_utf8_lossy(&list_output);
    if utf8_text.lines().any(|l| !l.trim().is_empty() && !l.trim().chars().all(|c| c == '\0')) {
        return true;
    }
    if list_output.len() >= 2 {
        let u16s: Vec<u16> = list_output
            .chunks_exact(2)
            .map(|c| u16::from_le_bytes([c[0], c[1]]))
            .collect();
        let decoded = String::from_utf16_lossy(&u16s);
        return decoded.lines().any(|l| !l.trim().is_empty());
    }
    false
}

pub(crate) fn check_wsl_available() -> bool {
    *WSL_AVAILABLE_CACHE.get_or_init(detect_wsl_available_inner)
}

fn hide_console(cmd: &mut std::process::Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}
