use crate::security::path_guard::resolve_under;
use rusqlite::{Connection, OpenFlags, OptionalExtension};
use serde::Serialize;
use std::collections::HashSet;
use std::path::Path;

const CURRENT_SCHEMA_VERSION: i64 = 3;

// === ANCHOR: BACKUP_DB_VIEWER_START ===
#[derive(Debug, Clone, Serialize)]
pub struct BackupDbViewerInspectReport {
    pub db_exists: bool,
    pub db_path: String,
    pub db_file: BackupDbViewerDbFileStats,
    pub schema_version: Option<String>,
    pub checkpoint_count: i64,
    pub rust_v2_count: i64,
    pub legacy_count: i64,
    pub cas_object_count: i64,
    pub cas_ref_count: i64,
    pub total_original_size_bytes: i64,
    pub total_stored_size_bytes: i64,
    pub auto_backup_on_commit: bool,
    pub retention_policy: Option<BackupDbViewerRetentionPolicy>,
    pub object_store: BackupDbViewerObjectStore,
    pub checkpoints: Vec<BackupDbViewerCheckpointRow>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct BackupDbViewerDbFileStats {
    pub database_bytes: i64,
    pub wal_bytes: i64,
    pub shm_bytes: i64,
    pub total_bytes: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BackupDbViewerRetentionPolicy {
    pub keep_latest: i64,
    pub keep_daily_days: i64,
    pub keep_weekly_weeks: i64,
    pub max_total_size_bytes: i64,
    pub max_age_days: i64,
    pub min_keep: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BackupDbViewerObjectStore {
    pub exists: bool,
    pub path: String,
    pub compression_summary: Vec<BackupDbViewerCompressionSummary>,
    pub stored_size_bytes: i64,
    pub original_size_bytes: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BackupDbViewerCompressionSummary {
    pub compression: String,
    pub object_count: i64,
}

#[derive(Debug, Clone, Serialize)]
pub struct BackupDbViewerCheckpointRow {
    pub checkpoint_id: String,
    pub display_name: String,
    pub created_at: String,
    pub pinned: bool,
    pub trigger: Option<String>,
    pub trigger_label: String,
    pub git_commit_sha: Option<String>,
    pub git_commit_message: Option<String>,
    pub file_count: i64,
    pub total_size_bytes: i64,
    pub original_size_bytes: i64,
    pub stored_size_bytes: i64,
    pub reused_file_count: i64,
    pub changed_file_count: i64,
    pub engine_version: Option<String>,
    pub parent_checkpoint_id: Option<String>,
    pub internal_badges: Vec<String>,
}

#[derive(Debug, Default)]
struct TableInfo {
    tables: HashSet<String>,
    checkpoints: HashSet<String>,
    retention_policy: HashSet<String>,
    cas_objects: HashSet<String>,
}

pub fn inspect(root: &Path) -> Result<BackupDbViewerInspectReport, String> {
    let db_path = resolve_under(root, ".vibelign/vibelign.db")
        .ok_or_else(|| "backup DB path escaped project root".to_string())?;
    let object_store_path = resolve_under(root, ".vibelign/rust_objects/blake3")
        .ok_or_else(|| "object store path escaped project root".to_string())?;
    let mut warnings = Vec::new();
    let db_file = load_db_file_stats(&db_path);

    if !db_path.exists() {
        warnings.push("Rust backup DB가 아직 없어요. 백업을 먼저 만들어 주세요.".to_string());
        return Ok(empty_report(
            false,
            db_path.display().to_string(),
            db_file,
            object_store_path,
            warnings,
        ));
    }

    let conn = Connection::open_with_flags(
        &db_path,
        OpenFlags::SQLITE_OPEN_READ_ONLY | OpenFlags::SQLITE_OPEN_NO_MUTEX,
    )
    .map_err(|error| format!("failed to open backup DB read-only: {error}"))?;
    if let Err(error) = conn.pragma_update(None, "query_only", true) {
        warnings.push(format!(
            "query_only pragma를 적용하지 못했지만 read-only connection으로 계속 표시합니다: {error}"
        ));
    }

    let table_info = load_table_info(&conn)?;
    let schema_version = read_meta_value(&conn, &table_info, "schema_version")?;
    if let Some(version) = schema_version
        .as_deref()
        .and_then(|value| value.parse::<i64>().ok())
    {
        if version > CURRENT_SCHEMA_VERSION {
            warnings.push(format!(
                "현재 엔진보다 새로운 백업 DB schema_version={version}입니다. 읽기 전용으로만 표시합니다."
            ));
        }
    }
    add_db_size_warnings(&db_file, &mut warnings);

    let auto_backup_on_commit = read_meta_value(&conn, &table_info, "auto_backup_on_commit")?
        .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "YES"))
        .unwrap_or(false);

    if !table_info.tables.contains("checkpoints") {
        warnings.push("checkpoints table이 없어 백업 row 요약을 0으로 표시합니다.".to_string());
    }
    if !table_info.tables.contains("cas_objects") {
        warnings.push("cas_objects table이 없어 object store 요약을 0으로 표시합니다.".to_string());
    }
    if !table_info.tables.contains("retention_policy") {
        warnings.push("retention_policy table이 없어 정리 정책을 표시하지 않습니다.".to_string());
    }

    let retention_policy = load_retention_policy(&conn, &table_info, &mut warnings)?;
    let object_store = load_object_store(&conn, &table_info, object_store_path)?;
    let checkpoints = load_checkpoints(&conn, &table_info, &mut warnings)?;

    Ok(BackupDbViewerInspectReport {
        db_exists: true,
        db_path: db_path.display().to_string(),
        db_file,
        schema_version,
        checkpoint_count: aggregate_count(&conn, &table_info, "checkpoints")?,
        rust_v2_count: aggregate_where_count(
            &conn,
            &table_info,
            "checkpoints",
            "engine_version",
            "engine_version = 'rust-v2'",
        )?,
        legacy_count: aggregate_legacy_count(&conn, &table_info)?,
        cas_object_count: object_store
            .compression_summary
            .iter()
            .map(|item| item.object_count)
            .sum(),
        cas_ref_count: sum_column(&conn, &table_info, "cas_objects", "ref_count")?,
        total_original_size_bytes: sum_column(
            &conn,
            &table_info,
            "checkpoints",
            "original_size_bytes",
        )?,
        total_stored_size_bytes: sum_column(
            &conn,
            &table_info,
            "checkpoints",
            "stored_size_bytes",
        )?,
        auto_backup_on_commit,
        retention_policy,
        object_store,
        checkpoints,
        warnings,
    })
}

fn empty_report(
    db_exists: bool,
    db_path: String,
    db_file: BackupDbViewerDbFileStats,
    object_store_path: std::path::PathBuf,
    warnings: Vec<String>,
) -> BackupDbViewerInspectReport {
    BackupDbViewerInspectReport {
        db_exists,
        db_path,
        db_file,
        schema_version: None,
        checkpoint_count: 0,
        rust_v2_count: 0,
        legacy_count: 0,
        cas_object_count: 0,
        cas_ref_count: 0,
        total_original_size_bytes: 0,
        total_stored_size_bytes: 0,
        auto_backup_on_commit: false,
        retention_policy: None,
        object_store: BackupDbViewerObjectStore {
            exists: object_store_path.exists(),
            path: object_store_path.display().to_string(),
            compression_summary: Vec::new(),
            stored_size_bytes: 0,
            original_size_bytes: 0,
        },
        checkpoints: Vec::new(),
        warnings,
    }
}

fn load_db_file_stats(db_path: &Path) -> BackupDbViewerDbFileStats {
    let database_bytes = file_size_bytes(db_path);
    let wal_bytes = file_size_bytes(&db_path.with_file_name("vibelign.db-wal"));
    let shm_bytes = file_size_bytes(&db_path.with_file_name("vibelign.db-shm"));
    BackupDbViewerDbFileStats {
        database_bytes,
        wal_bytes,
        shm_bytes,
        total_bytes: database_bytes + wal_bytes + shm_bytes,
    }
}

fn file_size_bytes(path: &Path) -> i64 {
    std::fs::metadata(path)
        .map(|metadata| metadata.len().min(i64::MAX as u64) as i64)
        .unwrap_or(0)
}

fn add_db_size_warnings(db_file: &BackupDbViewerDbFileStats, warnings: &mut Vec<String>) {
    const WARNING_BYTES: i64 = 64 * 1024 * 1024;
    const CRITICAL_BYTES: i64 = 256 * 1024 * 1024;
    if db_file.total_bytes >= CRITICAL_BYTES {
        warnings.push(
            "백업 관리 DB 파일이 256MB를 넘었어요. 백업 정리 뒤 DB 압축/정리 정책이 필요합니다."
                .to_string(),
        );
    } else if db_file.total_bytes >= WARNING_BYTES {
        warnings.push(
            "백업 관리 DB 파일이 64MB를 넘었어요. 계속 커지면 DB 압축/정리 정책을 검토하세요."
                .to_string(),
        );
    }
}

fn load_table_info(conn: &Connection) -> Result<TableInfo, String> {
    let mut info = TableInfo::default();
    let mut statement = conn
        .prepare("SELECT name FROM sqlite_master WHERE type = 'table'")
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| row.get::<_, String>(0))
        .map_err(|error| error.to_string())?;
    for row in rows {
        info.tables.insert(row.map_err(|error| error.to_string())?);
    }
    info.checkpoints = columns_for(conn, "checkpoints")?;
    info.retention_policy = columns_for(conn, "retention_policy")?;
    info.cas_objects = columns_for(conn, "cas_objects")?;
    Ok(info)
}

fn columns_for(conn: &Connection, table: &str) -> Result<HashSet<String>, String> {
    let mut columns = HashSet::new();
    let mut statement = conn
        .prepare(&format!("PRAGMA table_info({table})"))
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| row.get::<_, String>(1))
        .map_err(|error| error.to_string())?;
    for row in rows {
        columns.insert(row.map_err(|error| error.to_string())?);
    }
    Ok(columns)
}

fn read_meta_value(
    conn: &Connection,
    table_info: &TableInfo,
    key: &str,
) -> Result<Option<String>, String> {
    if !table_info.tables.contains("db_meta") {
        return Ok(None);
    }
    conn.query_row("SELECT value FROM db_meta WHERE key = ?", [key], |row| {
        row.get(0)
    })
    .optional()
    .map_err(|error| error.to_string())
}

fn load_retention_policy(
    conn: &Connection,
    table_info: &TableInfo,
    warnings: &mut Vec<String>,
) -> Result<Option<BackupDbViewerRetentionPolicy>, String> {
    if !table_info.tables.contains("retention_policy") {
        return Ok(None);
    }
    let required = [
        "keep_latest",
        "keep_daily_days",
        "keep_weekly_weeks",
        "max_total_size_bytes",
        "max_age_days",
        "min_keep",
    ];
    if required
        .iter()
        .any(|column| !table_info.retention_policy.contains(*column))
    {
        warnings
            .push("retention_policy schema가 오래되어 정리 정책을 표시하지 않습니다.".to_string());
        return Ok(None);
    }
    conn.query_row(
        "SELECT keep_latest, keep_daily_days, keep_weekly_weeks, max_total_size_bytes, max_age_days, min_keep
         FROM retention_policy WHERE id = 1",
        [],
        |row| {
            Ok(BackupDbViewerRetentionPolicy {
                keep_latest: row.get(0)?,
                keep_daily_days: row.get(1)?,
                keep_weekly_weeks: row.get(2)?,
                max_total_size_bytes: row.get(3)?,
                max_age_days: row.get(4)?,
                min_keep: row.get(5)?,
            })
        },
    )
    .optional()
    .map_err(|error| error.to_string())
}

fn load_object_store(
    conn: &Connection,
    table_info: &TableInfo,
    object_store_path: std::path::PathBuf,
) -> Result<BackupDbViewerObjectStore, String> {
    let compression_summary = if table_info.tables.contains("cas_objects") {
        if table_info.cas_objects.contains("compression") {
            let mut statement = conn
                .prepare(
                    "SELECT compression, COUNT(*) FROM cas_objects GROUP BY compression ORDER BY compression ASC",
                )
                .map_err(|error| error.to_string())?;
            let rows = statement
                .query_map([], |row| {
                    Ok(BackupDbViewerCompressionSummary {
                        compression: row
                            .get::<_, Option<String>>(0)?
                            .unwrap_or_else(|| "unknown".to_string()),
                        object_count: row.get(1)?,
                    })
                })
                .map_err(|error| error.to_string())?;
            let mut summary = Vec::new();
            for row in rows {
                summary.push(row.map_err(|error| error.to_string())?);
            }
            summary
        } else {
            let count = aggregate_count(conn, table_info, "cas_objects")?;
            if count == 0 {
                Vec::new()
            } else {
                vec![BackupDbViewerCompressionSummary {
                    compression: "unknown".to_string(),
                    object_count: count,
                }]
            }
        }
    } else {
        Vec::new()
    };
    Ok(BackupDbViewerObjectStore {
        exists: object_store_path.exists(),
        path: object_store_path.display().to_string(),
        compression_summary,
        stored_size_bytes: sum_column(conn, table_info, "cas_objects", "stored_size")?,
        original_size_bytes: sum_column(conn, table_info, "cas_objects", "size")?,
    })
}

fn load_checkpoints(
    conn: &Connection,
    table_info: &TableInfo,
    warnings: &mut Vec<String>,
) -> Result<Vec<BackupDbViewerCheckpointRow>, String> {
    if !table_info.tables.contains("checkpoints") {
        return Ok(Vec::new());
    }
    let required = [
        "checkpoint_id",
        "created_at",
        "message",
        "pinned",
        "total_size_bytes",
        "file_count",
    ];
    if required
        .iter()
        .any(|column| !table_info.checkpoints.contains(*column))
    {
        warnings.push("checkpoints schema가 오래되어 백업 row를 표시하지 않습니다.".to_string());
        return Ok(Vec::new());
    }
    let select = format!(
        "SELECT checkpoint_id, created_at, message, pinned, total_size_bytes, file_count,
         {engine_version}, {parent_checkpoint_id}, {original_size_bytes}, {stored_size_bytes},
         {reused_file_count}, {changed_file_count}, {trigger}, {git_commit_sha}, {git_commit_message}
         FROM checkpoints ORDER BY created_at DESC, checkpoint_id DESC",
        engine_version = optional_column(&table_info.checkpoints, "engine_version", "NULL"),
        parent_checkpoint_id = optional_column(&table_info.checkpoints, "parent_checkpoint_id", "NULL"),
        original_size_bytes = optional_column(&table_info.checkpoints, "original_size_bytes", "0"),
        stored_size_bytes = optional_column(&table_info.checkpoints, "stored_size_bytes", "0"),
        reused_file_count = optional_column(&table_info.checkpoints, "reused_file_count", "0"),
        changed_file_count = optional_column(&table_info.checkpoints, "changed_file_count", "0"),
        trigger = optional_column(&table_info.checkpoints, "trigger", "NULL"),
        git_commit_sha = optional_column(&table_info.checkpoints, "git_commit_sha", "NULL"),
        git_commit_message = optional_column(&table_info.checkpoints, "git_commit_message", "NULL"),
    );
    let mut statement = conn.prepare(&select).map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            let message: String = row.get(2)?;
            let trigger: Option<String> = row.get(12)?;
            let git_commit_message: Option<String> = row.get(14)?;
            let engine_version: Option<String> = row.get(6)?;
            Ok(BackupDbViewerCheckpointRow {
                checkpoint_id: row.get(0)?,
                display_name: display_name(
                    &message,
                    trigger.as_deref(),
                    git_commit_message.as_deref(),
                ),
                created_at: row.get(1)?,
                pinned: row.get::<_, i64>(3)? != 0,
                trigger: trigger.clone(),
                trigger_label: trigger_label(trigger.as_deref()).to_string(),
                git_commit_sha: row.get(13)?,
                git_commit_message,
                file_count: row.get(5)?,
                total_size_bytes: row.get(4)?,
                original_size_bytes: row.get(8)?,
                stored_size_bytes: row.get(9)?,
                reused_file_count: row.get(10)?,
                changed_file_count: row.get(11)?,
                engine_version: engine_version.clone(),
                parent_checkpoint_id: row.get(7)?,
                internal_badges: badges(engine_version.as_deref(), trigger.as_deref()),
            })
        })
        .map_err(|error| error.to_string())?;
    let mut checkpoints = Vec::new();
    for row in rows {
        checkpoints.push(row.map_err(|error| error.to_string())?);
    }
    Ok(checkpoints)
}

fn optional_column(columns: &HashSet<String>, column: &str, fallback: &str) -> String {
    if columns.contains(column) {
        column.to_string()
    } else {
        format!("{fallback} AS {column}")
    }
}

fn aggregate_count(conn: &Connection, table_info: &TableInfo, table: &str) -> Result<i64, String> {
    if !table_info.tables.contains(table) {
        return Ok(0);
    }
    conn.query_row(&format!("SELECT COUNT(*) FROM {table}"), [], |row| {
        row.get(0)
    })
    .map_err(|error| error.to_string())
}

fn aggregate_where_count(
    conn: &Connection,
    table_info: &TableInfo,
    table: &str,
    required_column: &str,
    predicate: &str,
) -> Result<i64, String> {
    let columns = columns_for_table(table_info, table);
    if !table_info.tables.contains(table) || !columns.contains(required_column) {
        return Ok(0);
    }
    conn.query_row(
        &format!("SELECT COUNT(*) FROM {table} WHERE {predicate}"),
        [],
        |row| row.get(0),
    )
    .map_err(|error| error.to_string())
}

fn aggregate_legacy_count(conn: &Connection, table_info: &TableInfo) -> Result<i64, String> {
    if !table_info.tables.contains("checkpoints") {
        return Ok(0);
    }
    if !table_info.checkpoints.contains("engine_version") {
        return aggregate_count(conn, table_info, "checkpoints");
    }
    conn.query_row(
        "SELECT COUNT(*) FROM checkpoints WHERE engine_version IS NULL OR engine_version != 'rust-v2'",
        [],
        |row| row.get(0),
    )
    .map_err(|error| error.to_string())
}

fn sum_column(
    conn: &Connection,
    table_info: &TableInfo,
    table: &str,
    column: &str,
) -> Result<i64, String> {
    let columns = columns_for_table(table_info, table);
    if !table_info.tables.contains(table) || !columns.contains(column) {
        return Ok(0);
    }
    conn.query_row(
        &format!("SELECT COALESCE(SUM({column}), 0) FROM {table}"),
        [],
        |row| row.get(0),
    )
    .map_err(|error| error.to_string())
}

fn columns_for_table<'a>(table_info: &'a TableInfo, table: &str) -> &'a HashSet<String> {
    match table {
        "checkpoints" => &table_info.checkpoints,
        "retention_policy" => &table_info.retention_policy,
        "cas_objects" => &table_info.cas_objects,
        _ => &table_info.tables,
    }
}

fn trigger_label(trigger: Option<&str>) -> &'static str {
    match trigger {
        Some("post_commit") => "코드 저장 뒤 자동 보관",
        Some("safe_restore") => "복원 보호용 내부 저장본",
        Some("manual") | None => "수동 백업",
        Some(_) => "기타",
    }
}

fn display_name(message: &str, trigger: Option<&str>, git_commit_message: Option<&str>) -> String {
    let source = git_commit_message
        .filter(|value| !value.trim().is_empty())
        .unwrap_or(message);
    let cleaned = clean_message(source);
    match trigger {
        Some("post_commit") => {
            if cleaned.is_empty() {
                "코드 저장 뒤 자동 보관".to_string()
            } else {
                format!("코드 저장 뒤 자동 보관 - {cleaned}")
            }
        }
        Some("safe_restore") => {
            if cleaned.is_empty() {
                "복원 보호용 내부 저장본".to_string()
            } else {
                format!("복원 보호용 내부 저장본 - {cleaned}")
            }
        }
        _ => {
            if cleaned.is_empty() {
                "메모 없는 저장본".to_string()
            } else {
                cleaned
            }
        }
    }
}

fn clean_message(value: &str) -> String {
    let mut text = value.trim().to_string();
    let lower = text.to_lowercase();
    if lower.starts_with("vibelign: checkpoint") {
        text = text["vibelign: checkpoint".len()..]
            .trim_start_matches([' ', '-'])
            .trim()
            .to_string();
    }
    text
}

fn badges(engine_version: Option<&str>, trigger: Option<&str>) -> Vec<String> {
    let mut badges = vec!["읽기 전용".to_string()];
    if engine_version == Some("rust-v2") {
        badges.push("Rust v2".to_string());
    }
    match trigger {
        Some("post_commit") => badges.push("자동 백업".to_string()),
        Some("safe_restore") => badges.push("복원 보호".to_string()),
        Some("manual") | None => badges.push("수동 백업".to_string()),
        Some(_) => badges.push("기타".to_string()),
    }
    badges
}
// === ANCHOR: BACKUP_DB_VIEWER_END ===

#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::schema::initialize;
    use rusqlite::{params, Connection};
    use tempfile::tempdir;

    #[test]
    fn inspect_missing_db_returns_empty_readable_state() {
        let dir = tempdir().unwrap();
        let report = inspect(dir.path()).unwrap();

        assert!(!report.db_exists);
        assert_eq!(report.db_file.total_bytes, 0);
        assert_eq!(report.checkpoint_count, 0);
        assert_eq!(report.cas_object_count, 0);
        assert!(report.checkpoints.is_empty());
        assert!(report
            .warnings
            .iter()
            .any(|warning| warning.contains("Rust backup DB")));
    }

    #[test]
    fn inspect_partial_db_with_only_db_meta_returns_warning_not_error() {
        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let conn = Connection::open(db_dir.join("vibelign.db")).unwrap();
        conn.execute(
            "CREATE TABLE db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO db_meta (key, value) VALUES ('schema_version', '1')",
            [],
        )
        .unwrap();
        conn.execute(
            "INSERT INTO db_meta (key, value) VALUES ('auto_backup_on_commit', '1')",
            [],
        )
        .unwrap();

        let report = inspect(dir.path()).unwrap();

        assert!(report.db_exists);
        assert!(report.db_file.database_bytes > 0);
        assert!(report.db_file.total_bytes >= report.db_file.database_bytes);
        assert_eq!(report.schema_version.as_deref(), Some("1"));
        assert_eq!(report.checkpoint_count, 0);
        assert_eq!(report.cas_object_count, 0);
        assert!(report.auto_backup_on_commit);
        assert!(report
            .warnings
            .iter()
            .any(|warning| warning.contains("table") || warning.contains("schema")));
    }

    #[test]
    fn inspect_summarizes_checkpoints_retention_and_cas_without_writing() {
        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let db_path = db_dir.join("vibelign.db");

        {
            let conn = Connection::open(&db_path).unwrap();
            initialize(&conn).unwrap();
            conn.execute(
                "UPDATE db_meta SET value='1' WHERE key='auto_backup_on_commit'",
                [],
            )
            .unwrap();
            conn.execute(
                "INSERT INTO checkpoints (checkpoint_id, created_at, message, pinned, total_size_bytes, file_count, engine_version, parent_checkpoint_id, original_size_bytes, stored_size_bytes, reused_file_count, changed_file_count, trigger, git_commit_sha, git_commit_message)
                 VALUES (?1, ?2, ?3, 0, ?4, ?5, 'rust-v2', NULL, ?6, ?7, ?8, ?9, 'post_commit', ?10, ?11)",
                params!["cp-1", "2026-05-01T10:00:00Z", "auto backup", 120_i64, 3_i64, 120_i64, 40_i64, 2_i64, 1_i64, "abcdef123456", "save work"],
            )
            .unwrap();
            conn.execute(
                "INSERT INTO checkpoint_files (checkpoint_id, relative_path, hash, size, storage_path, object_hash) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params!["cp-1", "src/main.rs", "hash-a", 40_i64, "cas:object-a", "object-a"],
            )
            .unwrap();
            conn.execute(
                "INSERT INTO cas_objects (hash, storage_path, ref_count, size, backend, compression, stored_size) VALUES (?1, ?2, ?3, ?4, 'local', 'none', ?5)",
                params!["object-a", "blake3/ob/je/object-a", 2_i64, 40_i64, 40_i64],
            )
            .unwrap();
        }

        let before_modified = std::fs::metadata(&db_path).unwrap().modified().unwrap();
        let report = inspect(dir.path()).unwrap();
        let after_modified = std::fs::metadata(&db_path).unwrap().modified().unwrap();

        assert!(report.db_exists);
        assert!(report.db_file.database_bytes > 0);
        assert!(report.db_file.total_bytes >= report.db_file.database_bytes);
        assert_eq!(report.checkpoint_count, 1);
        assert_eq!(report.rust_v2_count, 1);
        assert_eq!(report.legacy_count, 0);
        assert_eq!(report.cas_object_count, 1);
        assert_eq!(report.cas_ref_count, 2);
        assert_eq!(report.total_original_size_bytes, 120);
        assert_eq!(report.total_stored_size_bytes, 40);
        assert!(report.auto_backup_on_commit);
        assert_eq!(report.checkpoints[0].checkpoint_id, "cp-1");
        assert_eq!(
            report.checkpoints[0].display_name,
            "코드 저장 뒤 자동 보관 - save work"
        );
        assert_eq!(
            report.checkpoints[0].trigger_label,
            "코드 저장 뒤 자동 보관"
        );
        assert_eq!(before_modified, after_modified);
    }

    #[test]
    fn display_name_labels_safe_restore_rows() {
        assert_eq!(
            display_name("before restore", Some("safe_restore"), None),
            "복원 보호용 내부 저장본 - before restore"
        );
    }
}
