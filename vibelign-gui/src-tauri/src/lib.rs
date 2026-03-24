// === ANCHOR: LIB_START ===
mod vib_path;

use std::collections::HashMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

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

// ─── 앱 진입점 ─────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![get_vib_path, run_vib])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
// === ANCHOR: LIB_END ===
