// === ANCHOR: ERROR_LOGS_START ===
//! GUI 에서 통합 에러 로그를 보여주기 위한 read-only Tauri command.
//!
//! `.vibelign/logs/cli-error-*.jsonl` 과 `gui-error-*.jsonl` 을 모두 읽어
//! ts 내림차순으로 정렬한 뒤 limit 개수만 돌려준다. 사용자는 GUI 에서 자동
//! 백업 실패(post-commit hook), CLI 크래시, GUI 컴포넌트 에러를 한 화면에서
//! 본다. 로그 파일은 이미 redaction + retention 적용된 상태라 추가 처리 없음.

use std::path::PathBuf;

use serde::Serialize;

use super::platform::strip_unc_prefix;

#[derive(Serialize)]
pub(crate) struct ErrorLogEntry {
    ts: String,
    kind: String,
    error_class: Option<String>,
    message: String,
    context: Option<String>,
    raw_json: String,
}

const DEFAULT_LIMIT: usize = 200;
const MAX_LIMIT: usize = 2000;

#[tauri::command]
pub(crate) async fn read_error_logs(root: String, limit: Option<usize>) -> Vec<ErrorLogEntry> {
    let limit = limit.unwrap_or(DEFAULT_LIMIT).min(MAX_LIMIT).max(1);
    let root_path = PathBuf::from(&root);
    let canonical = match root_path.canonicalize() {
        Ok(path) => strip_unc_prefix(path),
        Err(_) => root_path,
    };
    tauri::async_runtime::spawn_blocking(move || collect_entries(&canonical, limit))
        .await
        .unwrap_or_default()
}

fn collect_entries(root: &std::path::Path, limit: usize) -> Vec<ErrorLogEntry> {
    let logs_dir = root.join(".vibelign").join("logs");
    let Ok(read_dir) = std::fs::read_dir(&logs_dir) else {
        return Vec::new();
    };

    let mut entries: Vec<ErrorLogEntry> = Vec::new();
    for dir_entry in read_dir.flatten() {
        let path = dir_entry.path();
        let file_name = match path.file_name().and_then(|name| name.to_str()) {
            Some(name) => name,
            None => continue,
        };
        let kind = if file_name.starts_with("cli-error-") {
            "cli"
        } else if file_name.starts_with("gui-error-") {
            "gui"
        } else {
            continue;
        };
        if !file_name.ends_with(".jsonl") {
            continue;
        }
        let Ok(text) = std::fs::read_to_string(&path) else {
            continue;
        };
        for line in text.lines() {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }
            if let Some(entry) = parse_line(trimmed, kind) {
                entries.push(entry);
            }
        }
    }
    entries.sort_by(|left, right| right.ts.cmp(&left.ts));
    entries.truncate(limit);
    entries
}

#[derive(Serialize)]
pub(crate) struct ClearErrorLogsResult {
    pub(crate) removed: usize,
    pub(crate) kept: usize,
}

/// `.vibelign/logs/{cli,gui}-error-*.jsonl` 만 삭제. `.lock` 파일이나 다른
/// 디렉토리는 건드리지 않는다. 수정 완료된 에러를 정리해 새로 발생하는 항목이
/// 눈에 띄게 하는 게 목적.
#[tauri::command]
pub(crate) async fn clear_error_logs(root: String) -> ClearErrorLogsResult {
    let root_path = PathBuf::from(&root);
    let canonical = match root_path.canonicalize() {
        Ok(path) => strip_unc_prefix(path),
        Err(_) => root_path,
    };
    tauri::async_runtime::spawn_blocking(move || sweep_error_logs(&canonical))
        .await
        .unwrap_or(ClearErrorLogsResult { removed: 0, kept: 0 })
}

fn sweep_error_logs(root: &std::path::Path) -> ClearErrorLogsResult {
    let logs_dir = root.join(".vibelign").join("logs");
    let Ok(read_dir) = std::fs::read_dir(&logs_dir) else {
        return ClearErrorLogsResult { removed: 0, kept: 0 };
    };
    let mut removed = 0_usize;
    let mut kept = 0_usize;
    for dir_entry in read_dir.flatten() {
        let path = dir_entry.path();
        let Some(file_name) = path.file_name().and_then(|name| name.to_str()) else {
            continue;
        };
        let is_target = (file_name.starts_with("cli-error-") || file_name.starts_with("gui-error-"))
            && file_name.ends_with(".jsonl");
        if !is_target {
            continue;
        }
        match std::fs::remove_file(&path) {
            Ok(()) => removed += 1,
            Err(_) => kept += 1,
        }
    }
    ClearErrorLogsResult { removed, kept }
}

fn parse_line(line: &str, kind: &str) -> Option<ErrorLogEntry> {
    let value: serde_json::Value = serde_json::from_str(line).ok()?;
    let ts = value.get("ts").and_then(|v| v.as_str()).unwrap_or("").to_string();
    let error_class = value
        .get("error_class")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let message = value
        .get("message_redacted")
        .or_else(|| value.get("error_message"))
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();
    let context = value
        .get("source")
        .or_else(|| value.get("command"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    Some(ErrorLogEntry {
        ts,
        kind: kind.to_string(),
        error_class,
        message,
        context,
        raw_json: line.to_string(),
    })
}
// === ANCHOR: ERROR_LOGS_END ===
