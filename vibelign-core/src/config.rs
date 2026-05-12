// === ANCHOR: CONFIG_START ===
//! Config status accessors used by the GUI direct bridge.
//!
//! Parity targets (Python):
//! - `vibelign/core/hook_setup.py::is_ai_enhancement_enabled` /
//!   `set_ai_enhancement_enabled` — naive line-scan / line-replace of
//!   `.vibelign/config.yaml`. Read default `false` when missing.
//! - `vibelign/core/checkpoint_engine/auto_backup.py::is_auto_backup_enabled` /
//!   `set_auto_backup_enabled` — reads/writes `db_meta.value` for key
//!   `auto_backup_on_commit` in `.vibelign/vibelign.db`. Read default `true`,
//!   `false` only when stored value is the literal "0".

use rusqlite::{params, Connection, OptionalExtension};
use std::path::Path;

pub fn ai_enhancement_status(root: &Path) -> Result<bool, String> {
    let path = root.join(".vibelign").join("config.yaml");
    let content = match std::fs::read_to_string(&path) {
        Ok(text) => text,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(false),
        Err(error) => return Err(error.to_string()),
    };
    for line in content.lines() {
        let trimmed = line.trim_start();
        if let Some(rest) = trimmed.strip_prefix("ai_enhancement:") {
            return Ok(rest.trim().eq_ignore_ascii_case("true"));
        }
    }
    Ok(false)
}

pub fn auto_backup_status(root: &Path) -> Result<bool, String> {
    let db_path = root.join(".vibelign").join("vibelign.db");
    if !db_path.exists() {
        return Ok(true);
    }
    let conn = Connection::open(&db_path).map_err(|error| error.to_string())?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        [],
    )
    .map_err(|error| error.to_string())?;
    let value: Option<String> = conn
        .query_row(
            "SELECT value FROM db_meta WHERE key = 'auto_backup_on_commit'",
            [],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    Ok(match value {
        None => true,
        Some(stored) => stored.trim() != "0",
    })
}

pub fn set_ai_enhancement(root: &Path, enabled: bool) -> Result<bool, String> {
    let vibelign_dir = root.join(".vibelign");
    std::fs::create_dir_all(&vibelign_dir).map_err(|error| error.to_string())?;
    let config_path = vibelign_dir.join("config.yaml");
    let content = std::fs::read_to_string(&config_path).unwrap_or_default();
    let mut lines: Vec<String> = if content.is_empty() {
        vec!["schema_version: 1".to_string()]
    } else {
        content.lines().map(String::from).collect()
    };
    let new_line = format!("ai_enhancement: {}", if enabled { "true" } else { "false" });
    let mut replaced = false;
    for line in lines.iter_mut() {
        if line.trim_start().starts_with("ai_enhancement:") {
            *line = new_line.clone();
            replaced = true;
            break;
        }
    }
    if !replaced {
        lines.push(new_line);
    }
    let mut output = lines.join("\n");
    let trimmed_len = output.trim_end().len();
    output.truncate(trimmed_len);
    output.push('\n');
    std::fs::write(&config_path, output).map_err(|error| error.to_string())?;
    Ok(enabled)
}

pub fn set_auto_backup(root: &Path, enabled: bool) -> Result<bool, String> {
    let vibelign_dir = root.join(".vibelign");
    std::fs::create_dir_all(&vibelign_dir).map_err(|error| error.to_string())?;
    let conn = Connection::open(vibelign_dir.join("vibelign.db"))
        .map_err(|error| error.to_string())?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        [],
    )
    .map_err(|error| error.to_string())?;
    conn.execute(
        "INSERT INTO db_meta(key, value) VALUES (?, ?) \
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        params!["auto_backup_on_commit", if enabled { "1" } else { "0" }],
    )
    .map_err(|error| error.to_string())?;
    Ok(enabled)
}

#[cfg(test)]
mod tests {
    use super::{ai_enhancement_status, auto_backup_status};
    use rusqlite::{params, Connection};

    #[test]
    fn ai_enhancement_returns_false_when_config_missing() {
        let temp = tempfile::tempdir().unwrap();
        assert!(!ai_enhancement_status(temp.path()).unwrap());
    }

    #[test]
    fn ai_enhancement_reads_true_from_yaml_line() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("config.yaml"),
            "schema_version: 1\nai_enhancement: true\n",
        )
        .unwrap();
        assert!(ai_enhancement_status(temp.path()).unwrap());
    }

    #[test]
    fn ai_enhancement_reads_false_from_yaml_line() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("config.yaml"),
            "ai_enhancement: false\nother: value\n",
        )
        .unwrap();
        assert!(!ai_enhancement_status(temp.path()).unwrap());
    }

    #[test]
    fn ai_enhancement_defaults_false_when_key_absent() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("config.yaml"), "schema_version: 1\n").unwrap();
        assert!(!ai_enhancement_status(temp.path()).unwrap());
    }

    #[test]
    fn auto_backup_defaults_true_when_db_missing() {
        let temp = tempfile::tempdir().unwrap();
        assert!(auto_backup_status(temp.path()).unwrap());
    }

    #[test]
    fn auto_backup_defaults_true_when_key_absent() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let conn = Connection::open(dir.join("vibelign.db")).unwrap();
        conn.execute(
            "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
            [],
        )
        .unwrap();
        drop(conn);
        assert!(auto_backup_status(temp.path()).unwrap());
    }

    #[test]
    fn auto_backup_returns_false_when_value_is_zero() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let conn = Connection::open(dir.join("vibelign.db")).unwrap();
        conn.execute(
            "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO db_meta(key, value) VALUES ('auto_backup_on_commit', '0')",
            params![],
        )
        .unwrap();
        drop(conn);
        assert!(!auto_backup_status(temp.path()).unwrap());
    }

    #[test]
    fn set_ai_enhancement_creates_config_with_schema_when_missing() {
        let temp = tempfile::tempdir().unwrap();
        let result = super::set_ai_enhancement(temp.path(), true).unwrap();
        assert!(result);
        let written = std::fs::read_to_string(temp.path().join(".vibelign/config.yaml")).unwrap();
        assert_eq!(written, "schema_version: 1\nai_enhancement: true\n");
    }

    #[test]
    fn set_ai_enhancement_replaces_existing_line_preserves_others() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join("config.yaml"),
            "schema_version: 1\nllm_provider: anthropic\nai_enhancement: false\nclaude_hook_enabled: true\n",
        )
        .unwrap();
        super::set_ai_enhancement(temp.path(), true).unwrap();
        let written = std::fs::read_to_string(dir.join("config.yaml")).unwrap();
        assert_eq!(
            written,
            "schema_version: 1\nllm_provider: anthropic\nai_enhancement: true\nclaude_hook_enabled: true\n",
        );
    }

    #[test]
    fn set_ai_enhancement_appends_when_key_absent() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("config.yaml"), "schema_version: 1\nllm_provider: anthropic\n").unwrap();
        super::set_ai_enhancement(temp.path(), false).unwrap();
        let written = std::fs::read_to_string(dir.join("config.yaml")).unwrap();
        assert_eq!(
            written,
            "schema_version: 1\nllm_provider: anthropic\nai_enhancement: false\n",
        );
    }

    #[test]
    fn set_ai_enhancement_round_trips_with_read() {
        let temp = tempfile::tempdir().unwrap();
        super::set_ai_enhancement(temp.path(), true).unwrap();
        assert!(ai_enhancement_status(temp.path()).unwrap());
        super::set_ai_enhancement(temp.path(), false).unwrap();
        assert!(!ai_enhancement_status(temp.path()).unwrap());
    }

    #[test]
    fn set_auto_backup_creates_table_and_upserts() {
        let temp = tempfile::tempdir().unwrap();
        super::set_auto_backup(temp.path(), false).unwrap();
        assert!(!auto_backup_status(temp.path()).unwrap());
        super::set_auto_backup(temp.path(), true).unwrap();
        assert!(auto_backup_status(temp.path()).unwrap());
    }

    #[test]
    fn set_auto_backup_replaces_existing_value() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let conn = Connection::open(dir.join("vibelign.db")).unwrap();
        conn.execute(
            "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO db_meta(key, value) VALUES ('auto_backup_on_commit', '1')",
            params![],
        )
        .unwrap();
        drop(conn);
        super::set_auto_backup(temp.path(), false).unwrap();
        assert!(!auto_backup_status(temp.path()).unwrap());
    }

    #[test]
    fn auto_backup_returns_true_when_value_is_one() {
        let temp = tempfile::tempdir().unwrap();
        let dir = temp.path().join(".vibelign");
        std::fs::create_dir_all(&dir).unwrap();
        let conn = Connection::open(dir.join("vibelign.db")).unwrap();
        conn.execute(
            "CREATE TABLE IF NOT EXISTS db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO db_meta(key, value) VALUES ('auto_backup_on_commit', '1')",
            params![],
        )
        .unwrap();
        drop(conn);
        assert!(auto_backup_status(temp.path()).unwrap());
    }
}
// === ANCHOR: CONFIG_END ===
