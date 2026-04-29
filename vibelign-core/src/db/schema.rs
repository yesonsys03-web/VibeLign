use rusqlite::{Connection, Result};

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
    Ok(())
}
