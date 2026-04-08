// === ANCHOR: VIB_PATH_START ===
//! vib 실행 파일 경로 탐색 로직.
//!
//! GUI 앱은 터미널 shell 환경을 상속받지 않아서 PATH에서 vib를 찾지 못할 수 있다.
//! 탐색 우선순위:
//!  0. <app>/binaries/vib         (번들 sidecar — Python 불필요)
//!  1. ~/.local/bin/vib          (uv tool install, Linux/macOS)
//!  2. ~/Library/Python/*/bin/vib (macOS pip)
//!  3. %APPDATA%\Python\*\Scripts\vib.exe (Windows)
//!  4. which vib / where vib     (shell 통해 fallback)

use std::path::{Path, PathBuf};
use std::process::Command;

/// `export … # VibeLign CLI` 줄이 이미 있으면 스킵한다.
fn append_vibelign_path_line(
    path: &Path,
    path_line: &str,
    create_if_missing: bool,
) -> Result<(), String> {
    const MARKER: &str = "# VibeLign CLI";
    if path.exists() {
        let existing = std::fs::read_to_string(path).map_err(|e| e.to_string())?;
        if existing.contains(MARKER) {
            return Ok(());
        }
        let mut content = existing;
        if !content.ends_with('\n') && !content.is_empty() {
            content.push('\n');
        }
        content.push_str(path_line);
        if !content.ends_with('\n') {
            content.push('\n');
        }
        std::fs::write(path, content).map_err(|e| e.to_string())?;
        return Ok(());
    }
    if create_if_missing {
        let mut line = path_line.to_string();
        if !line.ends_with('\n') {
            line.push('\n');
        }
        std::fs::write(path, line).map_err(|e| e.to_string())?;
    }
    Ok(())
}

/// macOS 등에서 `.bash_profile`이 `.bashrc`를 source 하는지 대략적으로 판별한다.
fn bash_profile_sources_bashrc(profile_content: &str) -> bool {
    profile_content.lines().any(|raw| {
        let t = raw.trim_start();
        if t.is_empty() || t.starts_with('#') {
            return false;
        }
        if !t.contains(".bashrc") {
            return false;
        }
        t.contains("source ")
            || t.starts_with(". ")
            || t.contains("&& . ")
            || t.contains("&& source ")
    })
}

fn configure_posix_shell_path(home: &Path, path_line: &str) -> Result<(), String> {
    // zsh (맥 기본): .zshrc 없어도 생성
    let zshrc = home.join(".zshrc");
    append_vibelign_path_line(&zshrc, path_line, true)?;

    let bash_profile = home.join(".bash_profile");
    let bashrc = home.join(".bashrc");
    let profile_exists = bash_profile.exists();
    let rc_exists = bashrc.exists();

    if profile_exists && rc_exists {
        let prof_txt = std::fs::read_to_string(&bash_profile).unwrap_or_default();
        if bash_profile_sources_bashrc(&prof_txt) {
            append_vibelign_path_line(&bashrc, path_line, false)?;
        } else {
            append_vibelign_path_line(&bash_profile, path_line, false)?;
        }
    } else if profile_exists {
        append_vibelign_path_line(&bash_profile, path_line, false)?;
    } else if rc_exists {
        append_vibelign_path_line(&bashrc, path_line, false)?;
    } else {
        let default_file = if cfg!(target_os = "macos") {
            bash_profile
        } else {
            bashrc
        };
        append_vibelign_path_line(&default_file, path_line, true)?;
    }

    Ok(())
}

/// vib 실행 파일 경로를 찾는다. 없으면 None.
pub fn find_vib() -> Option<PathBuf> {
    // 0. 번들 sidecar — 앱 실행파일 옆에 있는 vib (Python 불필요)
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            // Tauri sidecar: vib-{target-triple} 또는 vib
            let candidates = [
                // 컴파일 타임에 확정된 Rust 타겟 트리플 사용
                // e.g. vib-aarch64-apple-darwin / vib-x86_64-pc-windows-msvc / vib-x86_64-unknown-linux-gnu
                dir.join(format!("vib-{}", env!("TARGET_TRIPLE"))),
                dir.join("vib"),
                #[cfg(target_os = "windows")]
                dir.join("vib.exe"),
            ];
            for candidate in &candidates {
                if candidate.exists() {
                    return Some(candidate.clone());
                }
            }
        }
    }

    // 1. ~/.local/bin/vib  (uv tool install, Linux/macOS)
    if let Some(home) = home_dir() {
        let candidate = home.join(".local").join("bin").join("vib");
        if candidate.exists() {
            return Some(candidate);
        }
    }

    // 2. ~/Library/Python/*/bin/vib  (macOS pip)
    #[cfg(target_os = "macos")]
    if let Some(home) = home_dir() {
        let python_dir = home.join("Library").join("Python");
        if let Ok(entries) = std::fs::read_dir(&python_dir) {
            let mut candidates: Vec<PathBuf> = entries
                .filter_map(|e| e.ok())
                .map(|e| e.path().join("bin").join("vib"))
                .filter(|p| p.exists())
                .collect();
            candidates.sort();
            if let Some(p) = candidates.last() {
                return Some(p.clone());
            }
        }
    }

    // 3. %APPDATA%\Python\*\Scripts\vib.exe  (Windows)
    #[cfg(target_os = "windows")]
    if let Ok(appdata) = std::env::var("APPDATA") {
        let python_dir = PathBuf::from(appdata).join("Python");
        if let Ok(entries) = std::fs::read_dir(&python_dir) {
            let mut candidates: Vec<PathBuf> = entries
                .filter_map(|e| e.ok())
                .map(|e| e.path().join("Scripts").join("vib.exe"))
                .filter(|p| p.exists())
                .collect();
            candidates.sort();
            if let Some(p) = candidates.last() {
                return Some(p.clone());
            }
        }
    }

    // 4. which / where 를 통한 shell fallback
    #[cfg(not(target_os = "windows"))]
    let which_cmd = "which";
    #[cfg(target_os = "windows")]
    let which_cmd = "where";

    if let Ok(output) = Command::new(which_cmd).arg("vib").output() {
        if output.status.success() {
            let path_str = String::from_utf8_lossy(&output.stdout)
                .trim()
                .lines()
                .next()
                .unwrap_or("")
                .to_string();
            if !path_str.is_empty() {
                let p = PathBuf::from(&path_str);
                if p.exists() {
                    return Some(p);
                }
            }
        }
    }

    None
}

/// HOME 디렉터리 반환 (std::env::var("HOME") 기반).
fn home_dir() -> Option<PathBuf> {
    #[cfg(not(target_os = "windows"))]
    return std::env::var("HOME").ok().map(PathBuf::from);

    #[cfg(target_os = "windows")]
    return std::env::var("USERPROFILE").ok().map(PathBuf::from);
}

/// uv tool로 설치된 Python 기반 vib를 찾는다.
/// 사이드카(번들 바이너리)와 달리 watchdog 등 Python 패키지가 포함된 전체 환경을 가진다.
fn find_uv_tool_vib() -> Option<PathBuf> {
    // UV_TOOL_DIR 환경변수 우선
    let tool_dir = if let Ok(d) = std::env::var("UV_TOOL_DIR") {
        PathBuf::from(d)
    } else {
        #[cfg(any(target_os = "macos", target_os = "linux"))]
        {
            // XDG_DATA_HOME > ~/.local/share/uv/tools
            let base = std::env::var("XDG_DATA_HOME")
                .map(PathBuf::from)
                .unwrap_or_else(|_| home_dir().unwrap_or_default().join(".local").join("share"));
            base.join("uv").join("tools")
        }
        #[cfg(target_os = "windows")]
        {
            // %APPDATA%\uv\tools
            let base = std::env::var("APPDATA")
                .map(PathBuf::from)
                .unwrap_or_else(|_| {
                    home_dir()
                        .unwrap_or_default()
                        .join("AppData")
                        .join("Roaming")
                });
            base.join("uv").join("tools")
        }
    };

    #[cfg(any(target_os = "macos", target_os = "linux"))]
    let candidate = tool_dir.join("vibelign").join("bin").join("vib");
    #[cfg(target_os = "windows")]
    let candidate = tool_dir.join("vibelign").join("Scripts").join("vib.exe");

    if candidate.exists() {
        Some(candidate)
    } else {
        None
    }
}

pub fn find_watch_vib() -> Option<PathBuf> {
    find_uv_tool_vib()
        .filter(|p| std::fs::metadata(p).map_or(false, |m| m.len() > 0))
        .or_else(|| find_vib().filter(|p| std::fs::metadata(p).map_or(false, |m| m.len() > 0)))
}

/// vib CLI를 터미널에서 바로 사용할 수 있도록 PATH에 설치한다.
/// - macOS/Linux: ~/.local/bin/vib 복사 + zsh(`.zshrc`) / bash(`.bash_profile`·`.bashrc`)에 PATH 추가
/// - Windows: %LOCALAPPDATA%\Programs\VibeLign\vib.exe 복사 + 레지스트리 user PATH 추가
pub fn install_cli_to_path() -> Result<String, String> {
    // uv tool 버전(Python 환경 포함)을 우선 사용, 없으면 번들 사이드카로 폴백
    // 단, 소스 파일이 0 bytes이면 손상된 것으로 간주하고 건너뜀
    let vib =
        find_watch_vib().ok_or("유효한 vib 실행 파일을 찾을 수 없습니다 (0 bytes 또는 미설치)")?;

    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        use std::os::unix::fs::PermissionsExt;

        let home = home_dir().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
        let local_bin = home.join(".local").join("bin");
        std::fs::create_dir_all(&local_bin).map_err(|e| e.to_string())?;

        // uv tool vib는 심볼릭 링크로 연결 (복사하면 trampoline이 venv를 못 찾음)
        // 사이드카처럼 독립 실행 바이너리인 경우에만 복사
        let dest = local_bin.join("vib");
        if dest.exists() || dest.symlink_metadata().is_ok() {
            std::fs::remove_file(&dest).map_err(|e| e.to_string())?;
        }
        let use_symlink = find_uv_tool_vib().map_or(false, |p| p == vib);
        if use_symlink {
            std::os::unix::fs::symlink(&vib, &dest)
                .map_err(|e| format!("심볼릭 링크 생성 실패: {}", e))?;
        } else {
            std::fs::copy(&vib, &dest).map_err(|e| format!("바이너리 복사 실패: {}", e))?;
            std::fs::set_permissions(&dest, std::fs::Permissions::from_mode(0o755))
                .map_err(|e| e.to_string())?;
        }

        let path_line = r#"export PATH="$HOME/.local/bin:$PATH"  # VibeLign CLI"#;
        configure_posix_shell_path(&home, path_line)?;

        return Ok(format!("vib CLI 설치 완료: {}", dest.display()));
    }

    #[cfg(target_os = "windows")]
    {
        let local_app_data = std::env::var("LOCALAPPDATA")
            .map(PathBuf::from)
            .or_else(|_| {
                home_dir()
                    .ok_or("".to_string())
                    .map(|h| h.join("AppData").join("Local"))
            })
            .map_err(|_| "LOCALAPPDATA를 찾을 수 없습니다".to_string())?;

        let dest_dir = local_app_data.join("Programs").join("VibeLign");
        std::fs::create_dir_all(&dest_dir).map_err(|e| e.to_string())?;

        let dest = dest_dir.join("vib.exe");
        std::fs::copy(&vib, &dest).map_err(|e| format!("바이너리 복사 실패: {}", e))?;

        // 레지스트리 user PATH에 추가 (PowerShell)
        let dir_str = dest_dir.to_string_lossy().to_string();
        let ps_script = format!(
            r#"$old = [Environment]::GetEnvironmentVariable('Path','User'); if ($old -notlike '*VibeLign*') {{ [Environment]::SetEnvironmentVariable('Path', $old + ';{dir}', 'User') }}"#,
            dir = dir_str
        );
        let _ = Command::new("powershell")
            .args(["-NoProfile", "-NonInteractive", "-Command", &ps_script])
            .output();

        return Ok(format!("vib CLI 설치 완료: {}", dest.display()));
    }

    #[allow(unreachable_code)]
    Ok("지원하지 않는 플랫폼입니다".to_string())
}
// === ANCHOR: VIB_PATH_END ===
