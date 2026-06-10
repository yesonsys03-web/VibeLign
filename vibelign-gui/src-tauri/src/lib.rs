// === ANCHOR: LIB_START ===
mod code_access;
mod code_diff;
mod commands;
mod docs_access;
mod git_status;
mod onboarding;
mod vib_path;

use std::sync::{Arc, Mutex};

#[cfg(not(debug_assertions))]
use tauri::Manager;

use onboarding::{OnboardingRuntime, OnboardingState};

pub use onboarding::testing;

// ─── 앱 진입점 ─────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let (watch_state, watch_shutdown) = commands::watch::new_state_pair();
    let gui_error_state = commands::gui_error::GuiErrorState::new();
    let onboarding_inner: Arc<Mutex<OnboardingRuntime>> = Arc::new(Mutex::new(OnboardingRuntime {
        snapshot: Some(onboarding::build_initial_onboarding_snapshot()),
        logs: String::new(),
    }));

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            #[cfg(all(desktop, feature = "updater"))]
            app.handle()
                .plugin(tauri_plugin_updater::Builder::new().build())?;

            // 번들된 vib 실행파일 경로를 OnceLock 에 주입한다.
            // PyInstaller onedir 빌드는 `vib` 와 sibling `_internal/` 이 함께 있어야 실행되므로
            // Tauri PathResolver 의 resource_dir 를 통째로 보존하는 이 경로만 안전하다.
            #[cfg(not(debug_assertions))]
            {
                if let Ok(resource_dir) = app.path().resource_dir() {
                    #[cfg(target_os = "windows")]
                    let bundled = resource_dir.join("vib-runtime").join("vib.exe");
                    #[cfg(not(target_os = "windows"))]
                    let bundled = resource_dir.join("vib-runtime").join("vib");
                    let _ = vib_path::BUNDLED_VIB_PATH.set(bundled);
                }
            }
            #[cfg(debug_assertions)]
            let _ = &app;

            // 기존 gui_config.json 키를 api_keys.json으로 마이그레이션 (최초 1회)
            commands::settings::migrate_legacy_keys();
            // vib CLI 자동 PATH 설치는 버전당 1회만 수행한다.
            // Why: 매 시작마다 `~/.local/bin/vib` 를 덮어쓰면 `uv tool install`/`pipx` 로
            //      사용자가 직접 관리하던 바이너리가 말없이 교체되는 문제가 있었다.
            if !commands::settings::cli_installed_for_current_version() {
                match vib_path::install_cli_to_path() {
                    Ok(_) => commands::settings::mark_cli_installed_for_current_version(),
                    Err(e) => eprintln!("VibeLign: CLI PATH 설치 실패 — {e}"),
                }
            }
            // 앱 이동/재설치로 래퍼 타겟이 stale 해지는 경우를 매 부팅 시 재검증한다.
            // Why: onedir 래퍼는 번들 vib 의 절대경로를 품고 있어 .app 이 다른 폴더로 옮겨지면
            //      터미널 `vib` 가 "No such file or directory" 로 깨진다.
            #[cfg(not(debug_assertions))]
            if let Some(bundled) = vib_path::find_bundled_vib() {
                if let Err(e) = vib_path::refresh_gui_wrapper(&bundled) {
                    eprintln!("VibeLign: CLI 래퍼 갱신 실패 — {e}");
                }
            }
            // vib 프리워밍: 백그라운드에서 `vib --version` 을 한 번 돌려 PyInstaller onefile
            // 압축 해제와 OS 파일 캐시를 미리 데워둔다. 사용자가 Doctor/DocsViewer 등 첫
            // 서브프로세스 호출을 할 때 체감 콜드스타트가 크게 줄어든다.
            // Why: 릴리스 빌드에서 문서 클릭·Doctor 진입이 dev 모드보다 느렸던 주 원인이
            //      PyInstaller onefile 압축 해제였다.
            if let Some(vib) = vib_path::find_runtime_vib() {
                std::thread::spawn(move || {
                    let mut cmd = std::process::Command::new(&vib);
                    cmd.arg("--version")
                        .stdin(std::process::Stdio::null())
                        .stdout(std::process::Stdio::null())
                        .stderr(std::process::Stdio::null())
                        .env("PATH", commands::platform::augmented_vib_path())
                        .env("PYTHONUTF8", "1")
                        .env("PYTHONIOENCODING", "utf-8");
                    commands::platform::hide_console(&mut cmd);
                    let _ = cmd.status();
                });
            }
            Ok(())
        })
        .manage(watch_state)
        .manage(gui_error_state)
        .manage(OnboardingState(onboarding_inner))
        .invoke_handler(tauri::generate_handler![
            commands::vib_bridge::get_vib_path,
            commands::settings::setup_cli_path,
            onboarding::get_onboarding_snapshot,
            onboarding::start_native_install,
            onboarding::start_wsl_install,
            onboarding::retry_verification,
            onboarding::add_claude_to_user_path,
            onboarding::uninstall_claude_code,
            onboarding::start_login_probe,
            onboarding::get_onboarding_logs,
            commands::vib_bridge::run_vib,
            commands::vib_bridge::run_vib_with_progress,
            commands::vib_bridge::run_engine_request_direct,
            commands::planning::create_planning_template,
            commands::planning::append_planning_with_agents,
            commands::planning::load_latest_planning_session,
            commands::planning_chat::create_planning_chat_session,
            commands::planning_chat::append_planning_chat_turn,
            commands::planning_chat::load_latest_planning_chat_session,
            commands::planning_chat::list_planning_chat_sessions,
            commands::planning_chat::delete_planning_chat_session,
            commands::planning_chat_trash::restore_planning_chat_session,
            commands::planning_chat_trash::list_trashed_planning_sessions,
            commands::planning_chat_trash::empty_planning_trash,
            commands::planning_chat::load_planning_chat_session,
            commands::planning_chat::save_planning_chat_as_markdown,
            commands::planning_chat_retry::retry_planning_persona,
            commands::planning_chat_cards::update_card,
            commands::error_logs::read_error_logs,
            commands::error_logs::clear_error_logs,
            commands::settings::save_api_key,
            commands::settings::load_api_key,
            commands::settings::delete_api_key,
            commands::settings::save_provider_api_key,
            commands::settings::delete_provider_api_key,
            commands::settings::load_provider_api_keys,
            commands::settings::save_recent_projects,
            commands::settings::load_recent_projects,
            commands::watch::start_watch,
            commands::watch::stop_watch,
            commands::watch::watch_status,
            commands::watch::get_watch_logs,
            commands::watch::get_watch_errors,
            commands::platform::open_folder,
            commands::code::read_code_file,
            commands::code::read_code_file_diff,
            commands::code::list_code_files,
            commands::code::list_changed_files,
            commands::docs::read_file,
            commands::docs::list_docs_index,
            commands::docs::rebuild_docs_index,
            commands::docs::read_docs_visual,
            commands::docs::read_docs_html,
            commands::docs::list_extra_doc_sources,
            commands::docs::add_extra_doc_source,
            commands::docs::remove_extra_doc_source,
            commands::docs::enhance_doc_with_ai,
            commands::settings::get_env_key_status,
            commands::settings::get_planning_personas,
            commands::settings::set_planning_personas,
            commands::planning_persona::planning_provider_status,
            commands::project_summary::read_project_summary,
            commands::gui_error::record_gui_error,
            onboarding::check_git_installed,
            onboarding::check_wsl_available,
            onboarding::check_xcode_clt,
            onboarding::detect_installed_tools,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| match event {
            tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. } => {
                commands::watch::stop_for_exit(&watch_shutdown);
            }
            _ => {}
        });
}
// === ANCHOR: LIB_END ===
