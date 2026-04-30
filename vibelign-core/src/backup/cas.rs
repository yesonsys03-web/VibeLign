// === ANCHOR: BACKUP_CAS_START ===
use crate::security::path_guard::resolve_under;
use rusqlite::{params, Connection, OptionalExtension};
use std::fs;
use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone)]
#[allow(dead_code)]
pub struct CasObject {
    pub hash: String,
    pub storage_path: String,
    pub size: u64,
    pub ref_count: u32,
}

#[allow(dead_code)]
pub fn cas_enabled() -> bool {
    true
}

pub fn storage_sentinel(hash: &str) -> String {
    format!("cas:{hash}")
}

pub fn store_object(
    root: &Path,
    conn: &Connection,
    source: &Path,
    hash: &str,
    size: u64,
) -> Result<CasObject, String> {
    validate_hash(hash)?;
    reject_symlink(source)?;
    let object_path = object_path(root, hash)?;
    if let Some(parent) = object_path.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        reject_object_store_symlink_ancestry(root, parent)?;
    }
    write_object_if_missing(source, &object_path, hash)?;
    verify_file_content(&object_path, hash, size)?;
    let storage_path = root_relative_path(root, &object_path)?;
    conn.execute(
        "INSERT INTO cas_objects(hash, storage_path, ref_count, hash_algo, size, backend)
         VALUES (?, ?, 1, 'blake3', ?, 'local')
         ON CONFLICT(hash) DO UPDATE SET ref_count = ref_count + 1",
        params![hash, storage_path, size as i64],
    )
    .map_err(|error| error.to_string())?;
    object_from_row(conn, hash)
}

pub fn resolve_object(root: &Path, conn: &Connection, hash: &str) -> Result<PathBuf, String> {
    validate_hash(hash)?;
    let storage_path: String = conn
        .query_row(
            "SELECT storage_path FROM cas_objects WHERE hash = ?",
            params![hash],
            |row| row.get(0),
        )
        .optional()
        .map_err(|error| error.to_string())?
        .ok_or_else(|| "backup object missing from database".to_string())?;
    let source = resolve_under(root, &storage_path)
        .ok_or_else(|| "backup object path escaped project root".to_string())?;
    if !source.exists() {
        return Err("backup object file missing".to_string());
    }
    reject_symlink(&source)?;
    let canonical_source = source.canonicalize().map_err(|error| error.to_string())?;
    let object_root = root.join(".vibelign").join("rust_objects");
    let canonical_root = object_root
        .canonicalize()
        .map_err(|error| error.to_string())?;
    if !canonical_source.starts_with(canonical_root) {
        return Err("backup object path escaped object store".to_string());
    }
    Ok(source)
}

#[allow(dead_code)]
pub fn increment_ref(conn: &Connection, hash: &str) -> Result<(), String> {
    validate_hash(hash)?;
    let changed = conn
        .execute(
            "UPDATE cas_objects SET ref_count = ref_count + 1 WHERE hash = ?",
            params![hash],
        )
        .map_err(|error| error.to_string())?;
    if changed == 0 {
        return Err("backup object missing from database".to_string());
    }
    Ok(())
}

pub fn decrement_ref(conn: &Connection, hash: &str) -> Result<(), String> {
    validate_hash(hash)?;
    conn.execute(
        "UPDATE cas_objects
         SET ref_count = CASE WHEN ref_count > 0 THEN ref_count - 1 ELSE 0 END
         WHERE hash = ?",
        params![hash],
    )
    .map_err(|error| error.to_string())?;
    Ok(())
}

pub fn prune_unreferenced(root: &Path, conn: &Connection) -> Result<usize, String> {
    let mut statement = conn
        .prepare("SELECT hash, storage_path FROM cas_objects WHERE ref_count = 0")
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })
        .map_err(|error| error.to_string())?;
    let mut objects = Vec::new();
    for row in rows {
        objects.push(row.map_err(|error| error.to_string())?);
    }
    drop(statement);

    let mut pruned = 0;
    for (hash, storage_path) in objects {
        validate_hash(&hash)?;
        let object_path = object_path(root, &hash)?;
        let expected_storage_path = root_relative_path(root, &object_path)?;
        if storage_path != expected_storage_path {
            return Err("backup object metadata does not match object hash".to_string());
        }
        if object_path.exists() {
            reject_object_store_symlink_ancestry(root, &object_path)?;
            fs::remove_file(&object_path).map_err(|error| error.to_string())?;
            remove_empty_object_dirs(root, object_path.parent());
        }
        conn.execute("DELETE FROM cas_objects WHERE hash = ?", params![hash])
            .map_err(|error| error.to_string())?;
        pruned += 1;
    }
    Ok(pruned)
}

fn object_from_row(conn: &Connection, hash: &str) -> Result<CasObject, String> {
    conn.query_row(
        "SELECT hash, storage_path, size, ref_count FROM cas_objects WHERE hash = ?",
        params![hash],
        |row| {
            Ok(CasObject {
                hash: row.get(0)?,
                storage_path: row.get(1)?,
                size: row.get::<_, i64>(2)? as u64,
                ref_count: row.get::<_, i64>(3)? as u32,
            })
        },
    )
    .map_err(|error| error.to_string())
}

fn object_path(root: &Path, hash: &str) -> Result<PathBuf, String> {
    let prefix_a = hash
        .get(0..2)
        .ok_or_else(|| "backup object hash is too short".to_string())?;
    let prefix_b = hash
        .get(2..4)
        .ok_or_else(|| "backup object hash is too short".to_string())?;
    Ok(root
        .join(".vibelign")
        .join("rust_objects")
        .join("blake3")
        .join(prefix_a)
        .join(prefix_b)
        .join(hash))
}

fn write_object_if_missing(source: &Path, destination: &Path, hash: &str) -> Result<(), String> {
    if destination.exists() {
        return Ok(());
    }
    let temp_path = create_temp_object_file(source, destination, hash)?;
    match fs::rename(&temp_path, destination) {
        Ok(()) => Ok(()),
        Err(error) if destination.exists() => {
            let _ = fs::remove_file(&temp_path);
            let _ = error;
            Ok(())
        }
        Err(error) => {
            let _ = fs::remove_file(&temp_path);
            Err(error.to_string())
        }
    }
}

fn create_temp_object_file(
    source: &Path,
    destination: &Path,
    hash: &str,
) -> Result<PathBuf, String> {
    let parent = destination
        .parent()
        .ok_or_else(|| "backup object path has no parent".to_string())?;
    for attempt in 0..16_u8 {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|error| error.to_string())?
            .as_nanos();
        let temp_path = parent.join(format!(
            ".{hash}.{}.{}.tmp",
            std::process::id(),
            nonce + u128::from(attempt)
        ));
        let mut destination_file = match OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp_path)
        {
            Ok(file) => file,
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error.to_string()),
        };
        let mut source_file = fs::File::open(source).map_err(|error| error.to_string())?;
        std::io::copy(&mut source_file, &mut destination_file)
            .map_err(|error| error.to_string())?;
        destination_file
            .flush()
            .map_err(|error| error.to_string())?;
        return Ok(temp_path);
    }
    Err("could not create temporary backup object file".to_string())
}

fn verify_file_content(path: &Path, expected_hash: &str, expected_size: u64) -> Result<(), String> {
    let metadata = path.metadata().map_err(|error| error.to_string())?;
    if metadata.len() != expected_size {
        return Err("backup object changed while being stored".to_string());
    }
    let actual_hash = hash_file(path)?;
    if actual_hash != expected_hash {
        return Err("backup object hash mismatch while being stored".to_string());
    }
    Ok(())
}

fn hash_file(path: &Path) -> Result<String, String> {
    let mut file = fs::File::open(path).map_err(|error| error.to_string())?;
    let mut hasher = blake3::Hasher::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer).map_err(|error| error.to_string())?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(hasher.finalize().to_hex().to_string())
}

fn root_relative_path(root: &Path, path: &Path) -> Result<String, String> {
    Ok(path
        .strip_prefix(root)
        .map_err(|error| error.to_string())?
        .components()
        .map(|component| component.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/"))
}

fn validate_hash(hash: &str) -> Result<(), String> {
    if hash.len() < 4 || !hash.chars().all(|ch| ch.is_ascii_hexdigit()) {
        return Err("backup object hash is invalid".to_string());
    }
    Ok(())
}

fn reject_symlink(path: &Path) -> Result<(), String> {
    let metadata = fs::symlink_metadata(path).map_err(|error| error.to_string())?;
    if metadata.file_type().is_symlink() {
        return Err("backup object path contains symlink".to_string());
    }
    Ok(())
}

fn reject_object_store_symlink_ancestry(root: &Path, path: &Path) -> Result<(), String> {
    let object_root = root.join(".vibelign").join("rust_objects");
    let relative = path
        .strip_prefix(&object_root)
        .map_err(|_| "backup object path escaped object store".to_string())?;
    let mut current = object_root;
    match fs::symlink_metadata(&current) {
        Ok(metadata) if metadata.file_type().is_symlink() => {
            return Err("backup object path contains symlink".to_string());
        }
        Ok(_) => {}
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
        Err(error) => return Err(error.to_string()),
    }
    for component in relative.components() {
        current = current.join(component.as_os_str());
        match fs::symlink_metadata(&current) {
            Ok(metadata) if metadata.file_type().is_symlink() => {
                return Err("backup object path contains symlink".to_string());
            }
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.to_string()),
        }
    }
    Ok(())
}

fn remove_empty_object_dirs(root: &Path, mut parent: Option<&Path>) {
    let stop = root.join(".vibelign").join("rust_objects");
    while let Some(path) = parent {
        if path == stop || !path.exists() {
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
    use super::{decrement_ref, prune_unreferenced, resolve_object, store_object};
    use crate::db::schema;
    use rusqlite::{params, Connection};

    #[test]
    fn stores_identical_content_once_and_tracks_refs() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let first = root.join("a.txt");
        let second = root.join("b.txt");
        std::fs::write(&first, "same").unwrap();
        std::fs::write(&second, "same").unwrap();
        let hash = blake3::hash(b"same").to_hex().to_string();

        let first_object = store_object(root, &conn, &first, &hash, 4).unwrap();
        let second_object = store_object(root, &conn, &second, &hash, 4).unwrap();

        assert_eq!(first_object.storage_path, second_object.storage_path);
        assert_eq!(second_object.ref_count, 2);
        assert!(root.join(first_object.storage_path).exists());
    }

    #[test]
    fn stores_zero_byte_file_as_real_object() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let empty = root.join("empty.txt");
        std::fs::write(&empty, []).unwrap();
        let hash = blake3::hash(&[]).to_hex().to_string();

        let object = store_object(root, &conn, &empty, &hash, 0).unwrap();
        let resolved = resolve_object(root, &conn, &hash).unwrap();

        assert_eq!(object.size, 0);
        assert_eq!(std::fs::metadata(resolved).unwrap().len(), 0);
    }

    #[test]
    fn prunes_only_unreferenced_objects() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let file = root.join("a.txt");
        std::fs::write(&file, "content").unwrap();
        let hash = blake3::hash(b"content").to_hex().to_string();
        let object = store_object(root, &conn, &file, &hash, 7).unwrap();

        assert_eq!(prune_unreferenced(root, &conn).unwrap(), 0);
        decrement_ref(&conn, &hash).unwrap();
        assert_eq!(prune_unreferenced(root, &conn).unwrap(), 1);

        assert!(!root.join(object.storage_path).exists());
    }

    #[test]
    fn rejects_store_when_claimed_hash_does_not_match_bytes() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let file = root.join("a.txt");
        std::fs::write(&file, "actual").unwrap();
        let wrong_hash = blake3::hash(b"different").to_hex().to_string();

        let error = store_object(root, &conn, &file, &wrong_hash, 6).unwrap_err();

        assert!(error.contains("hash mismatch"));
    }

    #[test]
    fn rejects_prune_when_stored_path_does_not_match_hash_layout() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let hash = blake3::hash(b"content").to_hex().to_string();
        conn.execute(
            "INSERT INTO cas_objects(hash, storage_path, ref_count, hash_algo, size, backend)
             VALUES (?, 'app.py', 0, 'blake3', 7, 'local')",
            params![hash],
        )
        .unwrap();

        let error = prune_unreferenced(root, &conn).unwrap_err();

        assert!(error.contains("metadata does not match"));
    }
}
// === ANCHOR: BACKUP_CAS_END ===
