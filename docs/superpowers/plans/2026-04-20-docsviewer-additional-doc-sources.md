# Docs Viewer 추가 문서 소스 등록 기능 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Docs Viewer가 기본 문서 경로(`PROJECT_CONTEXT.md`, `docs/**`) 외에도 사용자가 등록한 프로젝트 내부 문서 폴더(예: `.omc/plans`, `.sisyphus/plans`)를 안전하게 인덱싱하고 읽을 수 있게 만든다. 숨김 폴더 전체를 열지 않고, 명시적으로 허용된 추가 문서 소스만 allowlist 방식으로 지원한다.

**Architecture in one line:** Python은 docs index의 single source of truth를 유지하되 추가 문서 소스 정책을 별도 모듈로 분리하고, Rust/Tauri는 동일 allowlist 정책으로 안전한 읽기 가드를 맞추며, GUI는 등록/제거 UI만 얇게 붙여 인덱스 재빌드와 표시를 연결한다.

**Tech Stack:** Python 3 (`pathlib`, dataclass/json), Rust/Tauri (`PathBuf`, `canonicalize`, UNC prefix handling), TypeScript/React (DocsViewer UI), existing `vib docs-index` / `.vibelign/docs_index.json` cache bridge.

---

## Non-Goals (Do Not Expand During Initial Implementation)

- [ ] 프로젝트 루트 밖 임의 폴더 열기
- [ ] `.git`, `.venv`, `node_modules` 같은 숨김/생성 폴더 전체 허용
- [ ] 원격 문서 저장소 연동
- [ ] 문서 소스별 권한 시스템/사용자 계정 시스템
- [ ] 문서 소스 설정을 거대한 범용 설정 프레임워크로 일반화

---

## Execution Rules

- [ ] docs index의 owner는 계속 Python (`vibelign/core/docs_cache.py`) 하나만 둔다.
- [ ] 추가 문서 소스는 **프로젝트 루트 내부 디렉토리만** 허용한다.
- [ ] 설정 파일에는 항상 **relative POSIX path** 로 저장한다. (예: `.omc/plans`)
- [ ] allowlist 되지 않은 hidden dir는 기존처럼 계속 차단한다.
- [ ] Python 인덱싱 규칙과 Rust `read_file` 허용 규칙은 반드시 parity를 맞춘다.
- [ ] `.md` / `.markdown` 외 파일은 읽지 않는다.
- [ ] 추가 기능 때문에 기존 기본 문서 소스(`PROJECT_CONTEXT.md`, `docs/**`) 동작이 바뀌면 안 된다.
- [ ] docs index cache / `vib docs-index` / GUI 사이드바는 같은 source 집합을 사용해야 한다.
- [ ] docs visual artifact build도 추가 문서 소스를 동일하게 인식해야 한다.
- [ ] `.vibelign/doc_sources.json` 쓰기는 반드시 atomic write (tempfile + `os.replace`) 로 수행한다. (`docs_index_cache.write_docs_index_cache` 패턴 재사용)
- [ ] Rust는 `doc_sources.json` 을 **직접 파싱하지 않는다**. Python이 이미 정규화한 allowlist를 `docs_index.json` payload 안에 넣어 전달하고, Rust는 그 필드만 소비한다. (정규화 규칙 중복 구현 금지)
- [ ] docs index cache payload 는 `sources_fingerprint` 를 포함하며, fingerprint mismatch 는 cache miss 로 처리한다. (source 추가/제거 즉시 반영 보장)
- [ ] Built-in source (`PROJECT_CONTEXT.md`, `docs/**`, README 등) 는 사용자가 제거할 수 없다. 제거 API는 extra source 에 한정한다.
- [ ] 등록된 source root 아래에서도 `docs_scan._should_skip_dir` 의 prune 정책은 그대로 적용된다. (`.omc/plans/.archive/` 는 등록했어도 스캔 제외)
- [ ] GUI 는 **backend 가 재빌드한 full index payload 를 받은 뒤에만** extra source 문서를 selectable 상태로 보여준다. cache fallback 중에는 built-in 만 selectable 이어야 하며, “보이지만 read 실패” 상태를 만들면 안 된다.

---

## Cross-Platform Rules (Windows / macOS / Linux)

> 이 기능은 경로 정규화가 핵심이다. 저장 형식과 실제 접근 판정을 분리하고, 비교는 항상 canonical path 기준으로 수행한다.

- [ ] 설정 저장 값은 OS와 무관하게 `/` 기준 relative path 문자열로 통일한다.
- [ ] Windows `\` 입력은 backend 정규화 단계에서 `/` 로 바꾼 뒤 저장한다.
- [ ] 허용 판정은 raw string 비교가 아니라 `canonicalize()` 후 project root에 `strip_prefix()` 가능한지로 확인한다.
- [ ] Windows UNC prefix (`\\?\`) 는 기존 `strip_unc_prefix()` 패턴을 그대로 재사용한다.
- [ ] Windows 대소문자 차이로 중복 저장되지 않도록 canonical path 기반으로 dedupe 한다.
- [ ] symlink / junction 때문에 겉보기 경로는 루트 내부여도 실제가 루트 밖이면 거부해야 한다.
- [ ] Tauri dialog가 절대 경로를 반환해도 저장은 backend가 relative path로 재계산해 확정한다.
- [ ] 테스트에 Windows-style path (`.OMC\\plans`, `foo\\bar`) 케이스를 반드시 포함한다.

---

## Edge Cases That Must Be Verified

- [ ] 등록된 `.omc/plans/*.md` 는 사이드바에 보이지만, 미등록 `.omc/other/*.md` 는 보이지 않는다.
- [ ] 추가 문서 소스를 등록해도 `.git/`, `.venv/`, `node_modules/` 는 계속 스캔/읽기 금지다.
- [ ] 존재하지 않는 폴더, 파일 경로, 중복 경로 등록 요청은 안전하게 거부된다.
- [ ] `..` 포함 경로, absolute path, project root 밖 경로는 거부된다.
- [ ] 동일 문서가 built-in source와 extra source에 중복 노출되지 않는다.
- [ ] 사이드바에 보이는 추가 문서는 실제 클릭 시 읽기 성공해야 한다. (index/read parity)
- [ ] docs index rebuild 후 `.vibelign/docs_index.json` 이 새 source를 반영한다.
- [ ] `vib docs-build` 전체 재생성 시 추가 문서 소스도 artifact 생성 대상에 포함된다.
- [ ] Windows에서 `\` 경로 입력과 BOM 포함 markdown 파일이 기존처럼 안전하게 동작한다.
- [ ] 등록 root 내부의 hidden sub-dir (`.archive/`, `.git/` 등) 는 등록된 source 아래여도 prune 된다.
- [ ] 사용자가 built-in source (`docs/`, `PROJECT_CONTEXT.md`) 를 제거 API로 삭제하려 하면 거부된다.
- [ ] source 추가/제거 직후 stale cache 가 반환되지 않는다. (`sources_fingerprint` mismatch → cache miss 경로 동작)
- [ ] GUI 에서 source 추가 중 동시에 `read_file` 호출해도 partial JSON 으로 인한 실패가 없다. (atomic write 검증)
- [ ] 현재 열려 있는 문서의 source 가 제거되면 사이드바에서 사라지고 뷰어는 현재 내용을 유지하되 다음 탐색부터 해당 source 에 접근 불가.
- [ ] 등록한 source 의 파일 수가 과도할 때 (e.g. 10k+) index 가 한도를 초과하면 경고를 돌려준다.
- [ ] extra source 내부 문서의 rename / move / delete 후 orphan `docs_visual` artifact 가 남지 않는다.
- [ ] 동일 파일명 문서가 여러 source 에 존재해도 selection key 는 항상 relative path 기준으로 안정적이며, 잘못된 문서로 점프하지 않는다.
- [ ] extra source 문서의 추가/제거/재빌드가 watcher 또는 refresh 흐름의 self-loop 를 만들지 않는다.
- [ ] 등록된 source root 자체가 삭제되거나 rename 되었을 때, 사이드바/캐시/읽기 가드가 stale 상태 없이 graceful fallback 한다.
- [ ] Linux case-sensitive 환경에서 `README.md` 와 `readme.md` 같은 경로 충돌이 잘못 dedupe 되지 않는다.
- [ ] extra source 안의 비UTF-8 또는 손상된 markdown 파일도 기존 built-in 문서와 동일한 오류 처리/fallback 규칙을 따른다.

---

## Main Files To Touch

| 파일 | 역할 | 변경 |
|------|------|------|
| `vibelign/core/doc_sources.py` | 추가 문서 소스 설정/정규화/allowlist 정책, atomic write, fingerprint 계산 | Create |
| `vibelign/core/meta_paths.py` | `.vibelign/doc_sources.json` 경로 추가 | Modify |
| `vibelign/core/docs_cache.py` | built-in source + extra source 통합 인덱싱, 등록 root 내 hidden sub-dir prune | Modify |
| `vibelign/core/docs_index_cache.py` | payload 에 `allowlist` / `sources_fingerprint` 필드 추가, mismatch 는 cache miss | Modify |
| `vibelign/core/docs_scan.py` | 전역 hidden prune 정책은 유지 (helper 재사용만) | Modify (minimal or none) |
| `vibelign/commands/vib_docs_build_cmd.py` | docs index / docs build가 extra source 동일 취급 | Modify |
| `vibelign-gui/src-tauri/src/docs_access.rs` | allowlist 판정 helper (**필수 분리**, parity 테스트 단일 진입점) | Create |
| `vibelign-gui/src-tauri/src/lib.rs` | `read_file` / docs commands 가 `docs_access` 헬퍼 사용 | Modify |
| `vibelign-gui/src/lib/vib.ts` | add/remove/list extra doc sources bridge + rebuild 트리거 | Modify |
| `vibelign-gui/src/lib/docs.ts` | `Custom` category label/order helper | Modify |
| `vibelign-gui/src/pages/DocsViewer.tsx` | 문서 소스 추가/제거 UI + rebuild wiring | Modify |
| `tests/test_docs_build_cmd.py` | extra source index/build 회귀 테스트 | Modify |
| `tests/test_meta_paths.py` | doc_sources path 추가 테스트 | Modify |
| `tests/test_doc_sources.py` | normalize/add/remove/atomic-write/fingerprint 테스트 | Create |
| `tests/test_cross_platform_paths.py` 또는 신규 테스트 | Windows path normalization / outside-root rejection | Modify/Create |
| Rust 테스트 (`src-tauri/src/docs_access.rs` 내 `#[cfg(test)]`) | hidden-path allowlist read parity 테스트 | Create |

---

## Data Contract

### `.vibelign/doc_sources.json`

```json
{
  "version": 1,
  "sources": [
    ".omc/plans",
    ".sisyphus/plans"
  ]
}
```

### Rules

- `version` 은 정수
- `sources` 는 문자열 배열
- 저장 전 정규화 수행
- 내부 저장값은 항상 relative POSIX path
- 중복 제거 및 정렬
- 등록 실패는 명확한 에러 메시지 반환
- 쓰기는 atomic: 같은 dir 에 tempfile 생성 → `os.replace` → (Windows 재시도). `docs_index_cache.write_docs_index_cache` 와 동일 패턴

### `.vibelign/docs_index.json` payload 확장

Rust `read_file` 가드가 이 파일만 읽어 allowlist 판정을 수행하도록, Python 이 정규화된 결과를 payload 에 포함한다.

```json
{
  "schema_version": 2,
  "root": "...",
  "generated_at_ms": 0,
  "sources_fingerprint": "sha256:...",
  "allowlist": {
    "extra_source_roots": [".omc/plans", ".sisyphus/plans"]
  },
  "entries": [ ... ]
}
```

- `schema_version` 은 `1` → `2` 로 bump (기존 캐시 자동 invalidate)
- `sources_fingerprint` 는 **정규화된 `sources` 배열만**으로 계산한다: `sha256(JSON.dumps(sorted_sources, ensure_ascii=False, separators=(",", ":")))`
- `allowlist.extra_source_roots` 는 정규화된 relative POSIX path 배열
- Rust 는 이 배열만 읽고 `doc_sources.json` 은 읽지 않는다
- fingerprint 가 현재 `doc_sources.load().fingerprint()` 와 다르면 cache miss

### Initial policy — `docs_visual` artifact 경로

> 아래 항목은 **초기 구현 정책**이다. 안전성/일관성 계약은 고정하지만, 저장 경로 네이밍 자체는 구현 중 테스트 결과에 따라 조정 가능하다.

- built-in source: 기존 그대로 `.vibelign/docs_visual/<rel>.json`
- extra source (hidden dir 포함): `.vibelign/docs_visual/_extra/<rel>.json`
- 이유: `.vibelign/docs_visual/.omc/plans/foo.md.json` 같이 nested hidden dir 를 만들지 않기 위함 — FS watcher/툴 오작동 방지

### Initial policy — Category 라벨

> 아래 항목은 **초기 UX 정책**이다. 구현/사용성 검증 결과에 따라 조정 가능하지만, built-in 과 extra source 를 구분해서 표시한다는 원칙은 유지한다.

- 등록된 extra source 의 문서는 **모두 `Custom` 카테고리** 로 라벨링
- UI 는 카테고리 옆에 source root 라벨 (예: `Custom · .omc/plans`) 병기
- built-in `Plan` / `Spec` / `Wiki` 재사용하지 않음 (사용자가 등록한 임의 디렉토리가 built-in 과 섞이면 필터/정렬 UX 가 모호해짐)

### Initial policy — Resource limits

> 파일 수 상한은 **초기 운영값**이다. 값 자체는 구현/실측 결과에 따라 조정 가능하지만, 무제한 스캔을 허용하지 않는다는 원칙은 유지한다.

- extra source 하나당 markdown 파일 수 상한: 기본 `2000`
- 초과 시 인덱싱은 상한까지 수행하고 warning 반환 (등록 자체는 허용)
- 상한값은 상수로 `doc_sources.py` 에 두고 테스트에서 fixture 로 override

---

## Module Boundary Recommendation

- `docs_cache.py` 는 **index orchestrator** 로 유지한다.
- `docs_scan.py` 의 전역 hidden-dir 차단 정책은 유지한다. hidden dir 허용은 여기서 전역 완화하지 않는다.
- 새 정책은 `doc_sources.py` 로 분리해, "무엇을 문서 소스로 볼 것인가"를 한 곳에서 관리한다.
- Rust 쪽은 `lib.rs` 에 로직을 더 쌓지 않고 `docs_access.rs` 로 **반드시 분리**한다. 이 모듈이 allowlist 판정의 유일한 진입점이며 parity 테스트도 여기에 둔다.
- Rust 는 `doc_sources.json` 을 직접 읽지 않는다. Python 이 채운 `docs_index.json` 의 `allowlist` 필드만 소비한다 — 정규화 규칙 중복 구현 금지.
- Frontend는 새 거대 상태 계층을 만들지 않고 `DocsViewer.tsx`에 얇은 source-management UI만 추가한다.

---

## Global Completion Tracker

- [ ] Phase 1 — 추가 문서 소스 저장소 정의
- [ ] Phase 2 — Python docs index에 extra source 통합
- [ ] Phase 3 — docs build / docs index cache parity 확보
- [ ] Phase 4 — Tauri read guard allowlist parity 확보
- [ ] Phase 5 — Docs Viewer source-management UI 추가
- [ ] Phase 6 — Cross-platform / regression verification

---

## Phase 1 — 추가 문서 소스 저장소 정의

**Target outcome:** `.vibelign/doc_sources.json` 의 경로, 스키마, 정규화 규칙이 고정되고, backend에서 add/remove/list 할 수 있다.

**Files**
- Create: `vibelign/core/doc_sources.py`
- Modify: `vibelign/core/meta_paths.py`
- Test: `tests/test_meta_paths.py` + 신규 `tests/test_doc_sources.py`

**Implementation checklist**
- [ ] `MetaPaths` 에 `doc_sources_path` 추가
- [ ] `doc_sources.py` 에 read/write/load/save helper 추가
- [ ] normalize 함수 추가: absolute/outside-root/`..`/non-dir/dedup/re-sort 처리
- [ ] canonical path → relative POSIX path 변환 규칙 고정
- [ ] save helper 는 **atomic write** 로 구현 (tempfile + `os.replace`, Windows 재시도)
- [ ] `fingerprint(sources: list[str]) -> str` 헬퍼 추가 — sorted list 의 SHA-256
- [ ] `MAX_FILES_PER_SOURCE = 2000` 상수 및 초과 시 warning 반환 API 설계
- [ ] built-in source 는 제거 API 대상에서 제외하는 guard (`remove()` 호출 시 extra source 만 허용)
- [ ] 에러 메시지를 사용자/GUI가 그대로 보여줄 수 있게 명확히 설계

**Validation**
- [ ] 빈 설정 파일/없는 파일에서 안전하게 `[]` 로 읽힌다
- [ ] `.omc/plans` 저장 시 그대로 relative POSIX path로 유지된다
- [ ] `foo\\bar` 입력도 `foo/bar` 로 정규화된다
- [ ] 루트 밖 절대 경로는 거부된다
- [ ] 동일 sources list 에 대해 `fingerprint()` 는 결정적 결과를 낸다
- [ ] partial 상태의 tempfile 이 `load()` 에 절대 보이지 않는다 (atomic 보장)

**Completion gate**
- [ ] 저장 포맷이 OS 무관하게 안정적이다
- [ ] `MetaPaths`가 새 경로를 discoverable 하게 제공한다
- [ ] atomic write 와 fingerprint API 가 공개 계약으로 고정됐다

---

## Phase 2 — Python docs index에 extra source 통합

**Target outcome:** built-in source + 등록된 extra source가 한 index 결과로 합쳐진다.

**Files**
- Modify: `vibelign/core/docs_cache.py`
- Modify: `vibelign/core/doc_sources.py`
- Optional minimal touch: `vibelign/core/docs_scan.py`
- Test: `tests/test_docs_build_cmd.py`, `tests/test_doc_sources.py`

**Implementation checklist**
- [ ] `_iter_index_targets()`가 built-in source 등록 후 extra source를 추가로 순회한다
- [ ] hidden dir 전역 스캔 완화 없이, **등록된 source directory만 직접 walk/glob** 한다
- [ ] 등록된 source root 아래에서도 `docs_scan._should_skip_dir` 규칙은 그대로 적용한다 (`.omc/plans/.archive/` 는 prune)
- [ ] `seen` dedupe 규칙을 built-in / extra source 모두에 적용한다 (canonical resolved path 기준)
- [ ] 카테고리는 `Custom` 고정, entry 에 `source_root` 메타 (예: `.omc/plans`) 포함해 UI 가 병기 라벨을 표시할 수 있게 한다
- [ ] `DocsIndexEntry` 에 `source_root: str | None` 필드 추가 (built-in = `None`, extra = 해당 root)
- [ ] source 하나당 파일 수가 `MAX_FILES_PER_SOURCE` 초과 시 상한까지만 수집하고 warning 기록

**Validation**
- [ ] 등록된 `.omc/plans/plan.md` 가 index에 나타나며 `category="Custom"`, `source_root=".omc/plans"` 로 라벨링
- [ ] 미등록 hidden path는 계속 index에서 제외된다
- [ ] 등록된 source 내부의 hidden sub-dir (`.archive/`) 는 여전히 제외된다
- [ ] built-in `docs/superpowers/plans/*.md` 와 중복 등록 시 한 번만 노출된다 (built-in 이 우선)

**Completion gate**
- [ ] index owner가 계속 Python 하나로 유지된다
- [ ] 기존 docs discovery 계약이 깨지지 않는다
- [ ] `DocsIndexEntry` 확장이 기존 JSON 소비자를 깨지 않는다 (optional 필드로 추가)

---

## Phase 3 — docs build / docs index cache parity 확보

**Target outcome:** `vib docs-index`, `.vibelign/docs_index.json`, `vib docs-build` 가 모두 같은 source 집합을 본다.

**Files**
- Modify: `vibelign/commands/vib_docs_build_cmd.py`
- Modify: `vibelign/core/docs_index_cache.py` (필요 시)
- Test: `tests/test_docs_build_cmd.py`

**Implementation checklist**
- [ ] `docs_index_cache` schema_version 을 `1` → `2` 로 bump (기존 캐시 자동 invalidate)
- [ ] `_make_payload()` 에 `sources_fingerprint`, `allowlist.extra_source_roots` 필드 추가
- [ ] `read_docs_index_cache()` 가 fingerprint mismatch 시 `None` 반환 (cache miss)
- [ ] `rebuild_docs_index_cache()`가 extra source 포함 결과를 캐시한다
- [ ] `run_vib_docs_index()` JSON 출력이 extra source 와 allowlist/fingerprint 를 반영한다
- [ ] `build_docs_visual_cache()` 전체 재생성 대상에 extra source 포함
- [ ] extra source 문서의 artifact 경로는 `.vibelign/docs_visual/_extra/<rel>.json` 으로 기록 — `meta_paths.docs_visual_path()` 시그니처에 `is_extra: bool` 추가 또는 source 기반 자동 판단
- [ ] 단일 문서 build 시 등록된 hidden path relative key 도 `_extra/` 접두사로 일관 처리

**Validation**
- [ ] GUI cache hit 시에도 extra source 문서가 보인다
- [ ] source 추가 직후 cache 는 자동으로 miss 되어 재빌드된다 (fingerprint mismatch)
- [ ] cache miss 후 subprocess rebuild 시에도 동일 결과다
- [ ] extra source 문서 artifact 가 `.vibelign/docs_visual/_extra/...` 아래 생성되며, `.vibelign/docs_visual/.omc/` 같은 nested hidden dir 는 만들어지지 않는다

**Completion gate**
- [ ] GUI / CLI / cache 간 source 불일치가 없다
- [ ] stale cache 로 인한 "sidebar 미반영" 재현 불가능함이 테스트로 고정됐다

---

## Phase 4 — Tauri read guard allowlist parity 확보

**Target outcome:** 사이드바에 보이는 extra source 문서는 실제 클릭해서 읽을 수 있고, 미등록 hidden path는 여전히 막힌다. **Rust 는 `doc_sources.json` 을 직접 파싱하지 않는다** — Python 이 이미 정규화해 둔 `docs_index.json` 의 `allowlist` 필드만 소비한다.

**Files**
- Create: `vibelign-gui/src-tauri/src/docs_access.rs` (**필수 분리**)
- Modify: `vibelign-gui/src-tauri/src/lib.rs`
- Test: `docs_access.rs` 내 `#[cfg(test)]` module — hidden-path allowlist parity

**Implementation checklist**
- [ ] `docs_access.rs` 에 `ExtraSourceAllowlist` 구조체 추가 — `docs_index.json` 의 `allowlist.extra_source_roots` 만 읽어 메모리 set 으로 유지
- [ ] `ExtraSourceAllowlist::load(root: &Path) -> Result<Self>` — `.vibelign/docs_index.json` 한 번만 열고, 파싱 실패/파일 없음은 빈 allowlist 로 fallback (built-in 만 동작)
- [ ] `is_allowed_doc_path(rel: &str, extras: &ExtraSourceAllowlist) -> bool` — built-in 규칙 (기존 hidden/IGNORED_DIRS prune) OR extra allowlist 매칭 둘 중 하나라도 true 면 허용
- [ ] extra 매칭 로직: `rel` 의 각 allowlist prefix 에 대해 `rel == prefix || rel.starts_with(format!("{prefix}/"))` 이고, `rel` 의 prefix 이후 세그먼트 에도 hidden/IGNORED_DIRS prune 을 다시 적용
- [ ] `lib.rs` 의 `resolve_doc_path()` 가 호출 당 allowlist 로드 (또는 fresh-if-mtime-changed 캐싱) 후 새 시그니처에 위임
- [ ] `doc_sources.json` 직접 parse 금지 — Rust 코드에서 해당 파일 이름이 등장하면 리뷰에서 reject
- [ ] UNC prefix 제거, `canonicalize`, `strip_prefix(root)` 패턴 유지
- [ ] `.md` / `.markdown` 확장자 제한은 그대로 유지
- [ ] Rust 측 `DOCS_INDEX_CACHE_SCHEMA_VERSION` 상수 `1` → `2` 로 동반 bump — Python 만 `2` 로 올리면 Rust `read_docs_index_cache_file()` 가 항상 mismatch 로 `None` 반환해 GUI 실행마다 subprocess cold-start
- [ ] `DocsIndexCachePayload` Rust 구조체에 `sources_fingerprint: Option<String>`, `allowlist: Option<...>` 필드를 `#[serde(default)]` 로 추가 (Rust 가 fingerprint 를 검증하진 않더라도, unknown-field 정책 변경 시 회귀 방지)
- [ ] `DocsIndexEntry` Rust 구조체에 `source_root: Option<String>` 필드 `#[serde(default)]` 로 추가 — 없으면 serde 가 값을 drop 해 GUI 가 `Custom · .omc/plans` 라벨 (167·355줄) 을 렌더 못함
- [ ] `read_docs_visual` 가 extra source 문서의 artifact 를 `.vibelign/docs_visual/_extra/<rel>.json` 에서 찾도록 경로 해결 분기 추가 — 이 분기는 `docs_access.rs` 의 allowlist 매칭 결과를 재사용한다 (built-in 은 기존 경로 유지, extra 만 `_extra/` 접두사). 없으면 extra 문서의 visual artifact 가 항상 null 로 반환돼 사이드바에 visual 누락

**Validation**
- [ ] 등록된 `.omc/plans/a.md` 는 `read_file` 성공
- [ ] 미등록 `.omc/private.md` 는 `read_file` 실패
- [ ] 등록된 root 아래 hidden sub-dir `.omc/plans/.archive/x.md` 는 실패
- [ ] 루트 밖 문서는 계속 실패
- [ ] `docs_index.json` 없거나 파싱 실패 시 built-in allowlist 만으로 graceful fallback (extra source 는 못 읽지만 built-in 은 정상)
- [ ] `docs_index.json` 없거나 파싱 실패 중인 상태에서 GUI 가 extra source 항목을 selectable 로 노출하지 않는다 (visible-but-unreadable 상태 금지)
- [ ] Windows-style input path도 최종 relative path 매칭이 안정적이다
- [ ] Python 의 `allowlist.extra_source_roots` 와 Rust 의 in-memory set 이 동일 내용일 때 같은 판정을 내린다 (parity 테스트)
- [ ] `schema_version = 2` payload 를 Rust `read_docs_index_cache_file()` 가 정상 수락해 subprocess fallback 이 발생하지 않는다 (캐시 hit 회귀 방지)
- [ ] extra source 문서 클릭 시 `read_docs_visual` 가 `.vibelign/docs_visual/_extra/<rel>.json` 에서 artifact 를 찾아 반환한다 (built-in 은 기존 경로 유지 회귀 테스트 동반)
- [ ] `source_root` 필드가 Rust 구조체를 거쳐 프론트엔드까지 도달해 `Custom · <root>` 라벨이 렌더된다 (null/empty 회귀 방지)

**Completion gate**
- [ ] Python index 결과와 Rust read guard 가 같은 문서 집합을 허용한다
- [ ] Rust 코드에서 `doc_sources.json` 을 여는 호출이 존재하지 않는다 (grep 으로 확인)
- [ ] Python / Rust `DOCS_INDEX_CACHE_SCHEMA_VERSION` 가 같은 값 (`2`) 으로 bump 되어 있다

---

## Phase 5 — Docs Viewer source-management UI 추가

**Target outcome:** 사용자가 GUI에서 추가 문서 소스를 등록/제거하고 즉시 사이드바에 반영할 수 있다.

**Files**
- Modify: `vibelign-gui/src/lib/vib.ts`
- Modify: `vibelign-gui/src/lib/docs.ts`
- Modify: `vibelign-gui/src/pages/DocsViewer.tsx`

**Implementation checklist**
- [ ] Tauri bridge 함수 추가: `list_extra_doc_sources` / `add_extra_doc_source(path)` / `remove_extra_doc_source(path)` — 모두 Python helper 호출
- [ ] `add` / `remove` 는 **내부에서 `rebuild_docs_index_cache()` 를 직접 호출해 완료 후 리턴** (별도 rebuild RPC 불필요, race 방지)
- [ ] `remove` 는 rebuild 전에 `.vibelign/docs_visual/_extra/<source_root>/` subtree 를 삭제해 orphan artifact 가 남지 않도록 한다 (built-in artifact 경로는 절대 건드리지 않음 — `_extra/` 하위만 대상, path traversal 방지 위해 resolved path 가 `_extra/` 안에 있는지 재확인)
- [ ] `add` / `remove` 반환 payload 에 갱신된 full index entries 포함 — 프론트엔드는 단일 라운드트립으로 사이드바를 다시 그린다
- [ ] Rust 쪽 `ExtraSourceAllowlist` in-memory 캐시는 cache invalidation 신호 (mtime 변경) 로 다음 `read_file` 호출 시 자동 갱신되게 한다
- [ ] 프론트엔드는 optimistic source 추가를 하지 않는다. backend 가 재빌드 완료 후 반환한 **authoritative full index** 만 렌더한다
- [ ] DocsViewer 상단 또는 사이드바에 `문서 소스 추가` 버튼 추가
- [ ] 폴더 선택 (Tauri dialog) → backend 정규화 → 거부 시 에러 토스트 / 성공 시 새 index 즉시 반영
- [ ] 현재 등록된 source 목록 (built-in 과 분리된 섹션) + 제거 버튼 추가, built-in 은 제거 불가 표시
- [ ] 등록 실패 시 backend 에러 메시지를 그대로 토스트에 노출
- [ ] 현재 열린 문서의 source 가 제거되면 뷰어 콘텐츠는 유지, 사이드바에서는 사라지며 다음 탐색부터 접근 불가
- [ ] 첫 버전에서는 source별 복잡한 필터/정렬 UX를 만들지 않는다 (`Custom · <root>` 라벨만 표시)

**Validation**
- [ ] source 추가 후 **별도 rebuild 버튼 없이** 단일 add 호출로 사이드바 갱신
- [ ] source 추가 직후 backend 응답 전까지 새 extra source 문서는 placeholder 또는 pending 상태일 뿐 selectable 상태는 아니다
- [ ] source 제거 후 문서 목록에서 사라지며, `.vibelign/docs_visual/_extra/<source_root>/` artifact subtree 도 동반 삭제된다 (built-in artifact 경로는 영향 없음)
- [ ] built-in source 제거 버튼이 UI 에 존재하지 않는다
- [ ] 등록 실패 케이스 (root 밖, `..`, 존재하지 않음) 에서 에러 토스트가 정확히 표시됨
- [ ] 기존 검색/선택 UX는 유지

**Completion gate**
- [ ] 사용자 관점에서 “폴더 추가 → 문서 보임” 흐름이 단일 클릭으로 완결된다
- [ ] rebuild 트리거 메커니즘이 명확히 한 경로 (add/remove RPC 내부) 로 일원화됐다

---

## Phase 6 — Cross-platform / regression verification

**Target outcome:** macOS/Windows/Linux에서 path normalization과 hidden-source allowlist가 회귀 없이 동작한다.

**Files**
- Modify: `tests/test_cross_platform_paths.py` 또는 신규 테스트
- Modify: `tests/test_docs_build_cmd.py`
- Modify/Create: Rust/Tauri tests

**Implementation checklist**
- [ ] Python unit tests: normalize/add/remove/load/save
- [ ] Python unit tests: atomic write — 동시 load/save 시 partial JSON 노출 없음 (스레드 또는 subprocess fixture)
- [ ] Python unit tests: `fingerprint()` 결정성 및 sources list 변경 시 값 변화
- [ ] Python unit tests: `docs_index_cache` fingerprint mismatch → cache miss 경로 동작
- [ ] Python unit tests: index includes registered hidden sources only, 등록 root 내 hidden sub-dir 는 제외
- [ ] Python unit tests: built-in source 제거 API 거부
- [ ] Python unit tests: `MAX_FILES_PER_SOURCE` 초과 시 warning + 상한 적용
- [ ] Python unit tests: `_extra/` 접두사로 `docs_visual` artifact 가 기록되며 nested hidden dir 생성 없음
- [ ] CLI/build tests: extra source artifact generation 및 `docs_index.json` payload 에 `allowlist` / `sources_fingerprint` 포함 검증
- [ ] Rust tests: read parity (`is_allowed_doc_path`) — built-in/extra/미등록/등록 root 내 hidden sub-dir 네 가지 경계 케이스
- [ ] Rust tests: `docs_index.json` 없거나 malformed 일 때 built-in 만으로 graceful fallback
- [ ] Rust tests: 소스에 `doc_sources.json` 문자열 리터럴이 등장하지 않음을 간단히 grep 기반으로 고정 (회귀 방지)
- [ ] Windows-style path input cases 추가 (`.OMC\\plans`, `foo\\bar`, UNC prefix)

**Suggested verification commands**
- [ ] `python -m pytest tests/test_meta_paths.py tests/test_doc_sources.py tests/test_docs_build_cmd.py tests/test_cross_platform_paths.py -v`
- [ ] `cd vibelign-gui/src-tauri && cargo test docs_access`
- [ ] GUI contract smoke: add → list → remove 단일 세션에서 사이드바 반영 확인

**Completion gate**
- [ ] Windows-safe path policy가 테스트로 고정되었다
- [ ] 숨김 폴더 전체 허용으로 정책이 새지 않았다
- [ ] stale cache / partial write / Rust-side JSON 재파싱 등 리뷰에서 지적한 4대 결함이 각각 실패 테스트 → 성공으로 고정됐다
- [ ] 기존 Docs Viewer 기능 회귀가 없다

---

## Final Success Criteria

- [ ] 사용자가 `.omc/plans` 같은 프로젝트 내부 폴더를 추가 문서 소스로 등록할 수 있다.
- [ ] Docs Viewer는 그 폴더의 markdown 파일을 일반 문서처럼 목록/읽기/재빌드할 수 있다.
- [ ] 미등록 hidden folder는 여전히 차단되고, 등록 root 내부의 hidden sub-dir 도 차단된다.
- [ ] Python index와 Rust read guard의 문서 허용 범위가 일치하며, 그 parity 는 `docs_index.json.allowlist` 라는 단일 진실 원천으로 유지된다.
- [ ] source 추가/제거 즉시 사이드바에 반영된다 — stale cache 는 `sources_fingerprint` 로 자동 invalidate 된다.
- [ ] `doc_sources.json` 쓰기가 atomic 이어서 동시 `read_file` 호출이 partial JSON 을 보지 않는다.
- [ ] Windows path normalization/UNC/case 차이로 인한 경로 버그가 테스트로 방지된다.
- [ ] 구현이 한 파일에 몰리지 않고, 정책(`doc_sources.py`)/인덱싱(`docs_cache.py`)/읽기(`docs_access.rs`)/UI(`DocsViewer.tsx`) 책임 경계가 유지된다.
