use crate::backup::cas;
use crate::backup::snapshot::{collect, SnapshotFile};
use crate::db::schema;
use crate::security::path_guard::resolve_under;
use rusqlite::{params, Connection, OptionalExtension};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct CreatedCheckpoint {
    pub checkpoint_id: String,
    pub created_at: String,
    pub file_count: usize,
    pub total_size_bytes: u64,
    pub files: Vec<SnapshotFile>,
}

#[derive(Debug, Clone, Default)]
pub struct CheckpointCreateMetadata {
    pub trigger: Option<String>,
    pub git_commit_sha: Option<String>,
    pub git_commit_message: Option<String>,
}

#[derive(Debug, Clone)]
pub struct ListedCheckpoint {
    pub checkpoint_id: String,
    pub created_at: String,
    pub message: String,
    pub file_count: usize,
    pub total_size_bytes: u64,
    pub pinned: bool,
}

#[derive(Debug, Clone, Copy)]
pub struct PruneResult {
    pub count: usize,
    pub bytes: u64,
}

pub fn list(root: &Path) -> Result<Vec<ListedCheckpoint>, String> {
    let db_path = root.join(".vibelign").join("vibelign.db");
    if !db_path.exists() {
        return Ok(Vec::new());
    }
    let conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    schema::initialize(&conn).map_err(|error| error.to_string())?;
    let has_table: Option<i64> = conn
        .query_row(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'checkpoints'",
            [],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    if has_table.is_none() {
        return Ok(Vec::new());
    }
    let mut statement = conn
        .prepare(
            "SELECT checkpoint_id, created_at, message, file_count, total_size_bytes, pinned
             FROM checkpoints ORDER BY created_at DESC, checkpoint_id DESC",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            Ok(ListedCheckpoint {
                checkpoint_id: row.get(0)?,
                created_at: row.get(1)?,
                message: row.get(2)?,
                file_count: row.get::<_, i64>(3)? as usize,
                total_size_bytes: row.get::<_, i64>(4)? as u64,
                pinned: row.get::<_, i64>(5)? != 0,
            })
        })
        .map_err(|error| error.to_string())?;
    let mut checkpoints = Vec::new();
    for row in rows {
        checkpoints.push(row.map_err(|error| error.to_string())?);
    }
    Ok(checkpoints)
}

pub fn create_with_metadata(
    root: &Path,
    message: &str,
    metadata: CheckpointCreateMetadata,
) -> Result<Option<CreatedCheckpoint>, String> {
    crate::backup::create::create_with_metadata(root, message, metadata)
}

pub fn restore(root: &Path, checkpoint_id: &str) -> Result<(), String> {
    let db_path = root.join(".vibelign").join("vibelign.db");
    if !db_path.exists() {
        return Err("checkpoint database missing".to_string());
    }
    let conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    let engine_version: Option<Option<String>> = conn
        .query_row(
            "SELECT engine_version FROM checkpoints WHERE checkpoint_id = ?",
            params![checkpoint_id],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    let Some(engine_version) = engine_version else {
        return Err("checkpoint not found".to_string());
    };
    let is_v2 = engine_version.as_deref() == Some("rust-v2");
    let mut statement = conn
        .prepare(
            "SELECT relative_path, storage_path, size, object_hash FROM checkpoint_files WHERE checkpoint_id = ?",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(params![checkpoint_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i64>(2)?,
                row.get::<_, Option<String>>(3)?,
            ))
        })
        .map_err(|error| error.to_string())?;
    let mut snapshot_files = Vec::new();
    for row in rows {
        snapshot_files.push(row.map_err(|error| error.to_string())?);
    }
    let snapshot_paths = snapshot_files
        .iter()
        .map(|(relative_path, _, _, _)| relative_path.clone())
        .collect::<std::collections::HashSet<_>>();
    for current in collect(root).map_err(|error| error.to_string())? {
        if snapshot_paths.contains(&current.relative_path) {
            continue;
        }
        let target = resolve_under(root, &current.relative_path)
            .ok_or_else(|| "current path escaped project root".to_string())?;
        if target.exists() {
            ensure_existing_path_has_no_symlink(&target)?;
            fs::remove_file(&target).map_err(|error| error.to_string())?;
            remove_empty_parents(root, target.parent());
        }
    }
    for (relative_path, storage_path, _size, object_hash) in snapshot_files {
        let source = if is_v2 {
            let hash = object_hash.ok_or_else(|| "backup object hash missing".to_string())?;
            cas::resolve_object(root, &conn, &hash)?
        } else {
            resolve_under(root, &storage_path)
                .ok_or_else(|| "storage path escaped project root".to_string())?
        };
        if !source.exists() {
            return Err("checkpoint file missing".to_string());
        }
        ensure_existing_path_has_no_symlink(&source)?;
        if !is_v2 {
            let storage_root = root
                .join(".vibelign")
                .join("rust_checkpoints")
                .join(checkpoint_id)
                .join("files");
            let canonical_source = source.canonicalize().map_err(|error| error.to_string())?;
            let canonical_storage_root = storage_root
                .canonicalize()
                .map_err(|error| error.to_string())?;
            if !canonical_source.starts_with(&canonical_storage_root) {
                return Err("checkpoint storage path escaped storage root".to_string());
            }
        }
        let target = resolve_under(root, &relative_path)
            .ok_or_else(|| "restore path escaped project root".to_string())?;
        if let Some(parent) = target.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
            ensure_existing_path_has_no_symlink(parent)?;
        }
        if target.exists() || target.symlink_metadata().is_ok() {
            ensure_existing_path_has_no_symlink(&target)?;
        }
        let was_readonly = target
            .metadata()
            .map(|metadata| metadata.permissions().readonly())
            .unwrap_or(false);
        if was_readonly {
            set_readonly(&target, false)?;
        }
        fs::copy(source, &target).map_err(|error| error.to_string())?;
        if was_readonly {
            set_readonly(&target, true)?;
        }
    }
    Ok(())
}

fn set_readonly(path: &Path, readonly: bool) -> Result<(), String> {
    let mut permissions = path
        .metadata()
        .map_err(|error| error.to_string())?
        .permissions();
    permissions.set_readonly(readonly);
    fs::set_permissions(path, permissions).map_err(|error| error.to_string())
}

fn ensure_existing_path_has_no_symlink(path: &Path) -> Result<(), String> {
    match fs::symlink_metadata(path) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err("restore path contains symlink".to_string());
        }
        Ok(_) => {}
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => return Err(error.to_string()),
    }
    let mut current = path;
    let mut stack = Vec::new();
    while let Some(parent) = current.parent() {
        stack.push(current);
        current = parent;
        if parent == current {
            break;
        }
    }
    stack.reverse();
    for component_path in stack {
        match fs::symlink_metadata(component_path) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err("restore path contains symlink".to_string());
            }
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.to_string()),
        }
    }
    Ok(())
}

pub fn prune(root: &Path, keep_latest: usize) -> Result<PruneResult, String> {
    let checkpoints = list(root)?;
    if checkpoints.len() <= keep_latest {
        return Ok(PruneResult { count: 0, bytes: 0 });
    }
    let db_path = root.join(".vibelign").join("vibelign.db");
    let mut conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    let mut deleted = PruneResult { count: 0, bytes: 0 };
    for checkpoint in checkpoints.iter().skip(keep_latest) {
        let engine_version: Option<String> = conn
            .query_row(
                "SELECT engine_version FROM checkpoints WHERE checkpoint_id = ?",
                params![checkpoint.checkpoint_id],
                |row| row.get(0),
            )
            .optional()
            .map_err(|error| error.to_string())?
            .flatten();
        let is_v2 = engine_version.as_deref() == Some("rust-v2");
        if is_v2 {
            let mut statement = conn
                .prepare(
                    "SELECT object_hash FROM checkpoint_files
                     WHERE checkpoint_id = ? AND object_hash IS NOT NULL",
                )
                .map_err(|error| error.to_string())?;
            let rows = statement
                .query_map(params![checkpoint.checkpoint_id], |row| {
                    row.get::<_, String>(0)
                })
                .map_err(|error| error.to_string())?;
            let mut object_hashes = Vec::new();
            for row in rows {
                object_hashes.push(row.map_err(|error| error.to_string())?);
            }
            drop(statement);
            let tx = conn.transaction().map_err(|error| error.to_string())?;
            for object_hash in object_hashes {
                cas::decrement_ref(&tx, &object_hash)?;
            }
            tx.execute(
                "DELETE FROM checkpoint_files WHERE checkpoint_id = ?",
                params![checkpoint.checkpoint_id],
            )
            .map_err(|error| error.to_string())?;
            tx.execute(
                "DELETE FROM checkpoints WHERE checkpoint_id = ?",
                params![checkpoint.checkpoint_id],
            )
            .map_err(|error| error.to_string())?;
            tx.commit().map_err(|error| error.to_string())?;
            cas::prune_unreferenced(root, &conn)?;
        } else {
            let storage_dir = root
                .join(".vibelign")
                .join("rust_checkpoints")
                .join(&checkpoint.checkpoint_id);
            if storage_dir.exists() {
                fs::remove_dir_all(storage_dir).map_err(|error| error.to_string())?;
            }
            conn.execute(
                "DELETE FROM checkpoint_files WHERE checkpoint_id = ?",
                params![checkpoint.checkpoint_id],
            )
            .map_err(|error| error.to_string())?;
            conn.execute(
                "DELETE FROM checkpoints WHERE checkpoint_id = ?",
                params![checkpoint.checkpoint_id],
            )
            .map_err(|error| error.to_string())?;
        }
        deleted.count += 1;
        deleted.bytes += checkpoint.total_size_bytes;
    }
    Ok(deleted)
}

fn remove_empty_parents(root: &Path, mut parent: Option<&Path>) {
    while let Some(path) = parent {
        if path == root || !path.exists() {
            break;
        }
        if fs::remove_dir(path).is_err() {
            break;
        }
        parent = path.parent();
    }
}

#[cfg(test)]
mod tests {
    use super::{
        create_with_metadata, prune, restore, CheckpointCreateMetadata, CreatedCheckpoint,
    };
    use rusqlite::{params, Connection};
    use std::path::Path;

    fn create(root: &Path, message: &str) -> Result<Option<CreatedCheckpoint>, String> {
        create_with_metadata(root, message, CheckpointCreateMetadata::default())
    }

    #[test]
    fn creates_sqlite_checkpoint_record() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("app.py"), "print(1)\n").unwrap();

        let created = create(root, "hello").unwrap().unwrap();

        assert_eq!(created.file_count, 1);
        assert!(root.join(".vibelign/vibelign.db").exists());
        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        let (engine_version, storage_path, object_hash): (String, String, String) = conn
            .query_row(
                "SELECT c.engine_version, f.storage_path, f.object_hash
                 FROM checkpoints c
                 JOIN checkpoint_files f ON f.checkpoint_id = c.checkpoint_id
                 WHERE c.checkpoint_id = ?",
                params![created.checkpoint_id],
                |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
            )
            .unwrap();
        assert_eq!(engine_version, "rust-v2");
        assert_eq!(storage_path, format!("cas:{object_hash}"));
        assert_eq!(
            conn.query_row(
                "SELECT ref_count FROM cas_objects WHERE hash = ?",
                params![object_hash],
                |row| row.get::<_, i64>(0),
            )
            .unwrap(),
            1
        );
    }

    #[test]
    fn lists_created_checkpoint_record() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("app.py"), "print(1)\n").unwrap();

        let created = create(root, "hello").unwrap().unwrap();
        let listed = super::list(root).unwrap();

        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].checkpoint_id, created.checkpoint_id);
        assert_eq!(listed[0].message, "hello");
    }

    #[test]
    fn restores_checkpoint_files_and_removes_new_files() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let app = root.join("app.py");
        std::fs::write(&app, "print(1)\n").unwrap();
        let created = create(root, "first").unwrap().unwrap();

        std::fs::write(&app, "print(2)\n").unwrap();
        std::fs::write(root.join("extra.txt"), "extra\n").unwrap();
        restore(root, &created.checkpoint_id).unwrap();

        assert_eq!(std::fs::read_to_string(app).unwrap(), "print(1)\n");
        assert!(!root.join("extra.txt").exists());
    }

    #[test]
    fn prunes_old_checkpoint_rows_and_storage() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let app = root.join("app.py");
        std::fs::write(&app, "print(1)\n").unwrap();
        let first = create(root, "first").unwrap().unwrap();
        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        let first_object_hash: String = conn
            .query_row(
                "SELECT object_hash FROM checkpoint_files WHERE checkpoint_id = ?",
                params![first.checkpoint_id],
                |row| row.get(0),
            )
            .unwrap();
        std::fs::write(&app, "print(2)\n").unwrap();
        let second = create(root, "second").unwrap().unwrap();

        let result = prune(root, 1).unwrap();

        assert_eq!(result.count, 1);
        let listed = super::list(root).unwrap();
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].checkpoint_id, second.checkpoint_id);
        assert!(conn
            .query_row(
                "SELECT 1 FROM cas_objects WHERE hash = ?",
                params![first_object_hash],
                |row| row.get::<_, i64>(0),
            )
            .is_err());
    }

    #[test]
    fn reuses_identical_content_across_checkpoints() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let shared = root.join("shared.txt");
        let changing = root.join("changing.txt");
        std::fs::write(&shared, "same\n").unwrap();
        std::fs::write(&changing, "one\n").unwrap();
        create(root, "first").unwrap().unwrap();
        std::fs::write(&changing, "two\n").unwrap();

        create(root, "second").unwrap().unwrap();

        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        let shared_hash = blake3::hash(b"same\n").to_hex().to_string();
        let ref_count: i64 = conn
            .query_row(
                "SELECT ref_count FROM cas_objects WHERE hash = ?",
                params![shared_hash],
                |row| row.get(0),
            )
            .unwrap();
        assert_eq!(ref_count, 2);
        let object_count: i64 = conn
            .query_row("SELECT COUNT(*) FROM cas_objects", [], |row| row.get(0))
            .unwrap();
        assert_eq!(object_count, 3);
    }

    #[test]
    fn skips_checkpoint_when_snapshot_has_not_changed() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("app.py"), "print(1)\n").unwrap();

        let first = create(root, "first").unwrap();
        let second = create(root, "second").unwrap();

        assert!(first.is_some());
        assert!(second.is_none());
        assert_eq!(super::list(root).unwrap().len(), 1);
    }

    #[cfg(unix)]
    #[test]
    fn restore_rejects_symlink_target() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let app = root.join("app.py");
        let outside = root.join("outside.txt");
        std::fs::write(&app, "print(1)\n").unwrap();
        std::fs::write(&outside, "outside\n").unwrap();
        let created = create(root, "first").unwrap().unwrap();
        std::fs::remove_file(&app).unwrap();
        std::os::unix::fs::symlink(&outside, &app).unwrap();

        let error = restore(root, &created.checkpoint_id).unwrap_err();

        assert!(error.contains("symlink"));
        assert_eq!(std::fs::read_to_string(outside).unwrap(), "outside\n");
    }

    #[cfg(unix)]
    #[test]
    fn symlink_guard_rejects_path_itself() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let outside = root.join("outside.txt");
        std::fs::write(&outside, "outside\n").unwrap();
        let symlink = root.join("link.txt");
        std::os::unix::fs::symlink(&outside, &symlink).unwrap();

        let error = super::ensure_existing_path_has_no_symlink(&symlink).unwrap_err();

        assert!(error.contains("symlink"));
        assert_eq!(std::fs::read_to_string(outside).unwrap(), "outside\n");
    }

    #[test]
    fn restore_overwrites_readonly_file_and_preserves_readonly_state() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let app = root.join("app.py");
        std::fs::write(&app, "print(1)\n").unwrap();
        let created = create(root, "first").unwrap().unwrap();
        std::fs::write(&app, "print(2)\n").unwrap();
        let mut permissions = app.metadata().unwrap().permissions();
        permissions.set_readonly(true);
        std::fs::set_permissions(&app, permissions).unwrap();

        restore(root, &created.checkpoint_id).unwrap();

        assert_eq!(std::fs::read_to_string(&app).unwrap(), "print(1)\n");
        assert!(app.metadata().unwrap().permissions().readonly());
    }
}
