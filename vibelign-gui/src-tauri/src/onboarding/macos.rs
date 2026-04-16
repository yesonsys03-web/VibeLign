#![cfg(target_os = "macos")]

use super::{
    append_onboarding_log, build_initial_onboarding_snapshot, build_onboarding_snapshot,
    clear_onboarding_logs, emit_onboarding_progress, onboarding_logs_available_from_state,
    run_command_capture_with_options, store_onboarding_snapshot, OnboardingLastError,
    OnboardingProgressEvent, OnboardingRuntime, OnboardingSnapshot, OnboardingState,
};
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
    _app: &tauri::AppHandle,
) -> OnboardingSnapshot {
    let _ = state;
    let mut snapshot = build_onboarding_snapshot();
    snapshot.state = "verifying_shells".to_string();
    snapshot
}

pub(crate) fn check_xcode_clt() -> bool {
    true
}
