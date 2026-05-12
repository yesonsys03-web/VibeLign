// === ANCHOR: MEMORY_STATE_START ===
//! Read `.vibelign/work_memory.json` and emit the same payload shape as
//! Python `vib memory show --json`. The TS consumer
//! (`vibelign-gui/src/lib/vib/memory.ts::parseMemorySummaryJson`) reads:
//! `schema_version`, `active_intent.text`, `next_action.text`,
//! `decisions[].text`, `relevant_files[].{path,why,source}`,
//! `verification[].{command,stale}`, `risks[].text`, `downgrade_warning`.
//!
//! Strategy: load raw JSON, ensure the top-level keys exist (with array /
//! null defaults), pass everything else through unchanged. Python's
//! `_memory_state_payload` is itself a near-passthrough that fills defaults
//! for legacy entries — replicating that contract here avoids modeling all
//! the nested dataclasses on the Rust side and keeps the contract anchored
//! to the JSON file, which is the source of truth.

use serde_json::{Map, Value};
use std::path::Path;

const SUPPORTED_SCHEMA_VERSION: u64 = 1;

pub fn load_payload(root: &Path) -> Result<Value, String> {
    let path = root.join(".vibelign").join("work_memory.json");
    let content = match std::fs::read_to_string(&path) {
        Ok(text) => text,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(Value::Object(default_payload()));
        }
        Err(error) => return Err(error.to_string()),
    };
    let raw: Value =
        serde_json::from_str(&content).map_err(|error| format!("work_memory.json parse: {error}"))?;
    let Value::Object(obj) = raw else {
        return Ok(Value::Object(default_payload()));
    };
    Ok(Value::Object(normalize(obj)))
}

fn default_payload() -> Map<String, Value> {
    let mut out = Map::new();
    out.insert("schema_version".to_string(), Value::Number(SUPPORTED_SCHEMA_VERSION.into()));
    out.insert("active_intent".to_string(), Value::Null);
    out.insert("next_action".to_string(), Value::Null);
    out.insert("decisions".to_string(), Value::Array(vec![]));
    out.insert("relevant_files".to_string(), Value::Array(vec![]));
    out.insert("verification".to_string(), Value::Array(vec![]));
    out.insert("risks".to_string(), Value::Array(vec![]));
    out.insert("observed_context".to_string(), Value::Array(vec![]));
    out.insert("archived_decisions".to_string(), Value::Array(vec![]));
    out.insert("downgrade_warning".to_string(), Value::String(String::new()));
    out
}

fn normalize(mut obj: Map<String, Value>) -> Map<String, Value> {
    obj.entry("schema_version")
        .or_insert(Value::Number(SUPPORTED_SCHEMA_VERSION.into()));
    obj.entry("active_intent").or_insert(Value::Null);
    obj.entry("next_action").or_insert(Value::Null);
    for key in ["decisions", "relevant_files", "verification", "risks", "observed_context", "archived_decisions"] {
        obj.entry(key.to_string()).or_insert(Value::Array(vec![]));
    }
    obj.entry("downgrade_warning").or_insert(Value::String(String::new()));

    let stored_version = obj
        .get("schema_version")
        .and_then(|v| v.as_u64())
        .unwrap_or(SUPPORTED_SCHEMA_VERSION);
    if stored_version > SUPPORTED_SCHEMA_VERSION {
        let existing = obj
            .get("downgrade_warning")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        if existing.is_empty() {
            obj.insert(
                "downgrade_warning".to_string(),
                Value::String(format!(
                    "work_memory.json schema_version={stored_version} is newer than this engine supports (max {SUPPORTED_SCHEMA_VERSION})"
                )),
            );
        }
    }
    obj
}

#[cfg(test)]
mod tests {
    use super::load_payload;
    use serde_json::json;

    #[test]
    fn returns_defaults_when_file_missing() {
        let temp = tempfile::tempdir().unwrap();
        let payload = load_payload(temp.path()).unwrap();
        let obj = payload.as_object().unwrap();
        assert_eq!(obj.get("schema_version").unwrap(), 1);
        assert!(obj.get("active_intent").unwrap().is_null());
        assert!(obj.get("decisions").unwrap().as_array().unwrap().is_empty());
        assert_eq!(obj.get("downgrade_warning").unwrap(), "");
    }

    #[test]
    fn passes_through_existing_fields() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let raw = json!({
            "schema_version": 1,
            "active_intent": {"text": "do thing"},
            "decisions": [{"text": "decided X"}],
            "relevant_files": [{"path": "a/b.rs", "why": "test", "source": "system"}],
            "verification": [{"command": "cargo test", "stale": false}],
            "risks": [{"text": "rebuild needed"}],
        });
        std::fs::write(dir.join("work_memory.json"), raw.to_string()).unwrap();

        let payload = load_payload(temp.path()).unwrap();
        let obj = payload.as_object().unwrap();
        assert_eq!(obj.get("active_intent").unwrap().get("text").unwrap(), "do thing");
        assert_eq!(obj.get("decisions").unwrap().as_array().unwrap().len(), 1);
        assert_eq!(obj.get("relevant_files").unwrap().as_array().unwrap().len(), 1);
        assert_eq!(obj.get("verification").unwrap().as_array().unwrap().len(), 1);
    }

    #[test]
    fn fills_missing_arrays_with_empty() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("work_memory.json"), r#"{"schema_version": 1}"#).unwrap();
        let obj = load_payload(temp.path()).unwrap();
        let obj = obj.as_object().unwrap();
        for key in ["decisions", "relevant_files", "verification", "risks", "observed_context", "archived_decisions"] {
            assert!(
                obj.get(key).unwrap().as_array().is_some(),
                "{key} must be filled with empty array",
            );
        }
        assert!(obj.get("active_intent").unwrap().is_null());
        assert!(obj.get("next_action").unwrap().is_null());
    }

    #[test]
    fn returns_defaults_when_file_not_object() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("work_memory.json"), "[1, 2, 3]").unwrap();
        let obj = load_payload(temp.path()).unwrap();
        assert!(obj.as_object().unwrap().get("active_intent").unwrap().is_null());
    }

    #[test]
    fn errors_on_invalid_json() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("work_memory.json"), "not json").unwrap();
        let result = load_payload(temp.path());
        assert!(result.is_err(), "parse error must surface");
    }

    #[test]
    fn sets_downgrade_warning_when_schema_version_too_new() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("work_memory.json"), r#"{"schema_version": 99}"#).unwrap();
        let obj = load_payload(temp.path()).unwrap();
        let warning = obj
            .as_object()
            .unwrap()
            .get("downgrade_warning")
            .and_then(|v| v.as_str())
            .unwrap();
        assert!(warning.contains("99"));
        assert!(warning.contains("newer"));
    }

    #[test]
    fn preserves_explicit_downgrade_warning() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("work_memory.json"),
            r#"{"schema_version": 99, "downgrade_warning": "explicit reason"}"#,
        )
        .unwrap();
        let obj = load_payload(temp.path()).unwrap();
        assert_eq!(
            obj.as_object().unwrap().get("downgrade_warning").unwrap(),
            "explicit reason",
        );
    }
}
// === ANCHOR: MEMORY_STATE_END ===
