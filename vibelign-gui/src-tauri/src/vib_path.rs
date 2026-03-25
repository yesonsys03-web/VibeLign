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
                dir.join(format!("vib-{}", std::env::consts::ARCH.to_string()
                    + "-" + std::env::consts::OS + if cfg!(target_os="macos") { "-darwin" } else { "" })),
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
// === ANCHOR: VIB_PATH_END ===
