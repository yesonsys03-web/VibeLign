use crate::constants::{CHECKPOINT_IGNORED_FILES, IGNORED_DIRS};
use std::collections::VecDeque;
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use unicode_normalization::UnicodeNormalization;
use walkdir::{DirEntry, WalkDir};

#[derive(Debug, Clone)]
pub struct SnapshotFile {
    pub relative_path: String,
    pub hash: String,
    pub size: u64,
    pub(crate) source_path: PathBuf,
}

#[derive(Debug, Clone)]
struct SnapshotJob {
    path: PathBuf,
    relative_path: String,
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
    let mut jobs = VecDeque::new();
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
        jobs.push_back(SnapshotJob {
            path: path.to_path_buf(),
            relative_path: relative_text,
        });
    }
    let mut files = hash_jobs(jobs)?;
    files.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
    Ok(files)
}

fn hash_jobs(jobs: VecDeque<SnapshotJob>) -> std::io::Result<Vec<SnapshotFile>> {
    let worker_count = std::thread::available_parallelism()
        .map(|count| count.get().clamp(1, 8))
        .unwrap_or(1);
    let jobs = Arc::new(Mutex::new(jobs));
    let results = Arc::new(Mutex::new(Vec::new()));
    std::thread::scope(|scope| {
        for _ in 0..worker_count {
            let jobs = Arc::clone(&jobs);
            let results = Arc::clone(&results);
            scope.spawn(move || loop {
                let job = {
                    let mut guard = match jobs.lock() {
                        Ok(guard) => guard,
                        Err(_) => return,
                    };
                    guard.pop_front()
                };
                let Some(job) = job else {
                    break;
                };
                let result = hash_file(&job.path).map(|(hash, size)| SnapshotFile {
                    relative_path: job.relative_path,
                    hash,
                    size,
                    source_path: job.path,
                });
                let mut guard = match results.lock() {
                    Ok(guard) => guard,
                    Err(_) => return,
                };
                guard.push(result);
            });
        }
    });
    let results = Arc::try_unwrap(results)
        .map_err(|_| std::io::Error::other("snapshot worker still holds results"))?
        .into_inner()
        .map_err(|_| std::io::Error::other("snapshot worker result lock failed"))?;
    let mut files = Vec::new();
    for result in results {
        files.push(result?);
    }
    Ok(files)
}

fn hash_file(path: &Path) -> std::io::Result<(String, u64)> {
    let mut file = fs::File::open(path)?;
    let mut hasher = blake3::Hasher::new();
    let mut size = 0_u64;
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
        size += read as u64;
    }
    Ok((hasher.finalize().to_hex().to_string(), size))
}

#[cfg(test)]
mod tests {
    use super::{collect, hash_jobs, SnapshotJob};
    use std::collections::VecDeque;

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
        std::fs::create_dir(root.join("한글")).unwrap();
        std::fs::write(root.join("한글").join("파일.txt"), "korean\n").unwrap();

        let paths: Vec<String> = collect(root)
            .unwrap()
            .into_iter()
            .map(|file| file.relative_path)
            .collect();

        assert!(paths.contains(&"é.txt".to_string()));
        assert!(paths.contains(&"한글/파일.txt".to_string()));
    }

    #[test]
    fn keeps_source_path_separate_from_normalized_relative_path() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let decomposed_name = "e\u{301}.txt";
        std::fs::write(root.join(decomposed_name), "accent\n").unwrap();

        let files = collect(root).unwrap();

        assert_eq!(files.len(), 1);
        assert_eq!(files[0].relative_path, "é.txt");
        assert_eq!(files[0].source_path, root.join(decomposed_name));
    }

    #[test]
    fn hashes_files_with_streaming_reader() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let content = vec![b'a'; 128 * 1024 + 17];
        std::fs::write(root.join("large.txt"), &content).unwrap();

        let files = collect(root).unwrap();

        assert_eq!(files.len(), 1);
        assert_eq!(files[0].size, content.len() as u64);
        assert_eq!(files[0].hash, blake3::hash(&content).to_hex().to_string());
    }

    #[test]
    fn collects_zero_byte_files_as_real_snapshot_entries() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("empty.txt"), []).unwrap();

        let files = collect(root).unwrap();

        assert_eq!(files.len(), 1);
        assert_eq!(files[0].relative_path, "empty.txt");
        assert_eq!(files[0].size, 0);
        assert_eq!(files[0].hash, blake3::hash(&[]).to_hex().to_string());
    }

    #[test]
    #[cfg(unix)]
    fn ignores_symlinks_and_broken_symlinks_during_snapshot() {
        use std::os::unix::fs::symlink;

        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        std::fs::write(root.join("real.txt"), "real\n").unwrap();
        symlink(root.join("real.txt"), root.join("link.txt")).unwrap();
        symlink(root.join("missing.txt"), root.join("broken.txt")).unwrap();

        let paths: Vec<String> = collect(root)
            .unwrap()
            .into_iter()
            .map(|file| file.relative_path)
            .collect();

        assert_eq!(paths, vec!["real.txt".to_string()]);
    }

    #[test]
    #[cfg(target_os = "macos")]
    fn macos_collects_executable_unicode_files_without_losing_normalized_name() {
        use std::os::unix::fs::PermissionsExt;

        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let path = root.join("스크립트.sh");
        std::fs::write(&path, "#!/bin/sh\necho ok\n").unwrap();
        let mut permissions = std::fs::metadata(&path).unwrap().permissions();
        permissions.set_mode(0o755);
        std::fs::set_permissions(&path, permissions).unwrap();

        let files = collect(root).unwrap();

        assert_eq!(files.len(), 1);
        assert_eq!(files[0].relative_path, "스크립트.sh");
        assert_eq!(files[0].size, 18);
    }

    #[test]
    fn returns_error_when_hashing_discovers_missing_file() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path();
        let mut jobs = VecDeque::new();
        jobs.push_back(SnapshotJob {
            path: root.join("missing.txt"),
            relative_path: "missing.txt".to_string(),
        });

        let error = hash_jobs(jobs).unwrap_err();

        assert_eq!(error.kind(), std::io::ErrorKind::NotFound);
    }
}
