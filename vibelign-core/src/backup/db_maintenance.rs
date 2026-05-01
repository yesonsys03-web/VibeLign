use crate::security::path_guard::resolve_under;
use chrono::{SecondsFormat, Utc};
use rusqlite::{Connection, OpenFlags};
use serde::Serialize;
use std::fs;
#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

const BUSY_TIMEOUT_MS: i64 = 15_000;
const MIN_VACUUM_RECLAIM_BYTES: i64 = 16 * 1024 * 1024;
const MIN_VACUUM_RECLAIM_RATIO: f64 = 0.10;

#[derive(Debug, Clone, Serialize)]
pub struct DbMaintenanceFileStats {
    pub database_bytes: i64,
    pub wal_bytes: i64,
    pub shm_bytes: i64,
    pub total_bytes: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct DbMaintenanceReport {
    pub result: String,
    pub mode: String,
    pub db_exists: bool,
    pub db_path: String,
    pub journal_mode: Option<String>,
    pub page_size: i64,
    pub page_count: i64,
    pub freelist_count: i64,
    pub estimated_free_bytes: i64,
    pub quick_check: String,
    pub planned_action: String,
    pub vacuum_recommended: bool,
    pub checkpoint_recommended: bool,
    pub backup_path: Option<String>,
    pub before: DbMaintenanceFileStats,
    pub after: DbMaintenanceFileStats,
    pub reclaimed_bytes: i64,
    pub blockers: Vec<String>,
    pub warnings: Vec<String>,
}

pub fn inspect(root: &Path) -> Result<DbMaintenanceReport, String> {
    inspect_inner(root, false)
}

pub fn compact(root: &Path) -> Result<DbMaintenanceReport, String> {
    inspect_inner(root, true)
}

fn inspect_inner(root: &Path, apply: bool) -> Result<DbMaintenanceReport, String> {
    let db_path = backup_db_path(root)?;
    let before = file_stats(&db_path);
    if !db_path.exists() {
        return Ok(missing_db_report(apply, &db_path, before));
    }

    let flags = if apply {
        OpenFlags::SQLITE_OPEN_READ_WRITE | OpenFlags::SQLITE_OPEN_NO_MUTEX
    } else {
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX
    };
    let conn = Connection::open_with_flags(&db_path, flags)
        .map_err(|error| format!("failed to open backup DB for maintenance: {error}"))?;
    conn.pragma_update(None, "busy_timeout", BUSY_TIMEOUT_MS)
        .map_err(|error| error.to_string())?;

    let journal_mode = query_string_pragma(&conn, "journal_mode")?;
    let page_size = query_i64_pragma(&conn, "page_size")?;
    let page_count = query_i64_pragma(&conn, "page_count")?;
    let freelist_count = query_i64_pragma(&conn, "freelist_count")?;
    let quick_check = query_quick_check(&conn)?;
    let estimated_free_bytes = page_size.saturating_mul(freelist_count);
    let vacuum_recommended = should_vacuum(page_count, freelist_count, estimated_free_bytes);
    let checkpoint_recommended = before.wal_bytes > 0;
    let planned_action = planned_action(checkpoint_recommended, vacuum_recommended);
    let mut blockers = Vec::new();
    if quick_check != "ok" {
        blockers.push(format!("quick_check failed: {quick_check}"));
    }

    if !apply || !blockers.is_empty() {
        return Ok(DbMaintenanceReport {
            result: "backup_db_maintenance".to_string(),
            mode: if apply { "apply" } else { "dry_run" }.to_string(),
            db_exists: true,
            db_path: db_path.display().to_string(),
            journal_mode,
            page_size,
            page_count,
            freelist_count,
            estimated_free_bytes,
            quick_check,
            planned_action,
            vacuum_recommended,
            checkpoint_recommended,
            backup_path: None,
            before: before.clone(),
            after: before,
            reclaimed_bytes: 0,
            blockers,
            warnings: Vec::new(),
        });
    }

    let backup_path = create_raw_backup(root, &db_path)?;
    let is_wal = journal_mode
        .as_deref()
        .map(|mode| mode.eq_ignore_ascii_case("wal"))
        .unwrap_or(false);
    let mut warnings = Vec::new();
    if is_wal {
        run_wal_checkpoint(&conn)?;
    } else {
        warnings.push("journal_mode이 WAL이 아니어서 WAL truncate를 건너뜁니다.".to_string());
    }
    if vacuum_recommended {
        conn.execute_batch("VACUUM")
            .map_err(|error| format!("failed to vacuum backup DB: {error}"))?;
    }
    drop(conn);

    let after = file_stats(&db_path);
    let reclaimed_bytes = before.total_bytes.saturating_sub(after.total_bytes);
    prune_maintenance_backups(root, 3)?;
    Ok(DbMaintenanceReport {
        result: "backup_db_maintenance".to_string(),
        mode: "apply".to_string(),
        db_exists: true,
        db_path: db_path.display().to_string(),
        journal_mode,
        page_size,
        page_count,
        freelist_count,
        estimated_free_bytes,
        quick_check,
        planned_action,
        vacuum_recommended,
        checkpoint_recommended,
        backup_path: Some(backup_path.display().to_string()),
        before,
        after,
        reclaimed_bytes,
        blockers,
        warnings,
    })
}

fn backup_db_path(root: &Path) -> Result<PathBuf, String> {
    resolve_under(root, ".vibelign/vibelign.db")
        .ok_or_else(|| "backup DB path escaped project root".to_string())
}

fn missing_db_report(
    apply: bool,
    db_path: &Path,
    before: DbMaintenanceFileStats,
) -> DbMaintenanceReport {
    DbMaintenanceReport {
        result: "backup_db_maintenance".to_string(),
        mode: if apply { "apply" } else { "dry_run" }.to_string(),
        db_exists: false,
        db_path: db_path.display().to_string(),
        journal_mode: None,
        page_size: 0,
        page_count: 0,
        freelist_count: 0,
        estimated_free_bytes: 0,
        quick_check: "not_run".to_string(),
        planned_action: "noop".to_string(),
        vacuum_recommended: false,
        checkpoint_recommended: false,
        backup_path: None,
        before: before.clone(),
        after: before,
        reclaimed_bytes: 0,
        blockers: vec!["backup DB does not exist".to_string()],
        warnings: Vec::new(),
    }
}

fn query_string_pragma(conn: &Connection, pragma: &str) -> Result<Option<String>, String> {
    conn.query_row(&format!("PRAGMA {pragma}"), [], |row| row.get(0))
        .map(Some)
        .map_err(|error| error.to_string())
}

fn query_i64_pragma(conn: &Connection, pragma: &str) -> Result<i64, String> {
    conn.query_row(&format!("PRAGMA {pragma}"), [], |row| row.get(0))
        .map_err(|error| error.to_string())
}

fn query_quick_check(conn: &Connection) -> Result<String, String> {
    conn.query_row("PRAGMA quick_check", [], |row| row.get(0))
        .map_err(|error| error.to_string())
}

fn should_vacuum(page_count: i64, freelist_count: i64, estimated_free_bytes: i64) -> bool {
    if estimated_free_bytes >= MIN_VACUUM_RECLAIM_BYTES {
        return true;
    }
    page_count > 0 && (freelist_count as f64 / page_count as f64) >= MIN_VACUUM_RECLAIM_RATIO
}

fn planned_action(checkpoint_recommended: bool, vacuum_recommended: bool) -> String {
    match (checkpoint_recommended, vacuum_recommended) {
        (false, false) => "noop",
        (true, false) => "checkpoint_only",
        (_, true) => "checkpoint_and_vacuum",
    }
    .to_string()
}

fn run_wal_checkpoint(conn: &Connection) -> Result<(), String> {
    conn.query_row("PRAGMA wal_checkpoint(TRUNCATE)", [], |_| Ok(()))
        .map_err(|error| format!("failed to checkpoint backup DB WAL: {error}"))
}

fn create_raw_backup(root: &Path, db_path: &Path) -> Result<PathBuf, String> {
    let backup_root = resolve_under(root, ".vibelign/db_maintenance_backups")
        .ok_or_else(|| "maintenance backup path escaped project root".to_string())?;
    reject_symlink_if_exists(&backup_root)?;
    fs::create_dir_all(&backup_root).map_err(|error| error.to_string())?;
    restrict_dir_permissions(&backup_root)?;
    let timestamp = Utc::now().to_rfc3339_opts(SecondsFormat::Micros, true);
    let safe_timestamp = timestamp.replace([':', '.', '-'], "");
    let backup_path = backup_root.join(safe_timestamp);
    fs::create_dir_all(&backup_path).map_err(|error| error.to_string())?;
    restrict_dir_permissions(&backup_path)?;
    copy_if_exists(db_path, &backup_path.join("vibelign.db"))?;
    copy_if_exists(
        &db_path.with_file_name("vibelign.db-wal"),
        &backup_path.join("vibelign.db-wal"),
    )?;
    copy_if_exists(
        &db_path.with_file_name("vibelign.db-shm"),
        &backup_path.join("vibelign.db-shm"),
    )?;
    Ok(backup_path)
}

fn copy_if_exists(source: &Path, destination: &Path) -> Result<(), String> {
    if source.exists() {
        reject_symlink_if_exists(source)?;
        fs::copy(source, destination).map_err(|error| error.to_string())?;
        restrict_file_permissions(destination)?;
    }
    Ok(())
}

fn prune_maintenance_backups(root: &Path, keep_latest: usize) -> Result<(), String> {
    let backup_root = resolve_under(root, ".vibelign/db_maintenance_backups")
        .ok_or_else(|| "maintenance backup path escaped project root".to_string())?;
    if !backup_root.exists() {
        return Ok(());
    }
    reject_symlink_if_exists(&backup_root)?;
    let mut entries = fs::read_dir(&backup_root)
        .map_err(|error| error.to_string())?
        .filter_map(Result::ok)
        .filter(|entry| is_real_directory(&entry.path()))
        .collect::<Vec<_>>();
    entries.sort_by_key(|entry| entry.file_name());
    let remove_count = entries.len().saturating_sub(keep_latest);
    for entry in entries.into_iter().take(remove_count) {
        fs::remove_dir_all(entry.path()).map_err(|error| error.to_string())?;
    }
    Ok(())
}

fn reject_symlink_if_exists(path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            Err("backup DB maintenance refuses to follow symlinks".to_string())
        }
        Ok(_) | Err(_) => Ok(()),
    }
}

fn is_real_directory(path: &Path) -> bool {
    match fs::symlink_metadata(path) {
        Ok(metadata) => metadata.is_dir() && !metadata.file_type().is_symlink(),
        Err(_) => false,
    }
}

#[cfg(unix)]
fn restrict_dir_permissions(path: &Path) -> Result<(), String> {
    fs::set_permissions(path, fs::Permissions::from_mode(0o700)).map_err(|error| error.to_string())
}

#[cfg(not(unix))]
fn restrict_dir_permissions(_path: &Path) -> Result<(), String> {
    Ok(())
}

#[cfg(unix)]
fn restrict_file_permissions(path: &Path) -> Result<(), String> {
    fs::set_permissions(path, fs::Permissions::from_mode(0o600)).map_err(|error| error.to_string())
}

#[cfg(not(unix))]
fn restrict_file_permissions(_path: &Path) -> Result<(), String> {
    Ok(())
}

fn file_stats(db_path: &Path) -> DbMaintenanceFileStats {
    let database_bytes = file_size_bytes(db_path);
    let wal_bytes = file_size_bytes(&db_path.with_file_name("vibelign.db-wal"));
    let shm_bytes = file_size_bytes(&db_path.with_file_name("vibelign.db-shm"));
    DbMaintenanceFileStats {
        database_bytes,
        wal_bytes,
        shm_bytes,
        total_bytes: database_bytes + wal_bytes + shm_bytes,
    }
}

fn file_size_bytes(path: &Path) -> i64 {
    fs::metadata(path)
        .map(|metadata| metadata.len().min(i64::MAX as u64) as i64)
        .unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::schema::initialize;
    use rusqlite::Connection;
    use tempfile::tempdir;

    #[test]
    fn dry_run_reports_db_file_stats_and_planned_action_without_writing() {
        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let db_path = db_dir.join("vibelign.db");
        {
            let conn = Connection::open(&db_path).unwrap();
            initialize(&conn).unwrap();
            conn.execute("CREATE TABLE db_maintenance_probe(value TEXT)", [])
                .unwrap();
            conn.execute("INSERT INTO db_maintenance_probe(value) VALUES ('x')", [])
                .unwrap();
            conn.execute("DELETE FROM db_maintenance_probe", [])
                .unwrap();
        }
        let before_modified = std::fs::metadata(&db_path).unwrap().modified().unwrap();

        let report = inspect(dir.path()).unwrap();
        let after_modified = std::fs::metadata(&db_path).unwrap().modified().unwrap();

        assert!(report.db_exists);
        assert!(report.before.total_bytes > 0);
        assert_eq!(report.mode, "dry_run");
        assert_eq!(report.quick_check, "ok");
        assert!(matches!(
            report.planned_action.as_str(),
            "noop" | "checkpoint_only" | "checkpoint_and_vacuum"
        ));
        assert!(report.backup_path.is_none());
        assert_eq!(before_modified, after_modified);
    }

    #[test]
    fn compact_apply_creates_db_backup_and_reports_after_stats() {
        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let db_path = db_dir.join("vibelign.db");
        {
            let conn = Connection::open(&db_path).unwrap();
            initialize(&conn).unwrap();
        }

        let report = compact(dir.path()).unwrap();

        assert!(report.db_exists);
        assert_eq!(report.mode, "apply");
        assert_eq!(report.quick_check, "ok");
        let backup_path = report.backup_path.expect("backup path");
        assert!(std::path::Path::new(&backup_path)
            .join("vibelign.db")
            .exists());
        assert!(report.after.total_bytes > 0);
        assert!(report.reclaimed_bytes >= 0);
    }

    #[test]
    #[cfg(unix)]
    fn compact_rejects_symlinked_db_source() {
        use std::os::unix::fs::symlink;

        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let outside = dir.path().join("outside.db");
        {
            let conn = Connection::open(&outside).unwrap();
            initialize(&conn).unwrap();
        }
        symlink(&outside, db_dir.join("vibelign.db")).unwrap();

        let error = compact(dir.path()).unwrap_err();

        assert!(error.contains("symlink"));
    }

    #[test]
    #[cfg(unix)]
    fn compact_rejects_symlinked_backup_root() {
        use std::os::unix::fs::symlink;

        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        {
            let conn = Connection::open(db_dir.join("vibelign.db")).unwrap();
            initialize(&conn).unwrap();
        }
        let outside = dir.path().join("outside_backups");
        std::fs::create_dir_all(&outside).unwrap();
        symlink(&outside, db_dir.join("db_maintenance_backups")).unwrap();

        let error = compact(dir.path()).unwrap_err();

        assert!(error.contains("symlink"));
    }
}
