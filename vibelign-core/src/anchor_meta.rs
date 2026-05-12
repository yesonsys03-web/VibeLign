// === ANCHOR: ANCHOR_META_START ===
//! Read + normalize + persist `.vibelign/anchor_meta.json` for the GUI direct bridge.
//!
//! Parity targets (Python):
//! - `vibelign/core/anchor_tools.py::load_anchor_meta` — read + normalize.
//! - `vibelign/core/anchor_tools.py::save_anchor_meta` — pretty JSON
//!   (`indent=2`, no ASCII escaping) + trailing newline.
//! - `vibelign/core/anchor_tools.py::set_anchor_intent` — load → merge fields
//!   (only when the caller supplied them) → force `_source = "manual"` → save.

use serde_json::{Map, Value};
use std::path::Path;

pub fn list_anchor_meta(root: &Path) -> Map<String, Value> {
    let path = root.join(".vibelign").join("anchor_meta.json");
    let Ok(content) = std::fs::read_to_string(&path) else {
        return Map::new();
    };
    let Ok(Value::Object(raw)) = serde_json::from_str::<Value>(&content) else {
        return Map::new();
    };
    let mut normalized = Map::new();
    for (key, value) in raw {
        if let Value::Object(entry) = value {
            normalized.insert(key, Value::Object(normalize_entry(&entry)));
        }
    }
    normalized
}

fn normalize_entry(entry: &Map<String, Value>) -> Map<String, Value> {
    let mut out = Map::new();
    copy_string(entry, "intent", &mut out);
    if let Some(items) = filter_string_list(entry.get("connects")) {
        if !items.is_empty() {
            out.insert("connects".to_string(), Value::Array(items));
        }
    }
    copy_string(entry, "warning", &mut out);
    if let Some(items) = filter_string_list(entry.get("aliases")) {
        if !items.is_empty() {
            out.insert("aliases".to_string(), Value::Array(items));
        }
    }
    copy_string(entry, "description", &mut out);
    copy_string(entry, "_source", &mut out);
    copy_string(entry, "_content_hash", &mut out);
    out
}

fn copy_string(src: &Map<String, Value>, key: &str, dst: &mut Map<String, Value>) {
    if let Some(Value::String(value)) = src.get(key) {
        dst.insert(key.to_string(), Value::String(value.clone()));
    }
}

fn filter_string_list(value: Option<&Value>) -> Option<Vec<Value>> {
    let arr = value?.as_array()?;
    Some(
        arr.iter()
            .filter_map(|item| item.as_str().map(|text| Value::String(text.to_string())))
            .collect(),
    )
}

pub fn set_anchor_intent(
    root: &Path,
    anchor_name: &str,
    intent: &str,
    connects: Option<&[String]>,
    warning: Option<&str>,
    aliases: Option<&[String]>,
    description: Option<&str>,
) -> Result<Map<String, Value>, String> {
    let mut data = list_anchor_meta(root);
    let existing = data
        .get(anchor_name)
        .and_then(|value| value.as_object())
        .cloned()
        .unwrap_or_default();

    let mut entry = Map::new();
    entry.insert("intent".to_string(), Value::String(intent.to_string()));
    insert_or_carry(&mut entry, &existing, "connects", connects.map(string_list_to_value));
    insert_or_carry(
        &mut entry,
        &existing,
        "warning",
        warning.map(|text| Value::String(text.to_string())),
    );
    insert_or_carry(&mut entry, &existing, "aliases", aliases.map(string_list_to_value));
    insert_or_carry(
        &mut entry,
        &existing,
        "description",
        description.map(|text| Value::String(text.to_string())),
    );
    entry.insert("_source".to_string(), Value::String("manual".to_string()));
    if let Some(value) = existing.get("_content_hash") {
        entry.insert("_content_hash".to_string(), value.clone());
    }

    data.insert(anchor_name.to_string(), Value::Object(entry.clone()));
    save_anchor_meta(root, &data)?;
    Ok(entry)
}

fn insert_or_carry(
    dst: &mut Map<String, Value>,
    existing: &Map<String, Value>,
    key: &str,
    provided: Option<Value>,
) {
    if let Some(value) = provided {
        dst.insert(key.to_string(), value);
    } else if let Some(value) = existing.get(key) {
        dst.insert(key.to_string(), value.clone());
    }
}

fn string_list_to_value(items: &[String]) -> Value {
    Value::Array(items.iter().map(|text| Value::String(text.clone())).collect())
}

fn save_anchor_meta(root: &Path, data: &Map<String, Value>) -> Result<(), String> {
    let dir = root.join(".vibelign");
    std::fs::create_dir_all(&dir).map_err(|error| error.to_string())?;
    let path = dir.join("anchor_meta.json");
    let json = serde_json::to_string_pretty(&Value::Object(data.clone()))
        .map_err(|error| error.to_string())?;
    std::fs::write(&path, json + "\n").map_err(|error| error.to_string())?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::list_anchor_meta;
    use serde_json::json;

    #[test]
    fn returns_empty_when_file_missing() {
        let temp = tempfile::tempdir().unwrap();
        assert!(list_anchor_meta(temp.path()).is_empty());
    }

    #[test]
    fn returns_empty_when_json_invalid() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("anchor_meta.json"), "not json").unwrap();
        assert!(list_anchor_meta(temp.path()).is_empty());
    }

    #[test]
    fn returns_empty_when_root_not_object() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("anchor_meta.json"), "[1, 2, 3]").unwrap();
        assert!(list_anchor_meta(temp.path()).is_empty());
    }

    #[test]
    fn normalizes_known_fields_and_drops_unknown() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let raw = json!({
            "FOO_START": {
                "intent": "do X",
                "connects": ["A", "B", 42, "C"],
                "warning": "be careful",
                "aliases": ["alt1", "alt2"],
                "description": "what this anchor covers",
                "_source": "auto",
                "_content_hash": "abc123",
                "unknown_field": "drop me",
                "extra_count": 99
            }
        });
        std::fs::write(dir.join("anchor_meta.json"), raw.to_string()).unwrap();

        let result = list_anchor_meta(temp.path());
        let entry = result.get("FOO_START").unwrap().as_object().unwrap();
        assert_eq!(entry.get("intent").unwrap(), "do X");
        assert_eq!(
            entry.get("connects").unwrap(),
            &json!(["A", "B", "C"]),
            "connects must keep only strings",
        );
        assert_eq!(entry.get("warning").unwrap(), "be careful");
        assert_eq!(entry.get("aliases").unwrap(), &json!(["alt1", "alt2"]));
        assert_eq!(entry.get("description").unwrap(), "what this anchor covers");
        assert_eq!(entry.get("_source").unwrap(), "auto");
        assert_eq!(entry.get("_content_hash").unwrap(), "abc123");
        assert!(entry.get("unknown_field").is_none());
        assert!(entry.get("extra_count").is_none());
    }

    #[test]
    fn drops_empty_connects_and_aliases() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let raw = json!({
            "BAR_START": {
                "intent": "only intent",
                "connects": [],
                "aliases": [42, 99]
            }
        });
        std::fs::write(dir.join("anchor_meta.json"), raw.to_string()).unwrap();

        let result = list_anchor_meta(temp.path());
        let entry = result.get("BAR_START").unwrap().as_object().unwrap();
        assert_eq!(entry.get("intent").unwrap(), "only intent");
        assert!(entry.get("connects").is_none(), "empty connects must be dropped");
        assert!(
            entry.get("aliases").is_none(),
            "aliases with no string items must be dropped",
        );
    }

    #[test]
    fn skips_non_object_entries() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let raw = json!({
            "OK_START": {"intent": "kept"},
            "BAD_START": "not an object",
            "ALSO_BAD_START": [1, 2, 3]
        });
        std::fs::write(dir.join("anchor_meta.json"), raw.to_string()).unwrap();

        let result = list_anchor_meta(temp.path());
        assert!(result.contains_key("OK_START"));
        assert!(!result.contains_key("BAD_START"));
        assert!(!result.contains_key("ALSO_BAD_START"));
    }

    #[test]
    fn set_anchor_intent_creates_entry_on_empty_file() {
        let temp = tempfile::tempdir().unwrap();
        let entry = super::set_anchor_intent(
            temp.path(),
            "NEW_START",
            "do thing",
            None,
            None,
            None,
            None,
        )
        .unwrap();
        assert_eq!(entry.get("intent").unwrap(), "do thing");
        assert_eq!(entry.get("_source").unwrap(), "manual");
        assert!(entry.get("connects").is_none());

        let reloaded = list_anchor_meta(temp.path());
        let stored = reloaded.get("NEW_START").unwrap().as_object().unwrap();
        assert_eq!(stored.get("intent").unwrap(), "do thing");
        assert_eq!(stored.get("_source").unwrap(), "manual");
    }

    #[test]
    fn set_anchor_intent_overrides_only_provided_fields() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let initial = json!({
            "EXISTING_START": {
                "intent": "old intent",
                "connects": ["a", "b"],
                "warning": "old warning",
                "description": "old desc",
                "_source": "auto",
                "_content_hash": "hash1"
            }
        });
        std::fs::write(dir.join("anchor_meta.json"), initial.to_string()).unwrap();

        let entry = super::set_anchor_intent(
            temp.path(),
            "EXISTING_START",
            "new intent",
            None,
            Some("new warning"),
            None,
            None,
        )
        .unwrap();
        assert_eq!(entry.get("intent").unwrap(), "new intent");
        assert_eq!(entry.get("connects").unwrap(), &json!(["a", "b"]));
        assert_eq!(entry.get("warning").unwrap(), "new warning");
        assert_eq!(entry.get("description").unwrap(), "old desc");
        assert_eq!(entry.get("_source").unwrap(), "manual");
        assert_eq!(entry.get("_content_hash").unwrap(), "hash1");
    }

    #[test]
    fn set_anchor_intent_overrides_with_provided_list() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("anchor_meta.json"),
            json!({
                "FOO_START": {"intent": "i", "connects": ["old1", "old2"]}
            })
            .to_string(),
        )
        .unwrap();
        let new_connects = vec!["new1".to_string(), "new2".to_string(), "new3".to_string()];
        let entry = super::set_anchor_intent(
            temp.path(),
            "FOO_START",
            "i",
            Some(&new_connects),
            None,
            None,
            None,
        )
        .unwrap();
        assert_eq!(entry.get("connects").unwrap(), &json!(["new1", "new2", "new3"]));
    }

    #[test]
    fn set_anchor_intent_preserves_other_anchors() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("anchor_meta.json"),
            json!({
                "OTHER_START": {"intent": "untouched", "_source": "manual"},
                "TARGET_START": {"intent": "old"}
            })
            .to_string(),
        )
        .unwrap();
        super::set_anchor_intent(temp.path(), "TARGET_START", "new", None, None, None, None).unwrap();

        let reloaded = list_anchor_meta(temp.path());
        assert_eq!(
            reloaded.get("OTHER_START").unwrap().get("intent").unwrap(),
            "untouched",
        );
        assert_eq!(reloaded.get("TARGET_START").unwrap().get("intent").unwrap(), "new");
    }

    #[test]
    fn set_anchor_intent_writes_pretty_with_trailing_newline() {
        let temp = tempfile::tempdir().unwrap();
        super::set_anchor_intent(temp.path(), "X_START", "y", None, None, None, None).unwrap();
        let written =
            std::fs::read_to_string(temp.path().join(".vibelign/anchor_meta.json")).unwrap();
        assert!(written.starts_with("{\n  \"X_START\""));
        assert!(written.ends_with("}\n"));
    }

    #[test]
    fn drops_typed_fields_when_type_mismatches() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let raw = json!({
            "TYPED_START": {
                "intent": 42,
                "warning": ["not", "a", "string"],
                "description": null
            }
        });
        std::fs::write(dir.join("anchor_meta.json"), raw.to_string()).unwrap();

        let result = list_anchor_meta(temp.path());
        let entry = result.get("TYPED_START").unwrap().as_object().unwrap();
        assert!(entry.is_empty());
    }
}
// === ANCHOR: ANCHOR_META_END ===
