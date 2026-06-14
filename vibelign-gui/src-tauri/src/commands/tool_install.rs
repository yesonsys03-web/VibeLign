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
}

const OPENCODE: ToolInstaller = ToolInstaller {
    id: "opencode", display_name: "OpenCode", probe_binary: "opencode",
    mac_program: "bash", mac_args: &["-c", "curl -fsSL https://opencode.ai/install | bash"],
    win_program: "npm", win_args: &["install", "-g", "opencode-ai"],
    auth: AuthKind::None,
    auth_hint: "무료 모델이라 추가 로그인이 필요 없어요 — 바로 쓸 수 있어요.",
    manual_url: "https://opencode.ai/download", recommended_for_beginner: true,
};
const CODEX: ToolInstaller = ToolInstaller {
    id: "codex", display_name: "Codex", probe_binary: "codex",
    mac_program: "npm", mac_args: &["install", "-g", "@openai/codex"],
    win_program: "powershell", win_args: &["-ExecutionPolicy", "Bypass", "-c", "irm https://chatgpt.com/codex/install.ps1 | iex"],
    auth: AuthKind::Login,
    auth_hint: "설치 후 OpenAI 로그인이 필요해요 — 터미널에서 `codex` 를 한 번 실행해 로그인하세요.",
    manual_url: "https://www.npmjs.com/package/@openai/codex", recommended_for_beginner: false,
};
const AGY: ToolInstaller = ToolInstaller {
    id: "agy", display_name: "Antigravity", probe_binary: "agy",
    mac_program: "bash", mac_args: &["-c", "curl -fsSL https://antigravity.google/cli/install.sh | bash"],
    win_program: "powershell", win_args: &["-ExecutionPolicy", "Bypass", "-c", "irm https://antigravity.google/cli/install.ps1 | iex"],
    auth: AuthKind::Login,
    auth_hint: "설치 후 Google 로그인이 필요해요 — `agy` 를 처음 실행하면 브라우저 로그인이 열려요.",
    manual_url: "https://antigravity.google/docs/cli-install", recommended_for_beginner: false,
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

#[tauri::command]
pub(crate) fn tool_install_status(id: String) -> Result<bool, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    Ok(find_executable(t.probe_binary).is_some())
}

#[tauri::command]
pub(crate) fn install_tool(app: tauri::AppHandle, id: String) -> Result<ToolInstallResult, String> {
    let t = tool_installer(&id).ok_or_else(|| "알 수 없는 도구".to_string())?;
    let Some((program, args)) = install_command(t, current_os()) else {
        // 지원 안 되는 OS → 가이드 수동 폴백
        return Ok(ToolInstallResult {
            installed: false, exit_code: None, auth: t.auth,
            auth_hint: t.auth_hint.to_string(), manual_url: t.manual_url.to_string(),
        });
    };
    let mut cmd = std::process::Command::new(&program);
    cmd.args(&args);
    cmd.env("PATH", augmented_vib_path());
    cmd.stdout(std::process::Stdio::piped());
    cmd.stderr(std::process::Stdio::piped());
    hide_console(&mut cmd);
    let mut child = cmd.spawn().map_err(|e| format!("설치 실행 실패: {e}"))?;

    let emit = |app: &tauri::AppHandle, stream: &str, line: String| {
        use tauri::Emitter;
        let _ = app.emit("tool-install-output", ToolInstallOutput { id: id.clone(), stream: stream.into(), line });
    };
    if let Some(out) = child.stdout.take() {
        let (app2, stream) = (app.clone(), "stdout");
        for line in BufReader::new(out).lines().map_while(Result::ok) {
            emit(&app2, stream, line);
        }
    }
    if let Some(err) = child.stderr.take() {
        for line in BufReader::new(err).lines().map_while(Result::ok) {
            emit(&app, "stderr", line);
        }
    }
    let status = child.wait().map_err(|e| format!("설치 대기 실패: {e}"))?;
    // 종료 후 새로 PATH 해석해 프로브(설치 직후 PATH 반영 확인).
    let installed = find_executable(t.probe_binary).is_some();
    Ok(ToolInstallResult {
        installed,
        exit_code: status.code(),
        auth: t.auth,
        auth_hint: t.auth_hint.to_string(),
        manual_url: t.manual_url.to_string(),
    })
}
// ANCHOR: TOOL_INSTALL_END

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
}
