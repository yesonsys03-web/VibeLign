# Code Explorer 트리 변경 표시 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Code Explorer 사이드바 트리에서 변경된 파일을 `M`(수정)/`U`(신규) 배지로, 폴더는 변경 개수 배지로 표시 — git status 기반.

**Architecture:** Rust 백엔드에 `git_status.rs` 모듈 추가 — `git status --porcelain -z` 한 번 호출로 변경 경로 집합을 산출하고 root 기준 상대경로로 정규화해 반환. 새 Tauri 커맨드 `list_changed_files`. 프론트는 `listCodeFiles`와 `listChangedFiles`를 병렬 호출, `Map<path,status>`를 `buildCodeTree`에 넘겨 파일 노드에 상태를 stamp 하고 디렉토리에 변경 개수를 롤업한다. `CodeFileTree`가 우측 배지를 렌더.

**Tech Stack:** Rust (Tauri 2, `std::process::Command` for git), TypeScript/React, Vitest.

**Spec:** `docs/superpowers/specs/2026-05-28-code-explorer-tree-change-markers-design.md`

---

## File Structure

**Rust (`vibelign-gui/src-tauri/`):**
- Create: `src/git_status.rs` — `ChangeStatus`/`ChangedEntry` 타입 + `list_changed_paths` (git status 파싱 + 경로 정규화)
- Modify: `src/lib.rs:1-6` — `mod git_status;` 선언
- Modify: `src/lib.rs:127-128` 부근 — invoke_handler에 `commands::code::list_changed_files` 등록
- Modify: `src/commands/code.rs` — `list_changed_files` Tauri 커맨드

**TypeScript (`vibelign-gui/src/`):**
- Modify: `src/lib/vib/types.ts` (TYPES_END 앵커 앞) — `ChangeStatus`, `ChangedEntry`
- Modify: `src/lib/vib/code.ts` — `listChangedFiles` 브리지
- Modify: `src/lib/vib/index.ts:4` — 명시 re-export에 `listChangedFiles` 추가
- Modify: `src/lib/code-explorer/tree.ts` — `CodeTreeNode`에 `changeStatus`/`changedCount`, `buildCodeTree(files, changes?)`, 롤업 함수
- Modify: `src/lib/code-explorer/tree.test.ts` — 롤업/stamp 테스트
- Modify: `src/components/code-explorer/CodeFileTree.tsx` — `changes` prop + 우측 배지 렌더
- Modify: `src/pages/CodeExplorer.tsx` — `listChangedFiles` 병렬 호출 + `changes` 상태 + prop 전달

각 파일 단일 책임: `git_status.rs`는 변경 경로 산출, `tree.ts`는 트리 구성/롤업, `CodeFileTree`는 렌더, `CodeExplorer`는 호출/상태.

---

## Task 1: Rust `git_status.rs` — 변경 경로 산출 (TDD)

**Files:**
- Create: `vibelign-gui/src-tauri/src/git_status.rs`
- Modify: `vibelign-gui/src-tauri/src/lib.rs:1-6` (모듈 선언)

- [ ] **Step 1: 실패하는 테스트 + 구현을 한 파일로 작성**

Create `vibelign-gui/src-tauri/src/git_status.rs`:

```rust
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub enum ChangeStatus {
    Modified,
    New,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct ChangedEntry {
    pub path: String,
    pub status: ChangeStatus,
}

/// git status 기반 변경 경로 집합. 비-git 디렉토리는 빈 Vec (에러 아님).
/// 반환 경로는 `root` 기준 상대경로(`/` 구분)이며, 디스크에 실제 존재하는 파일만 포함한다
/// (삭제·경로 불일치는 자연히 제외된다).
pub(crate) fn list_changed_paths(root: &Path) -> Result<Vec<ChangedEntry>, String> {
    // 1. git 저장소인지 — 아니면 마커 없음
    let probe = match std::process::Command::new("git")
        .args(["-C"]).arg(root)
        .args(["rev-parse", "--is-inside-work-tree"])
        .output()
    {
        Ok(o) => o,
        Err(_) => return Ok(Vec::new()), // git 미설치 → 마커 없음
    };
    if !probe.status.success() {
        return Ok(Vec::new());
    }

    // 2. root가 repo 하위 디렉토리일 때의 prefix (예: "vibelign-gui/"), repo 루트면 ""
    let prefix = std::process::Command::new("git")
        .args(["-C"]).arg(root)
        .args(["rev-parse", "--show-prefix"])
        .output()
        .ok()
        .filter(|o| o.status.success())
        .and_then(|o| String::from_utf8(o.stdout).ok())
        .map(|s| s.trim().to_string())
        .unwrap_or_default();

    // 3. porcelain -z: NUL 구분, 경로 이스케이프 없음(한글/공백 안전)
    let out = std::process::Command::new("git")
        .args(["-C"]).arg(root)
        .args(["status", "--porcelain", "-z", "--untracked-files=all"])
        .output()
        .map_err(|e| format!("git status 실행 실패: {e}"))?;
    if !out.status.success() {
        return Ok(Vec::new());
    }
    let raw = String::from_utf8_lossy(&out.stdout);

    let mut entries = Vec::new();
    let mut tokens = raw.split('\0');
    while let Some(entry) = tokens.next() {
        // 각 엔트리는 "XY PATH" (X=index, Y=worktree, 그다음 공백, 그다음 경로)
        if entry.len() < 4 {
            continue;
        }
        let xy = &entry[0..2];
        let path = &entry[3..]; // entry[2]는 공백
        // rename/copy 는 -z 에서 "XY new\0old" 2토큰 → old 토큰을 소비
        let bytes = xy.as_bytes();
        let is_rename = bytes[0] == b'R' || bytes[1] == b'R' || bytes[0] == b'C' || bytes[1] == b'C';
        if is_rename {
            let _orig = tokens.next();
        }

        let status = if xy == "??" {
            ChangeStatus::New
        } else {
            ChangeStatus::Modified
        };

        // porcelain 경로(repo-root 기준)를 root 기준 상대경로로 정규화한다.
        // 디스크에 실제 존재하는 파일만 통과(삭제·root 밖 경로는 자동 제외).
        let rel = match resolve_rel(path, &prefix, root) {
            Some(r) => r,
            None => continue,
        };
        entries.push(ChangedEntry { path: rel, status });
    }
    Ok(entries)
}

/// porcelain 경로를 `root` 기준 상대경로로 해석한다.
/// `git status --porcelain` 경로는 **repo-root 기준**이다(실측: git 2.50.1,
/// status.relativePaths 무관). 따라서:
/// - root 가 repo 하위(prefix 비어있지 않음)면, root 안의 파일은 반드시 prefix 로 시작.
///   prefix 로 시작하지 않으면 root 밖 → 제외. (as-is 폴백은 동명 파일 오탐을 유발하므로 금지)
/// - prefix 가 비어있으면 root == repo 루트 → 경로가 곧 root 기준.
/// 어느 경우든 디스크에 실제 존재하는 파일만 통과(삭제 자동 제외).
fn resolve_rel(path: &str, prefix: &str, root: &Path) -> Option<String> {
    let p = path.replace('\\', "/");
    if !prefix.is_empty() {
        let stripped = p.strip_prefix(prefix)?;
        return root.join(stripped).is_file().then(|| stripped.to_string());
    }
    root.join(&p).is_file().then(|| p)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn git_available() -> bool {
        std::process::Command::new("git")
            .arg("--version")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    fn run(root: &Path, args: &[&str]) {
        let st = std::process::Command::new("git")
            .args(["-C"]).arg(root).args(args)
            .status().expect("git");
        assert!(st.success(), "git {args:?} failed");
    }

    fn write(root: &Path, rel: &str, content: &[u8]) {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, content).unwrap();
    }

    fn init_repo(root: &Path) {
        run(root, &["init", "-q", "-b", "main"]);
        run(root, &["config", "user.email", "t@t.dev"]);
        run(root, &["config", "user.name", "t"]);
    }

    #[test]
    fn non_git_dir_returns_empty() {
        let root = TempDir::new().unwrap();
        write(root.path(), "src/main.ts", b"x\n");
        let changed = list_changed_paths(root.path()).expect("ok");
        assert!(changed.is_empty());
    }

    #[test]
    fn modified_tracked_file_is_modified() {
        if !git_available() { return; }
        let root = TempDir::new().unwrap();
        init_repo(root.path());
        write(root.path(), "src/main.ts", b"old\n");
        run(root.path(), &["add", "."]);
        run(root.path(), &["commit", "-q", "-m", "init"]);
        write(root.path(), "src/main.ts", b"new\n"); // worktree 수정

        let changed = list_changed_paths(root.path()).expect("ok");
        let hit = changed.iter().find(|e| e.path == "src/main.ts").expect("found");
        assert_eq!(hit.status, ChangeStatus::Modified);
    }

    #[test]
    fn untracked_file_is_new() {
        if !git_available() { return; }
        let root = TempDir::new().unwrap();
        init_repo(root.path());
        write(root.path(), "src/main.ts", b"a\n");
        run(root.path(), &["add", "."]);
        run(root.path(), &["commit", "-q", "-m", "init"]);
        write(root.path(), "src/brand_new.ts", b"fresh\n"); // add 안 함

        let changed = list_changed_paths(root.path()).expect("ok");
        let hit = changed.iter().find(|e| e.path == "src/brand_new.ts").expect("found");
        assert_eq!(hit.status, ChangeStatus::New);
    }

    #[test]
    fn deleted_file_is_excluded() {
        if !git_available() { return; }
        let root = TempDir::new().unwrap();
        init_repo(root.path());
        write(root.path(), "src/gone.ts", b"bye\n");
        run(root.path(), &["add", "."]);
        run(root.path(), &["commit", "-q", "-m", "init"]);
        std::fs::remove_file(root.path().join("src/gone.ts")).unwrap();

        let changed = list_changed_paths(root.path()).expect("ok");
        assert!(changed.iter().all(|e| e.path != "src/gone.ts"));
    }

    #[test]
    fn subdir_root_paths_are_relative_to_root() {
        if !git_available() { return; }
        // repo 루트에서 init 후, 하위 디렉토리 app/ 을 root 로 사용
        let repo = TempDir::new().unwrap();
        init_repo(repo.path());
        write(repo.path(), "app/src/main.ts", b"old\n");
        write(repo.path(), "outside.ts", b"o\n");
        run(repo.path(), &["add", "."]);
        run(repo.path(), &["commit", "-q", "-m", "init"]);
        write(repo.path(), "app/src/main.ts", b"new\n");

        let root = repo.path().join("app");
        let changed = list_changed_paths(&root).expect("ok");
        // root 기준 상대경로 "src/main.ts" 로 나와야 한다 (app/ prefix 제거)
        let hit = changed.iter().find(|e| e.path == "src/main.ts").expect("found");
        assert_eq!(hit.status, ChangeStatus::Modified);
        // app/ 밖의 outside.ts 는 포함되지 않는다
        assert!(changed.iter().all(|e| !e.path.contains("outside.ts")));
    }
}
```

- [ ] **Step 2: 모듈 등록**

Edit `vibelign-gui/src-tauri/src/lib.rs` — `mod code_diff;` 다음 줄에 추가 (알파벳/근접 순서 유지):

```rust
mod code_access;
mod code_diff;
mod commands;
mod docs_access;
mod git_status;
mod onboarding;
mod vib_path;
```

> 주의: 기존 줄 순서는 `code_access`/`code_diff`/`commands`/`docs_access`/`onboarding`/`vib_path`. `git_status`는 `docs_access`와 `onboarding` 사이에 삽입.

- [ ] **Step 3: 테스트 실행하여 통과 확인**

Run: `cd vibelign-gui/src-tauri && cargo test git_status:: 2>&1 | tail -15`
Expected: `test result: ok. 5 passed; 0 failed` (non_git, modified, untracked, deleted, subdir).

- [ ] **Step 4: 커밋**

```bash
git add vibelign-gui/src-tauri/src/git_status.rs vibelign-gui/src-tauri/src/lib.rs
git commit -m "feat(tree): git status 기반 변경 경로 산출 (git_status.rs)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `list_changed_files` Tauri 커맨드

**Files:**
- Modify: `vibelign-gui/src-tauri/src/commands/code.rs` (커맨드 추가)
- Modify: `vibelign-gui/src-tauri/src/lib.rs:127-128` 부근 (invoke_handler 등록)

- [ ] **Step 1: 커맨드 추가**

Edit `vibelign-gui/src-tauri/src/commands/code.rs` — 파일 상단 `use` 블록에 import 추가하고 (기존 `use crate::code_access::{...};` 아래), 파일 끝에 커맨드 추가:

상단 import (기존 `use crate::code_access::{...}` 다음 줄):

```rust
use crate::git_status::{list_changed_paths, ChangedEntry};
```

파일 끝:

```rust
#[tauri::command]
pub(crate) fn list_changed_files(root: String) -> Result<Vec<ChangedEntry>, String> {
    let root_path = PathBuf::from(root);
    list_changed_paths(&root_path)
}
```

> `PathBuf`는 이미 파일 상단에서 import 되어 있다.

- [ ] **Step 2: invoke_handler 등록**

Edit `vibelign-gui/src-tauri/src/lib.rs` — `commands::code::list_code_files,` 다음 줄에 추가:

```rust
            commands::code::read_code_file,
            commands::code::read_code_file_diff,
            commands::code::list_code_files,
            commands::code::list_changed_files,
```

- [ ] **Step 3: 전체 빌드 + 회귀**

Run: `cd vibelign-gui/src-tauri && cargo build 2>&1 | tail -5`
Expected: 컴파일 성공.

Run: `cd vibelign-gui/src-tauri && cargo test 2>&1 | grep -E "test result|error\["`
Expected: 모든 `test result:` 줄이 `0 failed`. (git_status 5 + code_diff 11 + code_access + 기타)

- [ ] **Step 4: 커밋**

```bash
git add vibelign-gui/src-tauri/src/commands/code.rs vibelign-gui/src-tauri/src/lib.rs
git commit -m "feat(tree): list_changed_files Tauri 커맨드 등록

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: TypeScript 타입 + `listChangedFiles` 브리지

**Files:**
- Modify: `vibelign-gui/src/lib/vib/types.ts` (TYPES_END 앵커 앞)
- Modify: `vibelign-gui/src/lib/vib/code.ts`
- Modify: `vibelign-gui/src/lib/vib/index.ts:4`

- [ ] **Step 1: 타입 추가**

Edit `vibelign-gui/src/lib/vib/types.ts` — `CodeFileDiffResult` 인터페이스 닫는 `}` 다음, `// === ANCHOR: TYPES_END ===` **앞에** 삽입:

```typescript
export type ChangeStatus = "modified" | "new";

export interface ChangedEntry {
  path: string;
  status: ChangeStatus;
}
```

- [ ] **Step 2: 브리지 함수 추가**

Edit `vibelign-gui/src/lib/vib/code.ts` — 기존 type import 줄에 `ChangedEntry` 추가하고, 파일 끝에 함수 추가.

import 줄을 다음으로 교체:

```typescript
import type { CodeFileEntry, CodeFileReadResult, CodeFileDiffResult, ChangedEntry } from "./types";
```

파일 끝:

```typescript
export async function listChangedFiles(root: string): Promise<ChangedEntry[]> {
  return invoke<ChangedEntry[]>("list_changed_files", { root });
}
```

> `root`는 경로 인자가 아니라 프로젝트 루트이므로 `normalizeBridgePath`를 적용하지 않는다 (기존 `listCodeFiles`도 root에 미적용).

- [ ] **Step 3: index.ts 명시 re-export 추가**

Edit `vibelign-gui/src/lib/vib/index.ts` — 4번째 줄을 다음으로 교체:

```typescript
export { listCodeFiles, readCodeFile, readCodeFileDiff, listChangedFiles } from "./code";
```

> 타입(`ChangeStatus`, `ChangedEntry`)은 `export * from "./types"`로 자동 노출.

- [ ] **Step 4: 타입체크**

Run: `cd vibelign-gui && npx tsc -p tsconfig.json --noEmit 2>&1 | tail -5`
Expected: 신규 코드 관련 에러 없음.

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/lib/vib/types.ts vibelign-gui/src/lib/vib/code.ts vibelign-gui/src/lib/vib/index.ts
git commit -m "feat(tree): ChangedEntry 타입 + listChangedFiles 브리지

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: `tree.ts` — `changeStatus` stamp + `changedCount` 롤업 (TDD)

**Files:**
- Modify: `vibelign-gui/src/lib/code-explorer/tree.ts`
- Modify: `vibelign-gui/src/lib/code-explorer/tree.test.ts`

- [ ] **Step 1: 실패하는 테스트 추가**

Edit `vibelign-gui/src/lib/code-explorer/tree.test.ts` — 파일 끝(마지막 `}` 또는 describe 블록 안 적절한 위치)에 추가. 먼저 import에 타입이 필요하면 상단 import를 확인하고, 테스트는 다음을 추가:

```typescript
import { buildCodeTree } from "./tree";
import type { ChangeStatus } from "../vib/types";

describe("buildCodeTree change markers", () => {
  const files = [
    { path: "src/a.ts", category: "code", imports: [] },
    { path: "src/b.ts", category: "code", imports: [] },
    { path: "docs/c.md", category: "docs", imports: [] },
  ];

  it("stamps changeStatus on file nodes and rolls up changedCount on directories", () => {
    const changes = new Map<string, ChangeStatus>([
      ["src/a.ts", "modified"],
      ["src/b.ts", "new"],
    ]);
    const tree = buildCodeTree(files, changes);

    const src = tree.children.find((n) => n.path === "src")!;
    const docs = tree.children.find((n) => n.path === "docs")!;
    const a = src.children.find((n) => n.path === "src/a.ts")!;
    const b = src.children.find((n) => n.path === "src/b.ts")!;
    const c = docs.children.find((n) => n.path === "docs/c.md")!;

    expect(a.changeStatus).toBe("modified");
    expect(b.changeStatus).toBe("new");
    expect(c.changeStatus).toBeUndefined();
    expect(src.changedCount).toBe(2);
    expect(docs.changedCount).toBe(0);
  });

  it("defaults to no markers when changes map is omitted", () => {
    const tree = buildCodeTree(files);
    const src = tree.children.find((n) => n.path === "src")!;
    expect(src.changedCount).toBe(0);
    const a = src.children.find((n) => n.path === "src/a.ts")!;
    expect(a.changeStatus).toBeUndefined();
  });
});
```

> `tree.test.ts`에 이미 `import { describe, it, expect }`(vitest globals 설정에 따라 생략 가능)와 다른 import가 있을 수 있다. 중복 import를 만들지 말고 기존 `buildCodeTree` import가 있으면 재사용하라. `ChangeStatus` import만 추가.

- [ ] **Step 2: 실행 → 실패 확인**

Run: `cd vibelign-gui && npx vitest run src/lib/code-explorer/tree.test.ts 2>&1 | tail -15`
Expected: 신규 두 테스트가 실패 — `changeStatus`/`changedCount`가 `CodeTreeNode`에 없어 타입 에러 또는 `undefined`.

- [ ] **Step 3: `tree.ts` 구현**

Edit `vibelign-gui/src/lib/code-explorer/tree.ts`:

(a) 상단 import에 타입 추가 (기존 `import type { CodeFileEntry } from "../vib/types";`를 교체):

```typescript
import type { CodeFileEntry, ChangeStatus } from "../vib/types";
```

(b) `CodeTreeNode` 인터페이스에 필드 2개 추가 (`category: CategoryKey;` 다음):

```typescript
export interface CodeTreeNode {
  name: string;
  path: string;
  kind: "directory" | "file";
  children: CodeTreeNode[];
  file?: CodeFileEntry;
  category: CategoryKey;
  // 변경 마커: 파일은 자신의 상태, 디렉토리는 하위 변경 파일 개수.
  changeStatus?: ChangeStatus;
  changedCount: number;
}
```

(c) `createNode`에 `changedCount: 0` 기본값 추가:

```typescript
function createNode(name: string, path: string, kind: "directory" | "file", file?: CodeFileEntry): CodeTreeNode {
  return {
    name,
    path,
    kind,
    children: [],
    file,
    category: file ? categorizeFileEntry(file) : "other",
    changedCount: 0,
  };
}
```

(d) 롤업 함수 추가 (`assignDirectoryCategories` 함수 다음에):

```typescript
function assignChangedCounts(node: CodeTreeNode): number {
  let count = 0;
  for (const child of node.children) {
    if (child.kind === "file") {
      if (child.changeStatus) count += 1;
    } else {
      count += assignChangedCounts(child);
    }
  }
  if (node.kind === "directory") {
    node.changedCount = count;
  }
  return count;
}
```

(e) `buildCodeTree` 시그니처에 `changes` 옵셔널 인자 추가하고, 파일 노드 생성 시 stamp + 마지막에 롤업 호출:

```typescript
export function buildCodeTree(files: CodeFileEntry[], changes?: ReadonlyMap<string, ChangeStatus>): CodeTreeNode {
  const root = createNode("", "", "directory");
  for (const file of [...files].sort((left, right) => left.path.localeCompare(right.path))) {
    const segments = file.path.split("/").filter(Boolean);
    let current = root;
    for (let index = 0; index < segments.length; index += 1) {
      const segment = segments[index];
      const childPath = current.path ? `${current.path}/${segment}` : segment;
      const isFile = index === segments.length - 1;
      let child = current.children.find((item) => item.name === segment && item.kind === (isFile ? "file" : "directory"));
      if (!child) {
        child = createNode(segment, childPath, isFile ? "file" : "directory", isFile ? file : undefined);
        if (isFile) {
          child.changeStatus = changes?.get(file.path);
        }
        current.children.push(child);
        current.children.sort(compareNodes);
      }
      current = child;
    }
  }
  assignDirectoryCategories(root);
  assignChangedCounts(root);
  return root;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd vibelign-gui && npx vitest run src/lib/code-explorer/tree.test.ts 2>&1 | tail -10`
Expected: 기존 + 신규 테스트 모두 통과.

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/lib/code-explorer/tree.ts vibelign-gui/src/lib/code-explorer/tree.test.ts
git commit -m "feat(tree): buildCodeTree changeStatus stamp + 디렉토리 changedCount 롤업

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: `CodeFileTree` — 우측 M/U 배지 + 폴더 개수 배지

**Files:**
- Modify: `vibelign-gui/src/components/code-explorer/CodeFileTree.tsx`

- [ ] **Step 1: `changes` prop 추가 + buildCodeTree에 전달**

Edit `vibelign-gui/src/components/code-explorer/CodeFileTree.tsx`:

(a) import에 타입 추가 (기존 `import type { CodeFileEntry } from "../../lib/vib";` 교체):

```typescript
import type { CodeFileEntry, ChangeStatus } from "../../lib/vib";
```

(b) `CodeFileTreeProps`에 `changes` 추가:

```typescript
interface CodeFileTreeProps {
  files: CodeFileEntry[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  autoExpandAll: boolean;
  changes: ReadonlyMap<string, ChangeStatus>;
}
```

(c) 구조분해 + useMemo 변경:

```typescript
export default function CodeFileTree({ files, selectedPath, onSelect, autoExpandAll, changes }: CodeFileTreeProps) {
  const tree = useMemo(() => buildCodeTree(files, changes), [files, changes]);
```

- [ ] **Step 2: 배지 렌더 추가**

`CodeFileTree.tsx`에서 파일명 `<span>{node.name}</span>` 다음(같은 button 안, 닫는 `</button>` 앞)에 배지 마크업 추가. 기존:

```tsx
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
          </button>
```

를 다음으로 교체:

```tsx
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
            {!isDirectory && node.changeStatus && (
              <span
                aria-label={node.changeStatus === "new" ? "신규 파일" : "수정된 파일"}
                title={node.changeStatus === "new" ? "신규 (untracked)" : "수정됨"}
                style={{
                  marginLeft: "auto",
                  flexShrink: 0,
                  fontSize: 10,
                  fontWeight: 800,
                  fontFamily: "ui-monospace, Menlo, Consolas, monospace",
                  color: active ? "#fff" : node.changeStatus === "new" ? "#22c55e" : "#f59e0b",
                }}
              >
                {node.changeStatus === "new" ? "U" : "M"}
              </span>
            )}
            {isDirectory && node.changedCount > 0 && (
              <span
                aria-label={`변경 파일 ${node.changedCount}개`}
                title={`하위 변경 파일 ${node.changedCount}개`}
                style={{
                  marginLeft: "auto",
                  flexShrink: 0,
                  fontSize: 10,
                  fontWeight: 700,
                  color: active ? "#fff" : "#888",
                }}
              >
                {node.changedCount}
              </span>
            )}
          </button>
```

> `marginLeft: "auto"`로 우측 정렬. `.btn`은 flex 컨테이너라 동작한다. active(다크) 행에서는 흰색으로 대비 확보.

- [ ] **Step 3: 타입체크**

Run: `cd vibelign-gui && npx tsc -p tsconfig.json --noEmit 2>&1 | tail -8`
Expected: 호출자(`CodeExplorer.tsx`)가 아직 `changes` prop을 안 줘서 **에러 발생** — Task 6에서 해결. 이 단계에서는 `CodeFileTree.tsx` 자체 문법/타입 에러가 없으면 OK (에러 메시지가 CodeExplorer.tsx의 missing prop `changes`만 가리켜야 함).

- [ ] **Step 4: (커밋은 Task 6과 함께 — tree/page는 짝)**

이 단계는 단독 커밋하지 않음. 다음 태스크에서 page를 함께 수정한 뒤 커밋.

---

## Task 6: `CodeExplorer` — `listChangedFiles` 병렬 호출 + `changes` 상태

**Files:**
- Modify: `vibelign-gui/src/pages/CodeExplorer.tsx`

- [ ] **Step 1: import 추가**

`vibelign-gui/src/pages/CodeExplorer.tsx`의 import 줄(`import { listCodeFiles, readCodeFile, readCodeFileDiff, ... } from "../lib/vib";`)을 다음으로 교체:

```tsx
import { listCodeFiles, readCodeFile, readCodeFileDiff, listChangedFiles, type CodeFileEntry, type CodeFileReadResult, type CodeFileDiffResult, type ChangeStatus, type ChangedEntry } from "../lib/vib";
```

- [ ] **Step 2: `changes` 상태 추가**

기존 useState 블록(파일·diff 관련) 근처에 추가 (예: `const [files, setFiles] = useState<CodeFileEntry[]>([]);` 다음 줄):

```tsx
  const [changes, setChanges] = useState<ReadonlyMap<string, ChangeStatus>>(new Map());
```

- [ ] **Step 3: `refreshFiles`를 병렬 호출로 변경**

기존 `refreshFiles` 함수를 다음으로 교체:

```tsx
  async function refreshFiles() {
    setIsRefreshing(true);
    setListError(null);
    try {
      const [next, changed] = await Promise.all([
        listCodeFiles(projectDir),
        listChangedFiles(projectDir).catch(() => [] as ChangedEntry[]),
      ]);
      setFiles(next);
      setChanges(new Map(changed.map((entry) => [entry.path, entry.status])));
      setSelectedPath((current) => current && next.some((file) => file.path === current) ? current : next[0]?.path ?? null);
    } catch (error: unknown) {
      setListError(error instanceof Error ? error.message : "코드 파일 목록을 읽을 수 없어요");
    } finally {
      setIsLoadingList(false);
      setIsRefreshing(false);
    }
  }
```

> git status 실패는 `.catch(() => [])`로 흡수 — 파일 목록은 정상 표시, 마커만 없음 (Diff 기능과 동일한 graceful 패턴).

- [ ] **Step 4: `CodeFileTree`에 `changes` 전달**

`tree={<CodeFileTree ... />}` 호출에 `changes={changes}` 추가:

```tsx
      tree={<CodeFileTree files={filteredFiles} selectedPath={selectedPath} onSelect={setSelectedPath} autoExpandAll={query.trim().length > 0} changes={changes} />}
```

- [ ] **Step 5: 타입체크**

Run: `cd vibelign-gui && npx tsc -p tsconfig.json --noEmit 2>&1 | tail -5`
Expected: 에러 없음.

- [ ] **Step 6: 빌드 + 프론트 테스트 회귀 (병렬 가능)**

Run:
- `cd vibelign-gui && npm run build 2>&1 | tail -8`
- `cd vibelign-gui && npx vitest run src/lib/code-explorer 2>&1 | tail -10`

Expected: build 성공; tree/filters 테스트 통과.

> 참고: `src/pages/__tests__/DocsViewer.epoch.test.tsx`의 2개 실패는 **기존 회귀**(iframe sandbox, 이 작업과 무관)다. 새로 깨진 게 없는지만 확인.

- [ ] **Step 7: 커밋 (Task 5 tree + Task 6 page)**

```bash
git add vibelign-gui/src/components/code-explorer/CodeFileTree.tsx vibelign-gui/src/pages/CodeExplorer.tsx
git commit -m "feat(tree): CodeFileTree 변경 배지 + CodeExplorer listChangedFiles 병렬 호출

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: 수동 QA (Diff QA와 함께)

**Files:** (없음 — 실행만)

- [ ] **Step 1: dev 앱이 최신인지 확인 / 재빌드**

이미 `npm run tauri dev`가 실행 중이면 Rust 변경(Task 1-2)은 watcher가 재컴파일, 프론트(Task 3-6)는 Vite HMR로 반영된다. 확신이 안 서면 dev 재시작.

- [ ] **Step 2: QA 체크리스트 (수동)**

git 저장소 프로젝트를 Code Explorer로 열고:

1. **워킹트리 수정 파일**: 추적 파일을 수정 → 트리에서 파일명 우측에 **`M`(주황)** 배지, 상위 폴더에 **개수 배지**.
2. **신규 untracked 파일**: git add 안 한 새 파일 → 우측에 **`U`(녹색)** 배지, 상위 폴더 개수 +1.
3. **변경 없는 파일**: 배지 없음.
4. **비-git 프로젝트**: 마커 전혀 없음 (에러 없이 트리 정상).
5. **폴더 접기/펴기**: 접힌 폴더에도 개수 배지가 보여 변경 위치를 알 수 있음.
6. **Refresh 버튼**: 파일 수정/저장 후 Refresh → 배지 갱신.
7. **Diff 연계**: `M` 배지 파일 클릭 → (직전 기능) 자동 Diff 뷰로 녹/빨 표시.

- [ ] **Step 3: 결과 기록**

문제 발견 시 케이스/증상 기록 → 별도 픽스 사이클. 모두 통과면 완료.

- [ ] **Step 4: 변경 없음 — 커밋 생략**

---

## 완료 기준

- 모든 task 체크박스 완료.
- `cargo test` 전부 통과 (git_status 5 신규 + 기존 diff/access).
- `tsc --noEmit` 에러 없음, `npm run build` 성공, `vitest` tree 테스트 통과 (DocsViewer 2개는 기존 무관 실패).
- Task 7 QA 7개 케이스 기대대로 동작.
- **릴리스는 Diff 기능과 함께 v2.2.22 단일 릴리스 커밋**으로 묶는다 (Diff 계획 `2026-05-28-code-explorer-diff-implementation.md` Task 10에서 버전 bump 수행 — 이 트리 기능 커밋들도 같은 릴리스에 포함).
