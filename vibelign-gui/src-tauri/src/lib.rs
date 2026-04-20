// === ANCHOR: LIB_START ===
mod onboarding;
mod vib_path;

use std::collections::HashMap;
use std::collections::VecDeque;
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use tauri::Emitter;
#[cfg(not(debug_assertions))]
use tauri::Manager;

use onboarding::{OnboardingRuntime, OnboardingState};

pub use onboarding::testing;

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

#[derive(Serialize)]
struct ReadFileResult {
    path: String,
    content: String,
    source_hash: String,
}

#[derive(Serialize, Deserialize)]
struct DocsIndexEntry {
    category: String,
    path: String,
    title: String,
    modified_at_ms: i64,
}

const DOCS_INDEX_CACHE_SCHEMA_VERSION: i64 = 1;

#[derive(Deserialize)]
struct DocsIndexCachePayload {
    schema_version: i64,
    root: String,
    #[serde(default)]
    entries: Vec<DocsIndexEntry>,
}

/// `.vibelign/docs_index.json` 을 읽어 엔트리 리스트로 돌려준다.
/// miss/schema 불일치/root 불일치/파싱 실패 시 None 을 반환해 subprocess 폴백을 허용한다.
fn read_docs_index_cache_file(root: &Path) -> Option<Vec<DocsIndexEntry>> {
    let cache_path = root.join(".vibelign").join("docs_index.json");
    let raw = std::fs::read_to_string(&cache_path).ok()?;
    let payload: DocsIndexCachePayload = serde_json::from_str(&raw).ok()?;
    if payload.schema_version != DOCS_INDEX_CACHE_SCHEMA_VERSION {
        return None;
    }
    let cached_root = strip_unc_prefix(
        PathBuf::from(&payload.root).canonicalize().ok()?,
    );
    if cached_root != root {
        return None;
    }
    Some(payload.entries)
}

#[derive(Serialize, Deserialize, Clone)]
struct DocsVisualContract {
    schema_version: i64,
    generator_version: String,
}

// contract 는 vib 바이너리에 baked-in 된 정적 값이라 프로세스 수명 내에서 바뀌지 않는다.
// 매 문서 클릭마다 vib subprocess 를 스폰하던 병목을 없애기 위해 첫 호출 결과를 메모리에 캐시한다.
static DOCS_VISUAL_CONTRACT_CACHE: Mutex<Option<DocsVisualContract>> = Mutex::new(None);

#[derive(Serialize)]
struct DocsVisualReadResult {
    path: String,
    artifact: serde_json::Value,
    contract: DocsVisualContract,
}

fn normalize_markdown_content(bytes: &[u8]) -> Result<String, String> {
    let bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(bytes);
    let text = std::str::from_utf8(bytes)
        .map_err(|_| "UTF-8 markdown 파일만 읽을 수 있어요".to_string())?;
    Ok(text.replace("\r\n", "\n").replace('\r', "\n"))
}

fn hash_markdown_content(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn normalize_relative_doc_path(path: &std::path::Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}

/// Python `docs_scan.IGNORED_DIRS` 와 같은 집합 — 인덱스 스캔에서 제외되는 폴더는
/// read_file 에서도 차단해 동일한 화이트리스트 규칙을 유지한다.
const DOCS_READ_IGNORED_DIRS: &[&str] = &[
    "node_modules", "target", "dist", "build", "out", "coverage",
    ".next", ".nuxt", ".turbo", ".cache", ".venv", "venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".gradle", ".idea", ".vscode", ".DS_Store",
];

fn is_allowed_doc_path(relative_path: &str) -> bool {
    let lower = relative_path.to_ascii_lowercase();
    if !lower.ends_with(".md") && !lower.ends_with(".markdown") {
        return false;
    }
    // 경로 탈출 차단
    if relative_path.contains("..") {
        return false;
    }
    // 모든 세그먼트가 숨김/무시 목록이 아니어야 한다 — docs_scan 의 prune 규칙과 대칭.
    for segment in relative_path.split('/') {
        if segment.is_empty() {
            return false;
        }
        if segment.starts_with('.') {
            return false;
        }
        if DOCS_READ_IGNORED_DIRS.contains(&segment) {
            return false;
        }
    }
    true
}

fn resolve_doc_path(root: &str, path: PathBuf) -> Result<(PathBuf, String), String> {
    let root_path = PathBuf::from(root)
        .canonicalize()
        .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?;
    let joined = if path.is_absolute() {
        path
    } else {
        root_path.join(path)
    };
    let canonical = joined
        .canonicalize()
        .map_err(|e| format!("문서를 찾을 수 없어요: {e}"))?;
    let relative = canonical
        .strip_prefix(&root_path)
        .map_err(|_| "프로젝트 루트 밖 파일은 읽을 수 없어요".to_string())?;
    let relative_path = normalize_relative_doc_path(relative);
    if !is_allowed_doc_path(&relative_path) {
        return Err("허용된 markdown 문서만 읽을 수 있어요".into());
    }
    Ok((canonical, relative_path))
}

#[tauri::command]
fn read_file(root: String, path: PathBuf) -> Result<ReadFileResult, String> {
    let (resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    let bytes = std::fs::read(&resolved_path).map_err(|e| format!("문서를 읽을 수 없어요: {e}"))?;
    let content = normalize_markdown_content(&bytes)?;
    Ok(ReadFileResult {
        path: relative_path,
        source_hash: hash_markdown_content(&content),
        content,
    })
}

/// Windows `canonicalize()` 가 반환하는 `\\?\` 접두사를 벗겨서
/// 외부 프로세스가 경로를 올바르게 해석하도록 한다.
fn strip_unc_prefix(p: PathBuf) -> PathBuf {
    #[cfg(target_os = "windows")]
    {
        let s = p.to_string_lossy();
        if let Some(stripped) = s.strip_prefix(r"\\?\") {
            return PathBuf::from(stripped);
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
fn augmented_vib_path() -> std::ffi::OsString {
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

/// `vib docs-index` 명령으로 docs index/visual contract를 받는다.
/// vib sidecar에는 vibelign 패키지가 self-contained 되어 있어 별도 Python 환경이 없어도 동작한다.
fn run_vib_docs_index(root: &Path, extra_args: &[&str]) -> Option<Result<String, String>> {
    let vib = vib_path::find_runtime_vib()?;
    let mut command = std::process::Command::new(&vib);
    command.arg("docs-index");
    // 기존 호출자가 넘기던 `--print-visual-contract` 를 새 CLI 플래그로 변환.
    let mut visual_contract = false;
    for arg in extra_args {
        if *arg == "--print-visual-contract" {
            visual_contract = true;
        }
    }
    if visual_contract {
        command.arg("--visual-contract");
    } else {
        command.arg(root.as_os_str());
    }
    command
        .current_dir(root)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .env("PATH", augmented_vib_path())
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8");

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    match command.output() {
        Ok(output) if output.status.success() => {
            Some(Ok(String::from_utf8_lossy(&output.stdout).into_owned()))
        }
        Ok(output) => {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
            let msg = if !stderr.is_empty() { stderr } else if !stdout.is_empty() { stdout } else { "vib docs-index 실행 실패".into() };
            Some(Err(format!("[vib docs-index] {msg}")))
        }
        Err(err) => Some(Err(format!("[vib docs-index] 실행 실패: {err}"))),
    }
}

fn run_docs_cache_helper(root: &str, extra_args: &[&str]) -> Result<String, String> {
    let root_path = strip_unc_prefix(
        PathBuf::from(root)
            .canonicalize()
            .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?,
    );

    match run_vib_docs_index(&root_path, extra_args) {
        Some(Ok(s)) => Ok(s),
        Some(Err(e)) => Err(format!(
            "{e}\n\nvib이 오래된 버전일 수 있어요. GUI를 재설치해 주세요."
        )),
        None => Err("vib을 찾을 수 없어요. GUI를 재설치해 주세요.".into()),
    }
}

#[tauri::command]
fn list_docs_index(root: String) -> Result<Vec<DocsIndexEntry>, String> {
    // 1) 캐시 파일이 있으면 즉시 반환 — subprocess cold-start 를 우회한다.
    let root_path = strip_unc_prefix(
        PathBuf::from(&root)
            .canonicalize()
            .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?,
    );
    if let Some(entries) = read_docs_index_cache_file(&root_path) {
        return Ok(entries);
    }

    // 2) 캐시 miss: subprocess 가 인덱스를 만들고 캐시 파일을 기록한다 (side-effect).
    let raw = run_docs_cache_helper(&root, &[])?;
    serde_json::from_str::<Vec<DocsIndexEntry>>(raw.trim())
        .map_err(|e| format!("docs index 결과를 해석할 수 없어요: {e}"))
}

/// 사이드바 새로고침 버튼이 호출한다. 캐시를 건너뛰고 강제로 subprocess 를 돌려
/// 파일 시스템 변화를 즉시 반영한다. Python 쪽이 캐시를 새로 기록하므로 후속 호출은
/// 다시 캐시 hit.
#[tauri::command]
fn rebuild_docs_index(root: String) -> Result<Vec<DocsIndexEntry>, String> {
    let raw = run_docs_cache_helper(&root, &[])?;
    serde_json::from_str::<Vec<DocsIndexEntry>>(raw.trim())
        .map_err(|e| format!("docs index 결과를 해석할 수 없어요: {e}"))
}

fn read_docs_visual_contract(root: &str) -> Result<DocsVisualContract, String> {
    if let Ok(guard) = DOCS_VISUAL_CONTRACT_CACHE.lock() {
        if let Some(cached) = guard.as_ref() {
            return Ok(cached.clone());
        }
    }

    let raw = run_docs_cache_helper(root, &["--print-visual-contract"])?;
    let payload: serde_json::Value = serde_json::from_str(raw.trim())
        .map_err(|e| format!("docs visual contract를 해석할 수 없어요: {e}"))?;
    let contract_value = payload
        .get("contract")
        .ok_or_else(|| "docs visual contract 항목이 없어요".to_string())?
        .clone();
    let contract: DocsVisualContract = serde_json::from_value(contract_value)
        .map_err(|e| format!("docs visual contract 형식이 올바르지 않아요: {e}"))?;

    if let Ok(mut guard) = DOCS_VISUAL_CONTRACT_CACHE.lock() {
        *guard = Some(contract.clone());
    }
    Ok(contract)
}

#[tauri::command]
fn read_docs_visual(root: String, path: PathBuf) -> Result<Option<DocsVisualReadResult>, String> {
    let (resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    let root_path = PathBuf::from(&root)
        .canonicalize()
        .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?;
    let relative = resolved_path
        .strip_prefix(&root_path)
        .map_err(|_| "프로젝트 루트 밖 파일은 읽을 수 없어요".to_string())?;
    let artifact_path = root_path
        .join(".vibelign")
        .join("docs_visual")
        .join(format!("{}.json", normalize_relative_doc_path(relative)));

    if !artifact_path.exists() {
        return Ok(None);
    }

    let artifact_text = std::fs::read_to_string(&artifact_path)
        .map_err(|e| format!("docs visual artifact를 읽을 수 없어요: {e}"))?;
    let artifact: serde_json::Value = serde_json::from_str(&artifact_text)
        .map_err(|e| format!("docs visual artifact JSON이 손상되었어요: {e}"))?;
    let contract = read_docs_visual_contract(&root)?;

    Ok(Some(DocsVisualReadResult {
        path: relative_path,
        artifact,
        contract,
    }))
}

#[tauri::command]
async fn enhance_doc_with_ai(
    root: String,
    path: PathBuf,
    models: Option<HashMap<String, String>>,
) -> Result<String, String> {
    let (_resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    let keys = read_keys_file();
    const PROVIDER_ENVS: &[&str] = &[
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GLM_API_KEY",
        "MOONSHOT_API_KEY",
    ];
    let available: Vec<(&str, String)> = PROVIDER_ENVS
        .iter()
        .filter_map(|name| {
            keys.get(*name)
                .map(|v| v.trim().to_string())
                .filter(|v| !v.is_empty())
                .map(|v| (*name, v))
        })
        .collect();
    if available.is_empty() {
        return Err(
            "설정 > API 키에 Anthropic/OpenAI/Gemini 중 하나의 키를 먼저 등록해주세요".into(),
        );
    }
    let vib = vib_path::find_runtime_vib()
        .ok_or_else(|| "vib 실행 파일을 찾을 수 없습니다".to_string())?;
    let mut command = std::process::Command::new(&vib);
    command
        .arg("docs-enhance")
        .arg(&relative_path)
        .arg("--json")
        .current_dir(&root)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .env("PATH", augmented_vib_path())
        .env("VIBELIGN_PROJECT_ROOT", &root)
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8");
    for (name, value) in &available {
        command.env(name, value);
    }
    if let Some(selected) = models {
        for (provider, model) in selected {
            let trimmed = model.trim();
            if trimmed.is_empty() {
                continue;
            }
            // provider 는 프런트엔드 입력이므로 env 이름으로 조립하기 전 문자 화이트리스트로 검증한다.
            // Why: 허용문자를 벗어난 이름은 플랫폼에 따라 env 주입/덮어쓰기가 가능하다.
            if provider.is_empty()
                || !provider
                    .chars()
                    .all(|c| c.is_ascii_alphanumeric() || c == '_')
            {
                continue;
            }
            let env_name = format!("VIBELIGN_DOCS_AI_MODEL_{}", provider.to_uppercase());
            command.env(env_name, trimmed);
        }
    }
    hide_console(&mut command);
    let output = command
        .output()
        .map_err(|e| format!("vib docs-enhance 실행 실패: {e}"))?;
    if !output.status.success() {
        let err = String::from_utf8_lossy(&output.stderr);
        let out = String::from_utf8_lossy(&output.stdout);
        let msg = if !err.trim().is_empty() { err.trim().to_string() } else { out.trim().to_string() };
        return Err(format!("docs-enhance 실패: {}", msg));
    }
    Ok(String::from_utf8_lossy(&output.stdout).into_owned())
}

// ─── Watch 프로세스 State ──────────────────────────────────────────────────────

const WATCH_BUFFER_LIMIT: usize = 200;

struct WatchRuntime {
    child: Option<std::process::Child>,
    logs: VecDeque<String>,
    errors: VecDeque<String>,
}

impl WatchRuntime {
    fn new() -> Self {
        Self {
            child: None,
            logs: VecDeque::with_capacity(WATCH_BUFFER_LIMIT),
            errors: VecDeque::with_capacity(WATCH_BUFFER_LIMIT),
        }
    }
}

struct WatchState(Arc<Mutex<WatchRuntime>>);

fn push_watch_line(buffer: &mut VecDeque<String>, line: String) {
    if line.is_empty() {
        return;
    }
    if buffer.len() >= WATCH_BUFFER_LIMIT {
        let _ = buffer.pop_front();
    }
    buffer.push_back(line);
}

#[cfg(target_os = "windows")]
fn emit_watch_log(app: &tauri::AppHandle, state: &Arc<Mutex<WatchRuntime>>, bytes: &[u8]) {
    let line = String::from_utf8_lossy(bytes).trim().to_string();
    if !line.is_empty() {
        if let Ok(mut guard) = state.lock() {
            push_watch_line(&mut guard.logs, line.clone());
        }
        let _ = app.emit("watch_log", line);
    }
}

#[cfg(target_os = "windows")]
fn emit_watch_error(app: &tauri::AppHandle, state: &Arc<Mutex<WatchRuntime>>, bytes: &[u8]) {
    let line = String::from_utf8_lossy(bytes).trim().to_string();
    if !line.is_empty() {
        if let Ok(mut guard) = state.lock() {
            push_watch_line(&mut guard.errors, line.clone());
        }
        let _ = app.emit("watch_error", line);
    }
}

#[cfg(target_os = "windows")]
fn spawn_watch_log_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        let mut reader = BufReader::new(reader);
        let mut buf = Vec::new();
        let mut byte = [0_u8; 1];

        loop {
            match reader.read(&mut byte) {
                Ok(0) => {
                    emit_watch_log(&app, &state, &buf);
                    break;
                }
                Ok(_) => match byte[0] {
                    b'\n' | b'\r' => {
                        emit_watch_log(&app, &state, &buf);
                        buf.clear();
                    }
                    b => buf.push(b),
                },
                Err(_) => {
                    emit_watch_log(&app, &state, &buf);
                    break;
                }
            }
        }
    });
}

#[cfg(not(target_os = "windows"))]
fn spawn_watch_log_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            if let Ok(line) = line {
                let trimmed = line.trim().to_string();
                if let Ok(mut guard) = state.lock() {
                    push_watch_line(&mut guard.logs, trimmed);
                }
                let _ = app.emit("watch_log", line);
            }
        }
    });
}

#[cfg(not(target_os = "windows"))]
fn spawn_watch_error_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            if let Ok(line) = line {
                let trimmed = line.trim().to_string();
                if !trimmed.is_empty() {
                    if let Ok(mut guard) = state.lock() {
                        push_watch_line(&mut guard.errors, trimmed.clone());
                    }
                    let _ = app.emit("watch_error", trimmed);
                }
            }
        }
    });
}

#[cfg(target_os = "windows")]
fn spawn_watch_error_thread<R: Read + Send + 'static>(reader: R, app: tauri::AppHandle, state: Arc<Mutex<WatchRuntime>>) {
    std::thread::spawn(move || {
        let mut reader = BufReader::new(reader);
        let mut buf = Vec::new();
        let mut byte = [0_u8; 1];

        loop {
            match reader.read(&mut byte) {
                Ok(0) => {
                    emit_watch_error(&app, &state, &buf);
                    break;
                }
                Ok(_) => match byte[0] {
                    b'\n' | b'\r' => {
                        emit_watch_error(&app, &state, &buf);
                        buf.clear();
                    }
                    b => buf.push(b),
                },
                Err(_) => {
                    emit_watch_error(&app, &state, &buf);
                    break;
                }
            }
        }
    });
}

fn kill_watch_child(child: &mut std::process::Child) {
    #[cfg(unix)]
    unsafe {
        let pgid = child.id() as i32;
        libc::killpg(pgid, libc::SIGKILL);
    }
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;

        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        let pid = child.id().to_string();
        let killed_tree = std::process::Command::new("taskkill")
            .args(["/PID", pid.as_str(), "/T", "/F"])
            .creation_flags(CREATE_NO_WINDOW)
            .status()
            .map(|status| status.success())
            .unwrap_or(false);

        if !killed_tree {
            let _ = child.kill();
        }
    }
    #[cfg(all(not(unix), not(target_os = "windows")))]
    { let _ = child.kill(); }
    let _ = child.wait();
}

impl Drop for WatchState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.0.lock() {
            if let Some(mut child) = guard.child.take() {
                kill_watch_child(&mut child);
            }
        }
    }
}

#[tauri::command]
fn start_watch(app: tauri::AppHandle, state: tauri::State<WatchState>, cwd: String) -> Result<(), String> {
    let vib = vib_path::find_watch_vib().ok_or("watch에 사용할 vib 실행 파일을 찾을 수 없습니다")?;
    // 기존 watch가 있으면 먼저 중지
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(ref mut child) = guard.child {
        kill_watch_child(child);
    }
    guard.child = None;
    guard.logs.clear();
    guard.errors.clear();
    let mut watch_cmd = std::process::Command::new(&vib);
    watch_cmd.arg("watch").current_dir(PathBuf::from(&cwd));
    watch_cmd.stdin(std::process::Stdio::piped());
    watch_cmd.stdout(std::process::Stdio::piped());
    watch_cmd.stderr(std::process::Stdio::piped());
    watch_cmd.env("PATH", augmented_vib_path());
    watch_cmd.env("PYTHONUNBUFFERED", "1");
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        watch_cmd.env("VIBELIGN_ASK_PLAIN", "1");
        watch_cmd.env("NO_COLOR", "1");
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
    guard.child = Some(child);
    let watch_state = Arc::clone(&state.0);
    drop(guard);

    if let Some(out) = stdout {
        let app2 = app.clone();
        spawn_watch_log_thread(out, app2, Arc::clone(&watch_state));
    }
    if let Some(err) = stderr {
        spawn_watch_error_thread(err, app, watch_state);
    }
    Ok(())
}

#[tauri::command]
fn stop_watch(state: tauri::State<WatchState>) -> Result<(), String> {
    let mut guard = state.0.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = guard.child.take() {
        kill_watch_child(&mut child);
    }
    Ok(())
}

#[tauri::command]
fn watch_status(state: tauri::State<WatchState>) -> bool {
    state.0.lock()
        .map(|g| g.child.is_some())
        .unwrap_or(false)
}

#[tauri::command]
fn get_watch_logs(state: tauri::State<WatchState>) -> Vec<String> {
    state
        .0
        .lock()
        .map(|g| g.logs.iter().cloned().collect())
        .unwrap_or_default()
}

#[tauri::command]
fn get_watch_errors(state: tauri::State<WatchState>) -> Vec<String> {
    state
        .0
        .lock()
        .map(|g| g.errors.iter().cloned().collect())
        .unwrap_or_default()
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

/// vib 실행 파일 경로를 반환한다. 없으면 None.
#[tauri::command]
fn get_vib_path() -> Option<String> {
    vib_path::find_runtime_vib().map(|p| p.to_string_lossy().into_owned())
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
async fn run_vib_with_progress(
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

        if let Some(dir) = cwd {
            cmd.current_dir(PathBuf::from(dir));
        }

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

// ─── API 키 저장소 ─────────────────────────────────────────────────────────────

/// 플랫폼별 api_keys.json 경로.
/// macOS/Linux: ~/.config/vibelign/api_keys.json
/// Windows:     %APPDATA%\vibelign\api_keys.json
fn keys_file_path() -> Option<PathBuf> {
    #[cfg(target_os = "windows")]
    {
        let appdata = std::env::var("APPDATA").ok()?;
        let dir = PathBuf::from(appdata).join("vibelign");
        std::fs::create_dir_all(&dir).ok()?;
        return Some(dir.join("api_keys.json"));
    }
    #[cfg(not(target_os = "windows"))]
    {
        let xdg_config = std::env::var("XDG_CONFIG_HOME")
            .map(PathBuf::from)
            .unwrap_or_else(|_| {
                let home = std::env::var("HOME")
                    .or_else(|_| std::env::var("USERPROFILE"))
                    .unwrap_or_default();
                PathBuf::from(home).join(".config")
            });
        let dir = xdg_config.join("vibelign");
        std::fs::create_dir_all(&dir).ok()?;
        Some(dir.join("api_keys.json"))
    }
}

fn read_keys_file() -> HashMap<String, String> {
    let path = match keys_file_path() { Some(p) => p, None => return HashMap::new() };
    let text = match std::fs::read_to_string(&path) { Ok(t) => t, Err(_) => return HashMap::new() };
    let val: serde_json::Value = match serde_json::from_str(&text) { Ok(v) => v, Err(_) => return HashMap::new() };
    let mut out = HashMap::new();
    if let Some(obj) = val.as_object() {
        for (k, v) in obj {
            if let Some(s) = v.as_str() {
                if !s.is_empty() { out.insert(k.clone(), s.to_string()); }
            }
        }
    }
    out
}

fn write_keys_file(keys: &HashMap<String, String>) -> Result<(), String> {
    let path = keys_file_path().ok_or("keys 파일 경로를 찾을 수 없습니다")?;
    let val = serde_json::to_string_pretty(keys).map_err(|e| e.to_string())?;
    std::fs::write(&path, val + "\n").map_err(|e| e.to_string())?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o600));
    }
    Ok(())
}

fn provider_to_env_key(provider: &str) -> &'static str {
    match provider {
        "ANTHROPIC" => "ANTHROPIC_API_KEY",
        "OPENAI"    => "OPENAI_API_KEY",
        "GEMINI"    => "GEMINI_API_KEY",
        "GLM"       => "GLM_API_KEY",
        "MOONSHOT"  => "MOONSHOT_API_KEY",
        _           => "",
    }
}

fn migrate_legacy_keys() {
    let new_path = match keys_file_path() { Some(p) => p, None => return };
    if new_path.exists() { return; }
    let legacy = read_gui_config();
    let pairs: &[(&str, &str)] = &[
        ("ANTHROPIC", "ANTHROPIC_API_KEY"),
        ("OPENAI",    "OPENAI_API_KEY"),
        ("GEMINI",    "GEMINI_API_KEY"),
        ("GLM",       "GLM_API_KEY"),
        ("MOONSHOT",  "MOONSHOT_API_KEY"),
    ];
    let mut migrated: HashMap<String, String> = HashMap::new();
    if let Some(obj) = legacy.get("provider_api_keys").and_then(|v| v.as_object()) {
        for (short, env_name) in pairs {
            if let Some(v) = obj.get(*short).and_then(|v| v.as_str()) {
                if !v.is_empty() { migrated.insert(env_name.to_string(), v.to_string()); }
            }
        }
    }
    if let Some(s) = legacy.get("anthropic_api_key").and_then(|v| v.as_str()) {
        if !s.is_empty() { migrated.entry("ANTHROPIC_API_KEY".into()).or_insert_with(|| s.to_string()); }
    }
    if !migrated.is_empty() { let _ = write_keys_file(&migrated); }
}

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
    // 임시 파일에 쓰고 rename 으로 원자 교체한다.
    // Why: API 키가 같은 파일에 저장되므로 중간 크래시 시 파일이 절단되면
    // 키를 잃는다. 동일 디렉터리 내 rename 은 POSIX / Windows 에서 원자적이다.
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, data.to_string()).map_err(|e| e.to_string())?;
    std::fs::rename(&tmp, &path).map_err(|e| e.to_string())
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

/// 현재 GUI 버전이 이미 CLI 를 PATH 에 설치했는지 확인한다.
/// Why: `install_cli_to_path` 가 앱 시작마다 호출되면서 사용자가 `uv tool install`/`pipx`
/// 등으로 직접 관리하던 `~/.local/bin/vib` 를 매번 덮어쓰는 문제를 차단한다.
fn cli_installed_for_current_version() -> bool {
    let cfg = read_gui_config();
    cfg.get("cli_path_installed_version")
        .and_then(|v| v.as_str())
        .map(|s| s == env!("CARGO_PKG_VERSION"))
        .unwrap_or(false)
}

fn mark_cli_installed_for_current_version() {
    let mut cfg = read_gui_config();
    if !cfg.is_object() {
        cfg = serde_json::json!({});
    }
    cfg["cli_path_installed_version"] =
        serde_json::Value::String(env!("CARGO_PKG_VERSION").to_string());
    let _ = write_gui_config(&cfg);
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
    save_provider_api_key("ANTHROPIC".to_string(), key)
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
    let env_key = provider_to_env_key(&provider);
    if env_key.is_empty() {
        return Err(format!("알 수 없는 provider: {provider}"));
    }
    let mut keys = read_keys_file();
    keys.insert(env_key.to_string(), key);
    write_keys_file(&keys)
}

#[tauri::command]
fn delete_provider_api_key(provider: String) -> Result<(), String> {
    let provider = provider.to_uppercase();
    let env_key = provider_to_env_key(&provider);
    if env_key.is_empty() {
        return Ok(());
    }
    let mut keys = read_keys_file();
    keys.remove(env_key);
    write_keys_file(&keys)
}

#[tauri::command]
fn load_provider_api_keys() -> HashMap<String, String> {
    let raw = read_keys_file();
    let pairs: &[(&str, &str)] = &[
        ("ANTHROPIC_API_KEY", "ANTHROPIC"),
        ("OPENAI_API_KEY",    "OPENAI"),
        ("GEMINI_API_KEY",    "GEMINI"),
        ("GLM_API_KEY",       "GLM"),
        ("MOONSHOT_API_KEY",  "MOONSHOT"),
    ];
    let mut out = HashMap::new();
    for (env_name, short_name) in pairs {
        if let Some(v) = raw.get(*env_name) {
            out.insert(short_name.to_string(), v.clone());
        }
    }
    out
}

// ─── 환경변수 + 키 파일 API 키 상태 ───────────────────────────────────────────

#[tauri::command]
fn get_env_key_status() -> HashMap<String, bool> {
    let keys = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GLM_API_KEY",
        "MOONSHOT_API_KEY",
    ];
    let stored = read_keys_file();
    keys.iter()
        .map(|k| {
            let from_env = !std::env::var(k).unwrap_or_default().is_empty();
            let from_file = stored.get(*k).map(|v| !v.is_empty()).unwrap_or(false);
            (k.to_string(), from_env || from_file)
        })
        .collect()
}

// ─── Git 설치 확인 ────────────────────────────────────────────────────────────

/// Windows 에서 자식 프로세스 실행 시 검은 콘솔 창이 순간적으로 뜨는 것을 막는다.
/// 비Windows 에서는 no-op.
#[cfg(target_os = "windows")]
fn hide_console(cmd: &mut std::process::Command) {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;
    cmd.creation_flags(CREATE_NO_WINDOW);
}

#[cfg(not(target_os = "windows"))]
fn hide_console(_cmd: &mut std::process::Command) {}

// ─── 프로젝트 요약 ─────────────────────────────────────────────────────────────

/// Windows에서 PATH에 git이 없을 때도 기본 설치 경로에서 찾아 반환
fn git_cmd() -> std::process::Command {
    // PATH에서 찾히면 바로 사용
    let mut probe = std::process::Command::new("git");
    probe.arg("--version");
    hide_console(&mut probe);
    if probe.output().map(|o| o.status.success()).unwrap_or(false) {
        let mut cmd = std::process::Command::new("git");
        hide_console(&mut cmd);
        return cmd;
    }
    #[cfg(target_os = "windows")]
    {
        let candidates = [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (Arm)\Git\cmd\git.exe",
        ];
        for path in &candidates {
            if std::path::Path::new(path).exists() {
                let mut cmd = std::process::Command::new(path);
                hide_console(&mut cmd);
                return cmd;
            }
        }
    }
    let mut cmd = std::process::Command::new("git"); // 최후 수단 — 실패해도 에러는 호출부에서 처리
    hide_console(&mut cmd);
    cmd
}

fn trunc(s: &str, max: usize) -> String {
    let mut chars = s.chars();
    let result: String = chars.by_ref().take(max).collect();
    if chars.next().is_some() { format!("{}…", result) } else { result }
}

fn parse_checkpoints_from_ctx(content: &str) -> Vec<[String; 2]> {
    let mut in_section = false;
    let mut results = Vec::new();
    for line in content.lines() {
        if line.starts_with("## 4.") { in_section = true; continue; }
        if in_section && line.starts_with("## ") { break; }
        if !in_section || !line.starts_with('|') { continue; }
        let cols: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if cols.len() < 3 { continue; }
        let ts = cols[1];
        let msg = cols[2];
        if msg.is_empty() || msg == "작업 내용" || msg.starts_with('-') || msg == "(메시지 없음)" { continue; }
        let detail = format!("{} — {}", ts, msg);
        results.push([trunc(msg, 20), detail]);
        if results.len() >= 2 { break; }
    }
    results
}

#[derive(Serialize)]
struct SummaryLine {
    display: String,
    detail: String,
}

#[derive(Serialize)]
struct ProjectSummary {
    project_name: String,
    checkpoints: Vec<SummaryLine>,
    git_commits: Vec<SummaryLine>,
}

#[tauri::command]
fn read_project_summary(dir: String) -> ProjectSummary {
    let path = std::path::Path::new(&dir);
    let project_name = path.file_name()
        .map(|n| n.to_string_lossy().to_string())
        .unwrap_or_else(|| "프로젝트".to_string());

    // git log: hash|subject|date (최근 3개)
    let git_commits = git_cmd()
        .args(["log", "-3", "--pretty=format:%h|%s|%ad", "--date=short"])
        .current_dir(path)
        .output()
        .ok()
        .map(|o| {
            String::from_utf8_lossy(&o.stdout).lines()
                .filter_map(|l| {
                    let parts: Vec<&str> = l.splitn(3, '|').collect();
                    if parts.len() < 2 { return None; }
                    let hash = parts[0].trim();
                    let subject = parts[1].trim();
                    if subject.is_empty() { return None; }
                    let date = parts.get(2).copied().unwrap_or("").trim();

                    // git show --stat: 변경 파일 목록 (on-load 프리페치)
                    let stat = git_cmd()
                        .args(["show", "--stat", "--pretty=format:%b", hash])
                        .current_dir(path)
                        .output()
                        .ok()
                        .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                        .unwrap_or_default();

                    let mut detail = format!("{} — {}", date, subject);
                    if !stat.is_empty() {
                        detail.push_str(&format!("\n\n{}", stat));
                    }

                    Some(SummaryLine { display: trunc(subject, 20), detail })
                })
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();

    let content = std::fs::read_to_string(path.join("PROJECT_CONTEXT.md")).unwrap_or_default();
    let checkpoints = parse_checkpoints_from_ctx(&content)
        .into_iter()
        .map(|[display, detail]| SummaryLine { display, detail })
        .collect();

    ProjectSummary { project_name, checkpoints, git_commits }
}

// ─── 앱 진입점 ─────────────────────────────────────────────────────────────────

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let watch_inner: Arc<Mutex<WatchRuntime>> = Arc::new(Mutex::new(WatchRuntime::new()));
    let watch_inner_for_exit = Arc::clone(&watch_inner);
    let onboarding_inner: Arc<Mutex<OnboardingRuntime>> = Arc::new(Mutex::new(OnboardingRuntime {
        snapshot: Some(onboarding::build_initial_onboarding_snapshot()),
        logs: String::new(),
    }));

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_process::init())
        .setup(|app| {
            #[cfg(all(desktop, feature = "updater"))]
            app.handle().plugin(tauri_plugin_updater::Builder::new().build())?;

            // 번들된 vib 실행파일 경로를 OnceLock 에 주입한다.
            // PyInstaller onedir 빌드는 `vib` 와 sibling `_internal/` 이 함께 있어야 실행되므로
            // Tauri PathResolver 의 resource_dir 를 통째로 보존하는 이 경로만 안전하다.
            #[cfg(not(debug_assertions))]
            {
                if let Ok(resource_dir) = app.path().resource_dir() {
                    #[cfg(target_os = "windows")]
                    let bundled = resource_dir.join("vib-runtime").join("vib.exe");
                    #[cfg(not(target_os = "windows"))]
                    let bundled = resource_dir.join("vib-runtime").join("vib");
                    let _ = vib_path::BUNDLED_VIB_PATH.set(bundled);
                }
            }
            #[cfg(debug_assertions)]
            let _ = &app;

            // 기존 gui_config.json 키를 api_keys.json으로 마이그레이션 (최초 1회)
            migrate_legacy_keys();
            // vib CLI 자동 PATH 설치는 버전당 1회만 수행한다.
            // Why: 매 시작마다 `~/.local/bin/vib` 를 덮어쓰면 `uv tool install`/`pipx` 로
            //      사용자가 직접 관리하던 바이너리가 말없이 교체되는 문제가 있었다.
            if !cli_installed_for_current_version() {
                match vib_path::install_cli_to_path() {
                    Ok(_) => mark_cli_installed_for_current_version(),
                    Err(e) => eprintln!("VibeLign: CLI PATH 설치 실패 — {e}"),
                }
            }
            // 앱 이동/재설치로 래퍼 타겟이 stale 해지는 경우를 매 부팅 시 재검증한다.
            // Why: onedir 래퍼는 번들 vib 의 절대경로를 품고 있어 .app 이 다른 폴더로 옮겨지면
            //      터미널 `vib` 가 "No such file or directory" 로 깨진다.
            #[cfg(not(debug_assertions))]
            if let Some(bundled) = vib_path::find_bundled_vib() {
                if let Err(e) = vib_path::refresh_gui_wrapper(&bundled) {
                    eprintln!("VibeLign: CLI 래퍼 갱신 실패 — {e}");
                }
            }
            // vib 프리워밍: 백그라운드에서 `vib --version` 을 한 번 돌려 PyInstaller onefile
            // 압축 해제와 OS 파일 캐시를 미리 데워둔다. 사용자가 Doctor/DocsViewer 등 첫
            // 서브프로세스 호출을 할 때 체감 콜드스타트가 크게 줄어든다.
            // Why: 릴리스 빌드에서 문서 클릭·Doctor 진입이 dev 모드보다 느렸던 주 원인이
            //      PyInstaller onefile 압축 해제였다.
            if let Some(vib) = vib_path::find_runtime_vib() {
                std::thread::spawn(move || {
                    let mut cmd = std::process::Command::new(&vib);
                    cmd.arg("--version")
                        .stdin(std::process::Stdio::null())
                        .stdout(std::process::Stdio::null())
                        .stderr(std::process::Stdio::null())
                        .env("PATH", augmented_vib_path())
                        .env("PYTHONUTF8", "1")
                        .env("PYTHONIOENCODING", "utf-8");
                    hide_console(&mut cmd);
                    let _ = cmd.status();
                });
            }
            Ok(())
        })
        .manage(WatchState(watch_inner))
        .manage(OnboardingState(onboarding_inner))
        .invoke_handler(tauri::generate_handler![
            get_vib_path,
            setup_cli_path,
            onboarding::get_onboarding_snapshot,
            onboarding::start_native_install,
            onboarding::start_wsl_install,
            onboarding::retry_verification,
            onboarding::add_claude_to_user_path,
            onboarding::uninstall_claude_code,
            onboarding::start_login_probe,
            onboarding::get_onboarding_logs,
            run_vib,
            run_vib_with_progress,
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
            get_watch_logs,
            get_watch_errors,
            open_folder,
            read_file,
            list_docs_index,
            rebuild_docs_index,
            read_docs_visual,
            enhance_doc_with_ai,
            get_env_key_status,
            read_project_summary,
            onboarding::check_git_installed,
            onboarding::check_wsl_available,
            onboarding::check_xcode_clt,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            match event {
                tauri::RunEvent::Exit | tauri::RunEvent::ExitRequested { .. } => {
                    if let Ok(mut guard) = watch_inner_for_exit.lock() {
                        if let Some(mut child) = guard.child.take() {
                            kill_watch_child(&mut child);
                        }
                    }
                }
                _ => {}
            }
        });
}
// === ANCHOR: LIB_END ===
