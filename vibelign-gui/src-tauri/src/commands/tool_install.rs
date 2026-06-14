// ANCHOR: TOOL_INSTALL_START
use serde::Serialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum AuthKind {
    None,
    Login,
}

#[derive(Debug, Clone, Serialize)]
pub(crate) struct ToolInstaller {
    pub id: &'static str,
    pub display_name: &'static str,
    pub probe_binary: &'static str,
    /// (program, args) — macOS
    pub mac_program: &'static str,
    pub mac_args: &'static [&'static str],
    /// (program, args) — Windows
    pub win_program: &'static str,
    pub win_args: &'static [&'static str],
    pub auth: AuthKind,
    pub auth_hint: &'static str,
    pub manual_url: &'static str,
    pub recommended_for_beginner: bool,
    /// OS별 제거 명령. None = 그 OS는 안내 폴백.
    pub mac_uninstall: Option<(&'static str, &'static [&'static str])>,
    pub win_uninstall: Option<(&'static str, &'static [&'static str])>,
    /// true 면 mac 에서 probe_binary 경로를 resolve 후 remove_file (agy).
    /// Windows 에서는 이 플래그를 무시하고 win_uninstall 명령 또는 안내 폴백으로 진행.
    pub uninstall_remove_binary: bool,
    /// 안내 폴백 시 보여줄 수동 제거 단계.
    pub uninstall_hint: &'static str,
    /// 안내 폴백 시 열 공식 문서 URL.
    pub uninstall_url: &'static str,
}

const OPENCODE: ToolInstaller = ToolInstaller {
    id: "opencode", display_name: "OpenCode", probe_binary: "opencode",
    mac_program: "bash", mac_args: &["-c", "curl -fsSL https://opencode.ai/install | bash"],
    win_program: "npm", win_args: &["install", "-g", "opencode-ai"],
    auth: AuthKind::None,
    auth_hint: "무료 모델이라 추가 로그인이 필요 없어요 — 바로 쓸 수 있어요.",
    manual_url: "https://opencode.ai/download", recommended_for_beginner: true,
    mac_uninstall: Some(("opencode", &["uninstall", "--keep-config", "--keep-data", "--force"])),
    win_uninstall: Some(("npm", &["uninstall", "-g", "opencode-ai"])),
    uninstall_remove_binary: false,
    uninstall_hint: "제거가 안 되면 `npm uninstall -g opencode-ai` 또는 설치 시 사용한 방법으로 지워주세요.",
    uninstall_url: "https://opencode.ai/docs/cli/",
};
const CODEX: ToolInstaller = ToolInstaller {
    id: "codex", display_name: "Codex", probe_binary: "codex",
    mac_program: "npm", mac_args: &["install", "-g", "@openai/codex"],
    win_program: "powershell", win_args: &["-ExecutionPolicy", "Bypass", "-c", "irm https://chatgpt.com/codex/install.ps1 | iex"],
    auth: AuthKind::Login,
    auth_hint: "설치 후 OpenAI 로그인이 필요해요 — 터미널에서 `codex` 를 한 번 실행해 로그인하세요.",
    manual_url: "https://www.npmjs.com/package/@openai/codex", recommended_for_beginner: false,
    mac_uninstall: Some(("npm", &["uninstall", "-g", "@openai/codex"])),
    win_uninstall: None,
    uninstall_remove_binary: false,
    uninstall_hint: "`npm uninstall -g @openai/codex` 를 실행하거나, npm 으로 설치하지 않았다면 설치 페이지의 제거 안내를 따라주세요.",
    uninstall_url: "https://www.npmjs.com/package/@openai/codex",
};
const AGY: ToolInstaller = ToolInstaller {
    id: "agy", display_name: "Antigravity", probe_binary: "agy",
    mac_program: "bash", mac_args: &["-c", "curl -fsSL https://antigravity.google/cli/install.sh | bash"],
    win_program: "powershell", win_args: &["-ExecutionPolicy", "Bypass", "-c", "irm https://antigravity.google/cli/install.ps1 | iex"],
    auth: AuthKind::Login,
    auth_hint: "설치 후 Google 로그인이 필요해요 — `agy` 를 처음 실행하면 브라우저 로그인이 열려요.",
    manual_url: "https://antigravity.google/docs/cli-install", recommended_for_beginner: false,
    mac_uninstall: None,
    win_uninstall: None,
    uninstall_remove_binary: true,
    uninstall_hint: "macOS: PATH 의 agy 실행파일(예: ~/.local/bin/agy)을 직접 지워주세요. Windows: 설정 > 앱 > 설치된 앱에서 'Antigravity CLI' 를 제거하세요. ANTIGRAVITY_API_KEY 환경변수가 있으면 함께 지워주세요.",
    uninstall_url: "https://antigravity.google/docs/cli-install",
};

pub(crate) fn tool_installer(id: &str) -> Option<&'static ToolInstaller> {
    match id {
        "opencode" => Some(&OPENCODE),
        "codex" => Some(&CODEX),
        "agy" => Some(&AGY),
        _ => None,
    }
}

/// os: "macos" | "windows" (그 외는 None → 가이드 수동 폴백). 반환 (program, args).
pub(crate) fn install_command(t: &ToolInstaller, os: &str) -> Option<(String, Vec<String>)> {
    match os {
        "macos" => Some((t.mac_program.to_string(), t.mac_args.iter().map(|s| s.to_string()).collect())),
        "windows" => Some((t.win_program.to_string(), t.win_args.iter().map(|s| s.to_string()).collect())),
        _ => None,
    }
}

/// os: "macos" | "windows". 그 OS에 제거 명령이 없으면 None(→ 안내 폴백 또는 remove_binary).
pub(crate) fn uninstall_command(t: &ToolInstaller, os: &str) -> Option<(String, Vec<String>)> {
    let (prog, args) = match os {
        "macos" => t.mac_uninstall?,
        "windows" => t.win_uninstall?,
        _ => return None,
    };
    Some((prog.to_string(), args.iter().map(|s| s.to_string()).collect()))
}

#[cfg(target_os = "macos")]
fn current_os() -> &'static str { "macos" }
#[cfg(target_os = "windows")]
fn current_os() -> &'static str { "windows" }
#[cfg(not(any(target_os = "macos", target_os = "windows")))]
fn current_os() -> &'static str { "other" }
use std::io::{BufRead, BufReader};
use super::platform::{augmented_vib_path, hide_console};
use super::planning_persona::find_executable;

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ToolInstallResult {
    pub installed: bool,
    pub exit_code: Option<i32>,
    /// none/login — 설치됐을 때 다음에 필요한 인증
    pub auth: AuthKind,
    pub auth_hint: String,
    /// 자동설치 불가/실패 시 수동 폴백용
    pub manual_url: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ToolInstallOutput {
    pub id: String,
    pub stream: String,
    pub line: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct ToolUninstallResult {
    /// 이 호출 후 바이너리가 없으면 true (애초에 설치 안 돼 있던 경우도 포함).
    pub removed: bool,
    pub exit_code: Option<i32>,
    /// removed=false 일 때 보여줄 수동 제거 안내.
    pub manual_hint: String,
    pub manual_url: String,
}

#[tauri::command]
pub(crate) fn tool_install_status(id: String) -> Result<bool, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    Ok(find_executable(t.probe_binary).is_some())
}

const SPAWN_FAIL: &str = "작업 실행에 실패했어요";

#[tauri::command]
pub(crate) async fn install_tool(
    app: tauri::AppHandle,
    id: String,
) -> Result<ToolInstallResult, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    let Some((program, args)) = install_command(t, current_os()) else {
        // 지원 안 되는 OS → 가이드 수동 폴백
        return Ok(ToolInstallResult {
            installed: false,
            exit_code: None,
            auth: t.auth,
            auth_hint: t.auth_hint.to_string(),
            manual_url: t.manual_url.to_string(),
        });
    };
    // 설치 프로세스 spawn + drain + wait 은 최대 수 분 걸릴 수 있으므로 blocking 풀로 뺀다.
    let probe_binary = t.probe_binary;
    let auth = t.auth;
    let auth_hint = t.auth_hint.to_string();
    let manual_url = t.manual_url.to_string();
    tauri::async_runtime::spawn_blocking(move || {
        use tauri::Emitter;
        let mut cmd = std::process::Command::new(&program);
        cmd.args(&args);
        cmd.env("PATH", augmented_vib_path());
        cmd.stdout(std::process::Stdio::piped());
        cmd.stderr(std::process::Stdio::piped());
        hide_console(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| format!("설치 실행 실패: {e}"))?;

        // stderr 를 별도 스레드에서 동시에 드레인 — 순차 읽기 데드락 방지(설치기는 stderr 수다스러움).
        let stderr_handle = child.stderr.take().map(|err| {
            let app2 = app.clone();
            let id2 = id.clone();
            std::thread::spawn(move || {
                for line in BufReader::new(err).lines().map_while(Result::ok) {
                    let _ = app2.emit(
                        "tool-install-output",
                        ToolInstallOutput { id: id2.clone(), stream: "stderr".into(), line },
                    );
                }
            })
        });
        if let Some(out) = child.stdout.take() {
            for line in BufReader::new(out).lines().map_while(Result::ok) {
                let _ = app.emit(
                    "tool-install-output",
                    ToolInstallOutput { id: id.clone(), stream: "stdout".into(), line },
                );
            }
        }
        if let Some(h) = stderr_handle {
            let _ = h.join();
        }
        let status = child.wait().map_err(|e| format!("설치 대기 실패: {e}"))?;
        // 종료 후 새로 PATH 해석해 프로브(설치 직후 PATH 반영 확인).
        let installed = find_executable(probe_binary).is_some();
        Ok(ToolInstallResult {
            installed,
            exit_code: status.code(),
            auth,
            auth_hint,
            manual_url,
        })
    })
    .await
    .map_err(|_| SPAWN_FAIL.to_string())?
}
// ANCHOR: TOOL_INSTALL_END

// ANCHOR: TOOL_UNINSTALL_START
/// resolve된 실행파일 경로(Option)를 받아 있으면 삭제하고, 호출 후 없으면 true.
/// 파일 1개만 remove_file — 비재귀·셸 미경유. None 이면 이미 없으므로 true.
fn remove_resolved_binary(resolved: Option<std::path::PathBuf>) -> std::io::Result<bool> {
    match resolved {
        Some(path) => {
            std::fs::remove_file(&path)?;
            Ok(!path.exists())
        }
        None => Ok(true),
    }
}

#[tauri::command]
pub(crate) async fn uninstall_tool(
    app: tauri::AppHandle,
    id: String,
) -> Result<ToolUninstallResult, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    let manual_hint = t.uninstall_hint.to_string();
    let manual_url = t.uninstall_url.to_string();

    // 1) agy mac: 명령이 없어 resolve된 단일 바이너리만 삭제(파일 1개, 비재귀, 셸 미경유).
    if t.uninstall_remove_binary && current_os() == "macos" {
        let removed = remove_resolved_binary(find_executable(t.probe_binary))
            .map_err(|e| format!("제거 실패: {e}"))?;
        return Ok(ToolUninstallResult { removed, exit_code: None, manual_hint, manual_url });
    }

    // 2) 제거 명령이 있으면 실행. 없으면 안내 폴백.
    let Some((program, args)) = uninstall_command(t, current_os()) else {
        return Ok(ToolUninstallResult { removed: false, exit_code: None, manual_hint, manual_url });
    };

    let probe_binary = t.probe_binary;
    tauri::async_runtime::spawn_blocking(move || {
        use tauri::Emitter;
        let mut cmd = std::process::Command::new(&program);
        cmd.args(&args);
        cmd.env("PATH", augmented_vib_path());
        cmd.stdout(std::process::Stdio::piped());
        cmd.stderr(std::process::Stdio::piped());
        hide_console(&mut cmd);
        let mut child = cmd.spawn().map_err(|e| format!("제거 실행 실패: {e}"))?;

        let stderr_handle = child.stderr.take().map(|err| {
            let app2 = app.clone();
            let id2 = id.clone();
            std::thread::spawn(move || {
                for line in BufReader::new(err).lines().map_while(Result::ok) {
                    let _ = app2.emit(
                        "tool-install-output",
                        ToolInstallOutput { id: id2.clone(), stream: "stderr".into(), line },
                    );
                }
            })
        });
        if let Some(out) = child.stdout.take() {
            for line in BufReader::new(out).lines().map_while(Result::ok) {
                let _ = app.emit(
                    "tool-install-output",
                    ToolInstallOutput { id: id.clone(), stream: "stdout".into(), line },
                );
            }
        }
        if let Some(h) = stderr_handle {
            let _ = h.join();
        }
        let status = child.wait().map_err(|e| format!("제거 대기 실패: {e}"))?;
        // 제거 후 재-probe — 정말 사라졌는지 검증(거짓 성공 방지).
        let removed = find_executable(probe_binary).is_none();
        Ok(ToolUninstallResult {
            removed,
            exit_code: status.code(),
            manual_hint,
            manual_url,
        })
    })
    .await
    .map_err(|_| SPAWN_FAIL.to_string())?
}
// ANCHOR: TOOL_UNINSTALL_END

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn registry_has_three_tools_with_probe() {
        for id in ["opencode", "codex", "agy"] {
            let t = tool_installer(id).expect("registered");
            assert!(!t.probe_binary.is_empty());
            assert!(!t.manual_url.is_empty());
        }
        assert!(tool_installer("unknown").is_none());
    }
    #[test]
    fn opencode_is_beginner_default_and_no_auth() {
        let t = tool_installer("opencode").unwrap();
        assert!(t.recommended_for_beginner);
        assert_eq!(t.auth, AuthKind::None);
    }
    #[test]
    fn codex_and_agy_need_login() {
        assert_eq!(tool_installer("codex").unwrap().auth, AuthKind::Login);
        assert_eq!(tool_installer("agy").unwrap().auth, AuthKind::Login);
    }
    #[test]
    fn install_command_selected_per_os() {
        // macos/windows 둘 다 비어있지 않은 program+args 를 돌려줘야 한다.
        let t = tool_installer("agy").unwrap();
        let mac = install_command(t, "macos").expect("mac cmd");
        let win = install_command(t, "windows").expect("win cmd");
        assert!(!mac.0.is_empty() && !mac.1.is_empty());
        assert!(!win.0.is_empty() && !win.1.is_empty());
    }
    #[test]
    fn unsupported_os_yields_no_command_for_manual_fallback() {
        let t = tool_installer("agy").unwrap();
        assert!(install_command(t, "linux-unknown").is_none());
    }

    #[test]
    fn uninstall_command_per_os() {
        let oc = tool_installer("opencode").unwrap();
        let mac = uninstall_command(oc, "macos").expect("opencode mac uninstall");
        assert_eq!(mac.0, "opencode");
        assert!(mac.1.iter().any(|a| a == "uninstall"));
        let win = uninstall_command(oc, "windows").expect("opencode win uninstall");
        assert_eq!(win.0, "npm");
    }

    #[test]
    fn codex_win_and_agy_have_no_command_fallback_to_manual() {
        let cx = tool_installer("codex").unwrap();
        assert!(uninstall_command(cx, "macos").is_some());
        assert!(uninstall_command(cx, "windows").is_none());
        let agy = tool_installer("agy").unwrap();
        assert!(uninstall_command(agy, "macos").is_none());
        assert!(uninstall_command(agy, "windows").is_none());
    }

    #[test]
    fn agy_uses_remove_binary_others_do_not() {
        assert!(tool_installer("agy").unwrap().uninstall_remove_binary);
        assert!(!tool_installer("opencode").unwrap().uninstall_remove_binary);
        assert!(!tool_installer("codex").unwrap().uninstall_remove_binary);
    }

    #[test]
    fn remove_resolved_binary_none_is_already_gone() {
        assert!(remove_resolved_binary(None).unwrap());
    }

    #[test]
    fn remove_resolved_binary_deletes_single_file() {
        let dir = std::env::temp_dir();
        let path = dir.join("vibelign_uninstall_test_bin");
        std::fs::write(&path, b"x").unwrap();
        assert!(path.exists());
        let removed = remove_resolved_binary(Some(path.clone())).unwrap();
        assert!(removed);
        assert!(!path.exists());
    }

    #[test]
    fn manual_fallback_tools_have_hint_and_url() {
        for id in ["opencode", "codex", "agy"] {
            let t = tool_installer(id).unwrap();
            assert!(!t.uninstall_hint.is_empty(), "{id} hint");
            assert!(!t.uninstall_url.is_empty(), "{id} url");
        }
    }
}
