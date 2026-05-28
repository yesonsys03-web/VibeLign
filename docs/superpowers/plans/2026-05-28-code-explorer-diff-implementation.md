# Code Explorer Diff 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Code Explorer 뷰어에 unified inline diff 모드 추가 — 마지막 git 커밋(없으면 최신 VibeLign checkpoint) 대비 변경된 줄을 녹/빨로 하이라이트.

**Architecture:** Rust 백엔드에 `read_code_file_diff` Tauri 커맨드 추가 — 기존 `code_access` 보안 가드로 경로 검증 후 (1) 현재 내용 읽기 (2) git→checkpoint→none 계층형 baseline 확보 (3) `similar` 크레이트로 line diff 계산 → 구조화된 라인 배열 반환. 프론트는 `DiffLine` 컴포넌트로 그리고 `CodeFileViewer`에 `diffMode` 토글 추가.

**Tech Stack:** Rust (Tauri 2, `similar` 2.x, `std::process::Command` for git), TypeScript/React, Vitest.

**Spec:** `docs/superpowers/specs/2026-05-28-code-explorer-diff-design.md`

---

## File Structure

**Rust (`vibelign-gui/src-tauri/`):**
- Modify: `Cargo.toml` (4-10줄 dependencies 블록) — `similar = "2"` 추가
- Modify: `Cargo.lock` — cargo가 자동 갱신 (수동 편집 금지)
- Create: `src/code_diff.rs` — diff 핵심 로직 (baseline 확보 + similar diff + DiffLine 타입)
- Modify: `src/code_access.rs` (38-83줄 부근) — 헬퍼 가시성 조정(`pub(crate) fn normalize_relative_input` 등 노출 필요한 것만)
- Modify: `src/lib.rs:2` — `mod code_diff;` 추가
- Modify: `src/lib.rs:127-128` — invoke_handler에 `commands::code::read_code_file_diff` 등록
- Modify: `src/commands/code.rs` — `read_code_file_diff` Tauri 커맨드 추가

**TypeScript (`vibelign-gui/src/`):**
- Modify: `lib/vib/types.ts:540` 부근(`CodeFileReadResult` 옆) — `DiffLine`, `CodeFileDiffResult` 인터페이스 추가
- Modify: `lib/vib/code.ts` — `readCodeFileDiff` 브리지 함수 추가
- Create: `components/code-explorer/DiffLine.tsx` — 한 줄짜리 diff 라인 컴포넌트
- Modify: `components/code-explorer/CodeFileViewer.tsx` — `diffMode` + `diff` prop, diff 모드 렌더링 분기, 헤더 토글
- Modify: `pages/CodeExplorer.tsx` — `readCodeFileDiff` 호출, `diffMode` 상태 관리, 자동 ON 규칙

각 파일은 단일 책임: `code_diff.rs`는 diff 산출, `DiffLine.tsx`는 한 줄 렌더, `CodeFileViewer`는 모드 분기/헤더, `CodeExplorer`는 상태/호출.

---

## Task 1: Rust `similar` 크레이트 의존성 추가

**Files:**
- Modify: `vibelign-gui/src-tauri/Cargo.toml` (dependencies 블록)
- Modify (자동): `vibelign-gui/src-tauri/Cargo.lock`

- [ ] **Step 1: dependencies에 `similar` 추가**

`vibelign-gui/src-tauri/Cargo.toml`의 `[dependencies]` 블록에 한 줄 삽입:

```toml
[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-opener = "2"
tauri-plugin-dialog = "2"
tauri-plugin-store = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
sha2 = "0.10"
similar = "2"
tauri-plugin-updater = "2.10.1"
tauri-plugin-process = "2.3.1"
vibelign-core = { path = "../../vibelign-core" }
```

- [ ] **Step 2: cargo가 lockfile을 채우도록 빌드**

Run: `cd vibelign-gui/src-tauri && cargo build 2>&1 | tail -5`
Expected: 컴파일 성공, Cargo.lock에 `similar` 항목 추가.

- [ ] **Step 3: 추가 검증**

Run: `grep -c '^name = "similar"$' vibelign-gui/src-tauri/Cargo.lock`
Expected: `1` (정확히 1개 entry).

- [ ] **Step 4: 커밋**

```bash
git add vibelign-gui/src-tauri/Cargo.toml vibelign-gui/src-tauri/Cargo.lock
git commit -m "deps: src-tauri에 similar 2 추가 (Code Explorer diff용)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `code_diff.rs` 타입 + baseline 확보 함수 (TDD)

**Files:**
- Create: `vibelign-gui/src-tauri/src/code_diff.rs`
- Modify: `vibelign-gui/src-tauri/src/lib.rs:2` (모듈 선언)

> `code_access.rs` 헬퍼는 `read_code_file_under`(이미 `pub(crate)`)를 통해 내부적으로 호출되므로 추가 가시성 조정 불필요.

- [ ] **Step 1: 실패하는 테스트 먼저 작성**

Create `vibelign-gui/src-tauri/src/code_diff.rs`:

```rust
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
```

- [ ] **Step 2: 모듈 등록**

Edit `vibelign-gui/src-tauri/src/lib.rs:2` — `mod code_access;` 다음 줄에 추가:

```rust
mod code_access;
mod code_diff;
mod commands;
```

- [ ] **Step 3: 테스트 실행하여 통과 확인**

Run: `cd vibelign-gui/src-tauri && cargo test code_diff:: -- --nocapture 2>&1 | tail -20`
Expected: `test result: ok. 4 passed; 0 failed` (none, checkpoint, latest-checkpoint, git)

- [ ] **Step 4: 커밋**

```bash
git add vibelign-gui/src-tauri/src/code_diff.rs vibelign-gui/src-tauri/src/lib.rs
git commit -m "feat(diff): baseline 확보 — git→checkpoint→none 계층형

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: similar로 line diff 계산 (TDD)

**Files:**
- Modify: `vibelign-gui/src-tauri/src/code_diff.rs` (compute_line_diff 추가)

- [ ] **Step 1: 실패하는 테스트 추가**

`code_diff.rs` `mod tests` 안에 추가:

```rust
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
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

Run: `cd vibelign-gui/src-tauri && cargo test code_diff::tests::diff_ 2>&1 | tail -10`
Expected: 컴파일 에러 `cannot find function 'compute_line_diff'`

- [ ] **Step 3: 구현**

`code_diff.rs`에 함수 2개 추가(파일 끝, `mod tests` 위):

```rust
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd vibelign-gui/src-tauri && cargo test code_diff:: 2>&1 | tail -10`
Expected: `test result: ok. 6 passed; 0 failed` (Task 2의 3 + 신규 3)

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src-tauri/src/code_diff.rs
git commit -m "feat(diff): similar로 line diff + added/removed 카운트

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `read_code_file_diff` Tauri 커맨드 (TDD — 통합 경로 검증)

**Files:**
- Modify: `vibelign-gui/src-tauri/src/code_diff.rs` (top-level `build_file_diff` 함수)
- Modify: `vibelign-gui/src-tauri/src/commands/code.rs` (Tauri 커맨드)
- Modify: `vibelign-gui/src-tauri/src/lib.rs:127-128` (invoke_handler 등록)

- [ ] **Step 1: 실패 테스트 — 경로 가드와 baseline 없음 결과**

`code_diff.rs` `mod tests` 끝에 추가:

```rust
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
```

- [ ] **Step 2: 실행하여 실패 확인**

Run: `cd vibelign-gui/src-tauri && cargo test code_diff::tests::build_diff_ 2>&1 | tail -10`
Expected: 컴파일 에러 `cannot find function 'build_file_diff'`

- [ ] **Step 3: `build_file_diff` 구현**

`code_diff.rs` `mod tests` 위에 추가:

```rust
use crate::code_access::read_code_file_under;

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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd vibelign-gui/src-tauri && cargo test code_diff:: 2>&1 | tail -15`
Expected: `test result: ok. 11 passed; 0 failed` (Task 2의 4 + Task 3의 3 + 신규 4)

- [ ] **Step 5: Tauri 커맨드 추가**

Edit `vibelign-gui/src-tauri/src/commands/code.rs` — 파일 끝에 추가:

```rust
use crate::code_diff::{build_file_diff, CodeFileDiffResult};

#[tauri::command]
pub(crate) fn read_code_file_diff(root: String, path: String) -> Result<CodeFileDiffResult, String> {
    let root_path = PathBuf::from(root);
    build_file_diff(&root_path, &path)
}
```

- [ ] **Step 6: invoke_handler 등록**

Edit `vibelign-gui/src-tauri/src/lib.rs:127-128` — `read_code_file` 다음 줄에 추가:

```rust
            commands::code::read_code_file,
            commands::code::read_code_file_diff,
            commands::code::list_code_files,
```

- [ ] **Step 7: 전체 빌드 확인**

Run: `cd vibelign-gui/src-tauri && cargo build 2>&1 | tail -5`
Expected: 컴파일 성공.

- [ ] **Step 8: 커밋**

```bash
git add vibelign-gui/src-tauri/src/code_diff.rs vibelign-gui/src-tauri/src/commands/code.rs vibelign-gui/src-tauri/src/lib.rs
git commit -m "feat(diff): read_code_file_diff Tauri 커맨드 + build_file_diff

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: TypeScript 타입 + 브리지 함수

**Files:**
- Modify: `vibelign-gui/src/lib/vib/types.ts` (540줄 부근, `CodeFileReadResult` 옆)
- Modify: `vibelign-gui/src/lib/vib/code.ts` (`readCodeFile` 옆)

- [ ] **Step 1: 타입 추가**

Edit `vibelign-gui/src/lib/vib/types.ts:547` — `CodeFileReadResult` 닫는 `}` 다음, `// === ANCHOR: TYPES_END ===` **앞에** 삽입:

```typescript
export type DiffLineKind = "context" | "added" | "removed";

export interface DiffLine {
  kind: DiffLineKind;
  old_no: number | null;
  new_no: number | null;
  text: string;
}

export type BaselineSource = "git" | "checkpoint" | "none";

export interface CodeFileDiffResult {
  path: string;
  language: string;
  baseline_source: BaselineSource;
  added: number;
  removed: number;
  lines: DiffLine[];
}
```

- [ ] **Step 2: 브리지 함수 추가**

Edit `vibelign-gui/src/lib/vib/code.ts` — 파일 끝에 추가:

```typescript
import type { CodeFileDiffResult } from "./types";

export async function readCodeFileDiff(root: string, path: string): Promise<CodeFileDiffResult> {
  return invoke<CodeFileDiffResult>("read_code_file_diff", {
    root,
    path: normalizeBridgePath(path),
  });
}
```

> 주의: 기존 import 줄 (`import type { CodeFileEntry, CodeFileReadResult } from "./types";`)에 `CodeFileDiffResult`를 추가하는 형태가 더 깔끔하면 그렇게 통합해도 됨.

- [ ] **Step 3: vib 모듈 재export 확인**

Run: `grep -n "readCodeFile\|CodeFileDiffResult\|DiffLine" vibelign-gui/src/lib/vib/index.ts vibelign-gui/src/lib/vib/code.ts vibelign-gui/src/lib/vib/types.ts`
Expected: types.ts에 신규 타입, code.ts에 `readCodeFileDiff`. index.ts가 와일드카드 re-export면 자동 노출.

만약 index.ts가 명시 re-export라면 `readCodeFileDiff`, `CodeFileDiffResult`, `DiffLine`, `BaselineSource`, `DiffLineKind`를 추가.

- [ ] **Step 4: 타입체크**

Run: `cd vibelign-gui && npx tsc -p tsconfig.json --noEmit 2>&1 | tail -10`
Expected: 신규 타입 관련 에러 없음.

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/lib/vib/types.ts vibelign-gui/src/lib/vib/code.ts vibelign-gui/src/lib/vib/index.ts
git commit -m "feat(diff): TS 타입 + readCodeFileDiff 브리지

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: `DiffLine.tsx` 컴포넌트

**Files:**
- Create: `vibelign-gui/src/components/code-explorer/DiffLine.tsx`

- [ ] **Step 1: 컴포넌트 작성**

Create `vibelign-gui/src/components/code-explorer/DiffLine.tsx`:

```tsx
import type { DiffLine as DiffLineType } from "../../lib/vib/types";

interface Props {
  line: DiffLineType;
}

const BG: Record<DiffLineType["kind"], string> = {
  context: "transparent",
  added: "rgba(46, 160, 67, 0.18)",   // 녹색 배경
  removed: "rgba(248, 81, 73, 0.18)", // 빨강 배경
};

const MARK: Record<DiffLineType["kind"], string> = {
  context: " ",
  added: "+",
  removed: "-",
};

export default function DiffLine({ line }: Props) {
  const oldNo = line.old_no === null ? "" : String(line.old_no);
  const newNo = line.new_no === null ? "" : String(line.new_no);
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "44px 44px 18px 1fr",
        fontFamily: "ui-monospace, Menlo, Consolas, monospace",
        background: BG[line.kind],
        whiteSpace: "pre",
      }}
    >
      <span style={{ textAlign: "right", paddingRight: 6, color: "#888" }}>{oldNo}</span>
      <span style={{ textAlign: "right", paddingRight: 6, color: "#888" }}>{newNo}</span>
      <span style={{ textAlign: "center", color: line.kind === "added" ? "#2ea043" : line.kind === "removed" ? "#f85149" : "#888" }}>
        {MARK[line.kind]}
      </span>
      <span>{line.text || " "}</span>
    </div>
  );
}
```

- [ ] **Step 2: 타입체크**

Run: `cd vibelign-gui && npx tsc -p tsconfig.json --noEmit 2>&1 | tail -5`
Expected: 에러 없음.

- [ ] **Step 3: 커밋**

```bash
git add vibelign-gui/src/components/code-explorer/DiffLine.tsx
git commit -m "feat(diff): DiffLine 컴포넌트 — 2단 gutter + ± 마커 + 배경색

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: `CodeFileViewer` 통합 — `diff` prop + Diff 토글

**Files:**
- Modify: `vibelign-gui/src/components/code-explorer/CodeFileViewer.tsx` (전면 수정)

- [ ] **Step 1: 새 props 정의 + 분기 렌더**

`vibelign-gui/src/components/code-explorer/CodeFileViewer.tsx`를 다음으로 교체:

```tsx
import type { CodeFileReadResult, CodeFileDiffResult } from "../../lib/vib/types";
import CodeLine from "./CodeLine";
import DiffLine from "./DiffLine";

interface CodeFileViewerProps {
  selectedPath: string | null;
  file: CodeFileReadResult | null;
  diff: CodeFileDiffResult | null;
  diffMode: boolean;
  onToggleDiffMode: () => void;
  isLoading: boolean;
  error: string | null;
}

export default function CodeFileViewer({
  selectedPath, file, diff, diffMode, onToggleDiffMode, isLoading, error,
}: CodeFileViewerProps) {
  if (!selectedPath) {
    return <div className="card" style={{ height: "100%", padding: 24 }}>왼쪽 트리에서 코드 파일을 선택하세요.</div>;
  }
  if (isLoading) {
    return <div className="card" style={{ height: "100%", padding: 24 }}>코드 파일을 읽는 중입니다…</div>;
  }
  if (error) {
    return <div className="alert-error" style={{ margin: 16 }}>{error}</div>;
  }
  if (!file) {
    return <div className="card" style={{ height: "100%", padding: 24 }}>표시할 코드가 없습니다.</div>;
  }

  const hasBaseline = diff !== null && diff.baseline_source !== "none";
  const toggleDisabled = !hasBaseline;
  const toggleTitle = toggleDisabled ? "비교할 기준선이 없습니다" : (diffMode ? "평면 뷰로 전환" : "Diff 뷰로 전환");
  const badge = hasBaseline ? `+${diff!.added} −${diff!.removed}` : "";

  const lines = file.content.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();

  return (
    <div className="card" style={{ height: "100%", padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "10px 12px", borderBottom: "2px solid #1A1A1A", display: "flex", gap: 10, alignItems: "center" }}>
        <strong style={{ overflowWrap: "anywhere" }}>{file.path}</strong>
        <button
          type="button"
          onClick={onToggleDiffMode}
          disabled={toggleDisabled}
          title={toggleTitle}
          style={{
            fontSize: 11, padding: "3px 8px",
            background: diffMode && hasBaseline ? "rgba(46,160,67,0.18)" : "transparent",
            border: "1px solid #333", borderRadius: 4,
            cursor: toggleDisabled ? "not-allowed" : "pointer",
            opacity: toggleDisabled ? 0.5 : 1,
          }}
        >
          Diff {badge && <span style={{ marginLeft: 6, color: "#888" }}>{badge}</span>}
        </button>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#666" }}>
          {file.language} · {file.line_count} lines · {file.size_bytes} bytes
        </span>
      </div>
      <div style={{ flex: 1, overflow: "auto", fontSize: 13, lineHeight: 1.55 }}>
        {diffMode && diff && hasBaseline
          ? diff.lines.map((line, i) => <DiffLine key={i} line={line} />)
          : lines.map((line, index) => <CodeLine key={index} lineNumber={index + 1} text={line} />)}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 타입체크**

Run: `cd vibelign-gui && npx tsc -p tsconfig.json --noEmit 2>&1 | tail -5`
Expected: 호출자(`CodeExplorer.tsx`)가 아직 새 props를 안 줘서 에러 발생 — Task 8에서 해결.
이 단계에서는 viewer 파일 자체만 에러 없으면 OK.

- [ ] **Step 3: (커밋은 Task 8과 함께 — viewer/page는 짝)**

이 단계는 단독 커밋하지 않음. 다음 태스크에서 page를 함께 수정한 뒤 커밋.

---

## Task 8: `CodeExplorer.tsx` — diff fetch + diffMode 상태 + 자동 ON

**Files:**
- Modify: `vibelign-gui/src/pages/CodeExplorer.tsx`

- [ ] **Step 1: import 추가**

`vibelign-gui/src/pages/CodeExplorer.tsx:8`을 다음으로 교체:

```tsx
import { listCodeFiles, readCodeFile, readCodeFileDiff, type CodeFileEntry, type CodeFileReadResult, type CodeFileDiffResult } from "../lib/vib";
```

- [ ] **Step 2: 상태 추가**

`CodeExplorer` 컴포넌트 안 기존 useState 블록(15-23줄) 바로 아래에 추가:

```tsx
  const [selectedDiff, setSelectedDiff] = useState<CodeFileDiffResult | null>(null);
  const [diffMode, setDiffMode] = useState<boolean>(false);
```

- [ ] **Step 3: 파일 로드 useEffect를 diff까지 함께 가져오도록 변경**

46-67줄 `useEffect`를 다음으로 교체:

```tsx
  useEffect(() => {
    let cancelled = false;
    if (!selectedPath) {
      setSelectedFile(null);
      setSelectedDiff(null);
      setDiffMode(false);
      setFileError(null);
      return () => { cancelled = true; };
    }
    setIsLoadingFile(true);
    setSelectedFile(null);
    setSelectedDiff(null);
    setFileError(null);
    Promise.all([
      readCodeFile(projectDir, selectedPath),
      readCodeFileDiff(projectDir, selectedPath).catch(() => null),
    ])
      .then(([fileResult, diffResult]) => {
        if (cancelled) return;
        setSelectedFile(fileResult);
        setSelectedDiff(diffResult);
        // 자동 ON 규칙: baseline 있고 변경 있음 → diffMode = true
        const hasBaseline = diffResult !== null && diffResult.baseline_source !== "none";
        const hasChanges = diffResult !== null && (diffResult.added + diffResult.removed) > 0;
        setDiffMode(hasBaseline && hasChanges);
      })
      .catch((error: unknown) => {
        if (!cancelled) setFileError(error instanceof Error ? error.message : "코드 파일을 읽을 수 없어요");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingFile(false);
      });
    return () => { cancelled = true; };
  }, [projectDir, selectedPath]);
```

- [ ] **Step 4: `viewer` prop에 새 인자 전달**

기존 81줄을 다음으로 교체:

```tsx
      viewer={<CodeFileViewer
        selectedPath={selectedPath}
        file={selectedFile}
        diff={selectedDiff}
        diffMode={diffMode}
        onToggleDiffMode={() => setDiffMode((v) => !v)}
        isLoading={isLoadingFile}
        error={fileError}
      />}
```

- [ ] **Step 5: 타입체크**

Run: `cd vibelign-gui && npx tsc -p tsconfig.json --noEmit 2>&1 | tail -5`
Expected: 에러 없음.

- [ ] **Step 6: 빌드 + 전체 Rust 테스트 회귀**

Run (병렬 가능):
- `cd vibelign-gui && npm run build 2>&1 | tail -10`
- `cd vibelign-gui/src-tauri && cargo test 2>&1 | tail -10`

Expected: 양쪽 모두 성공. cargo test는 Task 2-4의 신규 + 기존 11 통과.

- [ ] **Step 7: 커밋 (Task 7 viewer + Task 8 page)**

```bash
git add vibelign-gui/src/components/code-explorer/CodeFileViewer.tsx vibelign-gui/src/pages/CodeExplorer.tsx
git commit -m "feat(diff): CodeFileViewer diffMode 통합 + 자동 ON 규칙

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: 수동 QA (재빌드 후 실제 동작 확인)

**Files:** (없음 — 실행만)

- [ ] **Step 1: GUI dev 빌드 실행**

Run: `cd vibelign-gui && npm run tauri dev 2>&1 | tail -20`
Expected: Tauri 앱 실행, 콘솔에 컴파일 에러 없음.

- [ ] **Step 2: QA 체크리스트 (수동)**

VibeLign GUI에서 다음을 확인:

1. **git 추적 파일 + HEAD와 차이 있음**: Code Explorer에서 작업 트리에 수정된 파일 선택 → 자동으로 diff 뷰, 녹/빨 줄 보임, 헤더 `Diff +N −M` 뱃지.
2. **git 추적 파일 + 변경 없음**: HEAD와 동일한 파일 선택 → diff 가능하지만 자동 OFF(평면 뷰), 토글 활성, +0 −0.
3. **신규 untracked 파일**: git add 안 한 새 파일 → checkpoint도 없으면 토글 비활성("비교할 기준선이 없습니다"), 평면 뷰.
4. **git 없는 프로젝트 + checkpoint 있음**: 비git 디렉토리에서 `.vibelign/checkpoints/...` 시드 후 변경 → checkpoint 대비 diff 보임.
5. **`.swift` 파일**: Swift 파일도 diff 정상 동작 (Task v2.2.21 회귀 확인).
6. **토글 수동 ON/OFF**: 클릭마다 diff↔평면 전환.

- [ ] **Step 3: 결과 기록**

문제 발견 시 어떤 케이스에서 어떤 증상인지 기록 → 별도 버그 픽스 사이클. 모두 통과면 완료.

- [ ] **Step 4: 변경 없음 — 커밋 생략**

QA만 했으므로 커밋 없음.

---

## Task 10: 버전 bump + release 커밋

**Files:**
- Modify: 버전 소스 6개 (pyproject.toml, vibelign/__init__.py, vibelign-core/Cargo.toml, vibelign-gui/package.json, vibelign-gui/src-tauri/Cargo.toml, vibelign-gui/src-tauri/tauri.conf.json)
- Modify: 락 4개 (uv.lock, vibelign-core/Cargo.lock, vibelign-gui/package-lock.json, vibelign-gui/src-tauri/Cargo.lock)

- [ ] **Step 1: 현재 버전 확인**

Run: `grep -h '"2\.2\.' pyproject.toml vibelign/__init__.py 2>/dev/null | head -2`
Expected: 직전 release 버전(예: `2.2.21`). 다음 버전은 patch +1 = `2.2.22`.

- [ ] **Step 2: 6개 소스 + 4개 락 모두 새 버전으로 일괄 변경**

이전 release 커밋(v2.2.20→v2.2.21, `ebfa120`) 파일 리스트와 동일 패턴으로 정확히 한 줄씩 교체.
각 파일에서 `name = "..."` 또는 `"productName": "..."` 같은 식별자와 함께 unique한 컨텍스트로 교체 (단순 `"2.2.21"` replace_all은 다른 의존성 버전과 충돌 위험).

- [ ] **Step 3: 일관성 검증**

Run: `grep -rln "2\.2\.21" pyproject.toml uv.lock vibelign/__init__.py vibelign-core/Cargo.toml vibelign-core/Cargo.lock vibelign-gui/package.json vibelign-gui/package-lock.json vibelign-gui/src-tauri/Cargo.toml vibelign-gui/src-tauri/Cargo.lock vibelign-gui/src-tauri/tauri.conf.json`
Expected: 0줄 (모두 새 버전으로 바뀜).

Run: `grep -rln "2\.2\.22" 위와 동일 목록`
Expected: 10개 파일 모두 매칭.

- [ ] **Step 4: 빌드/테스트 회귀**

Run: `cd vibelign-gui/src-tauri && cargo test 2>&1 | tail -5`
Expected: 전 테스트 통과 (Cargo.lock 정합성 OK 증명).

- [ ] **Step 5: release 커밋**

```bash
git add pyproject.toml uv.lock vibelign/__init__.py \
  vibelign-core/Cargo.toml vibelign-core/Cargo.lock \
  vibelign-gui/package.json vibelign-gui/package-lock.json \
  vibelign-gui/src-tauri/Cargo.toml vibelign-gui/src-tauri/Cargo.lock \
  vibelign-gui/src-tauri/tauri.conf.json

git commit -m "release(v2.2.22): Code Explorer Diff 뷰 — unified inline

git HEAD → VibeLign checkpoint → none 계층형 baseline.
similar 크레이트 + 새 Tauri 커맨드 read_code_file_diff.
뷰어에 Diff 토글 + 자동 ON 규칙 (baseline 있고 변경 있음).

- code_diff.rs: baseline 확보 + similar line diff + 카운트 (10 테스트)
- DiffLine.tsx: 2단 gutter + ± 마커 + 녹/빨 배경
- CodeFileViewer: diffMode prop + Diff 토글 (+N −M 뱃지)
- CodeExplorer: readCodeFileDiff 호출 + 자동 ON 규칙
- 버전 2.2.21 → 2.2.22 통일 (소스 6 + lockfile 4)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: 푸시 + 태그 (사용자 확인 후)**

```bash
git push origin main
git tag v2.2.22 && git push origin v2.2.22
```

> 외부에 반영되는 단계 — 사용자 명시 승인 후에만 실행.

---

## 완료 기준

- 모든 task의 체크박스가 채워짐.
- `cargo test` 전부 통과 (신규 ≥11 + 기존 ≥11).
- `npm run build`(또는 `tsc --noEmit`) TypeScript 에러 없음.
- Task 9 QA 6개 케이스 모두 기대대로 동작.
- v2.2.22 release 커밋 + (승인 후) 푸시/태그.
