// === ANCHOR: DOCS_START ===
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::{docs_access, vib_path};

use super::platform::{augmented_vib_path, hide_console, strip_unc_prefix};
use super::settings::read_keys_file;

#[derive(Serialize)]
pub(crate) struct ReadFileResult {
    path: String,
    content: String,
    source_hash: String,
}

#[derive(Serialize, Deserialize)]
pub(crate) struct DocsIndexEntry {
    category: String,
    path: String,
    title: String,
    modified_at_ms: i64,
    #[serde(default)]
    source_root: Option<String>,
}

const DOCS_INDEX_CACHE_SCHEMA_VERSION: i64 = 3;

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
pub(crate) struct DocsVisualContract {
    schema_version: i64,
    generator_version: String,
}

// contract 는 vib 바이너리에 baked-in 된 정적 값이라 프로세스 수명 내에서 바뀌지 않는다.
// 매 문서 클릭마다 vib subprocess 를 스폰하던 병목을 없애기 위해 첫 호출 결과를 메모리에 캐시한다.
static DOCS_VISUAL_CONTRACT_CACHE: Mutex<Option<DocsVisualContract>> = Mutex::new(None);
static DOCS_HTML_CONTRACT_CACHE: Mutex<Option<DocsVisualContract>> = Mutex::new(None);

#[derive(Serialize)]
pub(crate) struct DocsVisualReadResult {
    path: String,
    artifact: serde_json::Value,
    contract: DocsVisualContract,
}

#[derive(Serialize)]
pub(crate) struct DocsHtmlReadResult {
    path: String,
    artifact: serde_json::Value,
    contract: DocsVisualContract,
}

fn normalize_text_document(bytes: &[u8]) -> Result<String, String> {
    let bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(bytes);
    let text = std::str::from_utf8(bytes)
        .map_err(|_| "UTF-8 텍스트 문서만 읽을 수 있어요".to_string())?;
    Ok(text.replace("\r\n", "\n").replace('\r', "\n"))
}

fn printable_document_runs(bytes: &[u8]) -> String {
    let mut runs: Vec<String> = Vec::new();
    let mut current: Vec<u8> = Vec::new();
    for byte in bytes {
        let printable = matches!(*byte, b'\t' | b'\n' | b'\r' | b' '..=b'~');
        if printable {
            current.push(*byte);
        } else {
            if current.len() >= 4 {
                runs.push(String::from_utf8_lossy(&current).trim().to_string());
            }
            current.clear();
        }
    }
    if current.len() >= 4 {
        runs.push(String::from_utf8_lossy(&current).trim().to_string());
    }
    runs.retain(|item| !item.is_empty());
    runs.truncate(400);
    if runs.is_empty() {
        String::new()
    } else {
        format!("{}\n", runs.join("\n"))
    }
}

fn normalize_document_content(path: &Path, bytes: &[u8]) -> Result<String, String> {
    let ext = path
        .extension()
        .and_then(|value| value.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    match ext.as_str() {
        "md" | "markdown" | "txt" | "csv" => normalize_text_document(bytes),
        "json" => {
            let text = normalize_text_document(bytes)?;
            match serde_json::from_str::<serde_json::Value>(&text) {
                Ok(value) => serde_json::to_string_pretty(&value)
                    .map(|pretty| format!("{pretty}\n"))
                    .map_err(|e| format!("JSON 문서를 정리할 수 없어요: {e}")),
                Err(_) => Ok(text),
            }
        }
        "pdf" | "docx" | "doc" => {
            let text = printable_document_runs(bytes);
            if text.is_empty() {
                Err(format!("{} 문서에서 표시할 텍스트를 추출할 수 없어요", ext.to_uppercase()))
            } else {
                Ok(text)
            }
        }
        _ => Err("지원하지 않는 문서 형식입니다".into()),
    }
}

fn hash_document_content(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn normalize_relative_doc_path(path: &std::path::Path) -> String {
    path.to_string_lossy().replace('\\', "/")
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
    let extras = docs_access::ExtraSourceAllowlist::load(&root_path);
    if !docs_access::is_allowed_doc_path(&relative_path, &extras) {
        return Err("허용된 문서 형식만 읽을 수 있어요".into());
    }
    Ok((canonical, relative_path))
}

#[tauri::command]
pub(crate) fn read_file(root: String, path: PathBuf) -> Result<ReadFileResult, String> {
    let (resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    let bytes = std::fs::read(&resolved_path).map_err(|e| format!("문서를 읽을 수 없어요: {e}"))?;
    let content = normalize_document_content(&resolved_path, &bytes)?;
    Ok(ReadFileResult {
        path: relative_path,
        source_hash: hash_document_content(&content),
        content,
    })
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
    } else if extra_args.iter().any(|arg| *arg == "--print-html-contract") {
        command.arg("--html-contract");
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
        Err(err) => Some(Err(format!(
            "[vib docs-index] 실행 실패: {err}\n  vib={vib:?}\n  cwd={root:?}\n  os_error={os:?}",
            os = err.raw_os_error()
        ))),
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
pub(crate) fn list_docs_index(root: String) -> Result<Vec<DocsIndexEntry>, String> {
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
pub(crate) fn rebuild_docs_index(root: String) -> Result<Vec<DocsIndexEntry>, String> {
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

fn read_docs_html_contract(root: &str) -> Result<DocsVisualContract, String> {
    if let Ok(guard) = DOCS_HTML_CONTRACT_CACHE.lock() {
        if let Some(cached) = guard.as_ref() {
            return Ok(cached.clone());
        }
    }

    let raw = run_docs_cache_helper(root, &["--print-html-contract"])?;
    let payload: serde_json::Value = serde_json::from_str(raw.trim())
        .map_err(|e| format!("docs HTML contract를 해석할 수 없어요: {e}"))?;
    let contract_value = payload
        .get("contract")
        .ok_or_else(|| "docs HTML contract 항목이 없어요".to_string())?
        .clone();
    let contract: DocsVisualContract = serde_json::from_value(contract_value)
        .map_err(|e| format!("docs HTML contract 형식이 올바르지 않아요: {e}"))?;

    if let Ok(mut guard) = DOCS_HTML_CONTRACT_CACHE.lock() {
        *guard = Some(contract.clone());
    }
    Ok(contract)
}

fn docs_artifact_path(root_path: &Path, relative_path: &str, dir_name: &str) -> PathBuf {
    let is_extra = read_docs_index_cache_file(root_path)
        .and_then(|entries| {
            entries
                .into_iter()
                .find(|entry| entry.path == relative_path)
                .map(|entry| entry.source_root.is_some())
        })
        .unwrap_or_else(|| {
            let extras = docs_access::ExtraSourceAllowlist::load(root_path);
            extras.roots().iter().any(|prefix| {
                relative_path == *prefix
                    || relative_path.starts_with(&format!("{prefix}/"))
            })
        });
    if is_extra {
        root_path
            .join(".vibelign")
            .join(dir_name)
            .join("_extra")
            .join(format!("{}.json", relative_path))
    } else {
        root_path
            .join(".vibelign")
            .join(dir_name)
            .join(format!("{}.json", relative_path))
    }
}

#[tauri::command]
pub(crate) fn read_docs_visual(root: String, path: PathBuf) -> Result<Option<DocsVisualReadResult>, String> {
    let (_resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    if !docs_access::is_canvas_eligible_path(&relative_path) {
        return Err(format!("Canvas visualization is unsupported for excluded docs path: {relative_path}"));
    }
    let root_path = strip_unc_prefix(
        PathBuf::from(&root)
            .canonicalize()
            .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?,
    );
    // Route extra source docs to `_extra/<rel>.json` to avoid hidden-dir nesting.
    let artifact_path = docs_artifact_path(&root_path, &relative_path, "docs_visual");

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
pub(crate) fn read_docs_html(root: String, path: PathBuf) -> Result<Option<DocsHtmlReadResult>, String> {
    let (_resolved_path, relative_path) = resolve_doc_path(&root, path)?;
    if !docs_access::is_canvas_eligible_path(&relative_path) {
        return Err(format!("Raw HTML Canvas is unsupported for excluded docs path: {relative_path}"));
    }
    let root_path = strip_unc_prefix(
        PathBuf::from(&root)
            .canonicalize()
            .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?,
    );
    let artifact_path = docs_artifact_path(&root_path, &relative_path, "docs_html");

    if !artifact_path.exists() {
        return Ok(None);
    }

    let artifact_text = std::fs::read_to_string(&artifact_path)
        .map_err(|e| format!("docs HTML artifact를 읽을 수 없어요: {e}"))?;
    let artifact: serde_json::Value = serde_json::from_str(&artifact_text)
        .map_err(|e| format!("docs HTML artifact JSON이 손상되었어요: {e}"))?;
    let contract = read_docs_html_contract(&root)?;

    Ok(Some(DocsHtmlReadResult {
        path: relative_path,
        artifact,
        contract,
    }))
}

// ─── 추가 문서 소스 관리 ────────────────────────────────────────────────────────

#[derive(Serialize, Deserialize)]
pub(crate) struct DocSourcesResponse {
    ok: bool,
    sources: Vec<String>,
    entries: Vec<DocsIndexEntry>,
    warnings: Vec<String>,
}

fn run_doc_sources_cmd(root: &str, args: &[&str]) -> Result<DocSourcesResponse, String> {
    let root_path = strip_unc_prefix(
        PathBuf::from(root)
            .canonicalize()
            .map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?,
    );
    let vib = vib_path::find_runtime_vib()
        .ok_or_else(|| "vib을 찾을 수 없어요. GUI를 재설치해 주세요.".to_string())?;
    let mut command = std::process::Command::new(&vib);
    command.arg("doc-sources");
    for arg in args {
        command.arg(arg);
    }
    command
        .current_dir(&root_path)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .env("PATH", augmented_vib_path())
        .env("VIBELIGN_PROJECT_ROOT", root_path.as_os_str())
        .env("PYTHONUTF8", "1")
        .env("PYTHONIOENCODING", "utf-8");

    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let output = command.output().map_err(|e| {
        format!(
            "vib doc-sources 실행 실패: {e}\n  vib={vib:?}\n  os_error={os:?}",
            os = e.raw_os_error()
        )
    })?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let raw = stdout.trim();

    if raw.is_empty() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
        return Err(format!("[vib doc-sources] 출력이 없어요: {stderr}"));
    }

    // Parse outer JSON — could be ok=true or ok=false
    let value: serde_json::Value = serde_json::from_str(raw)
        .map_err(|e| format!("[vib doc-sources] JSON 파싱 실패: {e}\n출력: {raw}"))?;

    if value.get("ok").and_then(|v| v.as_bool()) == Some(false) {
        let err = value.get("error")
            .and_then(|v| v.as_str())
            .unwrap_or("알 수 없는 오류")
            .to_string();
        return Err(err);
    }

    serde_json::from_value(value)
        .map_err(|e| format!("[vib doc-sources] 응답 역직렬화 실패: {e}"))
}

#[tauri::command]
pub(crate) fn list_extra_doc_sources(root: String) -> Result<DocSourcesResponse, String> {
    run_doc_sources_cmd(&root, &["list"])
}

#[tauri::command]
pub(crate) fn add_extra_doc_source(root: String, path: String) -> Result<DocSourcesResponse, String> {
    run_doc_sources_cmd(&root, &["add", &path])
}

#[tauri::command]
pub(crate) fn remove_extra_doc_source(root: String, path: String) -> Result<DocSourcesResponse, String> {
    run_doc_sources_cmd(&root, &["remove", &path])
}

#[tauri::command]
pub(crate) async fn enhance_doc_with_ai(
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
// === ANCHOR: DOCS_END ===
