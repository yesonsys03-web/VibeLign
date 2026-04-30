use crate::backup::disk;
use crate::backup::restore::{
    backup_source, checkpoint_context, copy_backup_file, copy_backup_object, target_path,
};
use std::collections::BTreeSet;
use std::path::Path;

pub fn restore_selected(
    root: &Path,
    checkpoint_id: &str,
    relative_paths: &[String],
) -> Result<usize, String> {
    disk::ensure_min_free_space(root)?;
    let (conn, is_v2, files) = checkpoint_context(root, checkpoint_id)?;
    let selected = relative_paths.iter().cloned().collect::<BTreeSet<_>>();
    let mut restored = 0_usize;
    for relative_path in selected {
        let file = files
            .get(&relative_path)
            .ok_or_else(|| "selected file missing from checkpoint".to_string())?;
        let target = target_path(root, &relative_path)?;
        if is_v2 {
            let object_hash = file
                .object_hash
                .as_deref()
                .ok_or_else(|| "backup object hash missing".to_string())?;
            copy_backup_object(root, &conn, &target, object_hash)?;
        } else {
            let source = backup_source(root, &conn, checkpoint_id, is_v2, file)?;
            copy_backup_file(root, &target, &source)?;
        }
        restored += 1;
    }
    Ok(restored)
}

#[cfg(test)]
mod tests {
    use super::restore_selected;
    use crate::backup::checkpoint::{create_with_metadata, CheckpointCreateMetadata};
    use rusqlite::{params, Connection};

    #[test]
    fn selected_restore_only_changes_requested_file() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("a.txt"), "old a\n").unwrap();
        std::fs::write(root.join("b.txt"), "old b\n").unwrap();
        let checkpoint = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::write(root.join("a.txt"), "new a\n").unwrap();
        std::fs::write(root.join("b.txt"), "new b\n").unwrap();

        let count =
            restore_selected(root, &checkpoint.checkpoint_id, &["a.txt".to_string()]).unwrap();

        assert_eq!(count, 1);
        assert_eq!(
            std::fs::read_to_string(root.join("a.txt")).unwrap(),
            "old a\n"
        );
        assert_eq!(
            std::fs::read_to_string(root.join("b.txt")).unwrap(),
            "new b\n"
        );
    }

    #[test]
    fn selected_restore_decodes_compressed_object() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let original = "export const value = 1;\n".repeat(256);
        std::fs::write(root.join("a.ts"), &original).unwrap();
        std::fs::write(root.join("b.txt"), "old b\n").unwrap();
        let checkpoint = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::write(root.join("a.ts"), "changed\n").unwrap();
        std::fs::write(root.join("b.txt"), "new b\n").unwrap();

        let count =
            restore_selected(root, &checkpoint.checkpoint_id, &["a.ts".to_string()]).unwrap();

        assert_eq!(count, 1);
        assert_eq!(
            std::fs::read_to_string(root.join("a.ts")).unwrap(),
            original
        );
        assert_eq!(
            std::fs::read_to_string(root.join("b.txt")).unwrap(),
            "new b\n"
        );
    }

    #[test]
    fn selected_restore_restores_readonly_target_after_decode_failure() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let original = "export const value = 1;\n".repeat(256);
        let target = root.join("a.ts");
        std::fs::write(&target, &original).unwrap();
        let checkpoint = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        let conn = Connection::open(root.join(".vibelign/vibelign.db")).unwrap();
        let storage_path: String = conn
            .query_row(
                "SELECT o.storage_path
                 FROM cas_objects o
                 JOIN checkpoint_files f ON f.object_hash = o.hash
                 WHERE f.checkpoint_id = ?",
                params![checkpoint.checkpoint_id],
                |row| row.get(0),
            )
            .unwrap();
        std::fs::write(root.join(storage_path), "not zstd").unwrap();
        std::fs::write(&target, "changed\n").unwrap();
        let mut permissions = target.metadata().unwrap().permissions();
        permissions.set_readonly(true);
        std::fs::set_permissions(&target, permissions).unwrap();

        let error =
            restore_selected(root, &checkpoint.checkpoint_id, &["a.ts".to_string()]).unwrap_err();

        assert!(!error.is_empty());
        assert_eq!(std::fs::read_to_string(&target).unwrap(), "changed\n");
        assert!(target.metadata().unwrap().permissions().readonly());
    }

    #[test]
    fn selected_restore_rejects_windows_backslash_escape() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("a.txt"), "old\n").unwrap();
        let checkpoint = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();

        let error = restore_selected(root, &checkpoint.checkpoint_id, &["..\\evil".to_string()])
            .unwrap_err();

        assert!(error.contains("missing") || error.contains("escaped"));
    }
}
