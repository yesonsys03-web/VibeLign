# Code Explorer Diff 뷰 설계

- 작성일: 2026-05-28
- 대상: VibeLign GUI Code Explorer (read-only 소스 뷰어, v2.2.19+)
- 목표: 뷰어에서 수정된 코드(녹색)/기존 코드(빨강)를 unified inline diff로 표시 (Cursor/Antigravity 스타일)

## 1. 배경

현재 Code Explorer는 `CodeFileViewer` → `CodeLine`으로 파일 내용을 줄 단위
평면 렌더링하는 순수 읽기 전용 뷰어다. diff 기능이 없어 "마지막 커밋 이후
무엇이 바뀌었는지"를 뷰어 안에서 볼 수 없다.

Rust 백엔드(`code_access.rs`)에는 이미 경로 정규화·보안 가드와
`read_code_file_under`가 있고, git을 `std::process::Command::new("git")`로
호출하는 패턴(`onboarding/mod.rs`, `commands/project_summary.rs`)도 존재한다.
VibeLign은 git과 독립적으로 `.vibelign/checkpoints/<ts>_<msg>/files/...`에
파일 전체 스냅샷을 저장한다.

## 2. 핵심 결정 (확정)

| 항목 | 결정 |
|---|---|
| diff 기준선(baseline) | **계층형**: Git HEAD → 최신 VibeLign checkpoint → 없음 |
| 렌더링 스타일 | **Unified inline** (제거=빨강 배경, 추가=녹색 배경, `±` 마커, old/new 2단 줄번호 gutter) |
| diff 계산 위치 | **Rust 백엔드** (baseline 확보 + 보안 가드가 이미 Rust에 있음) |
| diff 알고리즘 | Rust **`similar`** 크레이트 (line-level) |
| 토글 기본값 | baseline 존재 + 변경 있음 → **자동 ON**, 아니면 평면 뷰 |

## 3. 아키텍처

### 3.1 신규 Tauri 커맨드 `read_code_file_diff(root, path)`

처리 흐름:

```
1. code_access 가드로 path 정규화·검증 (기존 normalize_relative_input /
   parent-escape / ignored-dir / 확장자 가드 재사용)
2. 현재 파일 내용 읽기 (read_code_file_under 경로 재사용)
3. baseline 확보 — 계층형:
     a. git rev-parse --is-inside-work-tree 성공 AND `git ls-files --error-unmatch path` 성공
          → `git -C root show HEAD:<path>`  ⇒ baseline_source = "git"
     b. 위 실패 시 → 최신 .vibelign/checkpoints/<ts>/files/<path> 존재하면 읽기
          → baseline_source = "checkpoint"
     c. 둘 다 없음 → baseline 없음 ⇒ baseline_source = "none"
4. baseline 있으면 similar로 line diff 계산, 없으면 전체를 context로 반환
```

> git 추적 여부 확인에 `git ls-files --error-unmatch`를 쓰는 이유: 신규
> (untracked) 파일은 HEAD에 없으므로 `git show HEAD:path`가 실패한다.
> 이 경우 git baseline을 건너뛰고 checkpoint fallback으로 내려간다.

### 3.2 반환 shape (serde 직렬화)

```jsonc
{
  "path": "src/foo.ts",
  "language": "TypeScript",
  "baseline_source": "git",        // "git" | "checkpoint" | "none"
  "added": 3,
  "removed": 1,
  "lines": [
    { "kind": "context", "old_no": 12, "new_no": 12, "text": "const x = 1;" },
    { "kind": "removed", "old_no": 13, "new_no": null, "text": "return old(x);" },
    { "kind": "added",   "old_no": null, "new_no": 13, "text": "return next(x);" }
  ]
}
```

`kind`: `context`(동일) | `added`(추가, 녹색) | `removed`(제거, 빨강).
`old_no`/`new_no`는 해당 쪽에 존재할 때만 값을 가진다.

### 3.3 baseline_source = "none" 조건

- git 저장소가 아님 + checkpoint 없음
- 또는 git/checkpoint 어디에도 해당 경로가 없는 신규 파일

이 경우 `lines`는 전부 `context`로 채워 평면 뷰와 동일하게 보이고,
프론트의 Diff 토글은 비활성화된다.

## 4. 프론트엔드 컴포넌트

### 4.1 신규 `DiffLine.tsx`
- props: `kind`, `oldNo?`, `newNo?`, `text`
- 배경색: added=녹색, removed=빨강, context=기본
- 좌측 2단 gutter(old 줄번호 | new 줄번호) + `+`/`-`/` ` 마커
- 색상은 기존 디자인 토큰/CSS 변수에 맞춰 다크 테마와 조화

### 4.2 `CodeFileViewer` 확장
- 신규 prop `diffMode: boolean`
- `diffMode === true`: `read_code_file_diff` 결과를 `DiffLine[]`으로 렌더
- `diffMode === false`: 기존 `CodeLine` 평면 뷰 유지 (회귀 없음)

### 4.3 뷰어 헤더 토글
- 헤더에 "Diff" 토글 버튼 + `+N −M` 뱃지
- `baseline_source === "none"` → 토글 **비활성** + tooltip "비교할 기준선이 없습니다"
- 기본값: baseline 존재 + (added+removed > 0) → 자동 ON, 아니면 OFF(평면)

### 4.4 상태 관리 (`CodeExplorer.tsx`)
- 파일 선택 시 `read_code_file_diff` 호출(또는 기존 `read_code_file`와 통합)
- `diffMode` 상태 보관, 파일 전환 시 위 기본값 규칙으로 재계산
- 로딩/에러 처리는 기존 `selectedFile` 패턴 답습

## 5. 데이터 흐름

```
CodeExplorer (page)
  └ 파일 선택 → invoke("read_code_file_diff", {root, path})
       └ Rust: 가드 검증 → 현재 읽기 → baseline(git|checkpoint|none) → similar diff
       ← { baseline_source, added, removed, lines[] }
  └ diffMode 기본값 결정 → CodeFileViewer(diffMode)
       └ diffMode ? lines.map(DiffLine) : CodeLine 평면 뷰
```

## 6. 보안

- baseline 읽기는 **사용자 노출 relpath를 기존 가드로 먼저 검증**한 뒤 사용.
- checkpoint의 경우 내부적으로만 `.vibelign/checkpoints/<ts>/files/<relpath>`로
  매핑. `.vibelign`는 explorer ignored-dir이지만 이 매핑은 **정규화된 relpath만
  결합**하므로 경로 탈출(`..`, 절대경로, 심볼릭 링크 탈출)이 불가능하다.
- `git show HEAD:<path>`도 정규화된 relpath만 인자로 사용.
- 확장자 allowlist(`.swift` 포함)·크기 캡 등 기존 가드는 현재 파일 읽기 경로에서
  그대로 적용된다.

## 7. 의존성

- `vibelign-gui/src-tauri/Cargo.toml`에 `similar = "2"` 추가 (+ Cargo.lock 갱신).
- 직접 LCS 구현 대안도 있으나 정확도/유지보수상 `similar` 채택.

## 8. 테스트

`code_access.rs` 테스트 스타일(TempDir 기반)을 따른다:

1. **git baseline**: temp repo `git init`→commit→파일 수정 → 커맨드 호출 시
   removed/added 라인이 기대대로 나오고 `baseline_source == "git"`.
2. **checkpoint baseline**: git 없는 디렉토리 + `.vibelign/checkpoints/<ts>/files/`에
   원본 사본 배치 → `baseline_source == "checkpoint"`, diff 정상.
3. **baseline 없음**: 신규 파일(git/checkpoint 모두 없음) → `baseline_source == "none"`,
   `lines` 전부 `context`, `added == 0` 및 `removed == 0`.
4. **경로 가드**: parent-escape·절대경로·ignored-dir 입력이 diff 커맨드에서도 거부.
5. `.swift` 등 지원 확장자에서 diff 동작.

프론트는 필요 시 `DiffLine` 렌더 스냅샷/단위 테스트(기존 vitest 셋업) 추가.

## 9. 범위 밖 (YAGNI)

- side-by-side 분할 뷰 (단일 컬럼 unified로 충분)
- word/char-level intra-line diff (line-level만)
- 임의 두 커밋/체크포인트 선택 비교 UI (기준선은 자동 1순위만)
- diff 편집/스테이징/되돌리기 (읽기 전용 유지)
