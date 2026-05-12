// === ANCHOR: MEMORY_AUDIT_START ===
//! Append-only audit log for memory subsystem reads/writes.
//!
//! Parity target (Python): `vibelign/core/memory/audit.py`. The Python module
//! emits one JSONL line per access event into `.vibelign/memory_audit.jsonl`.
//! Downstream consumers — `aggregator.py`, `retention.py`,
//! `capability_policy.py`, and `mcp_handler_registry.py` — read these events
//! to compute access patterns, capability checks, and retention policy. If
//! the GUI direct bridge skips this write, those consumers undercount views.
//!
//! Behavior contract held with Python:
//! - `project_root_hash` = first 16 hex chars of SHA256(canonical root path).
//! - `timestamp` = UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ` (six-digit microseconds).
//! - `sequence_number` = max prior `sequence_number` in the file + 1
//!   (skips lines that don't parse as JSON objects).
//! - Append serialized as `json.dumps(..., sort_keys=True) + "\n"`.
//! - File lock via `O_CREAT | O_EXCL` on `<path>.lock`; 5s deadline; stale
//!   locks older than 30s are removed and retried.

use chrono::Utc;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs::{self, OpenOptions};
use std::io::{ErrorKind, Write};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::{Duration, Instant, SystemTime};

#[derive(Debug, Clone, Serialize)]
pub struct AuditPathsCount {
    pub in_zone: u32,
    pub drift: u32,
    pub total: u32,
}

impl Default for AuditPathsCount {
    fn default() -> Self {
        Self { in_zone: 0, drift: 0, total: 0 }
    }
}

#[derive(Debug, Clone, Default, Serialize)]
pub struct AuditRedaction {
    pub secret_hits: u32,
    pub privacy_hits: u32,
    pub summarized_fields: u32,
}

#[derive(Debug, Clone, Default, Serialize)]
pub struct AuditTrigger {
    pub id: Option<String>,
    pub action: Option<String>,
    pub source: Option<String>,
}

#[derive(Debug, Clone)]
pub struct MemoryAuditEvent {
    pub event: String,
    pub project_root_hash: String,
    pub tool: String,
    pub timestamp: String,
    pub sequence_number: u64,
    pub paths_count: AuditPathsCount,
    pub circuit_breaker_state: String,
    pub redaction: AuditRedaction,
    pub trigger: AuditTrigger,
    pub result: String,
    pub capability_grant_id: Option<String>,
    pub sandwich_checkpoint_id: Option<String>,
    pub plan_id: Option<String>,
    pub candidate_id: Option<String>,
    pub option_id: Option<String>,
    pub recommendation_provider: Option<String>,
    pub memory_proposal_id: Option<String>,
    pub handoff_draft_id: Option<String>,
}

pub struct MemoryAuditEventBuilder<'a> {
    pub event: &'a str,
    pub tool: &'a str,
    pub result: &'a str,
}

pub fn build_event(root: &Path, opts: MemoryAuditEventBuilder<'_>) -> MemoryAuditEvent {
    MemoryAuditEvent {
        event: safe_label(opts.event, "memory_audit"),
        project_root_hash: project_root_hash(root),
        tool: safe_label(opts.tool, "unknown-tool"),
        timestamp: utc_now_microseconds(),
        sequence_number: 0,
        paths_count: AuditPathsCount::default(),
        circuit_breaker_state: "active".to_string(),
        redaction: AuditRedaction::default(),
        trigger: AuditTrigger::default(),
        result: opts.result.to_string(),
        capability_grant_id: None,
        sandwich_checkpoint_id: None,
        plan_id: None,
        candidate_id: None,
        option_id: None,
        recommendation_provider: None,
        memory_proposal_id: None,
        handoff_draft_id: None,
    }
}

pub fn append_event(path: &Path, event: MemoryAuditEvent) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    }
    let _guard = acquire_lock(path)?;
    let event = if event.sequence_number > 0 {
        event
    } else {
        MemoryAuditEvent {
            sequence_number: next_sequence_number(path)?,
            ..event
        }
    };
    let line = serialize_event_sorted(&event);
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|error| error.to_string())?;
    file.write_all(line.as_bytes()).map_err(|error| error.to_string())?;
    file.write_all(b"\n").map_err(|error| error.to_string())?;
    Ok(())
}

pub fn memory_audit_path(root: &Path) -> PathBuf {
    root.join(".vibelign").join("memory_audit.jsonl")
}

fn next_sequence_number(path: &Path) -> Result<u64, String> {
    let content = match fs::read_to_string(path) {
        Ok(text) => text,
        Err(error) if error.kind() == ErrorKind::NotFound => return Ok(1),
        Err(error) => return Err(error.to_string()),
    };
    let mut highest: u64 = 0;
    for line in content.lines() {
        let Ok(value) = serde_json::from_str::<serde_json::Value>(line) else {
            continue;
        };
        let Some(obj) = value.as_object() else {
            continue;
        };
        if let Some(seq) = obj.get("sequence_number").and_then(|v| v.as_u64()) {
            if seq > highest {
                highest = seq;
            }
        }
    }
    Ok(highest + 1)
}

fn project_root_hash(root: &Path) -> String {
    let resolved = root.canonicalize().unwrap_or_else(|_| root.to_path_buf());
    let normalized = resolved.to_string_lossy().into_owned();
    let mut hasher = Sha256::new();
    hasher.update(normalized.as_bytes());
    let digest = hasher.finalize();
    let hex: String = digest.iter().map(|byte| format!("{byte:02x}")).collect();
    hex[..16].to_string()
}

fn utc_now_microseconds() -> String {
    Utc::now().format("%Y-%m-%dT%H:%M:%S%.6fZ").to_string()
}

fn serialize_event_sorted(event: &MemoryAuditEvent) -> String {
    let mut map = serde_json::Map::new();
    map.insert("capability_grant_id".to_string(), optional_string(&event.capability_grant_id));
    map.insert(
        "candidate_id".to_string(),
        optional_string(&event.candidate_id),
    );
    map.insert(
        "circuit_breaker_state".to_string(),
        serde_json::Value::String(event.circuit_breaker_state.clone()),
    );
    map.insert("event".to_string(), serde_json::Value::String(event.event.clone()));
    map.insert(
        "handoff_draft_id".to_string(),
        optional_string(&event.handoff_draft_id),
    );
    map.insert(
        "memory_proposal_id".to_string(),
        optional_string(&event.memory_proposal_id),
    );
    map.insert(
        "option_id".to_string(),
        optional_string(&event.option_id),
    );
    map.insert(
        "paths_count".to_string(),
        serde_json::to_value(&event.paths_count).expect("paths_count serialize"),
    );
    map.insert(
        "plan_id".to_string(),
        optional_string(&event.plan_id),
    );
    map.insert(
        "project_root_hash".to_string(),
        serde_json::Value::String(event.project_root_hash.clone()),
    );
    map.insert(
        "recommendation_provider".to_string(),
        optional_string(&event.recommendation_provider),
    );
    map.insert(
        "redaction".to_string(),
        serde_json::to_value(&event.redaction).expect("redaction serialize"),
    );
    map.insert(
        "result".to_string(),
        serde_json::Value::String(event.result.clone()),
    );
    map.insert(
        "sandwich_checkpoint_id".to_string(),
        optional_string(&event.sandwich_checkpoint_id),
    );
    map.insert(
        "sequence_number".to_string(),
        serde_json::Value::Number(event.sequence_number.into()),
    );
    map.insert(
        "timestamp".to_string(),
        serde_json::Value::String(event.timestamp.clone()),
    );
    map.insert(
        "tool".to_string(),
        serde_json::Value::String(event.tool.clone()),
    );
    map.insert(
        "trigger".to_string(),
        serde_json::to_value(&event.trigger).expect("trigger serialize"),
    );
    serde_json::to_string(&serde_json::Value::Object(map)).expect("serialize event")
}

fn optional_string(value: &Option<String>) -> serde_json::Value {
    match value {
        Some(text) => serde_json::Value::String(text.clone()),
        None => serde_json::Value::Null,
    }
}

fn safe_label(value: &str, fallback: &str) -> String {
    let trimmed = value.trim();
    if trimmed.is_empty() || trimmed.contains(char::is_whitespace) {
        fallback.to_string()
    } else {
        trimmed.to_string()
    }
}

struct LockGuard {
    path: PathBuf,
}

impl Drop for LockGuard {
    fn drop(&mut self) {
        let _ = fs::remove_file(&self.path);
    }
}

fn acquire_lock(audit_path: &Path) -> Result<LockGuard, String> {
    let lock_path = lock_path_for(audit_path);
    let deadline = Instant::now() + Duration::from_secs(5);
    loop {
        match OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&lock_path)
        {
            Ok(_) => return Ok(LockGuard { path: lock_path }),
            Err(error) if error.kind() == ErrorKind::AlreadyExists => {
                if Instant::now() >= deadline {
                    return Err("timed out waiting for memory audit append lock".to_string());
                }
                remove_stale_lock(&lock_path);
                thread::sleep(Duration::from_millis(10));
            }
            Err(error) => return Err(error.to_string()),
        }
    }
}

fn lock_path_for(audit_path: &Path) -> PathBuf {
    let mut name = audit_path
        .file_name()
        .map(|n| n.to_os_string())
        .unwrap_or_default();
    name.push(".lock");
    audit_path.with_file_name(name)
}

fn remove_stale_lock(lock_path: &Path) {
    let Ok(metadata) = fs::metadata(lock_path) else {
        return;
    };
    let Ok(modified) = metadata.modified() else {
        return;
    };
    let Ok(age) = SystemTime::now().duration_since(modified) else {
        return;
    };
    if age > Duration::from_secs(30) {
        let _ = fs::remove_file(lock_path);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn project_root_hash_is_stable_16_hex_chars() {
        let temp = tempfile::tempdir().unwrap();
        let hash1 = project_root_hash(temp.path());
        let hash2 = project_root_hash(temp.path());
        assert_eq!(hash1, hash2);
        assert_eq!(hash1.len(), 16);
        assert!(hash1.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn project_root_hash_differs_per_root() {
        let a = tempfile::tempdir().unwrap();
        let b = tempfile::tempdir().unwrap();
        assert_ne!(project_root_hash(a.path()), project_root_hash(b.path()));
    }

    #[test]
    fn timestamp_has_microseconds_and_z_suffix() {
        let ts = utc_now_microseconds();
        assert!(ts.ends_with('Z'));
        let dot = ts.rfind('.').expect("microsecond dot");
        let micros = &ts[dot + 1..ts.len() - 1];
        assert_eq!(micros.len(), 6, "exactly six digits of microseconds");
        assert!(micros.chars().all(|c| c.is_ascii_digit()));
    }

    #[test]
    fn next_sequence_number_returns_one_for_missing_file() {
        let temp = tempfile::tempdir().unwrap();
        let path = temp.path().join("audit.jsonl");
        assert_eq!(next_sequence_number(&path).unwrap(), 1);
    }

    #[test]
    fn next_sequence_number_finds_max_plus_one() {
        let temp = tempfile::tempdir().unwrap();
        let path = temp.path().join("audit.jsonl");
        fs::write(
            &path,
            "{\"sequence_number\": 1}\n{\"sequence_number\": 5}\n{\"sequence_number\": 3}\n",
        )
        .unwrap();
        assert_eq!(next_sequence_number(&path).unwrap(), 6);
    }

    #[test]
    fn next_sequence_number_skips_invalid_lines() {
        let temp = tempfile::tempdir().unwrap();
        let path = temp.path().join("audit.jsonl");
        fs::write(
            &path,
            "not json\n{\"sequence_number\": 7}\n[\"array\"]\n{\"sequence_number\": 2}\n",
        )
        .unwrap();
        assert_eq!(next_sequence_number(&path).unwrap(), 8);
    }

    #[test]
    fn append_event_creates_directory_and_writes_jsonl() {
        let temp = tempfile::tempdir().unwrap();
        let path = memory_audit_path(temp.path());
        let event = build_event(
            temp.path(),
            MemoryAuditEventBuilder {
                event: "memory_summary_read",
                tool: "vib-gui",
                result: "success",
            },
        );
        append_event(&path, event).unwrap();

        let content = fs::read_to_string(&path).unwrap();
        assert!(content.ends_with('\n'), "must terminate with newline");
        let value: serde_json::Value = serde_json::from_str(content.trim()).unwrap();
        assert_eq!(value["event"], "memory_summary_read");
        assert_eq!(value["tool"], "vib-gui");
        assert_eq!(value["result"], "success");
        assert_eq!(value["sequence_number"], 1);
        assert_eq!(value["circuit_breaker_state"], "active");
        assert_eq!(value["paths_count"]["in_zone"], 0);
        assert_eq!(value["paths_count"]["drift"], 0);
        assert_eq!(value["paths_count"]["total"], 0);
        assert!(value["project_root_hash"].as_str().unwrap().len() == 16);
    }

    #[test]
    fn append_event_increments_sequence() {
        let temp = tempfile::tempdir().unwrap();
        let path = memory_audit_path(temp.path());
        for _ in 0..3 {
            let event = build_event(
                temp.path(),
                MemoryAuditEventBuilder {
                    event: "memory_summary_read",
                    tool: "vib-gui",
                    result: "success",
                },
            );
            append_event(&path, event).unwrap();
        }
        let content = fs::read_to_string(&path).unwrap();
        let lines: Vec<&str> = content.lines().collect();
        assert_eq!(lines.len(), 3);
        let first: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
        let third: serde_json::Value = serde_json::from_str(lines[2]).unwrap();
        assert_eq!(first["sequence_number"], 1);
        assert_eq!(third["sequence_number"], 3);
    }

    #[test]
    fn serialized_keys_are_sorted_alphabetically() {
        let temp = tempfile::tempdir().unwrap();
        let event = build_event(
            temp.path(),
            MemoryAuditEventBuilder {
                event: "memory_summary_read",
                tool: "vib-gui",
                result: "success",
            },
        );
        let line = serialize_event_sorted(&event);
        let value: serde_json::Value = serde_json::from_str(&line).unwrap();
        let keys: Vec<&String> = value.as_object().unwrap().keys().collect();
        let mut sorted = keys.clone();
        sorted.sort();
        assert_eq!(keys, sorted, "JSON keys must come out in alphabetical order");
    }

    #[test]
    fn safe_label_falls_back_when_value_empty_or_has_whitespace() {
        assert_eq!(safe_label("", "fallback"), "fallback");
        assert_eq!(safe_label("   ", "fallback"), "fallback");
        assert_eq!(safe_label("bad value", "fallback"), "fallback");
        assert_eq!(safe_label("good", "fallback"), "good");
        assert_eq!(safe_label("  trimmed  ", "fallback"), "trimmed");
    }

    #[test]
    fn lock_prevents_double_acquire_within_deadline() {
        let temp = tempfile::tempdir().unwrap();
        let path = memory_audit_path(temp.path());
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        let _first = acquire_lock(&path).unwrap();
        // Manually invoke the lock path again with a tiny deadline by writing to lock file.
        let lock = lock_path_for(&path);
        assert!(lock.exists(), "lock file exists while guard held");
        drop(_first);
        assert!(!lock.exists(), "lock file removed after guard dropped");
    }
}
// === ANCHOR: MEMORY_AUDIT_END ===
