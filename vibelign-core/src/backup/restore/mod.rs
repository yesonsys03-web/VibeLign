pub mod files;
pub mod full;
pub mod preview;

use crate::backup::cas;
use crate::backup::diff::{checkpoint_engine_version, load_checkpoint_files, open_db, StoredFile};
use crate::security::path_guard::resolve_under;
use rusqlite::Connection;
use std::fs;
use std::path::{Path, PathBuf};

fn reject_relative_path(relative_path: &str) -> Result<(), String> {
    if relative_path.contains('\\') {
        return Err("restore path escaped project root".to_string());
    }
    Ok(())
}

fn target_path(root: &Path, relative_path: &str) -> Result<PathBuf, String> {
    reject_relative_path(relative_path)?;
    resolve_under(root, relative_path)
        .ok_or_else(|| "restore path escaped project root".to_string())
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

fn backup_source(
    root: &Path,
    conn: &Connection,
    checkpoint_id: &str,
    is_v2: bool,
    file: &StoredFile,
) -> Result<PathBuf, String> {
    let source = if is_v2 {
        let hash = file
            .object_hash
            .clone()
            .ok_or_else(|| "backup object hash missing".to_string())?;
        cas::resolve_object(root, conn, &hash)?
    } else {
        resolve_under(root, &file.storage_path)
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
    Ok(source)
}

fn copy_backup_file(root: &Path, target: &Path, source: &Path) -> Result<(), String> {
    write_restored_file(root, target, |target| {
        fs::copy(source, target).map_err(|error| error.to_string())?;
        Ok(())
    })
}

fn copy_backup_object(
    root: &Path,
    conn: &Connection,
    target: &Path,
    object_hash: &str,
) -> Result<(), String> {
    write_restored_file(root, target, |target| {
        cas::restore_object_to(root, conn, object_hash, target)
    })
}

fn write_restored_file<F>(root: &Path, target: &Path, mut write_file: F) -> Result<(), String>
where
    F: FnMut(&Path) -> Result<(), String>,
{
    if let Some(parent) = target.parent() {
        fs::create_dir_all(parent).map_err(|error| error.to_string())?;
        ensure_existing_path_has_no_symlink(parent)?;
    }
    if target.exists() || target.symlink_metadata().is_ok() {
        ensure_existing_path_has_no_symlink(target)?;
    }
    if !target.starts_with(root) {
        return Err("restore path escaped project root".to_string());
    }
    let was_readonly = target
        .metadata()
        .map(|metadata| metadata.permissions().readonly())
        .unwrap_or(false);
    if was_readonly {
        set_readonly(target, false)?;
    }
    let write_result = write_file(target);
    if was_readonly {
        set_readonly(target, true)?;
    }
    write_result?;
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

pub fn checkpoint_context(
    root: &Path,
    checkpoint_id: &str,
) -> Result<
    (
        Connection,
        bool,
        std::collections::BTreeMap<String, StoredFile>,
    ),
    String,
> {
    let conn = open_db(root)?;
    let is_v2 = checkpoint_engine_version(&conn, checkpoint_id)?.as_deref() == Some("rust-v2");
    let files = load_checkpoint_files(&conn, checkpoint_id)?;
    Ok((conn, is_v2, files))
}
