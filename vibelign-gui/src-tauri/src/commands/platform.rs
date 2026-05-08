// === ANCHOR: PLATFORM_START ===
use std::path::PathBuf;

#[tauri::command]
pub(crate) fn open_folder(path: String) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    std::process::Command::new("open")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    #[cfg(target_os = "windows")]
    std::process::Command::new("explorer")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    #[cfg(target_os = "linux")]
    std::process::Command::new("xdg-open")
        .arg(&path)
        .spawn()
        .map_err(|e| e.to_string())?;

    Ok(())
}

/// Windows `canonicalize()` 가 반환하는 `\\?\` 접두사를 벗겨서
/// 외부 프로세스가 경로를 올바르게 해석하도록 한다.
///
/// - `\\?\C:\path` → `C:\path`
/// - `\\?\UNC\server\share\path` → `\\server\share\path`
///   (네트워크 공유/WSL 경로; 이 케이스를 놓치면 CreateProcess 가 os error 267 로 거절한다)
pub(crate) fn strip_unc_prefix(p: PathBuf) -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        let s = p.to_string_lossy();
        if let Some(rest) = s.strip_prefix(r"\\?\UNC\") {
            return PathBuf::from(format!(r"\\{rest}"));
        }
        if let Some(rest) = s.strip_prefix(r"\\?\") {
            return PathBuf::from(rest);
        }
    }
    p
}

/// vib 서브프로세스가 fd/fdfind 같은 보조 바이너리를 찾을 수 있도록
/// 플랫폼별 기본 설치 경로를 기존 PATH 뒤에 덧붙여 돌려준다.
/// Why: GUI 번들에서 spawn 된 vib 는 로그인 셸 PATH 를 상속받지 못해
///      Homebrew(/opt/homebrew/bin, /usr/local/bin)·Scoop shims·cargo bin 등을
///      놓친다. 이 경우 fd 미탐지 → Python rglob 폴백 → `target/_internal`
///      같은 빌드 산출물까지 스캔되어 코드맵이 부풀어 오른다.
pub(crate) fn augmented_vib_path() -> std::ffi::OsString {
    let existing = std::env::var_os("PATH").unwrap_or_default();

    let mut extras: Vec<PathBuf> = Vec::new();

    #[cfg(target_os = "macos")]
    {
        extras.push(PathBuf::from("/opt/homebrew/bin"));
        extras.push(PathBuf::from("/usr/local/bin"));
        extras.push(PathBuf::from("/usr/bin"));
        if let Some(home) = std::env::var_os("HOME") {
            extras.push(PathBuf::from(&home).join(".cargo").join("bin"));
        }
    }

    #[cfg(target_os = "linux")]
    {
        extras.push(PathBuf::from("/usr/local/bin"));
        extras.push(PathBuf::from("/usr/bin"));
        if let Some(home) = std::env::var_os("HOME") {
            extras.push(PathBuf::from(&home).join(".cargo").join("bin"));
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Some(user) = std::env::var_os("USERPROFILE") {
            let user = PathBuf::from(&user);
            extras.push(user.join("scoop").join("shims"));
            extras.push(user.join(".cargo").join("bin"));
        }
        if let Some(local) = std::env::var_os("LOCALAPPDATA") {
            extras.push(
                PathBuf::from(&local)
                    .join("Microsoft")
                    .join("WinGet")
                    .join("Links"),
            );
        }
        extras.push(PathBuf::from(r"C:\ProgramData\chocolatey\bin"));
    }

    let mut combined = std::ffi::OsString::new();
    combined.push(&existing);
    for extra in &extras {
        if !extra.exists() {
            continue;
        }
        if !combined.is_empty() {
            #[cfg(windows)]
            combined.push(";");
            #[cfg(not(windows))]
            combined.push(":");
        }
        combined.push(extra.as_os_str());
    }
    combined
}

/// Windows 에서 자식 프로세스 실행 시 검은 콘솔 창이 순간적으로 뜨는 것을 막는다.
/// 비Windows 에서는 no-op.
#[cfg(target_os = "windows")]
pub(crate) fn hide_console(cmd: &mut std::process::Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(target_os = "windows"))]
pub(crate) fn hide_console(_cmd: &mut std::process::Command) {}
// === ANCHOR: PLATFORM_END ===
