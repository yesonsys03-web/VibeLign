// ANCHOR: DOCS_ACCESS_START
//! Extra-source allowlist guard for Tauri read operations.
//!
//! This module is the **single entry point** for `is_allowed_doc_path` logic.
//! It reads `docs_index.json`'s `allowlist.extra_source_roots` field only —
//! Rust MUST NOT parse `doc_sources.json` directly.
//!
//! NOTE: `load()` does NOT check `schema_version`. Schema enforcement is the
//! responsibility of `lib.rs`'s `read_docs_index_cache_file`. Here we simply
//! extract the allowlist as-is; on any read/parse failure we fall back to an
//! empty allowlist so that built-in docs remain readable.

use std::collections::BTreeSet;
use std::path::Path;

/// Python `docs_scan.IGNORED_DIRS`와 같은 집합 — read_file 가드와 인덱스 스캔에서
/// 동일하게 차단되는 폴더 목록.
pub const DOCS_READ_IGNORED_DIRS: &[&str] = &[
    "node_modules", "target", "dist", "build", "out", "coverage",
    ".next", ".nuxt", ".turbo", ".cache", ".venv", "venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    ".gradle", ".idea", ".vscode", ".DS_Store",
];

/// In-memory set of extra source roots loaded from `docs_index.json`.
/// Roots are normalized relative POSIX paths, e.g. `".omc/plans"`.
pub struct ExtraSourceAllowlist {
    roots: BTreeSet<String>,
}

impl ExtraSourceAllowlist {
    /// Empty allowlist — only built-in docs are accessible.
    #[cfg(test)]
    pub fn new_empty() -> Self {
        Self { roots: BTreeSet::new() }
    }

    /// Load allowlist from `<project_root>/.vibelign/docs_index.json`.
    /// Any read error, JSON parse failure, or missing field silently
    /// returns an empty allowlist (graceful fallback).
    pub fn load(project_root: &Path) -> Self {
        let path = project_root.join(".vibelign").join("docs_index.json");
        let roots = read_allowlist_from_docs_index(&path);
        Self { roots }
    }

    /// The set of normalized extra source root prefixes.
    pub fn roots(&self) -> &BTreeSet<String> {
        &self.roots
    }
}

/// Read `.allowlist.extra_source_roots` from `docs_index.json`.
/// Returns empty set on any failure.
fn read_allowlist_from_docs_index(path: &Path) -> BTreeSet<String> {
    let raw = match std::fs::read_to_string(path) {
        Ok(s) => s,
        Err(_) => return BTreeSet::new(),
    };
    let value: serde_json::Value = match serde_json::from_str(&raw) {
        Ok(v) => v,
        Err(_) => return BTreeSet::new(),
    };
    let roots_arr = match value
        .get("allowlist")
        .and_then(|a| a.get("extra_source_roots"))
        .and_then(|r| r.as_array())
    {
        Some(arr) => arr,
        None => return BTreeSet::new(),
    };
    roots_arr
        .iter()
        .filter_map(|v| v.as_str())
        .map(|s| {
            // Normalize: trim, replace backslashes with forward slash, strip
            // leading and trailing slashes. Skip empty after normalization.
            s.trim().replace('\\', "/").trim_matches('/').to_string()
        })
        .filter(|s| !s.is_empty())
        .collect()
}

/// Determine whether `relative_path` (already `/`-normalized, no leading `/`)
/// is an allowed markdown document path.
///
/// Rules:
/// 1. Extension must be `.md` or `.markdown` (case-insensitive).
/// 2. Path must not contain `..`.
/// 3. Empty segments are rejected.
/// 4. If the path falls under a registered extra source root prefix:
///    - The prefix itself may contain hidden-looking segments (e.g. `.omc/plans`).
///    - Segments AFTER the prefix must not start with `.` and must not be in
///      `DOCS_READ_IGNORED_DIRS`.
/// 5. If no extra prefix matched, fall back to built-in rules: every segment
///    must not start with `.` and must not be in `DOCS_READ_IGNORED_DIRS`.
pub fn is_allowed_doc_path(relative_path: &str, extras: &ExtraSourceAllowlist) -> bool {
    let lower = relative_path.to_ascii_lowercase();

    // 1) Extension check
    if !lower.ends_with(".md") && !lower.ends_with(".markdown") {
        return false;
    }

    // 2) Path traversal reject
    if relative_path.contains("..") {
        return false;
    }

    // 3) All segments must be non-empty first pass (before routing)
    for segment in relative_path.split('/') {
        if segment.is_empty() {
            return false;
        }
    }

    // 4) Try to match an extra source prefix
    for prefix in extras.roots() {
        if relative_path == prefix.as_str() {
            // The prefix itself ends with .md/.markdown (already checked above) — allow.
            return true;
        }
        if relative_path.starts_with(&format!("{prefix}/")) {
            // Matched an extra source root. Validate suffix segments only.
            let suffix = &relative_path[prefix.len() + 1..];
            for segment in suffix.split('/') {
                if segment.is_empty() {
                    return false;
                }
                if segment.starts_with('.') {
                    return false;
                }
                if DOCS_READ_IGNORED_DIRS.contains(&segment) {
                    return false;
                }
            }
            return true;
        }
    }

    // 5) Built-in rule: no hidden segments, no ignored dirs
    for segment in relative_path.split('/') {
        if segment.starts_with('.') {
            return false;
        }
        if DOCS_READ_IGNORED_DIRS.contains(&segment) {
            return false;
        }
    }
    true
}

// ANCHOR: DOCS_ACCESS_END

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeSet;

    fn allowlist_with(roots: &[&str]) -> ExtraSourceAllowlist {
        ExtraSourceAllowlist {
            roots: roots.iter().map(|s| s.to_string()).collect::<BTreeSet<_>>(),
        }
    }

    fn empty_allowlist() -> ExtraSourceAllowlist {
        ExtraSourceAllowlist::new_empty()
    }

    // ── Extension checks ───────────────────────────────────────────────────────

    #[test]
    fn test_extension_md_accepted() {
        assert!(is_allowed_doc_path("docs/wiki/index.md", &empty_allowlist()));
    }

    #[test]
    fn test_extension_markdown_accepted() {
        assert!(is_allowed_doc_path("docs/guide.markdown", &empty_allowlist()));
    }

    #[test]
    fn test_extension_case_insensitive_md() {
        assert!(is_allowed_doc_path("docs/README.MD", &empty_allowlist()));
    }

    #[test]
    fn test_extension_txt_rejected() {
        assert!(!is_allowed_doc_path("docs/note.txt", &empty_allowlist()));
    }

    #[test]
    fn test_extension_no_extension_rejected() {
        assert!(!is_allowed_doc_path("docs/README", &empty_allowlist()));
    }

    // ── Path traversal ─────────────────────────────────────────────────────────

    #[test]
    fn test_dotdot_rejected() {
        assert!(!is_allowed_doc_path("docs/../secret.md", &empty_allowlist()));
    }

    #[test]
    fn test_dotdot_in_filename_rejected() {
        assert!(!is_allowed_doc_path("docs/a..b.md", &empty_allowlist()));
    }

    // ── Built-in only (no extras) ──────────────────────────────────────────────

    #[test]
    fn test_builtin_only_accepts_non_hidden() {
        assert!(is_allowed_doc_path("docs/wiki/index.md", &empty_allowlist()));
    }

    #[test]
    fn test_builtin_rejects_node_modules() {
        assert!(!is_allowed_doc_path("node_modules/foo.md", &empty_allowlist()));
    }

    #[test]
    fn test_builtin_rejects_hidden_segment() {
        assert!(!is_allowed_doc_path(".hidden/foo.md", &empty_allowlist()));
    }

    #[test]
    fn test_builtin_rejects_dot_venv() {
        assert!(!is_allowed_doc_path(".venv/docs/page.md", &empty_allowlist()));
    }

    #[test]
    fn test_builtin_rejects_ignored_dir_nested() {
        assert!(!is_allowed_doc_path("src/target/foo.md", &empty_allowlist()));
    }

    // ── Extra allowlist: .omc/plans ────────────────────────────────────────────

    #[test]
    fn test_extra_direct_child_passes() {
        let extras = allowlist_with(&[".omc/plans"]);
        assert!(is_allowed_doc_path(".omc/plans/a.md", &extras));
    }

    #[test]
    fn test_extra_nested_passes() {
        let extras = allowlist_with(&[".omc/plans"]);
        assert!(is_allowed_doc_path(".omc/plans/sub/b.md", &extras));
    }

    #[test]
    fn test_extra_hidden_sub_dir_rejected() {
        let extras = allowlist_with(&[".omc/plans"]);
        // Sub-segment starts with `.` — must be rejected even under registered root
        assert!(!is_allowed_doc_path(".omc/plans/.archive/x.md", &extras));
    }

    #[test]
    fn test_extra_ignored_dir_in_sub_rejected() {
        let extras = allowlist_with(&[".omc/plans"]);
        assert!(!is_allowed_doc_path(".omc/plans/node_modules/y.md", &extras));
    }

    #[test]
    fn test_extra_unregistered_hidden_path_rejected() {
        let extras = allowlist_with(&[".omc/plans"]);
        // .omc/private.md does NOT start with ".omc/plans/"
        assert!(!is_allowed_doc_path(".omc/private.md", &extras));
    }

    #[test]
    fn test_extra_prefix_mismatch_fake_rejected() {
        let extras = allowlist_with(&[".omc/plans"]);
        // ".omc/plansfake/..." must NOT match ".omc/plans" prefix
        assert!(!is_allowed_doc_path(".omc/plansfake/a.md", &extras));
    }

    #[test]
    fn test_extra_bare_root_no_extension_rejected() {
        let extras = allowlist_with(&[".omc/plans"]);
        // ".omc/plans" itself has no .md extension
        assert!(!is_allowed_doc_path(".omc/plans", &extras));
    }

    #[test]
    fn test_extra_root_with_md_extension_accepted() {
        // An edge case: the extra root string itself ends with .md
        let extras = allowlist_with(&["custom/root.md"]);
        // rel == prefix and extension check passes
        assert!(is_allowed_doc_path("custom/root.md", &extras));
    }

    // ── load() fallback behaviour ──────────────────────────────────────────────

    #[test]
    fn test_load_missing_file_returns_empty() {
        let tmp = std::env::temp_dir().join("vibelign_test_nonexistent_12345");
        let allowlist = ExtraSourceAllowlist::load(&tmp);
        assert!(allowlist.roots().is_empty());
        // Built-in path still works with the empty allowlist
        assert!(is_allowed_doc_path("docs/guide.md", &allowlist));
    }

    #[test]
    fn test_load_malformed_json_returns_empty() {
        let dir = tempfile::tempdir().expect("tempdir");
        let vibelign_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&vibelign_dir).unwrap();
        std::fs::write(vibelign_dir.join("docs_index.json"), b"{invalid json}").unwrap();
        let allowlist = ExtraSourceAllowlist::load(dir.path());
        assert!(allowlist.roots().is_empty());
    }

    #[test]
    fn test_load_valid_allowlist() {
        let dir = tempfile::tempdir().expect("tempdir");
        let vibelign_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&vibelign_dir).unwrap();
        let json = r#"{
            "schema_version": 2,
            "root": "/some/root",
            "allowlist": {
                "extra_source_roots": [".omc/plans", ".sisyphus/plans"]
            },
            "entries": []
        }"#;
        std::fs::write(vibelign_dir.join("docs_index.json"), json).unwrap();
        let allowlist = ExtraSourceAllowlist::load(dir.path());
        assert_eq!(allowlist.roots().len(), 2);
        assert!(allowlist.roots().contains(".omc/plans"));
        assert!(allowlist.roots().contains(".sisyphus/plans"));
    }

    #[test]
    fn test_load_no_schema_version_check() {
        // load() does NOT check schema_version — it reads allowlist regardless
        let dir = tempfile::tempdir().expect("tempdir");
        let vibelign_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&vibelign_dir).unwrap();
        let json = r#"{
            "schema_version": 99,
            "allowlist": {
                "extra_source_roots": [".custom/docs"]
            }
        }"#;
        std::fs::write(vibelign_dir.join("docs_index.json"), json).unwrap();
        let allowlist = ExtraSourceAllowlist::load(dir.path());
        assert!(allowlist.roots().contains(".custom/docs"));
    }

    #[test]
    fn test_load_missing_allowlist_field_returns_empty() {
        let dir = tempfile::tempdir().expect("tempdir");
        let vibelign_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&vibelign_dir).unwrap();
        let json = r#"{"schema_version": 2, "root": "/x", "entries": []}"#;
        std::fs::write(vibelign_dir.join("docs_index.json"), json).unwrap();
        let allowlist = ExtraSourceAllowlist::load(dir.path());
        assert!(allowlist.roots().is_empty());
    }

    // ── BTreeSet determinism ───────────────────────────────────────────────────

    #[test]
    fn test_allowlist_is_deterministic() {
        let a = allowlist_with(&[".b/docs", ".a/plans", ".c/notes"]);
        let b = allowlist_with(&[".c/notes", ".a/plans", ".b/docs"]);
        // BTreeSet iteration order is sorted — check they yield same elements
        let a_vec: Vec<_> = a.roots().iter().collect();
        let b_vec: Vec<_> = b.roots().iter().collect();
        assert_eq!(a_vec, b_vec);
    }

    // ── Windows-style backslash normalization in load ──────────────────────────

    #[test]
    fn test_load_backslash_normalized() {
        let dir = tempfile::tempdir().expect("tempdir");
        let vibelign_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&vibelign_dir).unwrap();
        // Windows-style path stored in JSON (shouldn't happen but guard it)
        let json = r#"{
            "schema_version": 2,
            "allowlist": {
                "extra_source_roots": [".OMC\\plans"]
            }
        }"#;
        std::fs::write(vibelign_dir.join("docs_index.json"), json).unwrap();
        let allowlist = ExtraSourceAllowlist::load(dir.path());
        // Backslash should be normalized to forward slash
        assert!(allowlist.roots().contains(".OMC/plans"));
    }
}
