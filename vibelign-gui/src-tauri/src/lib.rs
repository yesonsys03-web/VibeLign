// === ANCHOR: LIB_START ===
mod vib_path;

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::Mutex;

use serde::{Deserialize, Serialize};

// ─── Watch 프로세스 State ──────────────────────────────────────────────────────

struct WatchState(Mutex<Option<std::process::Child>>);

impl Drop for WatchState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}

#[tauri::command]
fn start_watch(state: tauri::State<WatchState>, cwd: String) -> Result<(), String> {
    let vib = vib_path::find_vib().ok_or("vib 실행 파일을 찾을 수 없습니다")?;
    // 기존 watch가 있으면 먼저 중지
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(ref mut child) = *guard {
        let _ = child.kill();
    }
    let child = std::process::Command::new(&vib)
        .arg("watch")
        .current_dir(PathBuf::from(&cwd))
        .spawn()
        .map_err(|e| e.to_string())?;
    *guard = Some(child);
    Ok(())
}

#[tauri::command]
fn stop_watch(state: tauri::State<WatchState>) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.take() {
        let _ = child.kill();
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

        if let Some(dir) = cwd {
            cmd.current_dir(PathBuf::from(dir));
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

#[tauri::command]
fn save_api_key(key: String) -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    let existing = std::fs::read_to_string(&path)
        .ok()
        .and_then(|t| serde_json::from_str::<serde_json::Value>(&t).ok())
        .unwrap_or(serde_json::json!({}));
    let mut data = existing;
    data["anthropic_api_key"] = serde_json::Value::String(key);
    std::fs::write(&path, data.to_string()).map_err(|e| e.to_string())
}

#[tauri::command]
fn load_api_key() -> Option<String> {
    let path = config_path()?;
    let text = std::fs::read_to_string(&path).ok()?;
    let data: serde_json::Value = serde_json::from_str(&text).ok()?;
    data["anthropic_api_key"].as_str().map(String::from)
}

#[tauri::command]
fn delete_api_key() -> Result<(), String> {
    let path = config_path().ok_or("홈 디렉터리를 찾을 수 없습니다")?;
    if !path.exists() {
        return Ok(());
    }
    let text = std::fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let mut data: serde_json::Value =
        serde_json::from_str(&text).unwrap_or(serde_json::json!({}));
    if let Some(obj) = data.as_object_mut() {
        obj.remove("anthropic_api_key");
    }
    std::fs::write(&path, data.to_string()).map_err(|e| e.to_string())
}

// ─── 앱 진입점 ─────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(WatchState(Mutex::new(None)))
        .invoke_handler(tauri::generate_handler![
            get_vib_path,
            run_vib,
            save_api_key,
            load_api_key,
            delete_api_key,
            save_recent_projects,
            load_recent_projects,
            start_watch,
            stop_watch,
            watch_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
// === ANCHOR: LIB_END ===
