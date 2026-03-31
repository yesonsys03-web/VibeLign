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

use std::path::PathBuf;
use std::process::Command;

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

/// vib CLI를 터미널에서 바로 사용할 수 있도록 PATH에 설치한다.
/// - macOS/Linux: ~/.local/bin/vib 복사 + .zshrc/.bashrc에 PATH 라인 추가
/// - Windows: %LOCALAPPDATA%\Programs\VibeLign\vib.exe 복사 + 레지스트리 user PATH 추가
pub fn install_cli_to_path() -> Result<String, String> {
    let vib = find_vib().ok_or("번들된 vib 실행 파일을 찾을 수 없습니다")?;

    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        use std::os::unix::fs::PermissionsExt;

        let home = home_dir().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
        let local_bin = home.join(".local").join("bin");
        std::fs::create_dir_all(&local_bin).map_err(|e| e.to_string())?;

        // 바이너리 복사 (항상 최신으로 덮어씀)
        let dest = local_bin.join("vib");
        std::fs::copy(&vib, &dest).map_err(|e| format!("바이너리 복사 실패: {}", e))?;
        std::fs::set_permissions(&dest, std::fs::Permissions::from_mode(0o755))
            .map_err(|e| e.to_string())?;

        // .zshrc / .bashrc 에 PATH 라인 추가 (중복 방지)
        let path_line = r#"export PATH="$HOME/.local/bin:$PATH"  # VibeLign CLI"#;
        for rc in &[".zshrc", ".bashrc"] {
            let rc_path = home.join(rc);
            if rc_path.exists() || *rc == ".zshrc" {
                let existing = std::fs::read_to_string(&rc_path).unwrap_or_default();
                if !existing.contains(".local/bin") {
                    let mut content = existing;
                    if !content.ends_with('\n') { content.push('\n'); }
                    content.push_str(&format!("\n{}\n", path_line));
                    std::fs::write(&rc_path, content).map_err(|e| e.to_string())?;
                }
            }
        }

        return Ok(format!("vib CLI 설치 완료: {}", dest.display()));
    }

    #[cfg(target_os = "windows")]
    {
        let local_app_data = std::env::var("LOCALAPPDATA")
            .map(PathBuf::from)
            .or_else(|_| home_dir().ok_or("".to_string()).map(|h| h.join("AppData").join("Local")))
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

    Ok("지원하지 않는 플랫폼입니다".to_string())
}
// === ANCHOR: VIB_PATH_END ===
