use rusqlite::{params, Connection, Result};
use std::collections::HashSet;
use unicode_normalization::UnicodeNormalization;

const TARGET_SCHEMA_VERSION: i64 = 3;
const DEFAULT_MAX_TOTAL_SIZE_BYTES: i64 = 1_073_741_824;
const OLD_MAX_TOTAL_SIZE_BYTES: i64 = 2_147_483_648;

pub fn initialize(conn: &Connection) -> Result<()> {
    conn.pragma_update(None, "journal_mode", "WAL")?;
    conn.pragma_update(None, "busy_timeout", 5000_i64)?;
    conn.pragma_update(None, "synchronous", "NORMAL")?;
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS db_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        INSERT OR IGNORE INTO db_meta(key, value) VALUES ('schema_version', '1');
        INSERT OR IGNORE INTO db_meta(key, value) VALUES ('created_at', datetime('now'));

        CREATE TABLE IF NOT EXISTS checkpoints (
            id INTEGER PRIMARY KEY,
            checkpoint_id TEXT UNIQUE NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            pinned INTEGER NOT NULL DEFAULT 0,
            total_size_bytes INTEGER NOT NULL DEFAULT 0,
            file_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS checkpoint_files (
            id INTEGER PRIMARY KEY,
            checkpoint_id TEXT NOT NULL,
            relative_path TEXT NOT NULL,
            hash TEXT NOT NULL,
            hash_algo TEXT NOT NULL DEFAULT 'blake3',
            size INTEGER NOT NULL,
            storage_path TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(checkpoint_id) REFERENCES checkpoints(checkpoint_id)
        );

        CREATE TABLE IF NOT EXISTS retention_policy (
            id INTEGER PRIMARY KEY,
            keep_latest INTEGER DEFAULT 30,
            keep_daily_days INTEGER DEFAULT 14,
            keep_weekly_weeks INTEGER DEFAULT 8,
            max_total_size_bytes INTEGER DEFAULT 2147483648,
            max_age_days INTEGER DEFAULT 180,
            min_keep INTEGER DEFAULT 10,
            updated_at TEXT
        );
        INSERT OR IGNORE INTO retention_policy(id, updated_at) VALUES (1, datetime('now'));

        CREATE TABLE IF NOT EXISTS cas_objects (
            hash TEXT PRIMARY KEY,
            storage_path TEXT NOT NULL,
            ref_count INTEGER DEFAULT 1,
            hash_algo TEXT DEFAULT 'blake3',
            size INTEGER
        );
        ",
    )?;
    apply_migrations(conn, TARGET_SCHEMA_VERSION)?;
    Ok(())
}

pub fn apply_migrations(conn: &Connection, target: i64) -> Result<()> {
    if target < 2 {
        return Ok(());
    }
    apply_v2_migration(conn)?;
    if target >= 3 {
        apply_v3_migration(conn)?;
    }
    conn.execute(
        "INSERT INTO db_meta(key, value) VALUES ('schema_version', ?)
         ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        params![target.to_string()],
    )?;
    Ok(())
}

fn apply_v3_migration(conn: &Connection) -> Result<()> {
    add_column_if_missing(
        conn,
        "cas_objects",
        "compression",
        "TEXT NOT NULL DEFAULT 'none'",
    )?;
    add_column_if_missing(
        conn,
        "cas_objects",
        "stored_size",
        "INTEGER NOT NULL DEFAULT 0",
    )?;
    conn.execute(
        "UPDATE cas_objects SET stored_size = size WHERE stored_size = 0 AND size IS NOT NULL",
        [],
    )?;
    Ok(())
}

fn apply_v2_migration(conn: &Connection) -> Result<()> {
    add_column_if_missing(conn, "checkpoint_files", "object_hash", "TEXT")?;
    add_column_if_missing(conn, "checkpoints", "engine_version", "TEXT")?;
    add_column_if_missing(conn, "checkpoints", "parent_checkpoint_id", "TEXT")?;
    add_column_if_missing(
        conn,
        "checkpoints",
        "original_size_bytes",
        "INTEGER NOT NULL DEFAULT 0",
    )?;
    add_column_if_missing(
        conn,
        "checkpoints",
        "stored_size_bytes",
        "INTEGER NOT NULL DEFAULT 0",
    )?;
    add_column_if_missing(
        conn,
        "checkpoints",
        "reused_file_count",
        "INTEGER NOT NULL DEFAULT 0",
    )?;
    add_column_if_missing(
        conn,
        "checkpoints",
        "changed_file_count",
        "INTEGER NOT NULL DEFAULT 0",
    )?;
    add_column_if_missing(
        conn,
        "checkpoints",
        "trigger",
        "TEXT NOT NULL DEFAULT 'manual'",
    )?;
    add_column_if_missing(conn, "checkpoints", "git_commit_sha", "TEXT")?;
    add_column_if_missing(conn, "checkpoints", "git_commit_message", "TEXT")?;
    add_column_if_missing(
        conn,
        "cas_objects",
        "backend",
        "TEXT NOT NULL DEFAULT 'local'",
    )?;
    add_column_if_missing(conn, "cas_objects", "object_uri", "TEXT")?;
    add_column_if_missing(conn, "cas_objects", "encryption_key_id", "TEXT")?;
    add_column_if_missing(conn, "cas_objects", "sync_state", "TEXT")?;
    conn.execute(
        "INSERT OR IGNORE INTO db_meta(key, value) VALUES ('auto_backup_on_commit', '0')",
        [],
    )?;
    migrate_retention_defaults(conn)?;
    normalize_legacy_relative_paths(conn)?;
    Ok(())
}

fn add_column_if_missing(
    conn: &Connection,
    table: &str,
    column: &str,
    definition: &str,
) -> Result<()> {
    if column_exists(conn, table, column)? {
        return Ok(());
    }
    conn.execute(
        &format!("ALTER TABLE {table} ADD COLUMN {column} {definition}"),
        [],
    )?;
    Ok(())
}

fn column_exists(conn: &Connection, table: &str, column: &str) -> Result<bool> {
    let mut statement = conn.prepare(&format!("PRAGMA table_info({table})"))?;
    let rows = statement.query_map([], |row| row.get::<_, String>(1))?;
    for row in rows {
        if row? == column {
            return Ok(true);
        }
    }
    Ok(false)
}

fn migrate_retention_defaults(conn: &Connection) -> Result<()> {
    conn.execute(
        "UPDATE retention_policy
         SET min_keep = 20
         WHERE id = 1 AND min_keep = 10",
        [],
    )?;
    conn.execute(
        "UPDATE retention_policy
         SET max_total_size_bytes = ?
         WHERE id = 1 AND max_total_size_bytes = ?",
        params![DEFAULT_MAX_TOTAL_SIZE_BYTES, OLD_MAX_TOTAL_SIZE_BYTES],
    )?;
    Ok(())
}

fn normalize_legacy_relative_paths(conn: &Connection) -> Result<()> {
    let mut statement = conn.prepare(
        "SELECT id, checkpoint_id, relative_path
         FROM checkpoint_files
         ORDER BY checkpoint_id ASC, id ASC",
    )?;
    let rows = statement.query_map([], |row| {
        Ok((
            row.get::<_, i64>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
        ))
    })?;
    let mut updates = Vec::new();
    let mut seen = HashSet::new();
    for row in rows {
        let (id, checkpoint_id, relative_path) = row?;
        let normalized = relative_path.nfc().collect::<String>();
        if !seen.insert((checkpoint_id, normalized.clone())) {
            return Err(rusqlite::Error::InvalidQuery);
        }
        if normalized != relative_path {
            updates.push((id, normalized));
        }
    }
    drop(statement);
    for (id, normalized) in updates {
        conn.execute(
            "UPDATE checkpoint_files SET relative_path = ? WHERE id = ?",
            params![normalized, id],
        )?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{column_exists, initialize, DEFAULT_MAX_TOTAL_SIZE_BYTES};
    use rusqlite::{params, Connection};

    #[test]
    fn initialize_applies_current_migrations_idempotently() {
        let conn = Connection::open_in_memory().unwrap();

        initialize(&conn).unwrap();
        initialize(&conn).unwrap();

        assert!(column_exists(&conn, "checkpoints", "engine_version").unwrap());
        assert!(column_exists(&conn, "checkpoint_files", "object_hash").unwrap());
        assert!(column_exists(&conn, "cas_objects", "backend").unwrap());
        let schema_version: String = conn
            .query_row(
                "SELECT value FROM db_meta WHERE key = 'schema_version'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(schema_version, "3");
        assert!(column_exists(&conn, "cas_objects", "compression").unwrap());
        assert!(column_exists(&conn, "cas_objects", "stored_size").unwrap());
    }

    #[test]
    fn v2_migration_updates_only_old_retention_defaults() {
        let conn = Connection::open_in_memory().unwrap();

        initialize(&conn).unwrap();

        let (min_keep, max_total_size_bytes): (i64, i64) = conn
            .query_row(
                "SELECT min_keep, max_total_size_bytes FROM retention_policy WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(min_keep, 20);
        assert_eq!(max_total_size_bytes, DEFAULT_MAX_TOTAL_SIZE_BYTES);

        conn.execute(
            "UPDATE retention_policy SET min_keep = 7, max_total_size_bytes = 123 WHERE id = 1",
            [],
        )
        .unwrap();
        initialize(&conn).unwrap();
        let (min_keep, max_total_size_bytes): (i64, i64) = conn
            .query_row(
                "SELECT min_keep, max_total_size_bytes FROM retention_policy WHERE id = 1",
                [],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(min_keep, 7);
        assert_eq!(max_total_size_bytes, 123);
    }

    #[test]
    fn v2_migration_normalizes_legacy_relative_paths() {
        let conn = Connection::open_in_memory().unwrap();
        initialize(&conn).unwrap();
        conn.execute(
            "INSERT INTO checkpoints(checkpoint_id, message, created_at, total_size_bytes, file_count)
             VALUES ('cp1', 'legacy', 'now', 1, 1)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO checkpoint_files(checkpoint_id, relative_path, hash, size, storage_path)
             VALUES ('cp1', ?, 'hash', 1, 'stored')",
            params!["e\u{301}.txt"],
        )
        .unwrap();

        initialize(&conn).unwrap();

        let relative_path: String = conn
            .query_row(
                "SELECT relative_path FROM checkpoint_files WHERE checkpoint_id = 'cp1'",
                [],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(relative_path, "é.txt");
    }
}
