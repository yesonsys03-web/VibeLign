use crate::backup::cas;
use crate::db::schema;
use chrono::{DateTime, Datelike, Duration, Utc};
use rusqlite::{params, Connection};
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs;
use std::path::{Component, Path};

#[derive(Debug, Clone, Copy)]
pub struct RetentionPolicy {
    pub keep_latest: u32,
    pub keep_daily_days: u32,
    pub keep_weekly_weeks: u32,
    pub max_total_size_bytes: u64,
    pub max_age_days: u32,
    pub min_keep: u32,
}

#[derive(Debug, Clone)]
struct RetentionCheckpoint {
    checkpoint_id: String,
    created_at: String,
    created: DateTime<Utc>,
    total_size_bytes: u64,
    stored_size_bytes: u64,
    pinned: bool,
    trigger: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct CleanupPlan {
    pub checkpoint_ids: Vec<String>,
    pub planned_bytes: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct CleanupResult {
    pub planned_count: usize,
    pub deleted_count: usize,
    pub planned_bytes: u64,
    pub reclaimed_bytes: u64,
    pub partial_failure: bool,
}

impl Default for RetentionPolicy {
    fn default() -> Self {
        Self {
            keep_latest: 20,
            keep_daily_days: 30,
            keep_weekly_weeks: 12,
            max_total_size_bytes: 1024 * 1024 * 1024,
            max_age_days: 180,
            min_keep: 20,
        }
    }
}

pub fn load_policy(conn: &Connection) -> Result<RetentionPolicy, String> {
    let policy = conn
        .query_row(
            "SELECT keep_latest, keep_daily_days, keep_weekly_weeks,
                    max_total_size_bytes, max_age_days, min_keep
             FROM retention_policy WHERE id = 1",
            [],
            |row| {
                Ok(RetentionPolicy {
                    keep_latest: row.get::<_, i64>(0)?.max(0) as u32,
                    keep_daily_days: row.get::<_, i64>(1)?.max(0) as u32,
                    keep_weekly_weeks: row.get::<_, i64>(2)?.max(0) as u32,
                    max_total_size_bytes: row.get::<_, i64>(3)?.max(0) as u64,
                    max_age_days: row.get::<_, i64>(4)?.max(0) as u32,
                    min_keep: row.get::<_, i64>(5)?.max(0) as u32,
                })
            },
        )
        .map_err(|error| error.to_string())?;
    Ok(policy)
}

pub fn plan(conn: &Connection, policy: RetentionPolicy) -> Result<CleanupPlan, String> {
    let checkpoints = load_checkpoints(conn)?;
    Ok(plan_from_checkpoints(&checkpoints, policy))
}

pub fn apply(root: &Path) -> Result<CleanupResult, String> {
    let db_path = root.join(".vibelign").join("vibelign.db");
    if !db_path.exists() {
        return Ok(CleanupResult {
            planned_count: 0,
            deleted_count: 0,
            planned_bytes: 0,
            reclaimed_bytes: 0,
            partial_failure: false,
        });
    }
    let mut conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    schema::initialize(&conn).map_err(|error| error.to_string())?;
    conn.pragma_update(None, "busy_timeout", 15_000_i64)
        .map_err(|error| error.to_string())?;
    let policy = load_policy(&conn)?;
    let plan = plan(&conn, policy)?;
    apply_plan(root, &mut conn, &plan)
}

pub fn apply_plan(
    root: &Path,
    conn: &mut Connection,
    plan: &CleanupPlan,
) -> Result<CleanupResult, String> {
    if plan.checkpoint_ids.is_empty() {
        return Ok(CleanupResult {
            planned_count: 0,
            deleted_count: 0,
            planned_bytes: 0,
            reclaimed_bytes: 0,
            partial_failure: false,
        });
    }
    let checkpoint_ids = plan.checkpoint_ids.iter().cloned().collect::<BTreeSet<_>>();
    let legacy_dirs = legacy_storage_dirs(root, conn, &checkpoint_ids)?;
    let object_counts = object_ref_counts(conn, &checkpoint_ids)?;
    let tx = conn.transaction().map_err(|error| error.to_string())?;
    for (object_hash, count) in object_counts {
        tx.execute(
            "UPDATE cas_objects
             SET ref_count = CASE WHEN ref_count >= ? THEN ref_count - ? ELSE 0 END
             WHERE hash = ?",
            params![count as i64, count as i64, object_hash],
        )
        .map_err(|error| error.to_string())?;
    }
    for checkpoint_id in &checkpoint_ids {
        tx.execute(
            "DELETE FROM checkpoint_files WHERE checkpoint_id = ?",
            params![checkpoint_id],
        )
        .map_err(|error| error.to_string())?;
        tx.execute(
            "DELETE FROM checkpoints WHERE checkpoint_id = ? AND pinned = 0",
            params![checkpoint_id],
        )
        .map_err(|error| error.to_string())?;
    }
    tx.commit().map_err(|error| error.to_string())?;

    let mut partial_failure = false;
    let mut reclaimed_bytes = 0_u64;
    match cas::prune_unreferenced_detailed(root, conn) {
        Ok(pruned) => reclaimed_bytes += pruned.bytes,
        Err(_) => partial_failure = true,
    }
    for storage_dir in legacy_dirs {
        if storage_dir.exists() {
            if fs::remove_dir_all(&storage_dir).is_err() {
                partial_failure = true;
            }
        }
    }
    Ok(CleanupResult {
        planned_count: checkpoint_ids.len(),
        deleted_count: checkpoint_ids.len(),
        planned_bytes: plan.planned_bytes,
        reclaimed_bytes,
        partial_failure,
    })
}

fn load_checkpoints(conn: &Connection) -> Result<Vec<RetentionCheckpoint>, String> {
    let mut statement = conn
        .prepare(
            "SELECT checkpoint_id, created_at, total_size_bytes, stored_size_bytes,
                    pinned, trigger
             FROM checkpoints ORDER BY created_at DESC, checkpoint_id DESC",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            let created_at: String = row.get(1)?;
            let created = DateTime::parse_from_rfc3339(&created_at)
                .map(|value| value.with_timezone(&Utc))
                .unwrap_or_else(|_| Utc::now());
            Ok(RetentionCheckpoint {
                checkpoint_id: row.get(0)?,
                created_at,
                created,
                total_size_bytes: row.get::<_, i64>(2)?.max(0) as u64,
                stored_size_bytes: row.get::<_, i64>(3)?.max(0) as u64,
                pinned: row.get::<_, i64>(4)? != 0,
                trigger: row.get(5)?,
            })
        })
        .map_err(|error| error.to_string())?;
    let mut checkpoints = Vec::new();
    for row in rows {
        checkpoints.push(row.map_err(|error| error.to_string())?);
    }
    Ok(checkpoints)
}

fn plan_from_checkpoints(
    checkpoints: &[RetentionCheckpoint],
    policy: RetentionPolicy,
) -> CleanupPlan {
    let minimum_keep = policy.min_keep.max(policy.keep_latest) as usize;
    let mut keep = BTreeSet::new();
    for checkpoint in checkpoints.iter().take(minimum_keep) {
        keep.insert(checkpoint.checkpoint_id.clone());
    }
    for checkpoint in checkpoints {
        if checkpoint.pinned || checkpoint.trigger == "safe_restore" {
            keep.insert(checkpoint.checkpoint_id.clone());
        }
    }
    let now = checkpoints
        .first()
        .map(|checkpoint| checkpoint.created)
        .unwrap_or_else(Utc::now);
    protect_recent_and_representatives(checkpoints, policy, now, &mut keep);

    let mut total_stored = checkpoints
        .iter()
        .filter(|checkpoint| !keep.contains(&checkpoint.checkpoint_id))
        .map(|checkpoint| checkpoint.stored_size_bytes)
        .sum::<u64>()
        + checkpoints
            .iter()
            .filter(|checkpoint| keep.contains(&checkpoint.checkpoint_id))
            .map(|checkpoint| checkpoint.stored_size_bytes)
            .sum::<u64>();
    let max_age_cutoff = now - Duration::days(i64::from(policy.max_age_days));
    let mut candidates = checkpoints
        .iter()
        .filter(|checkpoint| !keep.contains(&checkpoint.checkpoint_id))
        .collect::<Vec<_>>();
    candidates.sort_by(|left, right| {
        let left_auto = left.trigger == "post_commit";
        let right_auto = right.trigger == "post_commit";
        right_auto
            .cmp(&left_auto)
            .then_with(|| left.created.cmp(&right.created))
            .then_with(|| left.created_at.cmp(&right.created_at))
    });
    let mut prune = Vec::new();
    let mut planned_bytes = 0_u64;
    for candidate in candidates {
        let over_size =
            policy.max_total_size_bytes > 0 && total_stored > policy.max_total_size_bytes;
        let too_old = candidate.created < max_age_cutoff;
        if !over_size && !too_old {
            continue;
        }
        prune.push(candidate.checkpoint_id.clone());
        planned_bytes += candidate.total_size_bytes;
        total_stored = total_stored.saturating_sub(candidate.stored_size_bytes);
    }
    CleanupPlan {
        checkpoint_ids: prune,
        planned_bytes,
    }
}

fn protect_recent_and_representatives(
    checkpoints: &[RetentionCheckpoint],
    policy: RetentionPolicy,
    now: DateTime<Utc>,
    keep: &mut BTreeSet<String>,
) {
    let recent_cutoff = now - Duration::days(i64::from(policy.keep_daily_days.min(7)));
    let daily_cutoff = now - Duration::days(i64::from(policy.keep_daily_days));
    let weekly_cutoff = now - Duration::weeks(i64::from(policy.keep_weekly_weeks));
    let monthly_cutoff = now - Duration::days(i64::from(policy.max_age_days.min(365)));
    let mut daily = BTreeMap::new();
    let mut weekly = BTreeMap::new();
    let mut monthly = BTreeMap::new();
    for checkpoint in checkpoints {
        if checkpoint.created >= recent_cutoff {
            keep.insert(checkpoint.checkpoint_id.clone());
        }
        if checkpoint.created >= daily_cutoff {
            daily
                .entry(checkpoint.created.date_naive())
                .or_insert_with(|| checkpoint.checkpoint_id.clone());
        }
        if checkpoint.created >= weekly_cutoff {
            weekly
                .entry(checkpoint.created.iso_week())
                .or_insert_with(|| checkpoint.checkpoint_id.clone());
        }
        if checkpoint.created >= monthly_cutoff {
            monthly
                .entry((checkpoint.created.year(), checkpoint.created.month()))
                .or_insert_with(|| checkpoint.checkpoint_id.clone());
        }
    }
    keep.extend(daily.into_values());
    keep.extend(weekly.into_values());
    keep.extend(monthly.into_values());
}

fn legacy_storage_dirs(
    root: &Path,
    conn: &Connection,
    checkpoint_ids: &BTreeSet<String>,
) -> Result<Vec<std::path::PathBuf>, String> {
    let mut dirs = Vec::new();
    for checkpoint_id in checkpoint_ids {
        let engine_version: Option<String> = conn
            .query_row(
                "SELECT engine_version FROM checkpoints WHERE checkpoint_id = ?",
                params![checkpoint_id],
                |row| row.get(0),
            )
            .map_err(|error| error.to_string())?;
        if engine_version.as_deref() != Some("rust-v2") {
            validate_checkpoint_dir_name(checkpoint_id)?;
            dirs.push(
                root.join(".vibelign")
                    .join("rust_checkpoints")
                    .join(checkpoint_id),
            );
        }
    }
    Ok(dirs)
}

fn validate_checkpoint_dir_name(checkpoint_id: &str) -> Result<(), String> {
    let path = Path::new(checkpoint_id);
    if path.components().count() != 1 {
        return Err("checkpoint id is not a safe storage directory name".to_string());
    }
    if path.components().any(|component| {
        !matches!(component, Component::Normal(_))
            || matches!(
                component,
                Component::ParentDir | Component::Prefix(_) | Component::RootDir
            )
    }) {
        return Err("checkpoint id is not a safe storage directory name".to_string());
    }
    if checkpoint_id.contains('\\') || checkpoint_id.contains('/') {
        return Err("checkpoint id is not a safe storage directory name".to_string());
    }
    Ok(())
}

fn object_ref_counts(
    conn: &Connection,
    checkpoint_ids: &BTreeSet<String>,
) -> Result<HashMap<String, usize>, String> {
    let mut counts = HashMap::new();
    for checkpoint_id in checkpoint_ids {
        let mut statement = conn
            .prepare(
                "SELECT object_hash FROM checkpoint_files
                 WHERE checkpoint_id = ? AND object_hash IS NOT NULL",
            )
            .map_err(|error| error.to_string())?;
        let rows = statement
            .query_map(params![checkpoint_id], |row| row.get::<_, String>(0))
            .map_err(|error| error.to_string())?;
        for row in rows {
            *counts
                .entry(row.map_err(|error| error.to_string())?)
                .or_insert(0) += 1;
        }
    }
    Ok(counts)
}

#[cfg(test)]
mod tests {
    use super::{apply, load_policy, plan, RetentionPolicy};
    use crate::backup::checkpoint::{create_with_metadata, CheckpointCreateMetadata};
    use crate::db::schema;
    use chrono::{Duration, SecondsFormat, Utc};
    use rusqlite::{params, Connection};

    #[test]
    fn load_policy_reads_database_defaults() {
        let conn = Connection::open_in_memory().unwrap();
        schema::initialize(&conn).unwrap();

        let policy = load_policy(&conn).unwrap();

        assert_eq!(policy.min_keep, 20);
        assert_eq!(policy.max_total_size_bytes, 1024 * 1024 * 1024);
    }

    #[test]
    fn plan_keeps_pinned_and_prunes_auto_before_manual() {
        let conn = Connection::open_in_memory().unwrap();
        schema::initialize(&conn).unwrap();
        insert_checkpoint(&conn, "manual-old", 3, 100, "manual", false);
        insert_checkpoint(&conn, "auto-old", 2, 100, "post_commit", false);
        insert_checkpoint(&conn, "pinned-old", 1, 100, "post_commit", true);
        insert_checkpoint(&conn, "latest", 0, 100, "manual", false);

        let cleanup = plan(
            &conn,
            RetentionPolicy {
                keep_latest: 1,
                min_keep: 1,
                keep_daily_days: 0,
                keep_weekly_weeks: 0,
                max_total_size_bytes: 250,
                max_age_days: 0,
            },
        )
        .unwrap();

        assert_eq!(cleanup.checkpoint_ids[0], "auto-old");
        assert!(!cleanup.checkpoint_ids.contains(&"pinned-old".to_string()));
    }

    #[test]
    fn plan_keeps_monthly_representatives() {
        let conn = Connection::open_in_memory().unwrap();
        schema::initialize(&conn).unwrap();
        insert_checkpoint(&conn, "current", 0, 100, "manual", false);
        insert_checkpoint(&conn, "month-two", 45, 100, "post_commit", false);
        insert_checkpoint(&conn, "month-three", 75, 100, "post_commit", false);

        let cleanup = plan(
            &conn,
            RetentionPolicy {
                keep_latest: 1,
                min_keep: 1,
                keep_daily_days: 0,
                keep_weekly_weeks: 0,
                max_total_size_bytes: 1,
                max_age_days: 365,
            },
        )
        .unwrap();

        assert!(!cleanup.checkpoint_ids.contains(&"month-two".to_string()));
        assert!(!cleanup.checkpoint_ids.contains(&"month-three".to_string()));
    }

    #[test]
    fn apply_rejects_unsafe_legacy_checkpoint_directory_names() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let db_dir = root.join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let mut conn = Connection::open(db_dir.join("vibelign.db")).unwrap();
        schema::initialize(&conn).unwrap();
        insert_checkpoint(&conn, "latest", 0, 1, "manual", false);
        insert_legacy_checkpoint(&conn, "..\\evil", 10, 1);
        conn.execute(
            "UPDATE retention_policy SET keep_latest = 1, min_keep = 1, keep_daily_days = 0,
             keep_weekly_weeks = 0, max_total_size_bytes = 1, max_age_days = 0 WHERE id = 1",
            [],
        )
        .unwrap();

        let error = super::apply_plan(
            root,
            &mut conn,
            &super::CleanupPlan {
                checkpoint_ids: vec!["..\\evil".to_string()],
                planned_bytes: 1,
            },
        )
        .unwrap_err();

        assert!(error.contains("safe storage directory"));
        let remaining: i64 = conn
            .query_row("SELECT COUNT(*) FROM checkpoints", [], |row| row.get(0))
            .unwrap();
        assert_eq!(remaining, 2);
    }

    #[test]
    fn apply_removes_old_checkpoint_and_preserves_live_cas_object() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("shared.txt"), "same\n").unwrap();
        create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::write(root.join("changed.txt"), "one\n").unwrap();
        create_with_metadata(root, "second", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        conn.execute(
            "UPDATE retention_policy SET keep_latest = 1, min_keep = 1, keep_daily_days = 0,
             keep_weekly_weeks = 0, max_total_size_bytes = 1, max_age_days = 0 WHERE id = 1",
            [],
        )
        .unwrap();

        let result = apply(root).unwrap();

        let remaining: i64 = conn
            .query_row("SELECT COUNT(*) FROM checkpoints", [], |row| row.get(0))
            .unwrap();
        let shared_hash = blake3::hash(b"same\n").to_hex().to_string();
        let shared_ref_count: i64 = conn
            .query_row(
                "SELECT ref_count FROM cas_objects WHERE hash = ?",
                params![shared_hash],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(result.deleted_count, 1);
        assert_eq!(remaining, 1);
        assert_eq!(shared_ref_count, 1);
    }

    fn insert_checkpoint(
        conn: &Connection,
        id: &str,
        age_days: i64,
        stored_size: i64,
        trigger: &str,
        pinned: bool,
    ) {
        let created_at =
            (Utc::now() - Duration::days(age_days)).to_rfc3339_opts(SecondsFormat::Micros, true);
        conn.execute(
            "INSERT INTO checkpoints(
                checkpoint_id, message, created_at, pinned, total_size_bytes,
                file_count, engine_version, trigger, stored_size_bytes
             ) VALUES (?, 'test', ?, ?, ?, 1, 'rust-v2', ?, ?)",
            params![
                id,
                created_at,
                i64::from(pinned),
                stored_size,
                trigger,
                stored_size
            ],
        )
        .unwrap();
    }

    fn insert_legacy_checkpoint(conn: &Connection, id: &str, age_days: i64, size: i64) {
        let created_at =
            (Utc::now() - Duration::days(age_days)).to_rfc3339_opts(SecondsFormat::Micros, true);
        conn.execute(
            "INSERT INTO checkpoints(
                checkpoint_id, message, created_at, pinned, total_size_bytes,
                file_count, engine_version, trigger, stored_size_bytes
             ) VALUES (?, 'legacy', ?, 0, ?, 1, NULL, 'manual', ?)",
            params![id, created_at, size, size],
        )
        .unwrap();
    }
}
