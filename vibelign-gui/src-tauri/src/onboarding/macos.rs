#![cfg(target_os = "macos")]

use super::{
    append_onboarding_log, build_initial_onboarding_snapshot, build_onboarding_snapshot,
    clear_onboarding_logs, emit_onboarding_progress, onboarding_logs_available_from_state,
    run_command_capture_with_options, run_command_capture_with_timeout, store_onboarding_snapshot,
    OnboardingLastError, OnboardingProgressEvent, OnboardingRuntime, OnboardingSnapshot,
    OnboardingState,
};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

pub(crate) fn start_install(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    let mut snapshot = build_initial_onboarding_snapshot();
    snapshot.state = "installing_native".to_string();
    snapshot.install_path_kind = "native-cmd".to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "Claude Code 를 설치하고 있어요".to_string();
    snapshot.detail = Some(
        "공식 install.sh 를 실행하는 중이에요. 완료까지 1~2분 걸릴 수 있어요.".to_string(),
    );
    snapshot.primary_button_label = None;
    snapshot.logs_available = onboarding_logs_available_from_state(&state.0);
    store_onboarding_snapshot(&state.0, &snapshot);

    let state_arc = Arc::clone(&state.0);
    let app_handle = app.clone();
    std::thread::spawn(move || {
        clear_onboarding_logs(&state_arc);
        run_macos_install_flow(&state_arc, &app_handle);
    });
    snapshot
}

fn run_macos_install_flow(state: &Arc<Mutex<OnboardingRuntime>>, app: &tauri::AppHandle) {
    emit_onboarding_progress(
        app,
        OnboardingProgressEvent {
            phase: "install".to_string(),
            state: "installing_native".to_string(),
            step_id: "run_macos_installer".to_string(),
            status: "started".to_string(),
            message: "공식 install.sh 를 실행하는 중이에요.".to_string(),
            stream_chunk: None,
            shell_target: Some("bash".to_string()),
            observed_path: None,
            error_code: None,
        },
    );

    append_onboarding_log(
        state,
        "[installer] running",
        "curl -fsSL https://claude.ai/install.sh | bash",
    );

    let state_for_sink = Arc::clone(state);
    let installer = run_command_capture_with_options(
        "/bin/bash",
        &["-c", "curl -fsSL https://claude.ai/install.sh | bash"],
        &[],
        |title, line| append_onboarding_log(&state_for_sink, title, line),
        Some(300),
    );

    let final_snapshot = match installer {
        Ok(result) => {
            append_onboarding_log(state, "[installer stdout]", &result.stdout);
            append_onboarding_log(state, "[installer stderr]", &result.stderr);
            if !result.ok {
                let mut failed = build_initial_onboarding_snapshot();
                failed.state = "needs_manual_step".to_string();
                failed.install_path_kind = "native-cmd".to_string();
                failed.next_action = "share_logs".to_string();
                failed.headline = "설치 스크립트가 실패했어요".to_string();
                failed.detail = Some(
                    "install.sh 종료 코드가 0 이 아니에요. 로그를 확인해 주세요.".to_string(),
                );
                failed.logs_available = onboarding_logs_available_from_state(state);
                failed.last_error = Some(OnboardingLastError {
                    code: "installer_false_success".to_string(),
                    summary: "install.sh 가 비정상 종료했어요.".to_string(),
                    detail: Some(format!("exit_code={}", result.exit_code)),
                    suggested_action: None,
                });
                emit_onboarding_progress(
                    app,
                    OnboardingProgressEvent {
                        phase: "install".to_string(),
                        state: failed.state.clone(),
                        step_id: "run_macos_installer".to_string(),
                        status: "failed".to_string(),
                        message: "install.sh 가 비정상 종료했어요.".to_string(),
                        stream_chunk: None,
                        shell_target: Some("bash".to_string()),
                        observed_path: None,
                        error_code: Some("installer_false_success".to_string()),
                    },
                );
                failed
            } else {
                emit_onboarding_progress(
                    app,
                    OnboardingProgressEvent {
                        phase: "install".to_string(),
                        state: "verifying_shells".to_string(),
                        step_id: "run_macos_installer".to_string(),
                        status: "succeeded".to_string(),
                        message: "install.sh 실행이 끝나서 새 셸 검증 단계로 넘어가요."
                            .to_string(),
                        stream_chunk: None,
                        shell_target: Some("bash".to_string()),
                        observed_path: None,
                        error_code: None,
                    },
                );
                verify_macos_shells(state, app)
            }
        }
        Err(err) => {
            let mut failed = build_initial_onboarding_snapshot();
            failed.state = "blocked".to_string();
            failed.next_action = "none".to_string();
            failed.headline = "설치 프로세스를 시작하지 못했어요".to_string();
            failed.detail = Some(err.clone());
            failed.logs_available = onboarding_logs_available_from_state(state);
            failed.last_error = Some(OnboardingLastError {
                code: "unknown".to_string(),
                summary: "설치 프로세스 spawn 자체가 실패했어요.".to_string(),
                detail: Some(err),
                suggested_action: None,
            });
            failed
        }
    };

    store_onboarding_snapshot(state, &final_snapshot);
}

fn verify_macos_shells(
    state: &Arc<Mutex<OnboardingRuntime>>,
    app: &tauri::AppHandle,
) -> OnboardingSnapshot {
    let mut snapshot = build_onboarding_snapshot();
    snapshot.state = "verifying_shells".to_string();
    snapshot.install_path_kind = "native-cmd".to_string();
    snapshot.next_action = "none".to_string();
    snapshot.headline = "새 셸에서 Claude 설치를 검증하는 중이에요".to_string();
    snapshot.detail = Some(
        "zsh 와 bash 에서 `claude` 실행 가능 여부를 확인하고 있어요.".to_string(),
    );
    snapshot.primary_button_label = None;
    snapshot.logs_available = onboarding_logs_available_from_state(state);
    emit_onboarding_progress(
        app,
        OnboardingProgressEvent {
            phase: "verify".to_string(),
            state: snapshot.state.clone(),
            step_id: "verify_version".to_string(),
            status: "started".to_string(),
            message: "zsh/bash 에서 `claude --version` 을 확인하는 중이에요.".to_string(),
            stream_chunk: None,
            shell_target: None,
            observed_path: None,
            error_code: None,
        },
    );

    append_onboarding_log(state, "[verify] running", "/bin/zsh -lc 'claude --version'");
    let zsh_result =
        run_command_capture_with_timeout("/bin/zsh", &["-lc", "claude --version"], &[], 30).ok();
    if let Some(r) = &zsh_result {
        append_onboarding_log(state, "[verify zsh stdout]", &r.stdout);
        append_onboarding_log(state, "[verify zsh stderr]", &r.stderr);
    }

    append_onboarding_log(state, "[verify] running", "/bin/bash -lc 'claude --version'");
    let bash_result =
        run_command_capture_with_timeout("/bin/bash", &["-lc", "claude --version"], &[], 30).ok();
    if let Some(r) = &bash_result {
        append_onboarding_log(state, "[verify bash stdout]", &r.stdout);
        append_onboarding_log(state, "[verify bash stderr]", &r.stderr);
    }

    let home = std::env::var("HOME").unwrap_or_default();
    let claude_bin = PathBuf::from(&home).join(".local/bin/claude");
    let direct_version = if claude_bin.exists() {
        append_onboarding_log(
            state,
            "[verify] running direct",
            &format!("{} --version (timeout 15s)", claude_bin.display()),
        );
        run_command_capture_with_timeout(
            claude_bin.to_str().unwrap_or("claude"),
            &["--version"],
            &[],
            15,
        )
        .ok()
    } else {
        None
    };
    if let Some(r) = &direct_version {
        append_onboarding_log(state, "[verify direct stdout]", &r.stdout);
        append_onboarding_log(state, "[verify direct stderr]", &r.stderr);
    }

    let zsh_ok = zsh_result.as_ref().map(|r| r.ok).unwrap_or(false);
    let bash_ok = bash_result.as_ref().map(|r| r.ok).unwrap_or(false);
    let direct_ok = direct_version.as_ref().map(|r| r.ok).unwrap_or(false);
    let claude_on_path = zsh_ok || bash_ok;

    snapshot.logs_available = onboarding_logs_available_from_state(state);
    snapshot.diagnostics.claude_on_path = Some(claude_on_path);
    snapshot.diagnostics.claude_version_ok = Some(claude_on_path || direct_ok);
    snapshot.diagnostics.claude_doctor_ok = Some(false);
    snapshot.diagnostics.login_status_known = Some(false);

    if zsh_ok && bash_ok {
        snapshot.state = "login_required".to_string();
        snapshot.next_action = "start_login".to_string();
        snapshot.headline = "설치가 잘 끝났어요!".to_string();
        snapshot.detail = Some(
            "새 터미널을 열고 `claude` 를 실행하면 로그인 화면이 떠요.".to_string(),
        );
        snapshot.primary_button_label = Some("다음으로".to_string());
        store_onboarding_snapshot(state, &snapshot);
        emit_onboarding_progress(
            app,
            OnboardingProgressEvent {
                phase: "verify".to_string(),
                state: snapshot.state.clone(),
                step_id: "verify_version".to_string(),
                status: "succeeded".to_string(),
                message: "zsh/bash 모두 통과했어요.".to_string(),
                stream_chunk: None,
                shell_target: None,
                observed_path: Some(claude_bin.to_string_lossy().to_string()),
                error_code: None,
            },
        );
        return snapshot;
    }

    if direct_ok {
        snapshot.state = "needs_manual_step".to_string();
        snapshot.next_action = "add_to_path".to_string();
        snapshot.headline = "Claude는 설치됐지만 PATH 연결이 아직 안 됐어요".to_string();
        snapshot.detail = Some(format!(
            "설치 자체는 성공했어요 (`{}`). zsh/bash rc 파일에 PATH 를 자동으로 추가해 드릴게요.",
            claude_bin.display()
        ));
        snapshot.primary_button_label = Some("PATH 자동 추가".to_string());
        snapshot.last_error = Some(OnboardingLastError {
            code: "path_not_configured".to_string(),
            summary: "새 셸의 PATH 에 `~/.local/bin` 이 들어있지 않아요.".to_string(),
            detail: Some(format!("{}/.local/bin", home)),
            suggested_action: Some("add_to_path".to_string()),
        });
        store_onboarding_snapshot(state, &snapshot);
        return snapshot;
    }

    snapshot.state = "needs_manual_step".to_string();
    snapshot.next_action = "share_logs".to_string();
    snapshot.headline = "설치 검증이 통과하지 않았어요".to_string();
    snapshot.detail = Some(
        "install.sh 는 끝났지만 zsh/bash 어느 쪽에서도 `claude` 를 찾지 못했어요.".to_string(),
    );
    snapshot.last_error = Some(OnboardingLastError {
        code: "installer_false_success".to_string(),
        summary: "설치 스크립트가 끝났지만 새 셸 검증은 통과하지 못했어요.".to_string(),
        detail: Some(format!(
            "zshOk={}, bashOk={}, directOk={}",
            zsh_ok, bash_ok, direct_ok
        )),
        suggested_action: None,
    });
    store_onboarding_snapshot(state, &snapshot);
    emit_onboarding_progress(
        app,
        OnboardingProgressEvent {
            phase: "verify".to_string(),
            state: snapshot.state.clone(),
            step_id: "verify_version".to_string(),
            status: "failed".to_string(),
            message: "zsh/bash 둘 다 실패했어요.".to_string(),
            stream_chunk: None,
            shell_target: None,
            observed_path: None,
            error_code: Some("installer_false_success".to_string()),
        },
    );
    snapshot
}

pub(crate) fn retry_verification(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    let mut progressing = build_initial_onboarding_snapshot();
    progressing.state = "verifying_shells".to_string();
    progressing.install_path_kind = "native-cmd".to_string();
    progressing.next_action = "none".to_string();
    progressing.headline = "설치 결과를 다시 확인하는 중이에요".to_string();
    progressing.primary_button_label = None;
    store_onboarding_snapshot(&state.0, &progressing);

    let state_arc = Arc::clone(&state.0);
    let app_handle = app.clone();
    std::thread::spawn(move || {
        let final_snapshot = verify_macos_shells(&state_arc, &app_handle);
        store_onboarding_snapshot(&state_arc, &final_snapshot);
    });
    progressing
}

pub(crate) fn check_xcode_clt() -> bool {
    true
}
