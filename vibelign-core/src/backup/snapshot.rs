use crate::constants::{CHECKPOINT_IGNORED_FILES, IGNORED_DIRS};
use std::fs;
use std::path::{Path, PathBuf};
use unicode_normalization::UnicodeNormalization;
use walkdir::{DirEntry, WalkDir};

#[derive(Debug, Clone)]
pub struct SnapshotFile {
    pub relative_path: String,
    pub hash: String,
    pub size: u64,
}

fn is_ignored_dir(entry: &DirEntry) -> bool {
    if !entry.file_type().is_dir() {
        return false;
    }
    let name = entry.file_name().to_string_lossy();
    IGNORED_DIRS
        .iter()
        .any(|ignored| name.eq_ignore_ascii_case(ignored))
}

fn should_include_vibelign_file(path: &Path) -> bool {
    match path.file_name().and_then(|name| name.to_str()) {
        Some(name) => !CHECKPOINT_IGNORED_FILES.contains(&name),
        None => false,
    }
}

fn normalize_relative(path: PathBuf) -> String {
    path.components()
        .map(|component| component.as_os_str().to_string_lossy())
        .collect::<Vec<_>>()
        .join("/")
        .nfc()
        .collect()
}

pub fn collect(root: &Path) -> std::io::Result<Vec<SnapshotFile>> {
    let mut files = Vec::new();
    for entry in WalkDir::new(root)
        .follow_links(false)
        .into_iter()
        .filter_entry(|entry| !is_ignored_dir(entry))
    {
        let entry = match entry {
            Ok(entry) => entry,
            Err(_) => continue,
        };
        if !entry.file_type().is_file() {
            continue;
        }
        let path = entry.path();
        let Ok(relative) = path.strip_prefix(root) else {
            continue;
        };
        let relative_text = normalize_relative(relative.to_path_buf());
        if relative_text.starts_with(".vibelign/rust_checkpoints/")
            || relative_text.starts_with(".vibelign/rust_objects/")
            || relative_text.starts_with(".vibelign/checkpoints/")
        {
            continue;
        }
        if relative_text.starts_with(".vibelign/") && !should_include_vibelign_file(path) {
            continue;
        }
        if let Some(name) = path.file_name().and_then(|name| name.to_str()) {
            if CHECKPOINT_IGNORED_FILES.contains(&name) {
                continue;
            }
        }
        let bytes = match fs::read(path) {
            Ok(bytes) => bytes,
            Err(_) => continue,
        };
        files.push(SnapshotFile {
            relative_path: relative_text,
            hash: blake3::hash(&bytes).to_hex().to_string(),
            size: bytes.len() as u64,
        });
    }
    files.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
    Ok(files)
}

#[cfg(test)]
mod tests {
    use super::collect;

    #[test]
    fn excludes_runtime_state_but_keeps_anchor_index() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("app.py"), "print(1)\n").unwrap();
        std::fs::create_dir(root.join(".vibelign")).unwrap();
        std::fs::write(root.join(".vibelign/anchor_index.json"), "{}\n").unwrap();
        std::fs::write(root.join(".vibelign/state.json"), "{}\n").unwrap();
        std::fs::create_dir_all(root.join(".vibelign/rust_objects/blake3/ab/cd")).unwrap();
        std::fs::write(
            root.join(".vibelign/rust_objects/blake3/ab/cd/object"),
            "stored\n",
        )
        .unwrap();

        let paths: Vec<String> = collect(root)
            .unwrap()
            .into_iter()
            .map(|file| file.relative_path)
            .collect();

        assert!(paths.contains(&"app.py".to_string()));
        assert!(paths.contains(&".vibelign/anchor_index.json".to_string()));
        assert!(!paths.contains(&".vibelign/rust_objects/blake3/ab/cd/object".to_string()));
        assert!(!paths.contains(&".vibelign/state.json".to_string()));
    }

    #[test]
    fn normalizes_relative_paths_to_nfc() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("e\u{301}.txt"), "accent\n").unwrap();

        let paths: Vec<String> = collect(root)
            .unwrap()
            .into_iter()
            .map(|file| file.relative_path)
            .collect();

        assert!(paths.contains(&"é.txt".to_string()));
    }
}
