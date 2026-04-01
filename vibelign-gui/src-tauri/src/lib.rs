// === ANCHOR: LIB_START ===
mod vib_path;

use std::collections::HashMap;
use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use tauri::{Emitter, Manager};

// ─── 폴더 열기 ────────────────────────────────────────────────────────────────

#[tauri::command]
fn open_folder(path: String) -> Result<(), String> {
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

// ─── Watch 프로세스 State ──────────────────────────────────────────────────────

struct WatchState(Arc<Mutex<Option<std::process::Child>>>);

fn kill_watch_child(child: &mut std::process::Child) {
    #[cfg(unix)]
    unsafe {
        let pgid = child.id() as i32;
        libc::killpg(pgid, libc::SIGKILL);
    }
    #[cfg(not(unix))]
    { let _ = child.kill(); }
    let _ = child.wait();
}

impl Drop for WatchState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.take() {
                kill_watch_child(&mut child);
            }
        }
    }
}

#[tauri::command]
fn start_watch(app: tauri::AppHandle, state: tauri::State<WatchState>, cwd: String) -> Result<(), String> {
    let vib = vib_path::find_vib().ok_or("vib 실행 파일을 찾을 수 없습니다")?;
    // 기존 watch가 있으면 먼저 중지
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(ref mut child) = *guard {
        let _ = child.kill();
    }
    let mut watch_cmd = std::process::Command::new(&vib);
    watch_cmd.arg("watch").current_dir(PathBuf::from(&cwd));
    watch_cmd.stdin(std::process::Stdio::piped());
    watch_cmd.stdout(std::process::Stdio::piped());
    watch_cmd.stderr(std::process::Stdio::piped());
    watch_cmd.env("PYTHONUNBUFFERED", "1");
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        watch_cmd.env("PYTHONUTF8", "1");
        watch_cmd.env("PYTHONIOENCODING", "utf-8");
        watch_cmd.creation_flags(CREATE_NO_WINDOW);
    }
    // Unix: 새 프로세스 그룹 생성 → 자식까지 전체 kill 가능
    #[cfg(unix)]
    unsafe {
        use std::os::unix::process::CommandExt;
        watch_cmd.pre_exec(|| { libc::setpgid(0, 0); Ok(()) });
    }
    let mut child = watch_cmd.spawn().map_err(|e| e.to_string())?;
    // watchdog 설치 프롬프트(y/N)에 자동으로 "y" 응답
    if let Some(mut stdin) = child.stdin.take() {
        use std::io::Write;
        let _ = stdin.write_all(b"y\n");
    }
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    *guard = Some(child);
    drop(guard);

    if let Some(out) = stdout {
        let app2 = app.clone();
        std::thread::spawn(move || {
            for line in BufReader::new(out).lines() {
                if let Ok(l) = line { let _ = app2.emit("watch_log", l); }
            }
        });
    }
    if let Some(err) = stderr {
        std::thread::spawn(move || {
            for line in BufReader::new(err).lines() {
                if let Ok(l) = line { let _ = app.emit("watch_log", l); }
            }
        });
    }
    Ok(())
}

#[tauri::command]
fn stop_watch(state: tauri::State<WatchState>) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.take() {
        kill_watch_child(&mut child);
    }
    Ok(())
}

#[tauri::command]
fn watch_status(state: tauri::State<WatchState>) -> bool {
    state.0.lock()
        .map(|g| g.is_some())
        .unwrap_or(false)
}

// ─── 타입 정의 ─────────────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub struct VibResult {
    pub ok: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

// ─── Tauri Commands ────────────────────────────────────────────────────────────

/// vib 실행 파일 경로를 반환한다. 없으면 None.
#[tauri::command]
fn get_vib_path() -> Option<String> {
    vib_path::find_vib().map(|p| p.to_string_lossy().into_owned())
}

/// vib CLI를 터미널 PATH에 설치한다 (앱 시작 시 자동 호출).
#[tauri::command]
fn setup_cli_path() -> Result<String, String> {
    vib_path::install_cli_to_path()
}

/// vib CLI를 실행하고 결과를 반환한다.
///
/// - `args`: `["doctor", "--json"]` 등
/// - `cwd`: 프로젝트 루트 경로 (없으면 현재 디렉터리)
/// - `env`: 추가 환경변수 (`{"ANTHROPIC_API_KEY": "..."}` 등)
#[tauri::command]
async fn run_vib(
    args: Vec<String>,
    cwd: Option<String>,
    env: Option<HashMap<String, String>>,
) -> VibResult {
    let vib = match vib_path::find_vib() {
        Some(p) => p,
        None => {
            return VibResult {
                ok: false,
                stdout: String::new(),
                stderr: "vib 실행 파일을 찾을 수 없습니다. 설치 후 재시작하세요.".into(),
                exit_code: -1,
            };
        }
    };

    tauri::async_runtime::spawn_blocking(move || {
        let mut cmd = std::process::Command::new(&vib);
        cmd.args(&args);
        cmd.stdin(std::process::Stdio::null());

        if let Some(dir) = cwd {
            cmd.current_dir(PathBuf::from(dir));
        }

        // Windows에서 Python 서브프로세스의 stdout 인코딩을 UTF-8로 강제 설정 + 콘솔 창 숨김
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.env("PYTHONUTF8", "1");
            cmd.env("PYTHONIOENCODING", "utf-8");
            cmd.creation_flags(CREATE_NO_WINDOW);
        }

        if let Some(env_map) = env {
            for (k, v) in env_map {
                cmd.env(k, v);
            }
        }

        match cmd.output() {
            Ok(output) => VibResult {
                ok: output.status.success(),
                stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
                stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
                exit_code: output.status.code().unwrap_or(-1),
            },
            Err(e) => VibResult {
                ok: false,
                stdout: String::new(),
                stderr: e.to_string(),
                exit_code: -1,
            },
        }
    })
    .await
    .unwrap_or(VibResult {
        ok: false,
        stdout: String::new(),
        stderr: "spawn_blocking 실패".into(),
        exit_code: -1,
    })
}

// ─── API 키 저장소 ─────────────────────────────────────────────────────────────

fn config_path() -> Option<PathBuf> {
    let home = std::env::var("HOME")
        .or_else(|_| std::env::var("USERPROFILE"))
        .ok()?;
    let dir = PathBuf::from(home).join(".vibelign");
    std::fs::create_dir_all(&dir).ok()?;
    Some(dir.join("gui_config.json"))
}

#[tauri::command]
fn save_recent_projects(dirs: Vec<String>) -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    let existing = std::fs::read_to_string(&path)
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .unwrap_or(serde_json::json!({}));
    let mut data = existing;
    data["recent_projects"] = serde_json::Value::Array(
        dirs.into_iter().map(serde_json::Value::String).collect(),
    );
    std::fs::write(&path, data.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_recent_projects() -> Vec<String> {
    let path = match config_path() { Some(p) => p, None => return vec![] };
    let text = match std::fs::read_to_string(&path) { Ok(t) => t, Err(_) => return vec![] };
    let data: serde_json::Value = match serde_json::from_str(&text) { Ok(v) => v, Err(_) => return vec![] };
    data["recent_projects"]
        .as_array()
        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
        .unwrap_or_default()
}

fn read_gui_config() -> serde_json::Value {
    let path = match config_path() {
        Some(p) => p,
        None => return serde_json::json!({}),
    };
    let text = std::fs::read_to_string(&path).unwrap_or_default();
    match serde_json::from_str::<serde_json::Value>(&text) {
        Ok(v) if v.is_object() => v,
        _ => serde_json::json!({}),
    }
}

fn write_gui_config(data: &serde_json::Value) -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    std::fs::write(&path, data.to_string()).map_err(|e| e.to_string())
}

/// `provider_api_keys` + 레거시 `anthropic_api_key`를 합친 맵.
fn provider_keys_from_config(data: &serde_json::Value) -> HashMap<String, String> {
    let mut out = HashMap::new();
    if let Some(obj) = data.get("provider_api_keys").and_then(|v| v.as_object()) {
        for (k, v) in obj {
            if let Some(s) = v.as_str() {
                if !s.is_empty() {
                    out.insert(k.to_uppercase(), s.to_string());
                }
            }
        }
    }
    if let Some(s) = data.get("anthropic_api_key").and_then(|v| v.as_str()) {
        if !s.is_empty() {
            out.entry("ANTHROPIC".into()).or_insert_with(|| s.to_string());
        }
    }
    out
}

#[tauri::command]
fn save_api_key(key: String) -> Result<(), String> {
    let mut data = read_gui_config();
    data["anthropic_api_key"] = serde_json::Value::String(key.clone());
    let pk = data
        .as_object_mut()
        .unwrap()
        .entry("provider_api_keys")
        .or_insert(serde_json::json!({}));
    if let Some(obj) = pk.as_object_mut() {
        obj.insert(
            "ANTHROPIC".into(),
            serde_json::Value::String(key),
        );
    }
    write_gui_config(&data)
}

#[tauri::command]
fn load_api_key() -> Option<String> {
    let data = read_gui_config();
    provider_keys_from_config(&data)
        .get("ANTHROPIC")
        .cloned()
        .or_else(|| data["anthropic_api_key"].as_str().map(String::from))
}

#[tauri::command]
fn delete_api_key() -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    if !path.exists() {
        return Ok(());
    }
    let mut data = read_gui_config();
    if let Some(obj) = data.as_object_mut() {
        obj.remove("anthropic_api_key");
    }
    if let Some(obj) = data
        .get_mut("provider_api_keys")
        .and_then(|v| v.as_object_mut())
    {
        obj.remove("ANTHROPIC");
    }
    write_gui_config(&data)
}

#[tauri::command]
fn save_provider_api_key(provider: String, key: String) -> Result<(), String> {
    let provider = provider.to_uppercase();
    let key = key.trim().to_string();
    if key.is_empty() {
        return Err("키가 비어 있습니다".into());
    }
    let mut data = read_gui_config();
    let pk = data
        .as_object_mut()
        .unwrap()
        .entry("provider_api_keys")
        .or_insert(serde_json::json!({}));
    if let Some(obj) = pk.as_object_mut() {
        obj.insert(provider.clone(), serde_json::Value::String(key.clone()));
    }
    if provider == "ANTHROPIC" {
        data["anthropic_api_key"] = serde_json::Value::String(key);
    }
    write_gui_config(&data)
}

#[tauri::command]
fn delete_provider_api_key(provider: String) -> Result<(), String> {
    let provider = provider.to_uppercase();
    let mut data = read_gui_config();
    if let Some(obj) = data
        .get_mut("provider_api_keys")
        .and_then(|v| v.as_object_mut())
    {
        obj.remove(&provider);
    }
    if provider == "ANTHROPIC" {
        if let Some(obj) = data.as_object_mut() {
            obj.remove("anthropic_api_key");
        }
    }
    write_gui_config(&data)
}

#[tauri::command]
fn load_provider_api_keys() -> HashMap<String, String> {
    let data = read_gui_config();
    provider_keys_from_config(&data)
}

// ─── 환경변수 API 키 상태 ──────────────────────────────────────────────────────

/// ANTHROPIC/OPENAI/GEMINI/GLM/MOONSHOT 환경변수 설정 여부를 반환한다.
#[tauri::command]
fn get_env_key_status() -> HashMap<String, bool> {
    let keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GLM_API_KEY",
        "MOONSHOT_API_KEY",
    ];
    keys.iter()
        .map(|k| (k.to_string(), !std::env::var(k).unwrap_or_default().is_empty()))
        .collect()
}

// ─── 앱 진입점 ─────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let watch_inner: Arc<Mutex<Option<std::process::Child>>> = Arc::new(Mutex::new(None));
    let watch_inner_for_exit = Arc::clone(&watch_inner);

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|_app| {
            // 앱 시작 시 vib CLI를 터미널 PATH에 자동 설치
            if let Err(e) = vib_path::install_cli_to_path() {
                eprintln!("VibeLign: CLI PATH 설치 실패 — {e}");
            }
            Ok(())
        })
        .manage(WatchState(watch_inner))
        .invoke_handler(tauri::generate_handler![
            get_vib_path,
            setup_cli_path,
            run_vib,
            save_api_key,
            load_api_key,
            delete_api_key,
            save_provider_api_key,
            delete_provider_api_key,
            load_provider_api_keys,
            save_recent_projects,
            load_recent_projects,
            start_watch,
            stop_watch,
            watch_status,
            open_folder,
            get_env_key_status,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            match event {
                tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. } => {
                    if let Ok(mut guard) = watch_inner_for_exit.lock() {
                        if let Some(mut child) = guard.take() {
                            kill_watch_child(&mut child);
                        }
                    }
                }
                _ => {}
            }
        });
}
// === ANCHOR: LIB_END ===
