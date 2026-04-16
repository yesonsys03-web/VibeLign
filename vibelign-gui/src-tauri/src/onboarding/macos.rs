#![cfg(target_os = "macos")]
// Populated in subsequent tasks (start_install, verify_macos_shells, etc.)

use super::{
    build_initial_onboarding_snapshot, store_onboarding_snapshot, OnboardingLastError,
    OnboardingSnapshot, OnboardingState,
};

pub(crate) fn start_install(
    _app: tauri::AppHandle,
    state: tauri::State<OnboardingState>,
) -> OnboardingSnapshot {
    let mut unsupported = build_initial_onboarding_snapshot();
    unsupported.state = "blocked".to_string();
    unsupported.next_action = "none".to_string();
    unsupported.headline = "macOS 자동 설치는 다음 단계에서 연결돼요".to_string();
    unsupported.detail = Some("macOS install runner 는 아직 구현되지 않았어요.".to_string());
    unsupported.last_error = Some(OnboardingLastError {
        code: "unsupported_environment".to_string(),
        summary: "macOS install runner 는 다음 Task 에서 채워져요.".to_string(),
        detail: None,
        suggested_action: None,
    });
    store_onboarding_snapshot(&state.0, &unsupported);
    unsupported
}

pub(crate) fn check_xcode_clt() -> bool {
    // Populated in subsequent tasks; default true to avoid warning banner.
    true
}
