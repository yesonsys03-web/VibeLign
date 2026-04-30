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
    pub stored_size: u64,
    pub ref_count: u32,
}

#[derive(Debug, Clone)]
struct ObjectStorage {
    compression: String,
    stored_size: u64,
    original_size: u64,
}

#[derive(Debug, Clone, Copy)]
pub struct PrunedCasObjects {
    pub count: usize,
    pub bytes: u64,
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
    let existing_storage = object_storage_from_db(conn, hash)?;
    let storage = match existing_storage.as_ref() {
        Some(storage) => storage.clone(),
        None => write_object_if_missing(source, &object_path, hash, size)?,
    };
    verify_file_content(&object_path, hash, size, &storage.compression)?;
    if existing_storage.is_some() {
        increment_ref(conn, hash)?;
    } else {
        let storage_path = root_relative_path(root, &object_path)?;
        conn.execute(
            "INSERT INTO cas_objects(
                 hash, storage_path, ref_count, hash_algo, size, backend, compression, stored_size
             ) VALUES (?, ?, 1, 'blake3', ?, 'local', ?, ?)",
            params![
                hash,
                storage_path,
                storage.original_size as i64,
                storage.compression,
                storage.stored_size as i64,
            ],
        )
        .map_err(|error| error.to_string())?;
    }
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

pub fn restore_object_to(
    root: &Path,
    conn: &Connection,
    hash: &str,
    target: &Path,
) -> Result<(), String> {
    validate_hash(hash)?;
    let source = resolve_object(root, conn, hash)?;
    let storage = object_storage_from_db(conn, hash)?
        .ok_or_else(|| "backup object missing from database".to_string())?;
    let temp_path = create_restore_temp_file(target)?;
    match storage.compression.as_str() {
        "none" => {
            fs::copy(&source, &temp_path).map_err(|error| {
                let _ = fs::remove_file(&temp_path);
                error.to_string()
            })?;
        }
        "zstd" => {
            let source_file = fs::File::open(&source).map_err(|error| error.to_string())?;
            let mut target_file = fs::File::create(&temp_path).map_err(|error| {
                let _ = fs::remove_file(&temp_path);
                error.to_string()
            })?;
            zstd::stream::copy_decode(source_file, &mut target_file).map_err(|error| {
                let _ = fs::remove_file(&temp_path);
                error.to_string()
            })?;
            target_file.flush().map_err(|error| {
                let _ = fs::remove_file(&temp_path);
                error.to_string()
            })?;
        }
        _ => {
            let _ = fs::remove_file(&temp_path);
            return Err("backup object compression is unsupported".to_string());
        }
    }
    verify_file_content(&temp_path, hash, storage.original_size, "none").map_err(|error| {
        let _ = fs::remove_file(&temp_path);
        error
    })?;
    replace_target_with_temp(target, &temp_path)?;
    Ok(())
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
    Ok(prune_unreferenced_detailed(root, conn)?.count)
}

pub fn prune_unreferenced_detailed(
    root: &Path,
    conn: &Connection,
) -> Result<PrunedCasObjects, String> {
    let mut statement = conn
        .prepare("SELECT hash, storage_path, stored_size FROM cas_objects WHERE ref_count = 0")
        .map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            Ok((
                row.get::<_, String>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i64>(2)?.max(0) as u64,
            ))
        })
        .map_err(|error| error.to_string())?;
    let mut objects = Vec::new();
    for row in rows {
        objects.push(row.map_err(|error| error.to_string())?);
    }
    drop(statement);

    let mut pruned = PrunedCasObjects { count: 0, bytes: 0 };
    for (hash, storage_path, size) in objects {
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
        pruned.count += 1;
        pruned.bytes += size;
    }
    Ok(pruned)
}

fn object_from_row(conn: &Connection, hash: &str) -> Result<CasObject, String> {
    conn.query_row(
        "SELECT hash, storage_path, size, stored_size, ref_count FROM cas_objects WHERE hash = ?",
        params![hash],
        |row| {
            Ok(CasObject {
                hash: row.get(0)?,
                storage_path: row.get(1)?,
                size: row.get::<_, i64>(2)? as u64,
                stored_size: row.get::<_, i64>(3)? as u64,
                ref_count: row.get::<_, i64>(4)? as u32,
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

fn create_restore_temp_file(target: &Path) -> Result<PathBuf, String> {
    let parent = target
        .parent()
        .ok_or_else(|| "restore target path has no parent".to_string())?;
    let name = target
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or("restore");
    for attempt in 0..16_u8 {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|error| error.to_string())?
            .as_nanos();
        let temp_path = parent.join(format!(
            ".{name}.restore.{}.{}.tmp",
            std::process::id(),
            nonce + u128::from(attempt)
        ));
        match OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp_path)
        {
            Ok(_) => return Ok(temp_path),
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => continue,
            Err(error) => return Err(error.to_string()),
        }
    }
    Err("could not create temporary restore file".to_string())
}

#[cfg(not(windows))]
fn replace_target_with_temp(target: &Path, temp_path: &Path) -> Result<(), String> {
    fs::rename(temp_path, target).map_err(|error| {
        let _ = fs::remove_file(temp_path);
        error.to_string()
    })
}

#[cfg(windows)]
fn replace_target_with_temp(target: &Path, temp_path: &Path) -> Result<(), String> {
    if target.exists() {
        fs::remove_file(target).map_err(|error| {
            let _ = fs::remove_file(temp_path);
            error.to_string()
        })?;
    }
    fs::rename(temp_path, target).map_err(|error| {
        let _ = fs::remove_file(temp_path);
        error.to_string()
    })
}

fn object_storage_from_db(conn: &Connection, hash: &str) -> Result<Option<ObjectStorage>, String> {
    conn.query_row(
        "SELECT compression, stored_size, size FROM cas_objects WHERE hash = ?",
        params![hash],
        |row| {
            Ok(ObjectStorage {
                compression: row.get(0)?,
                stored_size: row.get::<_, i64>(1)?.max(0) as u64,
                original_size: row.get::<_, i64>(2)?.max(0) as u64,
            })
        },
    )
    .optional()
    .map_err(|error| error.to_string())
}

fn write_object_if_missing(
    source: &Path,
    destination: &Path,
    hash: &str,
    size: u64,
) -> Result<ObjectStorage, String> {
    if destination.exists() {
        return infer_existing_object_storage(destination, hash, size);
    }
    let (temp_path, storage) = create_temp_object_file(source, destination, hash, size)?;
    match fs::rename(&temp_path, destination) {
        Ok(()) => Ok(storage),
        Err(error) if destination.exists() => {
            let _ = fs::remove_file(&temp_path);
            let _ = error;
            infer_existing_object_storage(destination, hash, size)
        }
        Err(error) => {
            let _ = fs::remove_file(&temp_path);
            Err(error.to_string())
        }
    }
}

fn infer_existing_object_storage(
    destination: &Path,
    hash: &str,
    size: u64,
) -> Result<ObjectStorage, String> {
    let stored_size = destination
        .metadata()
        .map_err(|error| error.to_string())?
        .len();
    if verify_file_content(destination, hash, size, "none").is_ok() {
        return Ok(ObjectStorage {
            compression: "none".to_string(),
            stored_size,
            original_size: size,
        });
    }
    if verify_file_content(destination, hash, size, "zstd").is_ok() {
        return Ok(ObjectStorage {
            compression: "zstd".to_string(),
            stored_size,
            original_size: size,
        });
    }
    Err("backup object hash mismatch while being stored".to_string())
}

fn create_temp_object_file(
    source: &Path,
    destination: &Path,
    hash: &str,
    size: u64,
) -> Result<(PathBuf, ObjectStorage), String> {
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
        if should_try_compression(source, size) {
            match write_temp_zstd(source, &temp_path) {
                Ok(stored_size) if stored_size < size => {
                    return Ok((
                        temp_path,
                        ObjectStorage {
                            compression: "zstd".to_string(),
                            stored_size,
                            original_size: size,
                        },
                    ));
                }
                Ok(_) => {
                    let _ = fs::remove_file(&temp_path);
                }
                Err(error) => {
                    let _ = fs::remove_file(&temp_path);
                    return Err(error);
                }
            }
        }
        let stored_size = write_temp_plain(source, &temp_path)?;
        return Ok((
            temp_path,
            ObjectStorage {
                compression: "none".to_string(),
                stored_size,
                original_size: size,
            },
        ));
    }
    Err("could not create temporary backup object file".to_string())
}

fn write_temp_zstd(source: &Path, temp_path: &Path) -> Result<u64, String> {
    let source_file = fs::File::open(source).map_err(|error| error.to_string())?;
    let mut destination_file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(temp_path)
        .map_err(|error| error.to_string())?;
    zstd::stream::copy_encode(source_file, &mut destination_file, 0)
        .map_err(|error| error.to_string())?;
    destination_file
        .flush()
        .map_err(|error| error.to_string())?;
    Ok(temp_path
        .metadata()
        .map_err(|error| error.to_string())?
        .len())
}

fn write_temp_plain(source: &Path, temp_path: &Path) -> Result<u64, String> {
    let mut destination_file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(temp_path)
        .map_err(|error| error.to_string())?;
    let mut source_file = fs::File::open(source).map_err(|error| error.to_string())?;
    std::io::copy(&mut source_file, &mut destination_file).map_err(|error| error.to_string())?;
    destination_file
        .flush()
        .map_err(|error| error.to_string())?;
    Ok(temp_path
        .metadata()
        .map_err(|error| error.to_string())?
        .len())
}

fn should_try_compression(source: &Path, size: u64) -> bool {
    if size == 0 {
        return false;
    }
    let Some(extension) = source.extension().and_then(|value| value.to_str()) else {
        return false;
    };
    matches!(
        extension.to_ascii_lowercase().as_str(),
        "css"
            | "csv"
            | "html"
            | "js"
            | "json"
            | "jsx"
            | "lock"
            | "md"
            | "py"
            | "rs"
            | "sql"
            | "svg"
            | "toml"
            | "ts"
            | "tsx"
            | "txt"
            | "xml"
            | "yaml"
            | "yml"
    )
}

fn verify_file_content(
    path: &Path,
    expected_hash: &str,
    expected_size: u64,
    compression: &str,
) -> Result<(), String> {
    let (actual_hash, actual_size) = hash_file_with_compression(path, compression)?;
    if actual_size != expected_size {
        return Err("backup object changed while being stored".to_string());
    }
    if actual_hash != expected_hash {
        return Err("backup object hash mismatch while being stored".to_string());
    }
    Ok(())
}

fn hash_file_with_compression(path: &Path, compression: &str) -> Result<(String, u64), String> {
    match compression {
        "none" => hash_reader(fs::File::open(path).map_err(|error| error.to_string())?),
        "zstd" => {
            let file = fs::File::open(path).map_err(|error| error.to_string())?;
            let decoder =
                zstd::stream::read::Decoder::new(file).map_err(|error| error.to_string())?;
            hash_reader(decoder)
        }
        _ => Err("backup object compression is unsupported".to_string()),
    }
}

fn hash_reader<R: Read>(mut reader: R) -> Result<(String, u64), String> {
    let mut hasher = blake3::Hasher::new();
    let mut size = 0_u64;
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = reader
            .read(&mut buffer)
            .map_err(|error| error.to_string())?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
        size += read as u64;
    }
    Ok((hasher.finalize().to_hex().to_string(), size))
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
    fn compresses_text_object_and_records_storage_metadata() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let text = "fn main() { println!(\"hello\"); }\n".repeat(256);
        let file = root.join("app.rs");
        std::fs::write(&file, &text).unwrap();
        let hash = blake3::hash(text.as_bytes()).to_hex().to_string();

        let object = store_object(root, &conn, &file, &hash, text.len() as u64).unwrap();

        let (compression, stored_size): (String, i64) = conn
            .query_row(
                "SELECT compression, stored_size FROM cas_objects WHERE hash = ?",
                params![hash],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(compression, "zstd");
        assert!(stored_size > 0);
        assert!(stored_size < text.len() as i64);
        assert_eq!(object.size, text.len() as u64);
    }

    #[test]
    fn skips_already_compressed_extension_even_when_bytes_are_repetitive() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let bytes = vec![b'a'; 4096];
        let file = root.join("asset.png");
        std::fs::write(&file, &bytes).unwrap();
        let hash = blake3::hash(&bytes).to_hex().to_string();

        store_object(root, &conn, &file, &hash, bytes.len() as u64).unwrap();

        let (compression, stored_size): (String, i64) = conn
            .query_row(
                "SELECT compression, stored_size FROM cas_objects WHERE hash = ?",
                params![hash],
                |row| Ok((row.get(0)?, row.get(1)?)),
            )
            .unwrap();
        assert_eq!(compression, "none");
        assert_eq!(stored_size, bytes.len() as i64);
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
    fn prune_reports_compressed_stored_size_as_reclaimed_bytes() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let conn = Connection::open(root.join("cas.db")).unwrap();
        schema::initialize(&conn).unwrap();
        let text = "fn main() { println!(\"hello\"); }\n".repeat(256);
        let file = root.join("app.rs");
        std::fs::write(&file, &text).unwrap();
        let hash = blake3::hash(text.as_bytes()).to_hex().to_string();
        let object = store_object(root, &conn, &file, &hash, text.len() as u64).unwrap();

        decrement_ref(&conn, &hash).unwrap();
        let pruned = super::prune_unreferenced_detailed(root, &conn).unwrap();

        assert_eq!(pruned.count, 1);
        assert_eq!(pruned.bytes, object.stored_size);
        assert!(pruned.bytes < text.len() as u64);
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
