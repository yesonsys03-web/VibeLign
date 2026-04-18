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
use std::sync::OnceLock;

/// Tauri setup 단계에서 PathResolver 로 확정한 번들 vib 절대 경로.
/// onedir PyInstaller 빌드에서는 실행 파일 옆에 `_internal/` 디렉터리가 함께 있어야 하므로
/// 앱 resource 경로(`<App>.app/Contents/Resources/vib-runtime/vib` 등) 를 통째로 보존해야 한다.
/// `current_exe()` 에서 올라가며 추측하는 기존 방식은 macOS 의 `.app` 레이아웃을 놓쳐서 쓰지 않는다.
#[allow(dead_code)] // release(not(debug_assertions)) 빌드에서만 set/get 된다
pub static BUNDLED_VIB_PATH: OnceLock<PathBuf> = OnceLock::new();

/// Windows 에서 자식 프로세스 실행 시 검은 콘솔 창이 순간적으로 뜨는 것을 막는다.
#[cfg(target_os = "windows")]
fn hide_console(cmd: &mut Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(target_os = "windows"))]
fn hide_console(_cmd: &mut Command) {}

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

fn is_nonempty_file(path: &Path) -> bool {
    std::fs::metadata(path).map_or(false, |m| m.len() > 0)
}

/// GUI 런타임이 사용할 번들 vib를 찾는다. 없으면 None.
///
/// dev 빌드(`debug_assertions`)에서는 항상 None 을 반환해 `find_vib` 폴백(시스템 `vib`,
/// uv tool entry point)으로 내려간다. 로컬 사이드카 스텁이 stale 되면 구형 CLI 를 호출해
/// 최신 명령(docs-build 등)이 누락되는 문제를 dev 단계에서 원천 차단한다.
/// 릴리즈(`tauri build`) 에서는 PyInstaller 번들이 정상 탐색된다.
#[cfg(debug_assertions)]
pub fn find_bundled_vib() -> Option<PathBuf> {
    None
}

#[cfg(not(debug_assertions))]
pub fn find_bundled_vib() -> Option<PathBuf> {
    // 0-a. Tauri setup 에서 resource_dir 기반으로 주입한 절대 경로 (권장 경로).
    if let Some(p) = BUNDLED_VIB_PATH.get() {
        if is_nonempty_file(p) {
            return Some(p.clone());
        }
    }

    // 0-b. Fallback: 앱 실행파일 옆의 vib-runtime 디렉터리를 직접 탐색.
    //      setup() 훅 이전에 호출되는 경로(현재는 없음)를 위한 안전망.
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let mut candidates: Vec<PathBuf> = Vec::new();
            #[cfg(target_os = "macos")]
            {
                // <App>.app/Contents/MacOS/vibelign-gui  →  Resources/vib-runtime/vib
                if let Some(contents) = dir.parent() {
                    candidates.push(contents.join("Resources").join("vib-runtime").join("vib"));
                }
            }
            #[cfg(not(target_os = "macos"))]
            {
                candidates.push(dir.join("vib-runtime").join("vib"));
                #[cfg(target_os = "windows")]
                candidates.push(dir.join("vib-runtime").join("vib.exe"));
                // Tauri Linux 에선 resources 가 `<prefix>/lib/vibelign-gui/` 아래로 들어간다.
                // 대표적으로 AppImage/deb 모두 실행파일과 같은 디렉터리에 resources 를 두므로 위 한 줄이면 충분하다.
            }
            for candidate in &candidates {
                if is_nonempty_file(candidate) {
                    return Some(candidate.clone());
                }
            }
        }
    }

    None
}

/// vib 실행 파일 경로를 찾는다. 없으면 None.
pub fn find_vib() -> Option<PathBuf> {
    if let Some(vib) = find_bundled_vib() {
        return Some(vib);
    }

    if let Some(vib) = find_uv_tool_vib() {
        if is_nonempty_file(&vib) {
            return Some(vib);
        }
    }

    // 1. ~/.local/bin/vib  (uv tool install, Linux/macOS)
    if let Some(home) = home_dir() {
        let candidate = home.join(".local").join("bin").join("vib");
        if is_nonempty_file(&candidate) {
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
                .filter(|p| is_nonempty_file(p))
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
                .filter(|p| is_nonempty_file(p))
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

    let mut which_command = Command::new(which_cmd);
    which_command.arg("vib");
    hide_console(&mut which_command);
    if let Ok(output) = which_command.output() {
        if output.status.success() {
            let path_str = String::from_utf8_lossy(&output.stdout)
                .trim()
                .lines()
                .next()
                .unwrap_or("")
                .to_string();
            if !path_str.is_empty() {
                let p = PathBuf::from(&path_str);
                if is_nonempty_file(&p) {
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

    if is_nonempty_file(&candidate) {
        Some(candidate)
    } else {
        None
    }
}

pub fn find_runtime_vib() -> Option<PathBuf> {
    find_bundled_vib().or_else(find_vib)
}

pub fn find_watch_vib() -> Option<PathBuf> {
    find_runtime_vib()
}

/// vib CLI를 터미널에서 바로 사용할 수 있도록 PATH에 설치한다.
/// - macOS/Linux: ~/.local/bin/vib 복사 + zsh(`.zshrc`) / bash(`.bash_profile`·`.bashrc`)에 PATH 추가
/// - Windows: %LOCALAPPDATA%\Programs\VibeLign\vib.exe 복사 + 레지스트리 user PATH 추가
pub fn install_cli_to_path() -> Result<String, String> {
    // GUI 설치본이 어디서든 같은 CLI를 제공하도록 번들 vib를 우선 사용한다.
    // 개발/복구 상황에서는 기존 탐색 순서로 폴백한다.
    let vib = find_bundled_vib()
        .or_else(find_vib)
        .ok_or("유효한 vib 실행 파일을 찾을 수 없습니다 (0 bytes 또는 미설치)")?;

    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        use std::os::unix::fs::PermissionsExt;

        let home = home_dir().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
        let local_bin = home.join(".local").join("bin");
        std::fs::create_dir_all(&local_bin).map_err(|e| e.to_string())?;

        let dest = local_bin.join("vib");
        // symlink 는 사용자가 직접 관리하는 바이너리(uv/pipx 등)로 간주하고 덮어쓰지 않는다.
        // Why: `~/.local/bin/vib` 가 `~/.local/share/uv/tools/vibelign/bin/vib` 등을 가리키는
        //      symlink 인 경우, 말없이 regular 파일로 교체하면 사용자의 tool 설치 환경이 깨진다.
        if let Ok(meta) = dest.symlink_metadata() {
            if meta.file_type().is_symlink() {
                return Ok(format!(
                    "기존 symlink 보존: {} (수동 관리 vib 로 판단해 설치를 건너뜁니다)",
                    dest.display()
                ));
            }
            std::fs::remove_file(&dest).map_err(|e| e.to_string())?;
        }
        // onedir 번들은 `vib` 옆의 `_internal/` 디렉터리까지 함께 있어야 실행된다.
        // 단일 바이너리 복사로는 동작하지 않으므로 번들 절대 경로로 exec 하는 얇은 쉘 래퍼를 심는다.
        let target = vib.to_string_lossy().to_string();
        let wrapper = format!("#!/bin/sh\nexec \"{}\" \"$@\"\n", target.replace('"', "\\\""));
        std::fs::write(&dest, wrapper).map_err(|e| format!("래퍼 스크립트 작성 실패: {}", e))?;
        std::fs::set_permissions(&dest, std::fs::Permissions::from_mode(0o755))
            .map_err(|e| e.to_string())?;

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

        // onedir 번들은 `vib.exe` 옆의 `_internal/` 디렉터리까지 함께 있어야 실행된다.
        // 단일 바이너리 복사로는 동작하지 않으므로 번들 절대 경로를 호출하는 .cmd 래퍼를 심는다.
        let dest = dest_dir.join("vib.cmd");
        let target = vib.to_string_lossy().to_string();
        let wrapper = format!("@echo off\r\n\"{}\" %*\r\n", target);
        std::fs::write(&dest, wrapper).map_err(|e| format!("래퍼 스크립트 작성 실패: {}", e))?;

        // 이전 버전이 설치한 단일 바이너리 vib.exe 가 남아있으면 PATHEXT 해석 순서상 .cmd 보다 우선될 수 있어 제거한다.
        let legacy_exe = dest_dir.join("vib.exe");
        if legacy_exe.exists() {
            let _ = std::fs::remove_file(&legacy_exe);
        }

        // 레지스트리 user PATH에 추가 (PowerShell)
        let dir_str = dest_dir.to_string_lossy().to_string();
        let ps_script = format!(
            r#"$old = [Environment]::GetEnvironmentVariable('Path','User'); if ($old -notlike '*VibeLign*') {{ [Environment]::SetEnvironmentVariable('Path', $old + ';{dir}', 'User') }}"#,
            dir = dir_str
        );
        let mut ps_cmd = Command::new("powershell");
        ps_cmd.args(["-NoProfile", "-NonInteractive", "-Command", &ps_script]);
        hide_console(&mut ps_cmd);
        let _ = ps_cmd.output();

        return Ok(format!("vib CLI 설치 완료: {}", dest.display()));
    }

    #[allow(unreachable_code)]
    Ok("지원하지 않는 플랫폼입니다".to_string())
}

/// GUI 앱이 다른 폴더로 이동/재설치되었을 때 `~/.local/bin/vib`(또는 `vib.cmd`) 래퍼가
/// stale 한 번들 경로를 가리키고 있으면 현재 번들 경로로 재작성한다.
///
/// 안전장치:
/// - symlink 는 사용자가 직접 관리하는 바이너리(uv/pipx)로 간주하고 절대 건드리지 않음.
/// - 래퍼 sentinel 패턴이 맞지 않는 regular 파일(사용자가 `pip install --user` 등으로 심은
///   일반 entry-point) 은 우리 래퍼가 아니라고 판단해 건드리지 않음.
/// - 래퍼 안의 타겟 경로가 이미 현재 번들과 같으면 no-op.
///
/// 호출 시점: 매 GUI 부팅 setup() 에서. PATH 등록/shell rc 편집은 하지 않고 파일만 갱신.
#[allow(dead_code)] // release(not(debug_assertions)) 빌드에서만 호출된다
pub fn refresh_gui_wrapper(bundled_vib: &Path) -> Result<(), String> {
    #[cfg(any(target_os = "macos", target_os = "linux"))]
    {
        let home = home_dir().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
        let dest = home.join(".local").join("bin").join("vib");
        // symlink 는 사용자 수동 관리로 간주
        if let Ok(meta) = dest.symlink_metadata() {
            if meta.file_type().is_symlink() {
                return Ok(());
            }
        } else {
            // 최초 설치 전이면 install_cli_to_path 가 처리한다
            return Ok(());
        }
        let content = std::fs::read_to_string(&dest).map_err(|e| e.to_string())?;
        // 우리 래퍼 sentinel 체크 (install_cli_to_path 가 쓰는 포맷)
        if !content.starts_with("#!/bin/sh\nexec \"") {
            return Ok(());
        }
        let target = bundled_vib.to_string_lossy().to_string();
        let expected = format!("#!/bin/sh\nexec \"{}\" \"$@\"\n", target.replace('"', "\\\""));
        if content == expected {
            return Ok(());
        }
        std::fs::write(&dest, expected)
            .map_err(|e| format!("래퍼 재작성 실패: {}", e))?;
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
        let dest = local_app_data
            .join("Programs")
            .join("VibeLign")
            .join("vib.cmd");
        if !dest.exists() {
            return Ok(());
        }
        let content = std::fs::read_to_string(&dest).map_err(|e| e.to_string())?;
        if !content.starts_with("@echo off") {
            return Ok(());
        }
        let target = bundled_vib.to_string_lossy().to_string();
        let expected = format!("@echo off\r\n\"{}\" %*\r\n", target);
        if content == expected {
            return Ok(());
        }
        std::fs::write(&dest, expected)
            .map_err(|e| format!("래퍼 재작성 실패: {}", e))?;
    }

    Ok(())
}
// === ANCHOR: VIB_PATH_END ===
