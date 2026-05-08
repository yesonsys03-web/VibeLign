use std::collections::HashMap;
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};

use serde::Serialize;
use tauri::Emitter;

use crate::vib_path;

use super::platform::augmented_vib_path;

#[derive(Serialize, serde::Deserialize)]
pub struct VibResult {
    pub ok: bool,
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

/// 프론트엔드가 `run_vib` 에 주입할 수 있는 환경변수 키 목록.
/// 이 목록에 없거나 `VIBELIGN_` 접두사가 아닌 키는 무시한다.
/// Why: 임의의 env(`LD_PRELOAD`, `PYTHONPATH`, `DYLD_INSERT_LIBRARIES` 등) 주입으로
/// vib 서브프로세스에서 코드 실행이 가능해지는 것을 IPC 경계에서 차단한다.
const ALLOWED_VIB_ENV_KEYS: &[&str] = &[
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GLM_API_KEY",
    "MOONSHOT_API_KEY",
    "PYTHONUTF8",
    "PYTHONIOENCODING",
    "NO_COLOR",
    "VIBELIGN_ASK_PLAIN",
    "VIBELIGN_PROJECT_ROOT",
];

fn is_allowed_vib_env_key(k: &str) -> bool {
    ALLOWED_VIB_ENV_KEYS.contains(&k) || k.starts_with("VIBELIGN_")
}

fn apply_project_rust_engine_env(
    cmd: &mut std::process::Command,
    cwd: Option<&Path>,
    env: Option<&HashMap<String, String>>,
) {
    if env
        .and_then(|env_map| env_map.get("VIBELIGN_ENGINE_PATH"))
        .is_some()
    {
        return;
    }
    if let Some(engine) = vib_path::find_runtime_rust_engine(cwd) {
        cmd.env("VIBELIGN_ENGINE_PATH", engine);
    }
}

/// vib 실행 파일 경로를 반환한다. 없으면 None.
#[tauri::command]
pub(crate) fn get_vib_path() -> Option<String> {
    vib_path::find_runtime_vib().map(|p| p.to_string_lossy().into_owned())
}

/// vib CLI를 실행하고 결과를 반환한다.
///
/// - `args`: `["doctor", "--json"]` 등
/// - `cwd`: 프로젝트 루트 경로 (없으면 현재 디렉터리)
/// - `env`: 추가 환경변수 (`{"ANTHROPIC_API_KEY": "..."}` 등)
#[tauri::command]
pub(crate) async fn run_vib(
    args: Vec<String>,
    cwd: Option<String>,
    env: Option<HashMap<String, String>>,
) -> VibResult {
    let vib = match vib_path::find_runtime_vib() {
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
        cmd.env("PATH", augmented_vib_path());

        let cwd_path = cwd.map(PathBuf::from);
        if let Some(dir) = cwd_path.as_ref() {
            cmd.current_dir(dir);
        }

        apply_project_rust_engine_env(&mut cmd, cwd_path.as_deref(), env.as_ref());

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
                if is_allowed_vib_env_key(&k) {
                    cmd.env(k, v);
                }
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

#[derive(Serialize, Clone)]
struct VibProgressEvent {
    step: String,
    done: Option<u64>,
    total: Option<u64>,
    cached: Option<u64>,
    to_call: Option<u64>,
    batches: Option<u64>,
    message: Option<String>,
    stage: Option<String>,
    batch: Option<u64>,
    count: Option<u64>,
    processed: Option<u64>,
    failed: Option<u64>,
    retried: Option<u64>,
    anchors: Option<u64>,
}

fn parse_progress_line(line: &str) -> Option<VibProgressEvent> {
    let rest = line.strip_prefix("[progress]")?.trim();
    let mut step: Option<String> = None;
    let mut done: Option<u64> = None;
    let mut total: Option<u64> = None;
    let mut cached: Option<u64> = None;
    let mut to_call: Option<u64> = None;
    let mut batches: Option<u64> = None;
    let mut message: Option<String> = None;
    let mut stage: Option<String> = None;
    let mut batch: Option<u64> = None;
    let mut count: Option<u64> = None;
    let mut processed: Option<u64> = None;
    let mut failed: Option<u64> = None;
    let mut retried: Option<u64> = None;
    let mut anchors: Option<u64> = None;
    for token in rest.split_whitespace() {
        let Some(eq) = token.find('=') else { continue };
        let (k, v) = token.split_at(eq);
        let v = &v[1..];
        match k {
            "step" => step = Some(v.to_string()),
            "done" => done = v.parse().ok(),
            "total" => total = v.parse().ok(),
            "cached" => cached = v.parse().ok(),
            "to_call" => to_call = v.parse().ok(),
            "batches" => batches = v.parse().ok(),
            "msg" => message = Some(v.to_string()),
            "stage" => stage = Some(v.to_string()),
            "batch" => batch = v.parse().ok(),
            "count" => count = v.parse().ok(),
            "processed" => processed = v.parse().ok(),
            "failed" => failed = v.parse().ok(),
            "retried" => retried = v.parse().ok(),
            "anchors" => anchors = v.parse().ok(),
            _ => {}
        }
    }
    Some(VibProgressEvent {
        step: step.unwrap_or_default(),
        done,
        total,
        cached,
        to_call,
        batches,
        message,
        stage,
        batch,
        count,
        processed,
        failed,
        retried,
        anchors,
    })
}

fn emit_progress_line(app: &tauri::AppHandle, event_name: &str, line: &str) {
    if let Some(payload) = parse_progress_line(line) {
        let _ = app.emit(event_name, payload);
    }
}

#[tauri::command]
pub(crate) async fn run_vib_with_progress(
    app: tauri::AppHandle,
    args: Vec<String>,
    cwd: Option<String>,
    env: Option<HashMap<String, String>>,
    event_name: String,
) -> VibResult {
    let vib = match vib_path::find_runtime_vib() {
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
        cmd.stdout(std::process::Stdio::piped());
        cmd.stderr(std::process::Stdio::piped());
        cmd.env("PATH", augmented_vib_path());
        cmd.env("PYTHONUNBUFFERED", "1");

        let cwd_path = cwd.map(PathBuf::from);
        if let Some(dir) = cwd_path.as_ref() {
            cmd.current_dir(dir);
        }

        apply_project_rust_engine_env(&mut cmd, cwd_path.as_deref(), env.as_ref());

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            cmd.env("PYTHONUTF8", "1");
            cmd.env("PYTHONIOENCODING", "utf-8");
            cmd.env("NO_COLOR", "1");
            cmd.creation_flags(CREATE_NO_WINDOW);
        }

        if let Some(env_map) = env {
            for (k, v) in env_map {
                if is_allowed_vib_env_key(&k) {
                    cmd.env(k, v);
                }
            }
        }

        let mut child = match cmd.spawn() {
            Ok(c) => c,
            Err(e) => {
                return VibResult {
                    ok: false,
                    stdout: String::new(),
                    stderr: e.to_string(),
                    exit_code: -1,
                };
            }
        };

        let stdout_handle = child.stdout.take();
        let stderr_handle = child.stderr.take();

        let app_for_stderr = app.clone();
        let event_for_stderr = event_name.clone();
        let stderr_thread = stderr_handle.map(|err| {
            std::thread::spawn(move || read_stderr_stream(err, &app_for_stderr, &event_for_stderr))
        });

        let stdout_thread = stdout_handle.map(|out| {
            std::thread::spawn(move || {
                let mut buf = String::new();
                let mut reader = BufReader::new(out);
                let _ = std::io::Read::read_to_string(&mut reader, &mut buf);
                buf
            })
        });

        let status = child.wait();
        let stderr_log = stderr_thread
            .and_then(|t| t.join().ok())
            .unwrap_or_default();
        let stdout_log = stdout_thread
            .and_then(|t| t.join().ok())
            .unwrap_or_default();

        match status {
            Ok(s) => VibResult {
                ok: s.success(),
                stdout: stdout_log,
                stderr: stderr_log,
                exit_code: s.code().unwrap_or(-1),
            },
            Err(e) => VibResult {
                ok: false,
                stdout: stdout_log,
                stderr: format!("{}\n{}", stderr_log, e),
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

#[cfg(not(target_os = "windows"))]
fn read_stderr_stream<R: Read + Send + 'static>(reader: R, app: &tauri::AppHandle, event_name: &str) -> String {
    let mut accumulated = String::new();
    for line in BufReader::new(reader).lines().map_while(Result::ok) {
        emit_progress_line(app, event_name, &line);
        accumulated.push_str(&line);
        accumulated.push('\n');
    }
    accumulated
}

#[cfg(target_os = "windows")]
fn read_stderr_stream<R: Read + Send + 'static>(reader: R, app: &tauri::AppHandle, event_name: &str) -> String {
    let mut accumulated = String::new();
    let mut reader = BufReader::new(reader);
    let mut buf: Vec<u8> = Vec::new();
    let mut byte = [0_u8; 1];
    loop {
        match reader.read(&mut byte) {
            Ok(0) => {
                if !buf.is_empty() {
                    let line = String::from_utf8_lossy(&buf).into_owned();
                    emit_progress_line(app, event_name, &line);
                    accumulated.push_str(&line);
                    accumulated.push('\n');
                }
                break;
            }
            Ok(_) => match byte[0] {
                b'\n' | b'\r' => {
                    if !buf.is_empty() {
                        let line = String::from_utf8_lossy(&buf).into_owned();
                        emit_progress_line(app, event_name, &line);
                        accumulated.push_str(&line);
                        accumulated.push('\n');
                        buf.clear();
                    }
                }
                b => buf.push(b),
            },
            Err(_) => break,
        }
    }
    accumulated
}
