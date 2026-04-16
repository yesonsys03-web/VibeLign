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
    std::process::Command::new("xcode-select")
        .arg("-p")
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}

pub(crate) const VIBELIGN_MARKER_BEGIN: &str = "# >>> vibelign >>>";
pub(crate) const VIBELIGN_MARKER_END: &str = "# <<< vibelign <<<";

const VIBELIGN_MARKER_BODY: &str = "\
# VibeLign onboarding 이 ~/.local/bin 을 PATH 에 추가했어요.
# 이 블록 전체를 지우면 PATH 추가도 같이 사라져요.
export PATH=\"$HOME/.local/bin:$PATH\"";

pub(crate) const VIBELIGN_RC_FILES: &[&str] = &[".zshrc", ".bash_profile", ".bashrc", ".profile"];

pub(crate) fn ensure_macos_path_marker_in_home(
    home: &std::path::Path,
) -> Result<Vec<std::path::PathBuf>, String> {
    let mut touched = Vec::new();
    for rc in VIBELIGN_RC_FILES {
        let path = home.join(rc);
        let existing = match std::fs::read_to_string(&path) {
            Ok(s) => s,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => String::new(),
            Err(e) => return Err(format!("{} 읽기 실패: {}", path.display(), e)),
        };
        if existing.contains(VIBELIGN_MARKER_BEGIN) && existing.contains(VIBELIGN_MARKER_END) {
            continue;
        }

        let mut new_contents = existing;
        if !new_contents.is_empty() && !new_contents.ends_with('\n') {
            new_contents.push('\n');
        }
        new_contents.push_str(VIBELIGN_MARKER_BEGIN);
        new_contents.push('\n');
        new_contents.push_str(VIBELIGN_MARKER_BODY);
        new_contents.push('\n');
        new_contents.push_str(VIBELIGN_MARKER_END);
        new_contents.push('\n');

        std::fs::write(&path, new_contents)
            .map_err(|e| format!("{} 쓰기 실패: {}", path.display(), e))?;
        touched.push(path);
    }
    Ok(touched)
}

fn ensure_macos_path_marker() -> Result<Vec<std::path::PathBuf>, String> {
    let home = std::env::var("HOME").map_err(|_| "HOME 환경변수를 읽을 수 없어요".to_string())?;
    ensure_macos_path_marker_in_home(std::path::Path::new(&home))
}

pub(crate) fn add_to_user_path(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    clear_onboarding_logs(&state.0);
    match ensure_macos_path_marker() {
        Ok(touched) => {
            for p in &touched {
                append_onboarding_log(&state.0, "[path-fix] updated", &p.to_string_lossy());
            }
            let state_arc = Arc::clone(&state.0);
            let app_handle = app.clone();
            std::thread::spawn(move || {
                let final_snapshot = verify_macos_shells(&state_arc, &app_handle);
                store_onboarding_snapshot(&state_arc, &final_snapshot);
            });
            let mut progressing = build_initial_onboarding_snapshot();
            progressing.state = "verifying_shells".to_string();
            progressing.install_path_kind = "native-cmd".to_string();
            progressing.next_action = "none".to_string();
            progressing.headline = "PATH 를 추가하고 다시 확인하는 중이에요".to_string();
            progressing.primary_button_label = None;
            progressing.logs_available = onboarding_logs_available_from_state(&state.0);
            store_onboarding_snapshot(&state.0, &progressing);
            progressing
        }
        Err(err) => {
            let mut failed = build_initial_onboarding_snapshot();
            failed.state = "blocked".to_string();
            failed.next_action = "none".to_string();
            failed.headline = "PATH 파일을 고치지 못했어요".to_string();
            failed.detail = Some(err.clone());
            failed.last_error = Some(OnboardingLastError {
                code: "unknown".to_string(),
                summary: "rc 파일에 PATH marker 를 추가하지 못했어요.".to_string(),
                detail: Some(err),
                suggested_action: None,
            });
            store_onboarding_snapshot(&state.0, &failed);
            failed
        }
    }
}

fn remove_vibelign_marker_block(path: &std::path::Path) -> Result<bool, String> {
    let contents = match std::fs::read_to_string(path) {
        Ok(s) => s,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(e) => return Err(format!("{} 읽기 실패: {}", path.display(), e)),
    };
    let Some(start) = contents.find(VIBELIGN_MARKER_BEGIN) else {
        return Ok(false);
    };
    let Some(end_rel) = contents[start..].find(VIBELIGN_MARKER_END) else {
        return Ok(false);
    };
    let end = start + end_rel + VIBELIGN_MARKER_END.len();
    let end = if contents[end..].starts_with('\n') {
        end + 1
    } else {
        end
    };
    let mut new_contents = String::new();
    new_contents.push_str(&contents[..start]);
    new_contents.push_str(&contents[end..]);
    std::fs::write(path, new_contents)
        .map_err(|e| format!("{} 쓰기 실패: {}", path.display(), e))?;
    Ok(true)
}

pub(crate) fn uninstall_macos_track_in_home(home: &std::path::Path) -> Result<(), String> {
    let targets: Vec<std::path::PathBuf> = vec![
        home.join(".local/bin/claude"),
        home.join(".local/share/claude"),
        home.join(".claude"),
        home.join(".claude.json"),
    ];
    for target in &targets {
        if !target.exists() {
            continue;
        }
        let result = if target.is_dir() {
            std::fs::remove_dir_all(target)
        } else {
            std::fs::remove_file(target)
        };
        if let Err(e) = result {
            return Err(format!("{} 삭제 실패: {}", target.display(), e));
        }
    }
    for rc in VIBELIGN_RC_FILES {
        remove_vibelign_marker_block(&home.join(rc))?;
    }
    Ok(())
}

fn uninstall_macos_track_runtime(state: &Arc<Mutex<OnboardingRuntime>>) -> Result<(), String> {
    let home = std::env::var("HOME").map_err(|_| "HOME 환경변수를 읽을 수 없어요".to_string())?;
    let home_path = std::path::PathBuf::from(&home);
    append_onboarding_log(state, "[uninstall macos] start", &format!("HOME={}", home));
    let result = uninstall_macos_track_in_home(&home_path);
    match &result {
        Ok(_) => append_onboarding_log(
            state,
            "[uninstall macos] done",
            "모든 타겟 삭제 및 rc marker 제거 완료",
        ),
        Err(e) => append_onboarding_log(state, "[uninstall macos] failed", e),
    }
    result
}

pub(crate) fn uninstall(
    app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    clear_onboarding_logs(&state.0);
    let ok = uninstall_macos_track_runtime(&state.0).is_ok();
    let mut snapshot = build_initial_onboarding_snapshot();
    snapshot.logs_available = onboarding_logs_available_from_state(&state.0);
    if ok {
        snapshot.headline = "Claude Code 를 삭제했어요".to_string();
        snapshot.detail = Some(
            "바이너리·설정·rc PATH 블록까지 모두 정리했어요. 다시 설치하려면 '자동 설치 시작' 을 눌러 주세요.".to_string(),
        );
    } else {
        snapshot.headline = "삭제 도중 문제가 있었어요".to_string();
        snapshot.detail = Some(
            "로그를 확인하고 남은 파일이 있으면 수동으로 지워 주세요.".to_string(),
        );
    }
    store_onboarding_snapshot(&state.0, &snapshot);
    emit_onboarding_progress(
        &app,
        OnboardingProgressEvent {
            phase: "install".to_string(),
            state: snapshot.state.clone(),
            step_id: "complete".to_string(),
            status: if ok {
                "succeeded".to_string()
            } else {
                "failed".to_string()
            },
            message: if ok {
                "macOS Claude Code 삭제 완료.".to_string()
            } else {
                "macOS Claude Code 삭제 실패.".to_string()
            },
            stream_chunk: None,
            shell_target: None,
            observed_path: None,
            error_code: if ok { None } else { Some("unknown".to_string()) },
        },
    );
    snapshot
}
