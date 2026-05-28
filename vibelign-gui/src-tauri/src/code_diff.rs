use std::path::Path;

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum DiffKind {
    Context,
    Added,
    Removed,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct DiffLine {
    pub kind: DiffKind,
    pub old_no: Option<u32>,
    pub new_no: Option<u32>,
    pub text: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum BaselineSource {
    Git,
    Checkpoint,
    None,
}

#[derive(Debug, serde::Serialize)]
pub struct CodeFileDiffResult {
    pub path: String,
    pub language: String,
    pub baseline_source: BaselineSource,
    pub added: u32,
    pub removed: u32,
    pub lines: Vec<DiffLine>,
}

/// 계층형 baseline 확보. (root, 정규화된 relpath)
/// 반환: (baseline 내용 또는 None, source)
pub(crate) fn resolve_baseline(root: &Path, rel: &str) -> (Option<String>, BaselineSource) {
    if let Some(text) = baseline_from_git(root, rel) {
        return (Some(text), BaselineSource::Git);
    }
    if let Some(text) = baseline_from_checkpoint(root, rel) {
        return (Some(text), BaselineSource::Checkpoint);
    }
    (None, BaselineSource::None)
}

fn baseline_from_git(root: &Path, rel: &str) -> Option<String> {
    // 1. git 저장소인지
    let probe = std::process::Command::new("git")
        .args(["-C"]).arg(root)
        .args(["rev-parse", "--is-inside-work-tree"])
        .output().ok()?;
    if !probe.status.success() { return None; }
    // 2. HEAD에 추적된 파일인지
    let ls = std::process::Command::new("git")
        .args(["-C"]).arg(root)
        .args(["ls-files", "--error-unmatch", "--", rel])
        .output().ok()?;
    if !ls.status.success() { return None; }
    // 3. git show HEAD:rel
    let show = std::process::Command::new("git")
        .args(["-C"]).arg(root)
        .arg("show").arg(format!("HEAD:{}", rel))
        .output().ok()?;
    if !show.status.success() { return None; }
    String::from_utf8(show.stdout).ok().map(normalize_newlines)
}

fn baseline_from_checkpoint(root: &Path, rel: &str) -> Option<String> {
    let checkpoints_dir = root.join(".vibelign").join("checkpoints");
    let latest = std::fs::read_dir(&checkpoints_dir).ok()?
        .flatten()
        .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
        .map(|e| e.file_name())
        .max()?; // 디렉토리명이 ISO timestamp prefix라 사전순 max = 최신
    let baseline_path = checkpoints_dir.join(latest).join("files").join(rel);
    let bytes = std::fs::read(&baseline_path).ok()?;
    if bytes.contains(&0) { return None; }
    let bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(&bytes);
    let s = std::str::from_utf8(bytes).ok()?;
    Some(normalize_newlines(s))
}

fn normalize_newlines(s: impl Into<String>) -> String {
    s.into().replace("\r\n", "\n").replace('\r', "\n")
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn write(root: &Path, rel: &str, content: &[u8]) {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, content).unwrap();
    }

    #[test]
    fn baseline_none_when_no_git_no_checkpoint() {
        let root = TempDir::new().unwrap();
        write(root.path(), "src/main.ts", b"new\n");
        let (text, src) = resolve_baseline(root.path(), "src/main.ts");
        assert!(text.is_none());
        assert_eq!(src, BaselineSource::None);
    }

    #[test]
    fn baseline_from_checkpoint_when_no_git() {
        let root = TempDir::new().unwrap();
        write(root.path(), "src/main.ts", b"new content\n");
        write(
            root.path(),
            ".vibelign/checkpoints/20260101T000000Z_init/files/src/main.ts",
            b"old content\n",
        );
        let (text, src) = resolve_baseline(root.path(), "src/main.ts");
        assert_eq!(text.as_deref(), Some("old content\n"));
        assert_eq!(src, BaselineSource::Checkpoint);
    }

    #[test]
    fn baseline_picks_latest_checkpoint_by_name() {
        let root = TempDir::new().unwrap();
        write(root.path(), ".vibelign/checkpoints/20260101T000000Z_a/files/src/main.ts", b"v1\n");
        write(root.path(), ".vibelign/checkpoints/20260201T000000Z_b/files/src/main.ts", b"v2\n");
        let (text, src) = resolve_baseline(root.path(), "src/main.ts");
        assert_eq!(text.as_deref(), Some("v2\n"));
        assert_eq!(src, BaselineSource::Checkpoint);
    }

    #[test]
    fn baseline_from_git_head_when_repo_present() {
        // git이 PATH에 없거나 호스트 정책상 실패하면 테스트 자체를 skip한다.
        let probe = std::process::Command::new("git").arg("--version").output();
        if probe.as_ref().map(|o| !o.status.success()).unwrap_or(true) { return; }

        let root = TempDir::new().unwrap();
        let run = |args: &[&str]| {
            let st = std::process::Command::new("git")
                .args(["-C"]).arg(root.path()).args(args)
                .status().expect("git");
            assert!(st.success(), "git {args:?} failed");
        };
        run(&["init", "-q", "-b", "main"]);
        run(&["config", "user.email", "t@t.dev"]);
        run(&["config", "user.name", "t"]);
        write(root.path(), "src/main.ts", b"old\n");
        run(&["add", "src/main.ts"]);
        run(&["commit", "-q", "-m", "init"]);
        // HEAD commit 후 작업트리만 수정
        write(root.path(), "src/main.ts", b"new\n");

        let (text, src) = resolve_baseline(root.path(), "src/main.ts");
        assert_eq!(text.as_deref(), Some("old\n"));
        assert_eq!(src, BaselineSource::Git);
    }
}
