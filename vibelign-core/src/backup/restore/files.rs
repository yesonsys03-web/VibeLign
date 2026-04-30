use crate::backup::restore::{backup_source, checkpoint_context, copy_backup_file, target_path};
use std::collections::BTreeSet;
use std::path::Path;

pub fn restore_selected(
    root: &Path,
    checkpoint_id: &str,
    relative_paths: &[String],
) -> Result<usize, String> {
    let (conn, is_v2, files) = checkpoint_context(root, checkpoint_id)?;
    let selected = relative_paths.iter().cloned().collect::<BTreeSet<_>>();
    let mut restored = 0_usize;
    for relative_path in selected {
        let file = files
            .get(&relative_path)
            .ok_or_else(|| "selected file missing from checkpoint".to_string())?;
        let source = backup_source(root, &conn, checkpoint_id, is_v2, file)?;
        let target = target_path(root, &relative_path)?;
        copy_backup_file(root, &target, &source)?;
        restored += 1;
    }
    Ok(restored)
}

#[cfg(test)]
mod tests {
    use super::restore_selected;
    use crate::backup::checkpoint::{create_with_metadata, CheckpointCreateMetadata};

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
