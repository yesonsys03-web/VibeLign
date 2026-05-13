// === ANCHOR: WIRE_SMOKE_PHASE3_START ===
//! End-to-end JSON wire smoke for Phase 3 PoC consumer #7~#12.
//!
//! Simulates exactly what the GUI's `callEngineDirect` does: build the
//! `EngineRequest` JSON, dispatch via `vibelign_core::ipc::handler::handle`,
//! parse the response back, and assert the shape the TS code reads.
//!
//! Usage:
//! ```
//! cargo run --example wire_smoke_phase3 -- /tmp/vib-wire-smoke
//! ```

use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use vibelign_core::ipc::handler::handle;
use vibelign_core::ipc::protocol::EngineRequest;

fn dispatch(request: Value) -> Value {
    let parsed: EngineRequest = serde_json::from_value(request).expect("request parse");
    let response = handle(parsed);
    serde_json::to_value(response).expect("response serialize")
}

fn assert_eq_msg<T: PartialEq + std::fmt::Debug>(actual: T, expected: T, what: &str) {
    if actual != expected {
        panic!("[FAIL] {what}: expected {expected:?}, got {actual:?}");
    }
    println!("  [OK] {what}");
}

fn smoke_ai_enhancement(root: &Path) {
    println!("\n== ai_enhancement_status / ai_enhancement_set ==");
    let initial = dispatch(json!({"command": "ai_enhancement_status", "root": root}));
    assert_eq_msg(initial["status"].as_str(), Some("ok"), "status=ok (initial read)");
    assert_eq_msg(initial["result"].as_str(), Some("ai_enhancement_status"), "result label");
    assert_eq_msg(initial["enabled"].as_bool(), Some(false), "default false when file missing");

    let enabled = dispatch(json!({"command": "ai_enhancement_set", "root": root, "enabled": true}));
    assert_eq_msg(enabled["status"].as_str(), Some("ok"), "set ok");
    assert_eq_msg(enabled["result"].as_str(), Some("ai_enhancement_set"), "set result label");
    assert_eq_msg(enabled["enabled"].as_bool(), Some(true), "set returns true");

    let after_set = dispatch(json!({"command": "ai_enhancement_status", "root": root}));
    assert_eq_msg(after_set["enabled"].as_bool(), Some(true), "round-trip read=true after set=true");

    dispatch(json!({"command": "ai_enhancement_set", "root": root, "enabled": false}));
    let after_disable = dispatch(json!({"command": "ai_enhancement_status", "root": root}));
    assert_eq_msg(after_disable["enabled"].as_bool(), Some(false), "round-trip read=false after set=false");
}

fn smoke_auto_backup(root: &Path) {
    println!("\n== auto_backup_status / auto_backup_set ==");
    let initial = dispatch(json!({"command": "auto_backup_status", "root": root}));
    assert_eq_msg(initial["status"].as_str(), Some("ok"), "status=ok (initial read)");
    assert_eq_msg(initial["result"].as_str(), Some("auto_backup_status"), "result label");
    assert_eq_msg(initial["enabled"].as_bool(), Some(true), "default true when DB missing");

    dispatch(json!({"command": "auto_backup_set", "root": root, "enabled": false}));
    let after_off = dispatch(json!({"command": "auto_backup_status", "root": root}));
    assert_eq_msg(after_off["enabled"].as_bool(), Some(false), "read=false after set=false");

    dispatch(json!({"command": "auto_backup_set", "root": root, "enabled": true}));
    let after_on = dispatch(json!({"command": "auto_backup_status", "root": root}));
    assert_eq_msg(after_on["enabled"].as_bool(), Some(true), "read=true after set=true");
}

fn smoke_anchor_meta(root: &Path) {
    println!("\n== anchor_list_meta / anchor_set_intent ==");
    let initial = dispatch(json!({"command": "anchor_list_meta", "root": root}));
    assert_eq_msg(initial["status"].as_str(), Some("ok"), "status=ok (initial read)");
    assert_eq_msg(initial["result"].as_str(), Some("anchor_list_meta"), "result label");
    assert_eq_msg(initial["meta"].as_object().map(|m| m.is_empty()), Some(true), "empty meta when file missing");

    let set_response = dispatch(json!({
        "command": "anchor_set_intent",
        "root": root,
        "anchor_name": "FOO_START",
        "intent": "test anchor purpose",
        "connects": ["BAR_START", "BAZ_START"],
        "warning": "be careful",
        "aliases": ["foo_alt"],
        "description": "a test anchor description"
    }));
    assert_eq_msg(set_response["status"].as_str(), Some("ok"), "set ok");
    assert_eq_msg(set_response["result"].as_str(), Some("anchor_set_intent"), "set result label");
    assert_eq_msg(set_response["anchor_name"].as_str(), Some("FOO_START"), "echo anchor name");
    let entry = set_response["entry"].as_object().expect("entry is object");
    assert_eq_msg(entry.get("intent").and_then(Value::as_str), Some("test anchor purpose"), "intent stored");
    assert_eq_msg(entry.get("_source").and_then(Value::as_str), Some("manual"), "_source forced to manual");
    assert_eq_msg(entry.get("warning").and_then(Value::as_str), Some("be careful"), "warning stored");
    assert_eq_msg(
        entry.get("connects").map(|v| v.clone()),
        Some(json!(["BAR_START", "BAZ_START"])),
        "connects stored as array",
    );

    let after_set = dispatch(json!({"command": "anchor_list_meta", "root": root}));
    let meta = after_set["meta"].as_object().expect("meta is object");
    let stored = meta.get("FOO_START").and_then(|v| v.as_object()).expect("FOO_START present");
    assert_eq_msg(stored.get("intent").and_then(Value::as_str), Some("test anchor purpose"), "list read sees stored intent");

    // Partial update: only intent provided, others should carry from existing entry.
    let partial = dispatch(json!({
        "command": "anchor_set_intent",
        "root": root,
        "anchor_name": "FOO_START",
        "intent": "updated purpose",
        "connects": null,
        "warning": null,
        "aliases": null,
        "description": null,
    }));
    let updated_entry = partial["entry"].as_object().expect("entry on partial");
    assert_eq_msg(updated_entry.get("intent").and_then(Value::as_str), Some("updated purpose"), "intent overwritten");
    assert_eq_msg(updated_entry.get("warning").and_then(Value::as_str), Some("be careful"), "warning carried over");
    assert_eq_msg(
        updated_entry.get("connects").map(|v| v.clone()),
        Some(json!(["BAR_START", "BAZ_START"])),
        "connects carried over",
    );
}

fn smoke_memory_summary(root: &Path) {
    println!("\n== memory_summary_read ==");

    // Empty project → defaults.
    let defaults = dispatch(json!({"command": "memory_summary_read", "root": root, "tool": "vib-gui"}));
    assert_eq_msg(defaults["status"].as_str(), Some("ok"), "status=ok (default state)");
    assert_eq_msg(defaults["result"].as_str(), Some("memory_summary_read"), "result label");
    let payload = defaults["payload"].as_object().expect("payload object");
    assert_eq_msg(payload["active_intent"].is_null(), true, "active_intent null when no file");
    assert_eq_msg(payload["decisions"].as_array().map(|a| a.is_empty()), Some(true), "empty decisions array");

    // Populated work_memory.json → passthrough with normalization.
    let dir = root.join(".vibelign");
    std::fs::write(
        dir.join("work_memory.json"),
        json!({
            "schema_version": 1,
            "active_intent": {"text": "smoke test intent"},
            "decisions": [{"text": "use Rust direct bridge"}],
            "relevant_files": [{"path": "src/main.rs", "why": "entry", "source": "system"}],
        })
        .to_string(),
    )
    .expect("write work_memory.json");
    let populated = dispatch(json!({"command": "memory_summary_read", "root": root, "tool": "vib-gui"}));
    let payload = populated["payload"].as_object().expect("payload");
    assert_eq_msg(
        payload["active_intent"].get("text").and_then(Value::as_str),
        Some("smoke test intent"),
        "active_intent.text passthrough",
    );
    assert_eq_msg(payload["decisions"].as_array().map(|a| a.len()), Some(1), "decisions length=1");

    // Audit log verification: two reads → two entries with sequence 1 and 2.
    let audit_path = dir.join("memory_audit.jsonl");
    let audit_content = std::fs::read_to_string(&audit_path).expect("audit file written");
    let lines: Vec<&str> = audit_content.lines().collect();
    assert_eq_msg(lines.len(), 2, "two audit entries for two reads");
    let first: Value = serde_json::from_str(lines[0]).expect("audit line 1 json");
    let second: Value = serde_json::from_str(lines[1]).expect("audit line 2 json");
    assert_eq_msg(first["event"].as_str(), Some("memory_summary_read"), "event label");
    assert_eq_msg(first["tool"].as_str(), Some("vib-gui"), "tool tagged as vib-gui");
    assert_eq_msg(first["result"].as_str(), Some("success"), "result success");
    assert_eq_msg(first["sequence_number"].as_u64(), Some(1), "first seq=1");
    assert_eq_msg(second["sequence_number"].as_u64(), Some(2), "second seq=2");
    assert_eq_msg(
        first["project_root_hash"].as_str().map(|h| h.len()),
        Some(16),
        "project_root_hash is 16 hex chars",
    );
}

fn smoke_error_paths(root: &Path) {
    println!("\n== error paths ==");
    // anchor_set_intent with empty anchor_name -- engine accepts (Python parity),
    // but the result is still ok; tests cover the rejection layer elsewhere.
    let response = dispatch(json!({
        "command": "anchor_set_intent",
        "root": root,
        "anchor_name": "EMPTY_INTENT_START",
        "intent": "",
        "connects": null,
        "warning": null,
        "aliases": null,
        "description": null,
    }));
    assert_eq_msg(response["status"].as_str(), Some("ok"), "empty intent accepted (parity with Python wrapper)");
    let entry = response["entry"].as_object().unwrap();
    assert_eq_msg(entry.get("intent").and_then(Value::as_str), Some(""), "empty intent preserved");
    assert_eq_msg(entry.get("_source").and_then(Value::as_str), Some("manual"), "_source still set");
}

fn main() {
    let root: PathBuf = std::env::args()
        .nth(1)
        .map(PathBuf::from)
        .expect("usage: cargo run --example wire_smoke_phase3 -- <root>");
    if root.exists() {
        std::fs::remove_dir_all(&root).expect("cleanup root");
    }
    std::fs::create_dir_all(&root).expect("create root");

    smoke_ai_enhancement(&root);
    smoke_auto_backup(&root);
    smoke_anchor_meta(&root);
    smoke_memory_summary(&root);
    smoke_error_paths(&root);

    println!("\n== ALL SMOKE PASSED ==");
}
// === ANCHOR: WIRE_SMOKE_PHASE3_END ===
