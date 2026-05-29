use std::path::Path;

use crate::code_access::read_code_file_under;

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

/// Windows: GUI 프로세스가 콘솔 자식(git)을 spawn 할 때 콘솔 창이 깜빡였다 사라지는 것을 막는다.
/// (code_access/vib_bridge/watch 등에서 쓰는 CREATE_NO_WINDOW 패턴과 동일.)
fn apply_no_window(cmd: &mut std::process::Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    #[cfg(not(windows))]
    let _ = cmd;
}

fn baseline_from_git(root: &Path, rel: &str) -> Option<String> {
    // `git show HEAD:<rel>` 한 번이면 충분하다: 비-git 디렉토리·HEAD 없음(빈 레포)·HEAD에 없는
    // (추적 안 된) 파일은 모두 비-제로 종료로 떨어져 None 이 된다.
    // (Windows 는 프로세스 spawn 비용이 커서 rev-parse+ls-files+show 3회를 1회로 축소 —
    //  파일 선택 시 코드 표시가 지연되던 주요 원인.)
    let mut cmd = std::process::Command::new("git");
    cmd.args(["-C"]).arg(root)
        .arg("show").arg(format!("HEAD:{}", rel));
    apply_no_window(&mut cmd);
    let show = cmd.output().ok()?;
    if !show.status.success() { return None; }
    String::from_utf8(show.stdout).ok().map(normalize_newlines)
}

fn baseline_from_checkpoint(root: &Path, rel: &str) -> Option<String> {
    let checkpoints_dir = root.join(".vibelign").join("checkpoints");
    // timestamp 형식 디렉터리만 후보로 둔다 — 스테이징/인덱스 같은 비-체크포인트 디렉터리가
    // 사전순으로 더 높게 정렬돼 baseline 을 가로채는 것을 막는다.
    let mut names: Vec<_> = std::fs::read_dir(&checkpoints_dir).ok()?
        .flatten()
        .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
        .map(|e| e.file_name())
        .filter(|name| is_checkpoint_dir_name(&name.to_string_lossy()))
        .collect();
    // 디렉터리명이 zero-padded timestamp prefix라 사전순 정렬 후 뒤에서부터 = 최신 우선.
    names.sort();
    // 최신부터 훑어 이 파일의 스냅샷을 가진 첫 체크포인트를 baseline 으로 쓴다.
    // (최신이 해당 파일을 안 가졌으면—삭제 후 재생성 등—이전 체크포인트로 폴백.)
    for name in names.into_iter().rev() {
        let baseline_path = checkpoints_dir.join(&name).join("files").join(rel);
        let bytes = match std::fs::read(&baseline_path) {
            Ok(b) => b,
            Err(_) => continue, // 이 체크포인트엔 이 파일 없음 → 이전 후보로 폴백
        };
        // 이 파일을 가진 가장 최근 체크포인트로 baseline 확정.
        // 바이너리/비-UTF8 이면 텍스트 diff 불가 → 기존과 동일하게 baseline 없음(None).
        if bytes.contains(&0) { return None; }
        let bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(&bytes);
        let s = std::str::from_utf8(bytes).ok()?;
        return Some(normalize_newlines(s));
    }
    None
}

/// 체크포인트 디렉터리 이름인지: `YYYYMMDD` + `T` + `hhmmss…` (8자리 + 'T' + 최소 6자리).
/// 정확한 마이크로초 자릿수는 버전마다 다를 수 있어 prefix 만 검사한다.
fn is_checkpoint_dir_name(name: &str) -> bool {
    let b = name.as_bytes();
    b.len() >= 15
        && b[..8].iter().all(u8::is_ascii_digit)
        && b[8] == b'T'
        && b[9..15].iter().all(u8::is_ascii_digit)
}

fn normalize_newlines(s: impl Into<String>) -> String {
    s.into().replace("\r\n", "\n").replace('\r', "\n")
}

pub(crate) fn compute_line_diff(baseline: &str, current: &str) -> Vec<DiffLine> {
    use similar::{ChangeTag, TextDiff};
    let diff = TextDiff::from_lines(baseline, current);
    let mut out = Vec::new();
    let mut old_no: u32 = 0;
    let mut new_no: u32 = 0;
    for change in diff.iter_all_changes() {
        // similar는 라인 끝 '\n'을 포함해 돌려준다 — 표시용으로 제거.
        let text = change.value().trim_end_matches('\n').to_string();
        match change.tag() {
            ChangeTag::Equal => {
                old_no += 1; new_no += 1;
                out.push(DiffLine { kind: DiffKind::Context, old_no: Some(old_no), new_no: Some(new_no), text });
            }
            ChangeTag::Delete => {
                old_no += 1;
                out.push(DiffLine { kind: DiffKind::Removed, old_no: Some(old_no), new_no: None, text });
            }
            ChangeTag::Insert => {
                new_no += 1;
                out.push(DiffLine { kind: DiffKind::Added, old_no: None, new_no: Some(new_no), text });
            }
        }
    }
    out
}

pub(crate) fn count_changes(lines: &[DiffLine]) -> (u32, u32) {
    let mut added = 0u32; let mut removed = 0u32;
    for l in lines {
        match l.kind {
            DiffKind::Added => added += 1,
            DiffKind::Removed => removed += 1,
            DiffKind::Context => {}
        }
    }
    (added, removed)
}

pub(crate) fn build_file_diff(root: &Path, rel: &str) -> Result<CodeFileDiffResult, String> {
    // 1. 사용자 노출 relpath를 기존 가드로 검증 (현재 파일 읽기가 동일 가드 통과)
    let current = read_code_file_under(root, rel)?;
    // current.path는 root 기준 정규화된 relpath (\\→/, 캐노니컬라이즈됨)
    let canonical_rel = current.path.clone();
    // 2. baseline 확보 (정규화된 relpath만 사용 → 경로 탈출 불가)
    let (baseline_text, source) = resolve_baseline(root, &canonical_rel);
    // 3. diff 계산 (baseline 없으면 빈 문자열 대신 current 자체를 양쪽에 → all context)
    let lines = match baseline_text {
        Some(b) => compute_line_diff(&b, &current.content),
        None => compute_line_diff(&current.content, &current.content),
    };
    let (added, removed) = count_changes(&lines);
    Ok(CodeFileDiffResult {
        path: canonical_rel,
        language: current.language,
        baseline_source: source,
        added,
        removed,
        lines,
    })
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
    fn baseline_falls_back_when_latest_checkpoint_lacks_file() {
        // 최신 체크포인트는 이 파일을 안 가졌고(삭제 후 재생성 등), 이전 체크포인트만 가졌다.
        // 최신만 보고 None 을 돌려주면 안 되고, 파일을 가진 가장 최근 체크포인트로 폴백해야 한다.
        let root = TempDir::new().unwrap();
        write(root.path(), ".vibelign/checkpoints/20260201T000000Z_new/files/other.ts", b"x\n");
        write(root.path(), ".vibelign/checkpoints/20260101T000000Z_old/files/src/main.ts", b"old content\n");
        let (text, src) = resolve_baseline(root.path(), "src/main.ts");
        assert_eq!(text.as_deref(), Some("old content\n"));
        assert_eq!(src, BaselineSource::Checkpoint);
    }

    #[test]
    fn baseline_ignores_non_checkpoint_sibling_dirs() {
        // checkpoints/ 아래 timestamp 형식이 아닌 디렉터리(사전순으로 "2026.." 보다 높게 정렬)는
        // 후보에서 제외돼야 한다 — 그 안의 파일이 진짜 체크포인트 baseline 을 가로채면 안 된다.
        let root = TempDir::new().unwrap();
        write(root.path(), ".vibelign/checkpoints/20260101T000000Z_real/files/src/main.ts", b"real\n");
        write(root.path(), ".vibelign/checkpoints/zz_not_a_checkpoint/files/src/main.ts", b"BOGUS\n");
        let (text, src) = resolve_baseline(root.path(), "src/main.ts");
        assert_eq!(text.as_deref(), Some("real\n"));
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

    #[test]
    fn git_baseline_excludes_untracked_file_in_repo() {
        // git 저장소이지만 HEAD에 없는(추적 안 된) 파일은 git baseline 이 아니어야 한다.
        // 단일 `git show HEAD:rel` 로 축소해도 이 동작이 유지되는지 잠그는 특성 테스트.
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
        write(root.path(), "tracked.ts", b"x\n");
        run(&["add", "tracked.ts"]);
        run(&["commit", "-q", "-m", "init"]);
        write(root.path(), "untracked.ts", b"y\n"); // add 안 함 → HEAD에 없음

        let (text, src) = resolve_baseline(root.path(), "untracked.ts");
        assert!(text.is_none());
        assert_ne!(src, BaselineSource::Git);
    }

    #[test]
    fn diff_marks_added_and_removed_lines() {
        let baseline = "a\nb\nc\n";
        let current  = "a\nB\nc\nd\n";
        let lines = compute_line_diff(baseline, current);
        // 기대: a=context(1,1), b=removed(2,_), B=added(_,2), c=context(3,3), d=added(_,4)
        assert_eq!(lines.len(), 5);
        assert_eq!(lines[0].kind, DiffKind::Context);
        assert_eq!(lines[0].old_no, Some(1));
        assert_eq!(lines[0].new_no, Some(1));
        assert_eq!(lines[1].kind, DiffKind::Removed);
        assert_eq!(lines[1].old_no, Some(2));
        assert_eq!(lines[1].new_no, None);
        assert_eq!(lines[1].text, "b");
        assert_eq!(lines[2].kind, DiffKind::Added);
        assert_eq!(lines[2].old_no, None);
        assert_eq!(lines[2].new_no, Some(2));
        assert_eq!(lines[2].text, "B");
        assert_eq!(lines[4].kind, DiffKind::Added);
        assert_eq!(lines[4].new_no, Some(4));
    }

    #[test]
    fn diff_identical_inputs_all_context() {
        let s = "x\ny\nz\n";
        let lines = compute_line_diff(s, s);
        assert_eq!(lines.len(), 3);
        assert!(lines.iter().all(|l| l.kind == DiffKind::Context));
    }

    #[test]
    fn diff_counts_added_removed() {
        let baseline = "a\nb\n";
        let current  = "a\nB\nc\n";
        let (added, removed) = count_changes(&compute_line_diff(baseline, current));
        assert_eq!(added, 2);    // B, c
        assert_eq!(removed, 1);  // b
    }

    #[test]
    fn build_diff_baseline_none_returns_all_context() {
        let root = TempDir::new().unwrap();
        write(root.path(), "src/main.ts", b"a\nb\nc\n");
        let result = build_file_diff(root.path(), "src/main.ts").expect("ok");
        assert_eq!(result.baseline_source, BaselineSource::None);
        assert_eq!(result.added, 0);
        assert_eq!(result.removed, 0);
        assert_eq!(result.lines.len(), 3);
        assert!(result.lines.iter().all(|l| l.kind == DiffKind::Context));
        assert_eq!(result.language, "TypeScript");
    }

    #[test]
    fn build_diff_checkpoint_baseline_marks_changes() {
        let root = TempDir::new().unwrap();
        write(root.path(), "src/main.ts", b"a\nB\nc\n");
        write(root.path(), ".vibelign/checkpoints/20260101T000000Z_x/files/src/main.ts", b"a\nb\nc\n");
        let result = build_file_diff(root.path(), "src/main.ts").expect("ok");
        assert_eq!(result.baseline_source, BaselineSource::Checkpoint);
        assert_eq!(result.added, 1);
        assert_eq!(result.removed, 1);
    }

    #[test]
    fn build_diff_rejects_parent_escape() {
        let root = TempDir::new().unwrap();
        let err = build_file_diff(root.path(), "../secret.ts").expect_err("rejected");
        assert!(err.contains("허용되지 않은 경로"));
    }

    #[test]
    fn build_diff_rejects_ignored_dir() {
        let root = TempDir::new().unwrap();
        write(root.path(), "node_modules/x.ts", b"x\n");
        let err = build_file_diff(root.path(), "node_modules/x.ts").expect_err("rejected");
        assert!(err.contains("읽을 수 없는 경로"));
    }
}
