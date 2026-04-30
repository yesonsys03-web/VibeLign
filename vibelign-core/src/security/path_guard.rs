use std::path::{Component, Path, PathBuf};

#[allow(dead_code)]
pub fn resolve_under(base: &Path, rel: &str) -> Option<PathBuf> {
    if has_textual_windows_escape(rel) {
        return None;
    }
    let rel_path = Path::new(rel);
    if rel_path.is_absolute() {
        return None;
    }
    if rel_path
        .components()
        .any(|component| matches!(component, Component::ParentDir | Component::Prefix(_)))
    {
        return None;
    }
    Some(base.join(rel_path))
}

fn has_textual_windows_escape(rel: &str) -> bool {
    rel.starts_with('/')
        || rel.starts_with("\\\\")
        || rel.as_bytes().get(1) == Some(&b':')
        || rel.split(['/', '\\']).any(|part| part == "..")
}

#[cfg(test)]
mod tests {
    use super::resolve_under;
    use std::path::Path;

    #[test]
    fn rejects_path_escape() {
        assert!(resolve_under(Path::new("/tmp/project"), "../evil").is_none());
        assert!(resolve_under(Path::new("/tmp/project"), "/tmp/evil").is_none());
    }

    #[test]
    fn accepts_forward_and_backslash_relative_names_without_parent_escape() {
        let base = Path::new("/tmp/project");

        assert_eq!(
            resolve_under(base, "src/core/main.py").unwrap(),
            base.join("src/core/main.py")
        );
        assert_eq!(
            resolve_under(base, "src\\core\\main.py").unwrap(),
            base.join("src\\core\\main.py")
        );
    }

    #[test]
    fn rejects_backslash_parent_escape_even_on_non_windows_hosts() {
        assert!(resolve_under(Path::new("/tmp/project"), "..\\evil").is_none());
    }

    #[test]
    #[cfg(target_os = "windows")]
    fn rejects_windows_drive_and_unc_absolute_paths() {
        let base = Path::new("C:\\project");

        assert!(resolve_under(base, "D:\\other\\file.txt").is_none());
        assert!(resolve_under(base, "\\\\server\\share\\file.txt").is_none());
    }
}
