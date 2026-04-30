use crate::backup::diff::{checkpoint_engine_version, checkpoint_parent_id, open_db};
use crate::backup::restore::preview::{preview_full, PreviewFile};
use serde::Serialize;
use std::path::Path;
use std::time::{Duration, SystemTime};

#[derive(Debug, Clone, Serialize)]
pub struct RestoreSuggestion {
    pub relative_path: String,
    pub reason_code: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct RestoreSuggestions {
    pub suggestions: Vec<RestoreSuggestion>,
    pub legacy_notice: Option<String>,
}

pub fn suggest(root: &Path, checkpoint_id: &str, cap: usize) -> Result<RestoreSuggestions, String> {
    let conn = open_db(root)?;
    let is_legacy = checkpoint_engine_version(&conn, checkpoint_id)?.as_deref() != Some("rust-v2");
    let parent_id = checkpoint_parent_id(&conn, checkpoint_id)?;
    if is_legacy || parent_id.is_none() {
        return Ok(RestoreSuggestions {
            suggestions: Vec::new(),
            legacy_notice: Some("legacy checkpoint has no restore suggestions".to_string()),
        });
    }
    let preview = preview_full(root, checkpoint_id)?;
    let limit = cap.clamp(3, 10);
    let mut missing = Vec::new();
    let mut recent = Vec::new();
    let mut high_change = Vec::new();
    let mut changed = Vec::new();
    for file in preview.selected_files {
        match file.status.as_str() {
            "will_restore_missing" => missing.push(item(file, "missing_now")),
            "will_replace" if recently_changed(root, &file.relative_path) => {
                recent.push(item(file, "recently_changed"));
            }
            "will_replace" if size_delta_is_high(&file) => {
                high_change.push(item(file, "high_change"))
            }
            "will_replace" => changed.push(item(file, "changed_on_date")),
            _ => {}
        }
    }
    let mut suggestions = Vec::new();
    for group in [&mut missing, &mut recent, &mut high_change, &mut changed] {
        group.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
        for suggestion in group.drain(..) {
            if suggestions.len() >= limit {
                break;
            }
            suggestions.push(suggestion);
        }
    }
    Ok(RestoreSuggestions {
        suggestions,
        legacy_notice: None,
    })
}

fn item(file: PreviewFile, reason_code: &str) -> RestoreSuggestion {
    RestoreSuggestion {
        relative_path: file.relative_path,
        reason_code: reason_code.to_string(),
    }
}

fn recently_changed(root: &Path, relative_path: &str) -> bool {
    root.join(relative_path)
        .metadata()
        .and_then(|metadata| metadata.modified())
        .ok()
        .and_then(|modified| SystemTime::now().duration_since(modified).ok())
        .map(|age| age <= Duration::from_secs(30 * 60))
        .unwrap_or(false)
}

fn size_delta_is_high(file: &PreviewFile) -> bool {
    let current = file.current_size.unwrap_or(0);
    let backup = file.backup_size.unwrap_or(0);
    current.abs_diff(backup) >= 1024 * 1024
}

#[cfg(test)]
mod tests {
    use super::suggest;
    use crate::backup::checkpoint::{create_with_metadata, CheckpointCreateMetadata};

    #[test]
    fn suggestions_prioritize_missing_files() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("missing.txt"), "old\n").unwrap();
        let first = create_with_metadata(root, "first", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::write(root.join("missing.txt"), "new\n").unwrap();
        let second = create_with_metadata(root, "second", CheckpointCreateMetadata::default())
            .unwrap()
            .unwrap();
        std::fs::remove_file(root.join("missing.txt")).unwrap();

        let result = suggest(root, &second.checkpoint_id, 5).unwrap();

        assert_ne!(first.checkpoint_id, second.checkpoint_id);
        assert_eq!(result.suggestions[0].relative_path, "missing.txt");
        assert_eq!(result.suggestions[0].reason_code, "missing_now");
    }
}
