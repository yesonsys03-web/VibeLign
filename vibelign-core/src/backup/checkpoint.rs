use crate::backup::snapshot::{collect, SnapshotFile};
use crate::db::schema;
use crate::security::path_guard::resolve_under;
use chrono::{SecondsFormat, Utc};
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

fn checkpoint_id_from_time(created_at: &str) -> String {
    let compact: String = created_at
        .chars()
        .filter(|ch| ch.is_ascii_digit())
        .collect();
    format!("{}Z", &compact[..20.min(compact.len())])
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

pub fn create(root: &Path, message: &str) -> Result<Option<CreatedCheckpoint>, String> {
    let vibelign_dir = root.join(".vibelign");
    fs::create_dir_all(&vibelign_dir).map_err(|error| error.to_string())?;
    let db_path = vibelign_dir.join("vibelign.db");
    let mut conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    schema::initialize(&conn).map_err(|error| error.to_string())?;
    let files = collect(root).map_err(|error| error.to_string())?;
    if matches_latest_snapshot(&conn, &files)? {
        return Ok(None);
    }
    let created_at = Utc::now().to_rfc3339_opts(SecondsFormat::Micros, true);
    let checkpoint_id = checkpoint_id_from_time(&created_at);
    let total_size_bytes = files.iter().map(|file| file.size).sum::<u64>();
    let storage_root = vibelign_dir
        .join("rust_checkpoints")
        .join(&checkpoint_id)
        .join("files");
    fs::create_dir_all(&storage_root).map_err(|error| error.to_string())?;

    let tx = conn.transaction().map_err(|error| error.to_string())?;
    tx.execute(
        "INSERT INTO checkpoints(checkpoint_id, message, created_at, pinned, total_size_bytes, file_count) VALUES (?, ?, ?, 0, ?, ?)",
        params![checkpoint_id, message, created_at, total_size_bytes as i64, files.len() as i64],
    )
    .map_err(|error| error.to_string())?;
    for file in &files {
        let source_path = resolve_under(root, &file.relative_path)
            .ok_or_else(|| "source path escaped project root".to_string())?;
        let storage_path = resolve_under(&storage_root, &file.relative_path)
            .ok_or_else(|| "storage path escaped checkpoint root".to_string())?;
        if let Some(parent) = storage_path.parent() {
            fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        }
        fs::copy(&source_path, &storage_path).map_err(|error| error.to_string())?;
        let storage_text = storage_path
            .strip_prefix(root)
            .map_err(|error| error.to_string())?
            .components()
            .map(|component| component.as_os_str().to_string_lossy())
            .collect::<Vec<_>>()
            .join("/");
        tx.execute(
            "INSERT INTO checkpoint_files(checkpoint_id, relative_path, hash, hash_algo, size, storage_path) VALUES (?, ?, ?, 'blake3', ?, ?)",
            params![checkpoint_id, file.relative_path, file.hash, file.size as i64, storage_text],
        )
        .map_err(|error| error.to_string())?;
    }
    tx.commit().map_err(|error| error.to_string())?;

    Ok(Some(CreatedCheckpoint {
        checkpoint_id,
        created_at,
        file_count: files.len(),
        total_size_bytes,
        files,
    }))
}

fn matches_latest_snapshot(conn: &Connection, files: &[SnapshotFile]) -> Result<bool, String> {
    let latest_id: Option<String> = conn
        .query_row(
            "SELECT checkpoint_id FROM checkpoints ORDER BY created_at DESC, checkpoint_id DESC LIMIT 1",
            [],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    let Some(checkpoint_id) = latest_id else {
        return Ok(false);
    };
    let mut statement = conn
        .prepare(
            "SELECT relative_path, hash, size FROM checkpoint_files WHERE checkpoint_id = ? ORDER BY relative_path ASC",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(params![checkpoint_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i64>(2)? as u64,
            ))
        })
        .map_err(|error| error.to_string())?;
    let mut latest = Vec::new();
    for row in rows {
        latest.push(row.map_err(|error| error.to_string())?);
    }
    let current = files
        .iter()
        .map(|file| (file.relative_path.clone(), file.hash.clone(), file.size))
        .collect::<Vec<_>>();
    Ok(current == latest)
}

pub fn restore(root: &Path, checkpoint_id: &str) -> Result<(), String> {
    let db_path = root.join(".vibelign").join("vibelign.db");
    if !db_path.exists() {
        return Err("checkpoint database missing".to_string());
    }
    let conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    let exists: Option<i64> = conn
        .query_row(
            "SELECT 1 FROM checkpoints WHERE checkpoint_id = ?",
            params![checkpoint_id],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?;
    if exists.is_none() {
        return Err("checkpoint not found".to_string());
    }
    let mut statement = conn
        .prepare(
            "SELECT relative_path, storage_path, size FROM checkpoint_files WHERE checkpoint_id = ?",
        )
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map(params![checkpoint_id], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i64>(2)?,
            ))
        })
        .map_err(|error| error.to_string())?;
    let mut snapshot_files = Vec::new();
    for row in rows {
        snapshot_files.push(row.map_err(|error| error.to_string())?);
    }
    let snapshot_paths = snapshot_files
        .iter()
        .map(|(relative_path, _, _)| relative_path.clone())
        .collect::<std::collections::HashSet<_>>();
    for current in collect(root).map_err(|error| error.to_string())? {
        if snapshot_paths.contains(&current.relative_path) {
            continue;
        }
        let target = resolve_under(root, &current.relative_path)
            .ok_or_else(|| "current path escaped project root".to_string())?;
        if target.exists() {
            fs::remove_file(&target).map_err(|error| error.to_string())?;
            remove_empty_parents(root, target.parent());
        }
    }
    for (relative_path, storage_path, _size) in snapshot_files {
        let storage_root = root
            .join(".vibelign")
            .join("rust_checkpoints")
            .join(checkpoint_id)
            .join("files");
        let source = resolve_under(root, &storage_path)
            .ok_or_else(|| "storage path escaped project root".to_string())?;
        if !source.exists() {
            return Err("checkpoint file missing".to_string());
        }
        ensure_existing_path_has_no_symlink(&source)?;
        let canonical_source = source.canonicalize().map_err(|error| error.to_string())?;
        let canonical_storage_root = storage_root
            .canonicalize()
            .map_err(|error| error.to_string())?;
        if !canonical_source.starts_with(&canonical_storage_root) {
            return Err("checkpoint storage path escaped storage root".to_string());
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
    let conn = Connection::open(db_path).map_err(|error| error.to_string())?;
    let mut deleted = PruneResult { count: 0, bytes: 0 };
    for checkpoint in checkpoints.iter().skip(keep_latest) {
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
    use super::{create, prune, restore};

    #[test]
    fn creates_sqlite_checkpoint_record() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("app.py"), "print(1)\n").unwrap();

        let created = create(root, "hello").unwrap().unwrap();

        assert_eq!(created.file_count, 1);
        assert!(root.join(".vibelign/vibelign.db").exists());
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
        std::fs::write(&app, "print(2)\n").unwrap();
        let second = create(root, "second").unwrap().unwrap();

        let result = prune(root, 1).unwrap();

        assert_eq!(result.count, 1);
        let listed = super::list(root).unwrap();
        assert_eq!(listed.len(), 1);
        assert_eq!(listed[0].checkpoint_id, second.checkpoint_id);
        assert!(!root
            .join(".vibelign/rust_checkpoints")
            .join(first.checkpoint_id)
            .exists());
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
