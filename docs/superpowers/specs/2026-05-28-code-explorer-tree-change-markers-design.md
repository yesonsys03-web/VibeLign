# Code Explorer 트리 변경 표시 설계

- 작성일: 2026-05-28
- 대상: VibeLign GUI Code Explorer 사이드바 트리 (`CodeFileTree`)
- 목표: 사이드바 트리에서 변경된 파일을 한눈에 식별 — 파일에 `M`(수정)/`U`(신규) 배지, 폴더에 변경 개수 배지

## 1. 배경

현재 Code Explorer 트리(`CodeFileTree`)는 `list_code_files`로 받은 파일 목록을
`buildCodeTree`로 계층 구성해 **카테고리 색**(좌측 점 + 4px 액센트 바)으로만 구분한다.
어떤 파일이 마지막 커밋 이후 수정됐는지 트리에서 알 수 없어, 변경 파일을 찾으려면
일일이 열어봐야 한다.

방금 추가된 **Diff 뷰**(`read_code_file_diff`, unified inline diff)와 짝을 이뤄,
"어디가 바뀌었나"를 트리에서 **먼저 식별**하고 클릭해 diff 를 보는 흐름을 완성한다.

Rust 백엔드 `code_diff.rs`에는 git 서브프로세스 호출 패턴
(`baseline_from_git`: `git rev-parse` / `ls-files` / `show`)이 이미 존재한다.

## 2. 핵심 결정 (확정)

| 항목 | 결정 |
|---|---|
| 판정 기준선 | **Git 기반만**. `git status` 한 번 호출로 추적-수정 + 신규(untracked). 비-git → 마커 없음 |
| 파일 마커 | `M`(수정, 주황) / `U`(신규·untracked, 녹색) **우측 글자 배지** |
| 폴더 마커 | 하위 변경 파일 **개수** 우측 배지 |
| staged-added 처리 | `U`(신규)로 표시 |
| 아키텍처 | `list_code_files`와 **분리된 별도 커맨드** `list_changed_files` + 프론트 병합 |
| 갱신 시점 | 파일 목록 로드 / Refresh 버튼 (기존 흐름 재사용). 파일 감시 없음 |

## 3. 아키텍처 (백엔드)

### 3.1 신규 Rust 모듈 `git_status.rs`

```
list_changed_paths(root: &Path) -> Result<Vec<ChangedEntry>, String>
```

- `ChangedEntry { path: String, status: ChangeStatus }`
- `enum ChangeStatus { Modified, New }` — serde `rename_all = "lowercase"` → `"modified" | "new"`

처리 흐름:

1. `git -C <root> rev-parse --is-inside-work-tree` 실패 → **빈 `Vec` 반환** (비-git, 마커 없음, 에러 아님).
2. `git -C <root> rev-parse --show-prefix` → `root`가 repo 하위 디렉토리일 때의 prefix 확보.
3. `git -C <root> status --porcelain -z --untracked-files=all` 실행.
4. NUL(`-z`) 단위로 각 엔트리의 2자 XY 코드 파싱:
   - `"??"` → `New` (U)
   - 그 외 추적 변경(`M`/`A`/`R`/`C`/`T`, index/worktree 어느 쪽이든) → `Modified` (M)
   - `"DD"`/`" D"`/`"D "` (삭제) → 디스크에 없으므로 **건너뜀**
   - rename `R  old -> new` (또는 `-z`의 두 경로) → **new 경로만** 사용
5. 경로 정규화: porcelain 경로(repo-root 기준)에서 show-prefix 를 strip → **`root` 기준 상대경로**.
   `\\`→`/` 정규화. prefix 밖(상위)으로 벗어나는 경로는 제외.

> `-z`는 경로를 그대로(따옴표/이스케이프 없이) NUL 구분으로 출력하므로 한글·공백 파일명도 안전하다.
> rename 엔트리는 `-z`에서 `XY<SP>new\0old\0` 형태이므로 파서가 rename 일 때 다음 토큰(old)을 함께 소비한다.

### 3.2 Tauri 커맨드

`commands/code.rs`에 추가:

```rust
#[tauri::command]
pub(crate) fn list_changed_files(root: String) -> Result<Vec<ChangedEntry>, String>
```

`lib.rs` invoke_handler 에 `commands::code::list_changed_files` 등록
(`list_code_files` 인접).

### 3.3 반환 shape

```jsonc
[
  { "path": "src/foo.ts", "status": "modified" },
  { "path": "src/new.ts", "status": "new" }
]
```

## 4. 프론트엔드

### 4.1 타입 + 브리지

- `types.ts`: `export type ChangeStatus = "modified" | "new";`
  `export interface ChangedEntry { path: string; status: ChangeStatus; }`
- `code.ts`: `listChangedFiles(root): Promise<ChangedEntry[]>` (`invoke("list_changed_files", { root })`).
- `index.ts`: 명시 re-export 에 `listChangedFiles` 추가 (타입은 `export *`로 자동 노출).

### 4.2 `tree.ts` 확장

- `CodeTreeNode`에 `changeStatus?: ChangeStatus`(파일), `changedCount: number`(디렉토리 롤업) 추가.
- `buildCodeTree(files, changes?: Map<string, ChangeStatus>)`:
  - 파일 노드에 `changeStatus` stamp.
  - 디렉토리 `changedCount`는 **트리에 실제 존재하는** 변경 파일만 집계 (git status 가 트리 밖 파일을 보고해도 무시).
  - `changes` 인자는 **옵셔널** — 기존 호출/테스트 호환.

### 4.3 `CodeFileTree` 렌더

- 파일: `changeStatus` 있으면 우측(`marginLeft: auto`)에 글자 배지
  - `M` 주황 (예: `#f59e0b`), `U` 녹색 (`#22c55e`).
- 디렉토리: `changedCount > 0`이면 우측에 숫자 배지.
- 좌측 카테고리 색과 **시각적으로 분리**(우측 정렬). active(다크) 행에서도 대비 유지.

### 4.4 `CodeExplorer` 상태/호출

- `refreshFiles`에서 `Promise.all([listCodeFiles(dir), listChangedFiles(dir).catch(() => [])])`.
- 결과를 `Map<path, status>`로 만들어 트리에 전달 (`buildCodeTree` 인자 또는 `CodeFileTree` prop).
- diff 기능과 동일하게 git 실패는 graceful (빈 배열 → 마커 없음, 파일 목록은 정상 표시).

## 5. 데이터 흐름

```
CodeExplorer refresh
  └ Promise.all(listCodeFiles, listChangedFiles)
       └ Rust: git status --porcelain -z → ChangedEntry[]
  └ Map<path, status> → buildCodeTree(files, changes)
       └ 파일 노드 stamp + 디렉토리 changedCount 롤업
  └ CodeFileTree → 파일 M/U 배지 + 폴더 개수 배지
```

## 6. 보안

- `list_changed_files`는 **git status 출력만** 사용하고, 사용자 경로 입력을 git 인자로
  보간하지 않는다(루트만 `-C <root>`). 경로 탈출 면역.
- 트리에 표시되는 대상은 이미 `list_explorer_files_under`가 가드한 경로 집합과의 **교집합**.
  git status 가 `.omc`/lockfile 등을 보고해도 트리에 없으면 배지/카운트에서 무시된다.

## 7. 테스트

Rust (`git_status.rs`, TempDir + 실제 `git init`, `code_diff.rs` 테스트 스타일):

1. 수정된 추적 파일 → `status == modified`.
2. untracked 신규 파일 → `status == new`.
3. 비-git 디렉토리 → 빈 `Vec` (에러 아님).
4. 삭제 파일 → 결과에서 제외.
5. (가능하면) repo 하위 디렉토리를 `root`로 → show-prefix strip 후 경로가 `root` 기준 상대경로.
   git 미설치 호스트에서는 `git --version` 프로브로 skip.

프론트 (`tree.test.ts` 확장):

6. `buildCodeTree(files, changes)`가 파일에 `changeStatus` stamp + 디렉토리 `changedCount` 롤업.

## 8. 범위 밖 (YAGNI)

- staged vs unstaged 구분 (모든 추적 변경을 `M`로 통합)
- 삭제 파일 tombstone 표시
- 비-git checkpoint baseline 트리 마킹
- 파일 시스템 watch 실시간 갱신
- 트리 내 per-line `+N −M` 카운트
