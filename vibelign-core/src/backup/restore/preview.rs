use crate::backup::diff::StoredFile;
use crate::backup::restore::{checkpoint_context, target_path};
use crate::backup::snapshot::collect;
use serde::Serialize;
use std::collections::{BTreeMap, BTreeSet};
use std::path::Path;

#[derive(Debug, Clone, Serialize)]
pub struct PreviewFile {
    pub relative_path: String,
    pub status: String,
    pub current_size: Option<u64>,
    pub backup_size: Option<u64>,
}

#[derive(Debug, Clone, Serialize)]
pub struct PreviewSummary {
    pub replace_count: usize,
    pub restore_missing_count: usize,
    pub delete_count: usize,
    pub unchanged_count: usize,
}

#[derive(Debug, Clone, Serialize)]
pub struct RestorePreview {
    pub checkpoint_id: String,
    pub selected_files: Vec<PreviewFile>,
    pub summary: PreviewSummary,
}

pub fn preview_full(root: &Path, checkpoint_id: &str) -> Result<RestorePreview, String> {
    let (_, _, checkpoint_files) = checkpoint_context(root, checkpoint_id)?;
    let current = current_map(root)?;
    preview_from_maps(checkpoint_id, &checkpoint_files, &current, None)
}

pub fn preview_selected(
    root: &Path,
    checkpoint_id: &str,
    relative_paths: &[String],
) -> Result<RestorePreview, String> {
    let (_, _, checkpoint_files) = checkpoint_context(root, checkpoint_id)?;
    let current = current_map(root)?;
    let selected = relative_paths.iter().cloned().collect::<BTreeSet<_>>();
    for path in &selected {
        target_path(root, path)?;
        if !checkpoint_files.contains_key(path) {
            return Err("selected file missing from checkpoint".to_string());
        }
    }
    preview_from_maps(checkpoint_id, &checkpoint_files, &current, Some(selected))
}

fn current_map(root: &Path) -> Result<BTreeMap<String, (String, u64)>, String> {
    let mut files = BTreeMap::new();
    for file in collect(root).map_err(|error| error.to_string())? {
        files.insert(file.relative_path, (file.hash, file.size));
    }
    Ok(files)
}

fn preview_from_maps(
    checkpoint_id: &str,
    checkpoint_files: &BTreeMap<String, StoredFile>,
    current: &BTreeMap<String, (String, u64)>,
    selected: Option<BTreeSet<String>>,
) -> Result<RestorePreview, String> {
    let is_selected_preview = selected.is_some();
    let paths = selected.unwrap_or_else(|| {
        checkpoint_files
            .keys()
            .chain(current.keys())
            .cloned()
            .collect::<BTreeSet<_>>()
    });
    let mut selected_files = Vec::new();
    let mut summary = PreviewSummary {
        replace_count: 0,
        restore_missing_count: 0,
        delete_count: 0,
        unchanged_count: 0,
    };
    for path in paths {
        match (checkpoint_files.get(&path), current.get(&path)) {
            (Some(backup), Some((current_hash, current_size)))
                if backup.hash != *current_hash || backup.size != *current_size =>
            {
                summary.replace_count += 1;
                selected_files.push(PreviewFile {
                    relative_path: path,
                    status: "will_replace".to_string(),
                    current_size: Some(*current_size),
                    backup_size: Some(backup.size),
                });
            }
            (Some(backup), None) => {
                summary.restore_missing_count += 1;
                selected_files.push(PreviewFile {
                    relative_path: path,
                    status: "will_restore_missing".to_string(),
                    current_size: None,
                    backup_size: Some(backup.size),
                });
            }
            (None, Some((_, current_size))) => {
                if !is_selected_preview {
                    summary.delete_count += 1;
                    selected_files.push(PreviewFile {
                        relative_path: path,
                        status: "will_delete".to_string(),
                        current_size: Some(*current_size),
                        backup_size: None,
                    });
                }
            }
            (Some(backup), Some((_, current_size))) => {
                summary.unchanged_count += 1;
                selected_files.push(PreviewFile {
                    relative_path: path,
                    status: "unchanged".to_string(),
                    current_size: Some(*current_size),
                    backup_size: Some(backup.size),
                });
            }
            (None, None) => {}
        }
    }
    Ok(RestorePreview {
        checkpoint_id: checkpoint_id.to_string(),
        selected_files,
        summary,
    })
}

#[cfg(test)]
mod tests {
    use super::{preview_full, preview_selected};
    use crate::backup::checkpoint::{create_with_metadata, CheckpointCreateMetadata};

    #[test]
    fn full_preview_reports_replace_restore_missing_and_delete_without_writes() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("replace.txt"), "old\n").unwrap();
        std::fs::write(root.join("missing.txt"), "old\n").unwrap();
        let checkpoint = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::write(root.join("replace.txt"), "new\n").unwrap();
        std::fs::remove_file(root.join("missing.txt")).unwrap();
        std::fs::write(root.join("extra.txt"), "extra\n").unwrap();

        let preview = preview_full(root, &checkpoint.checkpoint_id).unwrap();

        assert_eq!(preview.summary.replace_count, 1);
        assert_eq!(preview.summary.restore_missing_count, 1);
        assert_eq!(preview.summary.delete_count, 1);
        assert_eq!(
            std::fs::read_to_string(root.join("replace.txt")).unwrap(),
            "new\n"
        );
    }

    #[test]
    fn selected_preview_only_includes_selected_files() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("a.txt"), "old a\n").unwrap();
        std::fs::write(root.join("b.txt"), "old b\n").unwrap();
        let checkpoint = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::write(root.join("a.txt"), "new a\n").unwrap();
        std::fs::write(root.join("b.txt"), "new b\n").unwrap();

        let preview =
            preview_selected(root, &checkpoint.checkpoint_id, &["a.txt".to_string()]).unwrap();

        assert_eq!(preview.selected_files.len(), 1);
        assert_eq!(preview.selected_files[0].relative_path, "a.txt");
    }
}
