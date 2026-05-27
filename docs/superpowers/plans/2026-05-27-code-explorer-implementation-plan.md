# Code Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** VibeLign GUI 안에서 프로젝트 폴더 트리뷰를 보고, 선택한 소스 파일 코드를 read-only로 확인할 수 있게 만든다.

**Architecture:** Code Explorer는 DocsViewer와 분리된 새 GUI 도메인으로 만든다. 파일 목록은 기존 Rust `project_scan` IPC를 재사용하고, 실제 코드 읽기는 별도 Tauri command와 `code_access.rs` 보안 가드에서 처리한다. UI는 page/layout/tree/viewer/toolbar/utility 단위로 쪼개서 diff, anchor jump, syntax highlight 확장이 가능하게 유지한다.

**Tech Stack:** React 19, TypeScript, Tauri 2, Rust, existing `callEngineDirect({ command: "project_scan" })`, existing brutalism UI classes.

---

## Non-Goals for Initial Implementation

> 아래는 **하지 않을 일**이다. 실행기는 이 항목들을 작업(step)으로 처리하지 말 것.

- 코드 편집 기능
- 파일 저장 기능
- Cursor-style inline AI 수정 기능
- active diff 계산/API 구현
- syntax highlighter 패키지 추가
- 전체 텍스트 검색 인덱스
- 프로젝트 루트 밖 파일 탐색

---

## Execution Rules

> 아래는 구현 전반에 적용되는 **제약**이다. 개별 step이 아니므로 체크박스가 아니다.

- 컴포넌트를 한 파일에 몰아넣지 않는다.
- `App.tsx`는 탭 연결만 담당한다.
- `CodeExplorer.tsx`는 page-level state와 data loading만 담당한다.
- 트리 변환 로직은 React component 밖 `lib/code-explorer/tree.ts`에 둔다.
- Tauri 호출 wrapper는 `src/lib/vib/code.ts`에만 둔다.
- 코드 파일 read 보안 정책은 Rust `code_access.rs`에만 둔다.
- `DocsViewer`의 `read_file`과 `docs_access.rs` 정책을 코드 읽기용으로 확장하지 않는다.
- 프론트엔드 필터는 UX용이다. backend가 동일/더 강한 보안 검증을 다시 수행한다.
- 파일 경로 key는 항상 relative POSIX path (`src/App.tsx`)로 통일한다.
- hidden/system/generated directory는 기본 제외한다.
- unsupported extension, binary, non-UTF-8, oversized file은 user-readable error state로 표시한다.

---

## Main Files and Responsibilities

| 파일 | 역할 | 변경 |
|------|------|------|
| `vibelign-gui/src/App.tsx` | `CODE EXPLORER` 탭 wiring만 담당 | Modify |
| `vibelign-gui/src/pages/CodeExplorer.tsx` | page state, file list loading, selected file loading | Create |
| `vibelign-gui/src/components/code-explorer/CodeExplorerLayout.tsx` | 좌측 tree / 우측 viewer layout | Create |
| `vibelign-gui/src/components/code-explorer/CodeExplorerToolbar.tsx` | 검색, 새로고침, 상태 표시 | Create |
| `vibelign-gui/src/components/code-explorer/CodeFileTree.tsx` | folder/file tree rendering, expand/collapse, selection | Create |
| `vibelign-gui/src/components/code-explorer/CodeFileViewer.tsx` | read-only source display, line numbers, loading/error/empty states | Create |
| `vibelign-gui/src/components/code-explorer/CodeDiffViewer.tsx` | diff extension seam only; active rendering not wired in v1 | Create |
| `vibelign-gui/src/components/code-explorer/CodeLine.tsx` | code line rendering shared by viewer/diff viewer | Create |
| `vibelign-gui/src/lib/code-explorer/tree.ts` | flat file list → folder tree | Create |
| `vibelign-gui/src/lib/code-explorer/filters.ts` | query/category filter helpers | Create |
| `vibelign-gui/src/lib/code-explorer/tree.test.ts` | tree helper tests | Create |
| `vibelign-gui/src/lib/code-explorer/filters.test.ts` | filter helper tests | Create |
| `vibelign-gui/src/lib/vib/code.ts` | project scan + read code bridge wrappers | Create |
| `vibelign-gui/src/lib/vib/types.ts` | Code Explorer bridge types | Modify |
| `vibelign-gui/src/lib/vib/index.ts` | export code bridge wrappers | Modify |
| `vibelign-gui/src-tauri/src/code_access.rs` | source file allowlist, path guard, UTF-8/size checks | Create |
| `vibelign-gui/src-tauri/src/commands/code.rs` | Tauri `read_code_file` command | Create |
| `vibelign-gui/src-tauri/src/commands/mod.rs` | expose `code` command module | Modify |
| `vibelign-gui/src-tauri/src/lib.rs` | register `read_code_file` command | Modify |

---

## Data Contracts

### `CodeFileEntry`

```ts
export interface CodeFileEntry {
  path: string;
  category: string;
  imports: string[];
}
```

### `CodeFileReadResult`

```ts
export interface CodeFileReadResult {
  path: string;
  content: string;
  source_hash: string;
  size_bytes: number;
  line_count: number;
  language: string;
}
```

### `CodeTreeNode`

```ts
export interface CodeTreeNode {
  name: string;
  path: string;
  kind: "directory" | "file";
  children: CodeTreeNode[];
  file?: CodeFileEntry;
}
```

### `DiffLine` extension seam

```ts
export type DiffLineKind = "context" | "added" | "removed";

export interface DiffLine {
  kind: DiffLineKind;
  oldLineNumber: number | null;
  newLineNumber: number | null;
  text: string;
}
```

---

## Backend Security Policy

### Allowed code extensions

```rust
const CODE_READ_EXTENSIONS: &[&str] = &[
    "py", "js", "ts", "jsx", "tsx", "rs", "go", "java", "cs",
    "cpp", "c", "hpp", "h", "mjs", "cjs", "json", "toml", "yaml", "yml", "css", "html",
];
```

### Ignored path segments

```rust
const CODE_READ_IGNORED_DIRS: &[&str] = &[
    ".git", ".vibelign", ".omc", ".sisyphus", ".venv", "venv", "env",
    "node_modules", "dist", "build", "target", "coverage", ".next", ".nuxt",
    ".turbo", ".cache", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".tox", ".gradle", ".idea", ".vscode",
];
```

### Size and encoding

```rust
const MAX_CODE_READ_BYTES: u64 = 1_000_000;
```

- 코드 파일은 `MAX_CODE_READ_BYTES`, 데이터 파일(json/toml/yaml/yml)은 `MAX_DATA_READ_BYTES` 초과 시 read 거부
- BOM strip 후 UTF-8 decode
- NUL byte 포함 파일은 binary로 보고 거부
- `canonicalize()` 후 root 내부인지 `strip_prefix()`로 확인
- symlink가 root 밖으로 나가면 거부 (Phase 1 `rejects_symlink_escaping_root` 테스트로 고정, `#[cfg(unix)]`)
- **Known gap (Windows)**: `rejects_symlink_escaping_root`는 unix 전용이라 Windows **junction** 탈출 경로는 무검증이다. `canonicalize()`가 junction을 풀어 `strip_prefix(root)`로 막아주므로 런타임 보호는 유지되나, Windows junction 테스트(`#[cfg(windows)]`)는 후속 보강 항목으로 남긴다.
- Windows 예약 디바이스명(`CON`, `NUL`, `PRN`, `AUX`, `CONIN$`, `CONOUT$`, `COM1`~`COM9`, `LPT1`~`LPT9`)은 문자열 segment의 stem 기준으로 명시 거부한다. trailing dot/space도 Windows 파일명 정규화와 맞춰 거부한다. 예: `NUL`, `NUL.ts`, `src/PRN.ts`, `logs/COM1.rs`, `src/CONOUT$.ts`, `NUL. `.

---

## Global Completion Tracker

- [x] Phase 1 — Backend code read guard and Tauri command
- [x] Phase 2 — TypeScript bridge and pure tree/filter utilities
- [x] Phase 3 — Component-separated Code Explorer UI
- [x] Phase 4 — App tab integration
- [x] Phase 5 — Diff extension seam
- [x] Phase 6 — Verification and regression checks (자동 검증 완료, 수동 GUI 스모크는 미실행)

---

## Phase 1 — Backend code read guard and Tauri command

**Target outcome:** GUI can request one project-relative source file and receive normalized read-only content, with backend path/security checks enforced.

**Files**
- Create: `vibelign-gui/src-tauri/src/code_access.rs`
- Create: `vibelign-gui/src-tauri/src/commands/code.rs`
- Modify: `vibelign-gui/src-tauri/src/commands/mod.rs`
- Modify: `vibelign-gui/src-tauri/src/lib.rs`

- [ ] **Step 1: Create failing Rust tests for code access policy**

Add `#[cfg(test)]` tests in `vibelign-gui/src-tauri/src/code_access.rs` covering:

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn write(root: &std::path::Path, rel: &str, content: &[u8]) {
        let path = root.join(rel);
        std::fs::create_dir_all(path.parent().expect("parent")).expect("mkdir");
        std::fs::write(path, content).expect("write");
    }

    #[test]
    fn reads_supported_source_file() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "src/main.ts", b"export const value = 1;\n");

        let result = read_code_file_under(root.path(), "src/main.ts").expect("read source");

        assert_eq!(result.path, "src/main.ts");
        assert_eq!(result.content, "export const value = 1;\n");
        assert_eq!(result.line_count, 1);
        assert_eq!(result.language, "TypeScript");
    }

    #[test]
    fn rejects_parent_escape() {
        let root = TempDir::new().expect("temp root");
        let err = read_code_file_under(root.path(), "../secret.ts").expect_err("escape rejected");
        assert!(err.contains("프로젝트 루트 밖") || err.contains("허용되지 않은 경로"));
    }

    #[test]
    fn rejects_windows_absolute_and_unc() {
        // raw 입력 기준 거부이므로 OS와 무관하게 모든 빌드에서 검증된다.
        let root = TempDir::new().expect("temp root");
        for input in ["C:\\Windows\\system.ini", "C:/Windows/system.ini", "\\\\server\\share\\x.ts", "/etc/passwd"] {
            let err = read_code_file_under(root.path(), input).expect_err("absolute/UNC rejected");
            assert!(err.contains("허용되지 않은 경로"), "input={input} err={err}");
        }
    }

    #[test]
    fn rejects_windows_reserved_device_names() {
        // Windows reserved device names are rejected at string level so every OS build verifies the guard.
        let root = TempDir::new().expect("temp root");
        for input in ["NUL", "NUL.ts", "NUL. ", "src/CON.js", "logs/PRN.ts", "serial/COM1.rs", "printer/LPT9.py", "AUX.json", "src/CONOUT$.ts"] {
            let err = read_code_file_under(root.path(), input).expect_err("reserved device name rejected");
            assert!(err.contains("예약된 파일명"), "input={input} err={err}");
        }
    }

    #[test]
    fn rejects_hidden_or_generated_directory() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "node_modules/pkg/index.ts", b"export {};\n");

        let err = read_code_file_under(root.path(), "node_modules/pkg/index.ts").expect_err("ignored dir rejected");

        assert!(err.contains("읽을 수 없는 경로"));
    }

    #[test]
    fn rejects_unsupported_extension() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "assets/logo.png", b"png");

        let err = read_code_file_under(root.path(), "assets/logo.png").expect_err("extension rejected");

        assert!(err.contains("지원하지 않는 코드 파일"));
    }

    #[test]
    fn rejects_binary_file() {
        let root = TempDir::new().expect("temp root");
        write(root.path(), "src/binary.ts", b"abc\0def");

        let err = read_code_file_under(root.path(), "src/binary.ts").expect_err("binary rejected");

        assert!(err.contains("바이너리"));
    }

    #[cfg(unix)]
    #[test]
    fn rejects_symlink_escaping_root() {
        let outside = TempDir::new().expect("outside root");
        write(outside.path(), "secret.ts", b"export const secret = 1;\n");
        let root = TempDir::new().expect("temp root");
        std::os::unix::fs::symlink(outside.path().join("secret.ts"), root.path().join("link.ts"))
            .expect("symlink");

        let err = read_code_file_under(root.path(), "link.ts").expect_err("symlink escape rejected");

        assert!(err.contains("프로젝트 루트 밖"));
    }
}
```

- [ ] **Step 2: Run Rust tests and confirm failure**

Run:

```bash
cargo test --manifest-path vibelign-gui/src-tauri/Cargo.toml code_access
```

Expected: FAIL because `code_access.rs` and `read_code_file_under` do not exist yet.

- [ ] **Step 3: Implement `code_access.rs`**

Create `vibelign-gui/src-tauri/src/code_access.rs` with:

```rust
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::path::{Component, Path, PathBuf};

const MAX_CODE_READ_BYTES: u64 = 1_000_000;
// json/yaml/toml 같은 데이터 파일(project_map.json, lockfile 등)은 코드보다 훨씬 커서
// 1MB 코드 캡으로는 정당한 파일도 거부된다. 데이터 포맷에는 더 큰 캡을 따로 둔다.
const MAX_DATA_READ_BYTES: u64 = 5_000_000;
const DATA_READ_EXTENSIONS: &[&str] = &["json", "toml", "yaml", "yml"];
const WINDOWS_RESERVED_DEVICE_NAMES: &[&str] = &[
    "con", "prn", "aux", "nul", "conin$", "conout$",
    "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
    "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
];
const CODE_READ_EXTENSIONS: &[&str] = &[
    "py", "js", "ts", "jsx", "tsx", "rs", "go", "java", "cs", "cpp", "c", "hpp", "h",
    "mjs", "cjs", "json", "toml", "yaml", "yml", "css", "html",
];
const CODE_READ_IGNORED_DIRS: &[&str] = &[
    ".git", ".vibelign", ".omc", ".sisyphus", ".venv", "venv", "env", "node_modules", "dist",
    "build", "target", "coverage", ".next", ".nuxt", ".turbo", ".cache", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".gradle", ".idea", ".vscode",
];

#[derive(Debug, Serialize)]
pub(crate) struct CodeFileReadResult {
    pub(crate) path: String,
    pub(crate) content: String,
    pub(crate) source_hash: String,
    pub(crate) size_bytes: u64,
    pub(crate) line_count: usize,
    pub(crate) language: String,
}

pub(crate) fn read_code_file_under(root: &Path, rel: &str) -> Result<CodeFileReadResult, String> {
    let root = root.canonicalize().map_err(|e| format!("프로젝트 루트를 확인할 수 없어요: {e}"))?;
    let rel = normalize_relative_input(rel)?;
    reject_ignored_segments(&rel)?;
    let joined = root.join(&rel);
    let canonical = joined.canonicalize().map_err(|e| format!("코드 파일을 찾을 수 없어요: {e}"))?;
    let relative = canonical
        .strip_prefix(&root)
        .map_err(|_| "프로젝트 루트 밖 파일은 읽을 수 없어요".to_string())?;
    let relative_path = relative.to_string_lossy().replace('\\', "/");
    reject_ignored_segments(&relative_path)?;
    ensure_supported_extension(&canonical)?;
    let meta = std::fs::metadata(&canonical).map_err(|e| format!("파일 정보를 읽을 수 없어요: {e}"))?;
    if !meta.is_file() {
        return Err("일반 파일만 읽을 수 있어요".to_string());
    }
    let max_bytes = if is_data_extension(&canonical) { MAX_DATA_READ_BYTES } else { MAX_CODE_READ_BYTES };
    if meta.len() > max_bytes {
        return Err(format!("파일이 너무 커서 미리보기를 열 수 없어요 ({} bytes)", meta.len()));
    }
    let bytes = std::fs::read(&canonical).map_err(|e| format!("코드 파일을 읽을 수 없어요: {e}"))?;
    if bytes.contains(&0) {
        return Err("바이너리 파일은 코드 뷰어에서 열 수 없어요".to_string());
    }
    let bytes = bytes.strip_prefix(&[0xEF, 0xBB, 0xBF]).unwrap_or(&bytes);
    let content = std::str::from_utf8(bytes)
        .map_err(|_| "UTF-8 텍스트 코드 파일만 읽을 수 있어요".to_string())?
        .replace("\r\n", "\n")
        .replace('\r', "\n");
    let source_hash = hash_content(&content);
    let line_count = content.lines().count();
    // size_bytes는 뷰어가 표시하는 정규화된 content 기준으로 맞춘다.
    // (meta.len()은 BOM/CRLF 정규화 전 on-disk 크기라 표시 내용과 어긋난다.)
    let size_bytes = content.len() as u64;
    Ok(CodeFileReadResult {
        path: relative_path.clone(),
        content,
        source_hash,
        size_bytes,
        line_count,
        language: language_for_path(&relative_path).to_string(),
    })
}

fn is_data_extension(path: &Path) -> bool {
    let ext = path.extension().and_then(|value| value.to_str()).unwrap_or("").to_ascii_lowercase();
    DATA_READ_EXTENSIONS.contains(&ext.as_str())
}

fn normalize_relative_input(rel: &str) -> Result<String, String> {
    let raw = rel.trim();
    // 절대경로/UNC/드라이브 차단은 정규화 *전* raw 기준으로 판정한다.
    // (replace('\\',"/")+trim_matches('/')를 먼저 하면 leading '/'·UNC '\\'가
    //  지워져서 Windows 절대경로 가드가 죽은 코드가 된다.)
    if raw.starts_with('/')                     // POSIX 절대경로
        || raw.starts_with('\\')                // Windows 절대경로 + UNC(\\server\share)
        || raw.as_bytes().get(1) == Some(&b':') // 드라이브: C:\ , C:/ , C:foo
    {
        return Err("허용되지 않은 경로입니다".to_string());
    }
    let trimmed = raw.replace('\\', "/").trim_matches('/').to_string();
    if trimmed.is_empty() {
        return Err("파일 경로가 비어 있어요".to_string());
    }
    let rel_path = PathBuf::from(&trimmed);
    if rel_path.components().any(|component| matches!(component, Component::ParentDir | Component::Prefix(_) | Component::RootDir)) {
        return Err("허용되지 않은 경로입니다".to_string());
    }
    Ok(trimmed)
}

fn reject_ignored_segments(rel: &str) -> Result<(), String> {
    for segment in rel.split('/') {
        if segment.is_empty() || segment == "." || segment == ".." {
            return Err("허용되지 않은 경로입니다".to_string());
        }
        let lower = segment.to_ascii_lowercase();
        let normalized_segment = lower.trim_end_matches(|ch| ch == ' ' || ch == '.');
        let stem = normalized_segment.split('.').next().unwrap_or("");
        if WINDOWS_RESERVED_DEVICE_NAMES.contains(&stem) {
            return Err("Windows 예약된 파일명은 열 수 없어요".to_string());
        }
        if CODE_READ_IGNORED_DIRS.contains(&lower.as_str()) || segment.starts_with('.') {
            return Err("읽을 수 없는 경로입니다".to_string());
        }
    }
    Ok(())
}

fn ensure_supported_extension(path: &Path) -> Result<(), String> {
    let ext = path.extension().and_then(|value| value.to_str()).unwrap_or("").to_ascii_lowercase();
    if CODE_READ_EXTENSIONS.contains(&ext.as_str()) {
        Ok(())
    } else {
        Err("지원하지 않는 코드 파일 형식입니다".to_string())
    }
}

fn hash_content(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn language_for_path(path: &str) -> &'static str {
    match path.rsplit('.').next().unwrap_or("").to_ascii_lowercase().as_str() {
        "py" => "Python",
        "ts" | "tsx" => "TypeScript",
        "js" | "jsx" | "mjs" | "cjs" => "JavaScript",
        "rs" => "Rust",
        "go" => "Go",
        "java" => "Java",
        "cs" => "C#",
        "c" | "h" => "C",
        "cpp" | "hpp" => "C++",
        "json" => "JSON",
        "toml" => "TOML",
        "yaml" | "yml" => "YAML",
        "css" => "CSS",
        "html" => "HTML",
        _ => "Text",
    }
}
```

- [ ] **Step 4: Add Tauri command wrapper**

Create `vibelign-gui/src-tauri/src/commands/code.rs`:

```rust
use std::path::PathBuf;

use crate::code_access::{read_code_file_under, CodeFileReadResult};

#[tauri::command]
pub(crate) fn read_code_file(root: String, path: String) -> Result<CodeFileReadResult, String> {
    let root_path = PathBuf::from(root);
    read_code_file_under(&root_path, &path)
}
```

**중요 — 앵커 보존:** `commands/mod.rs`는 `// === ANCHOR: MOD_START ===` ~ `MOD_END`, `lib.rs`는 `// === ANCHOR: LIB_START ===` ~ `LIB_END` 앵커로 감싸여 있다. 파일을 전체 교체하지 말고 앵커 **내부에 한 줄씩만 삽입**한다 (CLAUDE.md 규칙 3·4, `vib guard --strict`).

`vibelign-gui/src-tauri/src/commands/mod.rs` — `MOD_START` 앵커 안 알파벳 순서 위치에 한 줄 추가:

```rust
pub(crate) mod code;
```

`vibelign-gui/src-tauri/src/lib.rs` — `LIB_START` 앵커 안 `mod commands;` 위(알파벳 순)에 한 줄 추가:

```rust
mod code_access;
```

같은 `lib.rs`의 `tauri::generate_handler![...]` 목록 안(예: `commands::docs::read_file,` 부근)에 한 줄 추가:

```rust
commands::code::read_code_file,
```

- [ ] **Step 5: Run Rust tests and verify pass**

Run:

```bash
cargo test --manifest-path vibelign-gui/src-tauri/Cargo.toml code_access
```

Expected: PASS.

---

## Phase 2 — TypeScript bridge and pure tree/filter utilities

**Target outcome:** Frontend can list project source files through existing `project_scan` IPC and read a selected file through the new Tauri command. Tree/filter helpers are independently tested.

**Files**
- Modify: `vibelign-gui/src/lib/vib/types.ts`
- Create: `vibelign-gui/src/lib/vib/code.ts`
- Modify: `vibelign-gui/src/lib/vib/index.ts`
- Create: `vibelign-gui/src/lib/code-explorer/tree.ts`
- Create: `vibelign-gui/src/lib/code-explorer/filters.ts`
- Create: `vibelign-gui/src/lib/code-explorer/tree.test.ts`
- Create: `vibelign-gui/src/lib/code-explorer/filters.test.ts`

- [ ] **Step 1: Add TypeScript bridge types**

Append to `vibelign-gui/src/lib/vib/types.ts`:

```ts
export interface CodeFileEntry {
  path: string;
  category: string;
  imports: string[];
}

export interface ProjectScanResult {
  result?: string;
  files?: CodeFileEntry[];
}

export interface CodeFileReadResult {
  path: string;
  content: string;
  source_hash: string;
  size_bytes: number;
  line_count: number;
  language: string;
}
```

- [ ] **Step 2: Add code bridge wrapper**

Create `vibelign-gui/src/lib/vib/code.ts`:

```ts
import { invoke } from "@tauri-apps/api/core";

import { callEngineDirect, normalizeBridgePath } from "./core";
import type { CodeFileEntry, CodeFileReadResult, ProjectScanResult } from "./types";

export async function listCodeFiles(root: string): Promise<CodeFileEntry[]> {
  const result = await callEngineDirect<ProjectScanResult>({
    command: "project_scan",
    root,
  });
  return [...(result.files ?? [])].sort((left, right) => left.path.localeCompare(right.path));
}

export async function readCodeFile(root: string, path: string): Promise<CodeFileReadResult> {
  return invoke<CodeFileReadResult>("read_code_file", {
    root,
    path: normalizeBridgePath(path),
  });
}
```

Modify `vibelign-gui/src/lib/vib/index.ts`:

```ts
export { listCodeFiles, readCodeFile } from "./code";
```

- [ ] **Step 3: Add pure tree helper tests**

Create `vibelign-gui/src/lib/code-explorer/tree.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { buildCodeTree, collectDirectoryPaths, flattenVisibleTree } from "./tree";
import type { CodeFileEntry } from "../vib/types";

const files: CodeFileEntry[] = [
  { path: "src/App.tsx", category: "ui", imports: [] },
  { path: "src/lib/vib/code.ts", category: "service", imports: ["@tauri-apps/api/core"] },
  { path: "vibelign/core/project_scan.py", category: "core", imports: [] },
];

describe("code explorer tree", () => {
  it("builds a stable nested tree from flat file paths", () => {
    const tree = buildCodeTree(files);

    expect(tree.children.map((node) => node.name)).toEqual(["src", "vibelign"]);
    expect(tree.children[0].children.map((node) => node.name)).toEqual(["lib", "App.tsx"]);
  });

  it("flattens visible folders according to expanded paths", () => {
    const tree = buildCodeTree(files);
    const visible = flattenVisibleTree(tree, new Set(["src", "src/lib", "src/lib/vib"]));

    expect(visible.map((item) => item.node.path)).toContain("src/App.tsx");
    expect(visible.map((item) => item.node.path)).toContain("src/lib/vib/code.ts");
    expect(visible.map((item) => item.node.path)).not.toContain("vibelign/core/project_scan.py");
  });

  it("collects every directory path for search auto-expand", () => {
    const tree = buildCodeTree(files);
    const dirs = collectDirectoryPaths(tree);

    expect(dirs).toEqual(new Set(["src", "src/lib", "src/lib/vib", "vibelign", "vibelign/core"]));
  });
});
```

- [ ] **Step 4: Implement tree helper**

Create `vibelign-gui/src/lib/code-explorer/tree.ts`:

```ts
import type { CodeFileEntry } from "../vib/types";

export interface CodeTreeNode {
  name: string;
  path: string;
  kind: "directory" | "file";
  children: CodeTreeNode[];
  file?: CodeFileEntry;
}

export interface VisibleCodeTreeItem {
  node: CodeTreeNode;
  depth: number;
}

function createNode(name: string, path: string, kind: "directory" | "file", file?: CodeFileEntry): CodeTreeNode {
  return { name, path, kind, children: [], file };
}

export function buildCodeTree(files: CodeFileEntry[]): CodeTreeNode {
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
        current.children.push(child);
        current.children.sort(compareNodes);
      }
      current = child;
    }
  }
  return root;
}

export function flattenVisibleTree(root: CodeTreeNode, expandedPaths: ReadonlySet<string>): VisibleCodeTreeItem[] {
  const result: VisibleCodeTreeItem[] = [];
  function visit(node: CodeTreeNode, depth: number) {
    for (const child of node.children) {
      result.push({ node: child, depth });
      if (child.kind === "directory" && expandedPaths.has(child.path)) {
        visit(child, depth + 1);
      }
    }
  }
  visit(root, 0);
  return result;
}

export function collectDirectoryPaths(root: CodeTreeNode): Set<string> {
  const paths = new Set<string>();
  function visit(node: CodeTreeNode) {
    for (const child of node.children) {
      if (child.kind === "directory") {
        paths.add(child.path);
        visit(child);
      }
    }
  }
  visit(root);
  return paths;
}

function compareNodes(left: CodeTreeNode, right: CodeTreeNode): number {
  if (left.kind !== right.kind) return left.kind === "directory" ? -1 : 1;
  return left.name.localeCompare(right.name);
}
```

- [ ] **Step 5: Add filter helper tests and implementation**

Create `vibelign-gui/src/lib/code-explorer/filters.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { filterCodeFiles } from "./filters";

describe("filterCodeFiles", () => {
  const files = [
    { path: "src/App.tsx", category: "ui", imports: [] },
    { path: "vibelign/core/project_scan.py", category: "core", imports: [] },
  ];

  it("matches path and category case-insensitively", () => {
    expect(filterCodeFiles(files, "APP").map((file) => file.path)).toEqual(["src/App.tsx"]);
    expect(filterCodeFiles(files, "core").map((file) => file.path)).toEqual(["vibelign/core/project_scan.py"]);
  });
});
```

Create `vibelign-gui/src/lib/code-explorer/filters.ts`:

```ts
import type { CodeFileEntry } from "../vib/types";

export function filterCodeFiles(files: CodeFileEntry[], query: string): CodeFileEntry[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return files;
  return files.filter((file) => [file.path, file.category, file.imports.join(" ")].join(" ").toLowerCase().includes(normalized));
}
```

> 언어 라벨은 backend `read_code_file`가 `CodeFileReadResult.language`로 이미 내려주고 `CodeFileViewer`가 그대로 표시한다. 프론트 전용 `language.ts` 헬퍼는 v1에서 호출되는 곳이 없어 만들지 않는다(중복/죽은 코드 방지).

- [ ] **Step 6: Run utility tests**

Run:

```bash
npm run test -- src/lib/code-explorer/tree.test.ts src/lib/code-explorer/filters.test.ts
```

Working directory: `vibelign-gui`

Expected: PASS.

---

## Phase 3 — Component-separated Code Explorer UI

**Target outcome:** UI is split into small components: toolbar, layout, tree, viewer, line renderer. No component owns unrelated responsibilities.

**Files**
- Create: `vibelign-gui/src/pages/CodeExplorer.tsx`
- Create: `vibelign-gui/src/components/code-explorer/CodeExplorerLayout.tsx`
- Create: `vibelign-gui/src/components/code-explorer/CodeExplorerToolbar.tsx`
- Create: `vibelign-gui/src/components/code-explorer/CodeFileTree.tsx`
- Create: `vibelign-gui/src/components/code-explorer/CodeFileViewer.tsx`
- Create: `vibelign-gui/src/components/code-explorer/CodeLine.tsx`

- [ ] **Step 1: Create `CodeLine`**

Create `vibelign-gui/src/components/code-explorer/CodeLine.tsx`:

```tsx
interface CodeLineProps {
  lineNumber: number | null;
  text: string;
  tone?: "normal" | "added" | "removed";
}

export default function CodeLine({ lineNumber, text, tone = "normal" }: CodeLineProps) {
  const background = tone === "added" ? "#D9FFE2" : tone === "removed" ? "#FFE0E0" : "transparent";
  const color = tone === "removed" ? "#8A1F1F" : "#1A1A1A";
  return (
    <div style={{ display: "grid", gridTemplateColumns: "64px minmax(0, 1fr)", background, color }}>
      <div style={{ padding: "0 10px", textAlign: "right", userSelect: "none", color: "#888", borderRight: "1px solid #DDD" }}>
        {lineNumber ?? ""}
      </div>
      <pre style={{ margin: 0, padding: "0 10px", whiteSpace: "pre", overflow: "visible", fontFamily: "IBM Plex Mono, monospace" }}>
        {text || " "}
      </pre>
    </div>
  );
}
```

- [ ] **Step 2: Create read-only file viewer**

Create `vibelign-gui/src/components/code-explorer/CodeFileViewer.tsx`:

```tsx
import type { CodeFileReadResult } from "../../lib/vib";
import CodeLine from "./CodeLine";

interface CodeFileViewerProps {
  selectedPath: string | null;
  file: CodeFileReadResult | null;
  isLoading: boolean;
  error: string | null;
}

export default function CodeFileViewer({ selectedPath, file, isLoading, error }: CodeFileViewerProps) {
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

  const lines = file.content.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();

  return (
    <div className="card" style={{ height: "100%", padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "10px 12px", borderBottom: "2px solid #1A1A1A", display: "flex", gap: 10, alignItems: "center" }}>
        <strong style={{ overflowWrap: "anywhere" }}>{file.path}</strong>
        <span style={{ marginLeft: "auto", fontSize: 11, color: "#666" }}>{file.language} · {file.line_count} lines · {file.size_bytes} bytes</span>
      </div>
      <div style={{ flex: 1, overflow: "auto", fontSize: 13, lineHeight: 1.55 }}>
        {lines.map((line, index) => <CodeLine key={index} lineNumber={index + 1} text={line} />)}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create toolbar**

Create `vibelign-gui/src/components/code-explorer/CodeExplorerToolbar.tsx`:

```tsx
interface CodeExplorerToolbarProps {
  query: string;
  fileCount: number;
  isRefreshing: boolean;
  onQueryChange: (value: string) => void;
  onRefresh: () => void;
}

export default function CodeExplorerToolbar({ query, fileCount, isRefreshing, onQueryChange, onRefresh }: CodeExplorerToolbarProps) {
  return (
    <div className="card" style={{ display: "flex", gap: 10, alignItems: "center", padding: 12 }}>
      <input
        className="input-field"
        value={query}
        onChange={(event) => onQueryChange(event.target.value)}
        placeholder="파일명, 경로, 카테고리, import 검색..."
        style={{ flex: 1 }}
      />
      <span style={{ fontSize: 12, fontWeight: 700 }}>{fileCount} files</span>
      <button className="btn btn-secondary btn-sm" onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? "새로고침 중…" : "새로고침"}
      </button>
    </div>
  );
}
```

- [ ] **Step 4: Create tree component**

Create `vibelign-gui/src/components/code-explorer/CodeFileTree.tsx`:

```tsx
import { useMemo, useState } from "react";

import { buildCodeTree, collectDirectoryPaths, flattenVisibleTree } from "../../lib/code-explorer/tree";
import type { CodeFileEntry } from "../../lib/vib";

interface CodeFileTreeProps {
  files: CodeFileEntry[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  // query가 활성화되면(검색 중) 매칭 파일의 모든 상위 폴더를 자동으로 펼친다.
  // CodeExplorer가 query 비어있지 않을 때 true로 넘긴다.
  autoExpandAll: boolean;
}

export default function CodeFileTree({ files, selectedPath, onSelect, autoExpandAll }: CodeFileTreeProps) {
  const tree = useMemo(() => buildCodeTree(files), [files]);
  // 기본 펼침: 프로젝트가 무엇이든(VibeLign 레포 가정 금지) 1단계 디렉터리를 펼친다.
  const firstLevelDirs = useMemo(
    () => new Set(tree.children.filter((node) => node.kind === "directory").map((node) => node.path)),
    [tree],
  );
  const [userExpanded, setUserExpanded] = useState<Set<string> | null>(null);
  const expandedPaths = useMemo(() => {
    if (autoExpandAll) return collectDirectoryPaths(tree); // 검색 중에는 매칭 결과가 항상 보이도록 전부 펼침
    return userExpanded ?? firstLevelDirs;
  }, [autoExpandAll, tree, userExpanded, firstLevelDirs]);
  const visible = useMemo(() => flattenVisibleTree(tree, expandedPaths), [tree, expandedPaths]);

  function toggle(path: string) {
    if (autoExpandAll) return; // 검색 중에는 자동 펼침이 우선하므로 수동 토글 무시
    setUserExpanded((prev) => {
      const next = new Set(prev ?? firstLevelDirs); // 최초 토글은 현재 기본(1단계 펼침)에서 시작
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  }

  return (
    <div className="card" style={{ height: "100%", overflow: "auto", padding: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 800, color: "#888", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
        Project Code
      </div>
      {visible.length === 0 ? (
        <div style={{ fontSize: 12, color: "#666" }}>표시할 코드 파일이 없습니다.</div>
      ) : visible.map(({ node, depth }) => {
        const active = node.path === selectedPath;
        const isDirectory = node.kind === "directory";
        return (
          <button
            key={`${node.kind}:${node.path}`}
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => isDirectory ? toggle(node.path) : onSelect(node.path)}
            title={node.path}
            style={{
              width: "100%",
              justifyContent: "flex-start",
              textAlign: "left",
              paddingLeft: 8 + depth * 14,
              marginBottom: 3,
              background: active ? "#1A1A1A" : undefined,
              color: active ? "#fff" : undefined,
              textTransform: "none",
              letterSpacing: 0,
              overflow: "hidden",
            }}
          >
            <span style={{ width: 16, display: "inline-block" }}>{isDirectory ? (expandedPaths.has(node.path) ? "▾" : "▸") : ""}</span>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{node.name}</span>
          </button>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 5: Create layout component**

Create `vibelign-gui/src/components/code-explorer/CodeExplorerLayout.tsx`:

```tsx
import type { ReactNode } from "react";

interface CodeExplorerLayoutProps {
  toolbar: ReactNode;
  tree: ReactNode;
  viewer: ReactNode;
}

export default function CodeExplorerLayout({ toolbar, tree, viewer }: CodeExplorerLayoutProps) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column", gap: 12, padding: 12, minHeight: 0 }}>
      {toolbar}
      <div style={{ flex: 1, minHeight: 0, display: "grid", gridTemplateColumns: "320px minmax(0, 1fr)", gap: 12 }}>
        <div style={{ minHeight: 0 }}>{tree}</div>
        <div style={{ minHeight: 0 }}>{viewer}</div>
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create page component**

Create `vibelign-gui/src/pages/CodeExplorer.tsx`:

```tsx
import { useEffect, useMemo, useState } from "react";

import CodeExplorerLayout from "../components/code-explorer/CodeExplorerLayout";
import CodeExplorerToolbar from "../components/code-explorer/CodeExplorerToolbar";
import CodeFileTree from "../components/code-explorer/CodeFileTree";
import CodeFileViewer from "../components/code-explorer/CodeFileViewer";
import { filterCodeFiles } from "../lib/code-explorer/filters";
import { listCodeFiles, readCodeFile, type CodeFileEntry, type CodeFileReadResult } from "../lib/vib";

interface CodeExplorerProps {
  projectDir: string;
}

export default function CodeExplorer({ projectDir }: CodeExplorerProps) {
  const [files, setFiles] = useState<CodeFileEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<CodeFileReadResult | null>(null);
  const [query, setQuery] = useState("");
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const filteredFiles = useMemo(() => filterCodeFiles(files, query), [files, query]);

  async function refreshFiles() {
    setIsRefreshing(true);
    setListError(null);
    try {
      const next = await listCodeFiles(projectDir);
      setFiles(next);
      setSelectedPath((current) => current && next.some((file) => file.path === current) ? current : next[0]?.path ?? null);
    } catch (error: unknown) {
      setListError(error instanceof Error ? error.message : "코드 파일 목록을 읽을 수 없어요");
    } finally {
      setIsLoadingList(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    void refreshFiles();
  }, [projectDir]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedPath) {
      setSelectedFile(null);
      setFileError(null);
      return () => { cancelled = true; };
    }
    setIsLoadingFile(true);
    setSelectedFile(null);
    setFileError(null);
    readCodeFile(projectDir, selectedPath)
      .then((result) => {
        if (!cancelled) setSelectedFile(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) setFileError(error instanceof Error ? error.message : "코드 파일을 읽을 수 없어요");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingFile(false);
      });
    return () => { cancelled = true; };
  }, [projectDir, selectedPath]);

  if (isLoadingList) {
    return <div style={{ padding: 16 }}>코드 파일 목록을 불러오는 중입니다…</div>;
  }

  if (listError) {
    return <div className="alert-error" style={{ margin: 16 }}>{listError}</div>;
  }

  return (
    <CodeExplorerLayout
      toolbar={<CodeExplorerToolbar query={query} fileCount={filteredFiles.length} isRefreshing={isRefreshing} onQueryChange={setQuery} onRefresh={() => void refreshFiles()} />}
      tree={<CodeFileTree files={filteredFiles} selectedPath={selectedPath} onSelect={setSelectedPath} autoExpandAll={query.trim().length > 0} />}
      viewer={<CodeFileViewer selectedPath={selectedPath} file={selectedFile} isLoading={isLoadingFile} error={fileError} />}
    />
  );
}
```

---

## Phase 4 — App tab integration

**Target outcome:** VibeLign GUI top navigation has `CODE EXPLORER`, and selecting it opens the new page without changing existing tabs.

**Files**
- Modify: `vibelign-gui/src/App.tsx`

- [ ] **Step 1: Add import and Page union**

Modify imports:

```tsx
import CodeExplorer from "./pages/CodeExplorer";
```

Modify page type:

```tsx
type Page = "home" | "manual" | "docs" | "code" | "doctor" | "backups" | "logs" | "settings";
```

- [ ] **Step 2: Add nav tab**

Add near `DOCS VIEWER` tab:

```tsx
<button className={`nav-tab ${page === "code" ? "active" : ""}`} onClick={() => setPage("code")}>
  CODE EXPLORER
</button>
```

- [ ] **Step 3: Add page render branch**

Add near docs branch:

```tsx
{page === "code" && <CodeExplorer projectDir={projectDir} />}
```

- [ ] **Step 4: Run TypeScript check through build**

Run:

```bash
npm run build
```

Working directory: `vibelign-gui`

Expected: `tsc && vite build` completes successfully.

---

## Phase 5 — Diff extension seam

**Target outcome:** Diff feature is not active in v1, but the codebase has a small, isolated component seam so red/green diff highlighting can be added without rewriting `CodeFileViewer`.

**Files**
- Create: `vibelign-gui/src/components/code-explorer/CodeDiffViewer.tsx`

- [ ] **Step 1: Create passive diff viewer component**

Create `vibelign-gui/src/components/code-explorer/CodeDiffViewer.tsx`:

```tsx
import CodeLine from "./CodeLine";

export type DiffLineKind = "context" | "added" | "removed";

export interface DiffLine {
  kind: DiffLineKind;
  oldLineNumber: number | null;
  newLineNumber: number | null;
  text: string;
}

interface CodeDiffViewerProps {
  path: string;
  lines: DiffLine[];
}

export default function CodeDiffViewer({ path, lines }: CodeDiffViewerProps) {
  return (
    <div className="card" style={{ height: "100%", padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "10px 12px", borderBottom: "2px solid #1A1A1A", fontWeight: 800 }}>
        Diff Preview · {path}
      </div>
      <div style={{ flex: 1, overflow: "auto", fontSize: 13, lineHeight: 1.55 }}>
        {lines.map((line, index) => (
          <CodeLine
            key={index}
            lineNumber={line.kind === "removed" ? line.oldLineNumber : line.newLineNumber}
            text={line.text}
            tone={line.kind === "added" ? "added" : line.kind === "removed" ? "removed" : "normal"}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Keep diff component unmounted in v1**

Do not import `CodeDiffViewer` into `CodeExplorer.tsx` in the initial implementation. It exists as a typed extension seam and should be wired only when a real diff data source is added.

---

## Phase 6 — Verification and regression checks

**Target outcome:** The feature builds, unit tests pass, and existing DocsViewer behavior is not affected.

**Files**
- No new files unless verification reveals a defect.

- [ ] **Step 1: Run frontend utility tests**

Run:

```bash
npm run test -- src/lib/code-explorer/tree.test.ts src/lib/code-explorer/filters.test.ts
```

Working directory: `vibelign-gui`

Expected: PASS.

- [ ] **Step 2: Run Rust code access tests**

Run:

```bash
cargo test --manifest-path vibelign-gui/src-tauri/Cargo.toml code_access
```

Expected: PASS.

- [ ] **Step 3: Run GUI production build**

Run:

```bash
npm run build
```

Working directory: `vibelign-gui`

Expected: `tsc && vite build` passes.

- [ ] **Step 4: Check LSP diagnostics on modified TypeScript files**

Run LSP diagnostics for:

```text
vibelign-gui/src/App.tsx
vibelign-gui/src/pages/CodeExplorer.tsx
vibelign-gui/src/components/code-explorer/CodeExplorerLayout.tsx
vibelign-gui/src/components/code-explorer/CodeExplorerToolbar.tsx
vibelign-gui/src/components/code-explorer/CodeFileTree.tsx
vibelign-gui/src/components/code-explorer/CodeFileViewer.tsx
vibelign-gui/src/components/code-explorer/CodeDiffViewer.tsx
vibelign-gui/src/components/code-explorer/CodeLine.tsx
vibelign-gui/src/lib/vib/code.ts
vibelign-gui/src/lib/code-explorer/tree.ts
vibelign-gui/src/lib/code-explorer/filters.ts
```

Expected: zero TypeScript errors.

- [ ] **Step 5: Manual GUI smoke check**

Run:

```bash
npm run tauri dev
```

Working directory: `vibelign-gui`

Expected manual observations:

- `CODE EXPLORER` tab appears after selecting a project.
- Left tree shows source files grouped by folders.
- Selecting `vibelign-gui/src/App.tsx` displays code with line numbers.
- Selecting a file under unsupported/ignored path is impossible from the tree and rejected if invoked directly.
- `DOCS VIEWER`, `BACKUPS`, `Doctor`, and `에러로그` tabs still open.

---

## Completion Gates

> 최종 수용 기준(acceptance criteria)이다. 개별 작업 step이 아니므로 체크박스가 아니다. Phase 6 검증으로 확인한다.

- No Code Explorer component exceeds a single clear responsibility.
- `App.tsx` only wires the page and does not contain Code Explorer logic.
- `DocsViewer` backend read policy remains document-only.
- Backend refuses root escapes, hidden/generated dirs, unsupported extensions, binary files, and oversized files (code/data cap 분리).
- Backend refuses root escapes, Windows absolute/UNC paths, Windows reserved device names, hidden/generated dirs, unsupported extensions, binary files, and oversized files (code/data cap 분리).
- `CodeFileTree`는 특정 프로젝트(예: VibeLign 레포) 폴더명을 하드코딩하지 않고, 1단계 디렉터리 기본 펼침 + 검색 시 자동 펼침으로 동작한다.
- Frontend tree/filter helpers have unit tests.
- Rust code access policy has unit tests (symlink escape 포함).
- GUI build passes.
- Diff red/green rendering seam exists but is not active without a real diff source.

---

## Self-Review Notes

- **Spec coverage:** Folder tree, read-only code viewing, component separation, backend read safety, and diff-highlight extension seam are covered by Phases 1–5.
- **No single-file concentration:** UI, bridge, pure logic, and backend security are intentionally split across separate files.
- **Type consistency:** `CodeFileEntry`, `CodeFileReadResult`, `CodeTreeNode`, and `DiffLine` names are defined before use and reused consistently.
- **Initial scope control:** Active diff calculation, editing, search index, and syntax highlighting are explicitly out of the first implementation so the first version remains reviewable.
