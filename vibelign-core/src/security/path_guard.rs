use std::path::{Component, Path, PathBuf};

#[allow(dead_code)]
pub fn resolve_under(base: &Path, rel: &str) -> Option<PathBuf> {
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

#[cfg(test)]
mod tests {
    use super::resolve_under;
    use std::path::Path;

    #[test]
    fn rejects_path_escape() {
        assert!(resolve_under(Path::new("/tmp/project"), "../evil").is_none());
        assert!(resolve_under(Path::new("/tmp/project"), "/tmp/evil").is_none());
    }
}
