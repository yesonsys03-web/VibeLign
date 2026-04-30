// === ANCHOR: BACKUP_CREATE_START ===
use crate::backup::cas;
use crate::backup::checkpoint::{CheckpointCreateMetadata, CreatedCheckpoint};
use crate::backup::disk;
use crate::backup::snapshot::{collect, SnapshotFile};
use crate::db::schema;
use chrono::{SecondsFormat, Utc};
use rusqlite::{params, Connection, OptionalExtension, Transaction};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Clone)]
struct LatestFile {
    hash: String,
    size: u64,
    object_hash: Option<String>,
}

#[derive(Debug, Clone)]
enum PlannedFileKind {
    Changed,
    Reused { object_hash: String },
}

#[derive(Debug, Clone)]
struct PlannedFile {
    snapshot: SnapshotFile,
    kind: PlannedFileKind,
}

#[derive(Debug, Clone)]
struct LatestSnapshot {
    checkpoint_id: String,
    files: HashMap<String, LatestFile>,
}

#[derive(Debug, Clone)]
struct CreatePlan {
    files: Vec<PlannedFile>,
    parent_checkpoint_id: Option<String>,
    original_size_bytes: u64,
    stored_size_bytes: u64,
    reused_file_count: usize,
    changed_file_count: usize,
    no_changes: bool,
}

pub fn create_with_metadata(
    root: &Path,
    message: &str,
    metadata: CheckpointCreateMetadata,
) -> Result<Option<CreatedCheckpoint>, String> {
    disk::ensure_min_free_space(root)?;
    let vibelign_dir = root.join(".vibelign");
    fs::create_dir_all(&vibelign_dir).map_err(|error| error.to_string())?;
    let db_path = vibelign_dir.join("vibelign.db");
    let mut conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    schema::initialize(&conn).map_err(|error| error.to_string())?;
    let snapshot_files = collect(root).map_err(|error| error.to_string())?;
    let plan = plan_checkpoint(&conn, snapshot_files)?;
    if plan.no_changes {
        return Ok(None);
    }

    let created_at = Utc::now().to_rfc3339_opts(SecondsFormat::Micros, true);
    let checkpoint_id = checkpoint_id_from_time(&created_at);
    let tx = conn.transaction().map_err(|error| error.to_string())?;
    insert_checkpoint(&tx, &checkpoint_id, message, &created_at, &metadata, &plan)?;
    let stored_size_bytes = insert_checkpoint_files(root, &tx, &checkpoint_id, &plan.files)?;
    update_checkpoint_stored_size(&tx, &checkpoint_id, stored_size_bytes)?;
    tx.commit().map_err(|error| error.to_string())?;

    let files = plan
        .files
        .into_iter()
        .map(|file| file.snapshot)
        .collect::<Vec<_>>();
    Ok(Some(CreatedCheckpoint {
        checkpoint_id,
        created_at,
        file_count: files.len(),
        total_size_bytes: plan.original_size_bytes,
        files,
    }))
}

fn plan_checkpoint(conn: &Connection, files: Vec<SnapshotFile>) -> Result<CreatePlan, String> {
    let latest = latest_snapshot(conn)?;
    let original_size_bytes = files.iter().map(|file| file.size).sum::<u64>();
    let no_changes = latest
        .as_ref()
        .map(|latest| snapshot_matches_latest(&files, &latest.files))
        .unwrap_or(false);
    if no_changes {
        return Ok(CreatePlan {
            files: Vec::new(),
            parent_checkpoint_id: latest.map(|latest| latest.checkpoint_id),
            original_size_bytes,
            stored_size_bytes: 0,
            reused_file_count: 0,
            changed_file_count: 0,
            no_changes: true,
        });
    }

    let latest_checkpoint_id = latest.as_ref().map(|latest| latest.checkpoint_id.clone());
    let latest_files = latest
        .as_ref()
        .map(|latest| &latest.files)
        .cloned()
        .unwrap_or_default();
    let mut planned = Vec::new();
    let mut stored_size_bytes = 0_u64;
    let mut reused_file_count = 0_usize;
    let mut changed_file_count = 0_usize;
    for file in files {
        let unchanged = latest_files.get(&file.relative_path).and_then(|latest| {
            if latest.hash == file.hash && latest.size == file.size {
                latest.object_hash.clone()
            } else {
                None
            }
        });
        let kind = if let Some(object_hash) = unchanged {
            reused_file_count += 1;
            PlannedFileKind::Reused { object_hash }
        } else {
            stored_size_bytes += file.size;
            changed_file_count += 1;
            PlannedFileKind::Changed
        };
        planned.push(PlannedFile {
            snapshot: file,
            kind,
        });
    }

    Ok(CreatePlan {
        files: planned,
        parent_checkpoint_id: latest_checkpoint_id,
        original_size_bytes,
        stored_size_bytes,
        reused_file_count,
        changed_file_count,
        no_changes: false,
    })
}

fn latest_snapshot(conn: &Connection) -> Result<Option<LatestSnapshot>, String> {
    let checkpoint_id: Option<String> = conn
        .query_row(
            "SELECT checkpoint_id FROM checkpoints
             WHERE engine_version = 'rust-v2'
             ORDER BY created_at DESC, checkpoint_id DESC LIMIT 1",
            [],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    let Some(checkpoint_id) = checkpoint_id else {
        return Ok(None);
    };
    let mut statement = conn
        .prepare(
            "SELECT relative_path, hash, size, object_hash
             FROM checkpoint_files WHERE checkpoint_id = ?",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(params![checkpoint_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                LatestFile {
                    hash: row.get(1)?,
                    size: row.get::<_, i64>(2)? as u64,
                    object_hash: row.get(3)?,
                },
            ))
        })
        .map_err(|error| error.to_string())?;
    let mut files = HashMap::new();
    for row in rows {
        let (relative_path, latest_file) = row.map_err(|error| error.to_string())?;
        files.insert(relative_path, latest_file);
    }
    Ok(Some(LatestSnapshot {
        checkpoint_id,
        files,
    }))
}

fn snapshot_matches_latest(
    files: &[SnapshotFile],
    latest_files: &HashMap<String, LatestFile>,
) -> bool {
    if files.len() != latest_files.len() {
        return false;
    }
    files.iter().all(|file| {
        latest_files
            .get(&file.relative_path)
            .map(|latest| latest.hash == file.hash && latest.size == file.size)
            .unwrap_or(false)
    })
}

fn insert_checkpoint(
    tx: &Transaction<'_>,
    checkpoint_id: &str,
    message: &str,
    created_at: &str,
    metadata: &CheckpointCreateMetadata,
    plan: &CreatePlan,
) -> Result<(), String> {
    let trigger = metadata
        .trigger
        .clone()
        .unwrap_or_else(|| "manual".to_string());
    tx.execute(
        "INSERT INTO checkpoints(
             checkpoint_id, message, created_at, pinned, total_size_bytes, file_count,
             engine_version, parent_checkpoint_id, trigger, git_commit_sha, git_commit_message,
             original_size_bytes, stored_size_bytes, reused_file_count, changed_file_count
         ) VALUES (?, ?, ?, 0, ?, ?, 'rust-v2', ?, ?, ?, ?, ?, ?, ?, ?)",
        params![
            checkpoint_id,
            message,
            created_at,
            plan.original_size_bytes as i64,
            plan.files.len() as i64,
            plan.parent_checkpoint_id,
            trigger,
            metadata.git_commit_sha,
            metadata.git_commit_message,
            plan.original_size_bytes as i64,
            plan.stored_size_bytes as i64,
            plan.reused_file_count as i64,
            plan.changed_file_count as i64,
        ],
    )
    .map_err(|error| error.to_string())?;
    Ok(())
}

fn insert_checkpoint_files(
    root: &Path,
    tx: &Transaction<'_>,
    checkpoint_id: &str,
    files: &[PlannedFile],
) -> Result<u64, String> {
    let mut stored_size_bytes = 0_u64;
    for file in files {
        let object_hash = match &file.kind {
            PlannedFileKind::Reused { object_hash } => {
                cas::increment_ref(tx, object_hash)?;
                object_hash.clone()
            }
            PlannedFileKind::Changed => {
                let object = cas::store_object(
                    root,
                    tx,
                    &file.snapshot.source_path,
                    &file.snapshot.hash,
                    file.snapshot.size,
                )?;
                stored_size_bytes += object.stored_size;
                object.hash
            }
        };
        tx.execute(
            "INSERT INTO checkpoint_files(
                 checkpoint_id, relative_path, hash, hash_algo, size, storage_path, object_hash
             ) VALUES (?, ?, ?, 'blake3', ?, ?, ?)",
            params![
                checkpoint_id,
                file.snapshot.relative_path,
                file.snapshot.hash,
                file.snapshot.size as i64,
                cas::storage_sentinel(&object_hash),
                object_hash,
            ],
        )
        .map_err(|error| error.to_string())?;
    }
    Ok(stored_size_bytes)
}

fn update_checkpoint_stored_size(
    tx: &Transaction<'_>,
    checkpoint_id: &str,
    stored_size_bytes: u64,
) -> Result<(), String> {
    tx.execute(
        "UPDATE checkpoints SET stored_size_bytes = ? WHERE checkpoint_id = ?",
        params![stored_size_bytes as i64, checkpoint_id],
    )
    .map_err(|error| error.to_string())?;
    Ok(())
}

fn checkpoint_id_from_time(created_at: &str) -> String {
    let compact: String = created_at
        .chars()
        .filter(|ch| ch.is_ascii_digit())
        .collect();
    format!("{}Z", &compact[..20.min(compact.len())])
}

#[cfg(test)]
mod tests {
    use super::create_with_metadata;
    use crate::backup::checkpoint::CheckpointCreateMetadata;
    use rusqlite::{params, Connection};

    #[test]
    fn records_incremental_metrics_and_reuses_unchanged_objects() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("same.txt"), "same\n").unwrap();
        std::fs::write(root.join("changing.txt"), "one\n").unwrap();
        create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::write(root.join("changing.txt"), "two\n").unwrap();

        let created = create_with_metadata(root, "second", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();

        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        let (original, stored, reused, changed): (i64, i64, i64, i64) = conn
            .query_row(
                "SELECT original_size_bytes, stored_size_bytes, reused_file_count, changed_file_count
                 FROM checkpoints WHERE checkpoint_id = ?",
                params![created.checkpoint_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
            )
            .unwrap();
        assert_eq!(original, 9);
        assert_eq!(stored, 4);
        assert_eq!(reused, 1);
        assert_eq!(changed, 1);

        let same_hash = blake3::hash(b"same\n").to_hex().to_string();
        let ref_count: i64 = conn
            .query_row(
                "SELECT ref_count FROM cas_objects WHERE hash = ?",
                params![same_hash],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(ref_count, 2);
    }

    #[test]
    fn preserves_no_changes_without_incrementing_refs() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("app.py"), "print(1)\n").unwrap();
        let first = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();

        let second =
            create_with_metadata(root, "second", CheckpointCreateMetadata::default()).unwrap();

        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        let checkpoint_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM checkpoints", [], |row| row.get(0))
            .unwrap();
        let ref_count: i64 = conn
            .query_row(
                "SELECT ref_count FROM cas_objects WHERE hash = (SELECT object_hash FROM checkpoint_files WHERE checkpoint_id = ?)",
                params![first.checkpoint_id],
                |row| row.get(0),
            )
            .unwrap();
        assert!(second.is_none());
        assert_eq!(checkpoint_count, 1);
        assert_eq!(ref_count, 1);
    }

    #[test]
    fn stores_decomposed_unicode_file_with_normalized_snapshot_key() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("e\u{301}.txt"), "accent\n").unwrap();

        let created = create_with_metadata(root, "unicode", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();

        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        let (relative_path, object_count): (String, i64) = conn
            .query_row(
                "SELECT f.relative_path, (SELECT COUNT(*) FROM cas_objects)
                 FROM checkpoint_files f WHERE f.checkpoint_id = ?",
                params![created.checkpoint_id],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(relative_path, "é.txt");
        assert_eq!(object_count, 1);
    }
}
// === ANCHOR: BACKUP_CREATE_END ===
