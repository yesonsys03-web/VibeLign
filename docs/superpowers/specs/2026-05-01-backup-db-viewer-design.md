# Backup DB Viewer 설계

> **Status:** draft for review. Implementation plan not written yet.

## 문제

Backup Engine v2는 백업 목록과 메타데이터를 `.vibelign/vibelign.db`에 저장하고, 실제 파일 내용은 `.vibelign/rust_objects/`에 중복 없이 보관한다. GUI의 BACKUPS 화면은 사용자가 이해하기 쉬운 백업 목록을 보여주지만, 개발자/관리자가 DB 기준으로 상태를 확인하기는 어렵다.

- 백업 DB가 Rust v2 경로를 정상 사용 중인지
- 백업별 파일 수, 실제 저장 크기, 재사용 파일 수, 생성 이유가 무엇인지
- 자동 백업 설정과 정리 정책이 어떤 값인지
- GUI 목록에 보이는 백업이 DB row와 어떻게 매칭되는지

반대로 `.vibelign/vibelign.db`를 일반 SQLite 편집기처럼 직접 편집하게 하면 복원 무결성이 깨질 수 있다. 특히 `checkpoint_files`, `cas_objects`, `object_hash`, `ref_count`, `engine_version`, `checkpoint_id`는 복원·미리보기·정리 로직이 직접 의존한다. 첫 구현은 편집 기능을 넣지 않고, DB를 안전하게 볼 수 있는 읽기 전용 viewer로 제한한다.

## 목표

BACKUPS 탭 안에 자식 메뉴인 **Backup DB Viewer**를 추가해 `.vibelign/vibelign.db`의 상태와 백업 메타데이터를 읽기 전용으로 확인할 수 있게 한다.

핵심 원칙:

- 이 기능은 Raw SQL 편집기가 아니라 **백업 DB 뷰어**다.
- 첫 구현은 읽기 전용이다.
- DB 내용을 raw table dump처럼 노출하지 않고, 요약 카드·검색 가능한 목록·상세 패널로 읽기 쉽게 보여준다.
- 편집 기능은 후속 phase로 분리한다.
- React에서 SQL 문자열을 보내지 않는다.
- 복원에 필요한 내부 테이블과 해시/object 저장소 정보는 읽기 전용이다.

사용자에게 보이는 말 규칙:

| 내부 용어 | 사용자에게 보이는 말 |
|---|---|
| checkpoint | 백업 / 저장본 |
| checkpoint_id | 저장본 ID |
| trigger | 만들어진 이유 |
| post_commit | 코드 저장 뒤 자동 보관 |
| CAS object | 중복 없이 보관한 파일 |
| vibelign.db | 백업 관리 DB |
| raw SQL | 화면에 표시하지 않음 |

## 범위

### 포함

- BACKUPS 화면의 자식 메뉴로 들어갈 수 있는 Backup DB Viewer
- 백업 DB 상태 요약
- 백업 row 상세 조회
- object store 통계 조회
- 백업 관리 DB 파일 크기(`vibelign.db`, `vibelign.db-wal`, `vibelign.db-shm`) 조회
- 자동 백업 설정 조회
- 정리 정책 조회
- GUI 백업 목록과 DB row 매칭 확인
- checkpoint table / object table / retention table의 읽기 전용 요약

### 제외

- 임의 SQL 실행창
- 모든 DB 편집 기능
- `checkpoint_files` 편집
- `cas_objects` 편집
- object 파일 직접 삭제/이동
- 백업 DB schema migration을 GUI에서 수동 실행하는 기능
- Python fallback JSON checkpoint를 같은 화면에서 편집하는 기능

Python fallback 백업은 `.vibelign/checkpoints/` JSON manifest를 사용한다. 이번 기능은 Rust/SQLite 백업 DB viewer이며, fallback JSON 백업 viewer/edit 기능은 별도 후속 기능으로 둔다.

## 읽기 전용 정책

첫 구현은 DB를 수정하지 않는다. 다음 값은 표시할 수 있지만 편집할 수 없다.

- `checkpoints.checkpoint_id`
- `checkpoints.created_at`
- `checkpoints.engine_version`
- `checkpoints.parent_checkpoint_id`
- `checkpoints.trigger`
- `checkpoints.git_commit_sha`
- `checkpoints.git_commit_message`
- `checkpoints.total_size_bytes`
- `checkpoints.file_count`
- `checkpoints.original_size_bytes`
- `checkpoints.stored_size_bytes`
- `checkpoints.reused_file_count`
- `checkpoints.changed_file_count`
- 모든 `checkpoint_files.*`
- 모든 `cas_objects.*`
- `db_meta.schema_version`
- `db_meta.created_at`

`trigger`, `git_commit_sha`, `git_commit_message`는 provenance 정보이므로 처음에는 읽기 전용으로 둔다. 나중에 사용자가 수동 수정 필요성을 명확히 제기하면 별도 spec에서 다룬다.

## DB 파일 성장 정책

기존 `retention_policy.max_total_size_bytes`는 백업 데이터와 CAS/object-store 정리 기준이다. SQLite 관리 파일인 `.vibelign/vibelign.db` 자체는 row 삭제 후에도 즉시 작아지지 않을 수 있고, WAL 모드에서는 `.vibelign/vibelign.db-wal`과 `.vibelign/vibelign.db-shm`도 함께 관찰해야 한다. 따라서 DB 파일 성장 정책은 object-store retention과 분리한다.

첫 구현에서 DB Viewer는 다음을 읽기 전용으로 표시한다.

- `vibelign.db` 크기
- `vibelign.db-wal` 크기
- `vibelign.db-shm` 크기
- 세 파일의 합산 크기

운영 정책:

- 64MB 이상: 경고 상태로 표시하고, 백업 정리 뒤 DB 압축/정리 필요성을 안내한다.
- 256MB 이상: 강한 경고 상태로 표시하고, 별도 CLI maintenance 명령에서 compaction을 수행해야 한다.
- DB Viewer는 여전히 읽기 전용이다. `VACUUM`, `PRAGMA wal_checkpoint(TRUNCATE)`, `incremental_vacuum` 같은 쓰기/정리 작업은 이 화면에서 직접 실행하지 않는다.
- 실제 DB compaction은 `vib backup-db-maintenance` 명령으로 분리한다. 기본은 dry-run이며, 실제 정리는 `--apply`를 붙였을 때만 실행한다. 이 명령은 백업 작업 중이 아닐 때만 실행하고, 실행 전 quick-check/잠금 확인/DB 원본 파일 백업을 수행한다.
- Rust와 Python fallback의 백업 대상 정책은 정렬해야 한다. Rust snapshot은 `.vibelign/vibelign.db*`를 제외하므로, Python fallback도 동일한 제외 정책을 갖는지 별도 확인·수정한다.

maintenance 명령의 동작:

1. dry-run에서 `vibelign.db*` 크기, `page_size`, `page_count`, `freelist_count`, `quick_check`, 실행 계획을 보고한다.
2. `--apply`에서 `.vibelign/db_maintenance_backups/<timestamp>/`에 `vibelign.db`, `vibelign.db-wal`, `vibelign.db-shm` 원본을 먼저 복사한다.
3. `PRAGMA wal_checkpoint(TRUNCATE)`로 WAL을 먼저 비운다.
4. 삭제된 row가 많고 freelist가 큰 경우에만 `VACUUM` 또는 안전한 compaction 전략을 수행한다.
5. compaction 전후의 DB/WAL/SHM 크기와 reclaim 추정치를 보고한다.
6. 실패 시 원본 DB를 손상시키지 않고 명확한 복구 안내를 반환한다.

## 데이터 모델

첫 구현은 신규 테이블을 만들지 않는다. DB viewer는 기존 Rust/SQLite schema를 읽기만 한다.

읽는 테이블:

- `db_meta`
- `checkpoints`
- `checkpoint_files` 요약
- `retention_policy`
- `cas_objects` 요약

DB Viewer는 새 schema를 만들거나 migration을 수행하지 않는다.

## Backend API 설계

React는 DB를 직접 열지 않는다. 다음 중 하나로 backend API를 제공한다.

1. Rust 엔진 IPC command 추가
2. Python CLI command 추가
3. Tauri native command 추가

추천은 **Rust 엔진 IPC command 추가 + Python wrapper + GUI wrapper**다. 백업 DB schema와 restore invariants가 Rust 엔진에 있으므로, DB viewer도 같은 경계에서 읽는 편이 안전하다.

### Engine requests

```rust
BackupDbViewerInspect { root: PathBuf }
```

첫 구현에는 update request를 추가하지 않는다.

### Inspect response

```json
{
  "db_exists": true,
  "db_file": {
    "database_bytes": 40960,
    "wal_bytes": 0,
    "shm_bytes": 32768,
    "total_bytes": 73728
  },
  "schema_version": "3",
  "checkpoint_count": 2,
  "rust_v2_count": 2,
  "legacy_count": 0,
  "cas_object_count": 861,
  "cas_ref_count": 2144,
  "total_original_size_bytes": 281637991,
  "total_stored_size_bytes": 134709997,
  "auto_backup_on_commit": true,
  "retention_policy": {
    "keep_latest": 30,
    "keep_daily_days": 14,
    "keep_weekly_weeks": 8,
    "max_total_size_bytes": 1073741824,
    "max_age_days": 180,
    "min_keep": 20
  },
  "checkpoints": []
}
```

`checkpoints[]`에는 BACKUPS 화면보다 더 많은 읽기 전용 필드를 포함한다. 단, `checkpoint_files` 전체 목록은 기본 응답에 넣지 않는다. 대형 프로젝트에서 응답이 과도하게 커질 수 있기 때문이다. 파일 목록은 선택한 백업 상세에서 lazy load하는 후속 API로 확장한다.

## Validation 규칙

첫 구현은 읽기 전용이므로 write validation은 없다. Inspect request는 다음만 검증한다.

- `root`는 프로젝트 루트로 resolve되어야 한다.
- DB path는 반드시 `root/.vibelign/vibelign.db`여야 한다.
- schema version이 현재 엔진보다 높으면 writable state를 가정하지 않고 읽기 전용 경고만 표시한다.

## Transaction / Audit 규칙

첫 구현은 write transaction과 audit row를 만들지 않는다. Inspect는 read-only connection으로 열고 가능한 경우 `PRAGMA query_only=ON`을 적용한다.

## GUI 설계

### 진입점

초기 구현은 BACKUPS 화면 안에 자식 메뉴를 추가한다.

```text
BACKUPS
  ├─ 백업 목록
  └─ Backup DB Viewer
```

이유:

- 기능이 백업 DB에 직접 연결된다.
- Settings는 API 키와 전역 설정이 중심이라 백업 상세 관리와 거리가 있다.
- 사용자는 백업 목록을 보다가 바로 DB 상세로 들어가는 흐름이 자연스럽다.

### 화면 구조

Backup DB Viewer는 BACKUPS 페이지 안의 별도 child view로 연다. 상단에는 `백업 목록` / `DB Viewer` 전환 탭을 둔다.

기존 BACKUPS UI는 `BackupCard`, `SafetySummary`, `StorageSavings`, `FileHistoryTable`, `RestorePreviewPanel`처럼 요약 카드, 검색 가능한 목록, 선택 항목 상세 패널을 조합한다. DB Viewer도 이 패턴을 따른다. SQLite table을 그대로 펼치는 화면이 아니라, DB row를 사람이 읽기 쉬운 백업 상태 정보로 번역해 보여준다.

섹션:

1. **DB 상태**
   - DB 경로
   - DB 파일/WAL/SHM 크기
   - schema version
   - Rust v2 백업 수
   - object 수
   - 저장공간 재사용 요약
   - 자동 백업 상태

2. **백업 DB rows**
   - 백업 ID
   - 표시 이름
   - 생성 시간
   - 보호 여부
   - 만들어진 이유
   - 파일 수
   - 원본 크기 / 실제 저장 크기
   - 재사용 파일 수 / 변경 파일 수
   - GUI 표시 이름과 DB message 매칭

3. **정리 정책**
   - 보존 개수
   - 일/주 대표 백업 보존 기간
   - 최대 저장 크기
   - 최대 보존 기간

4. **Object store**
   - object 수
   - ref count 합계
   - 압축/저장 크기 요약
   - `.vibelign/rust_objects/blake3` 존재 여부

### 가독성 요구사항

- 화면 첫 영역은 숫자 카드로 구성한다: 전체 백업 수, Rust v2 백업 수, object 수, 원본 대비 저장 크기, 자동 백업 상태.
- 백업 목록은 raw DB table이 아니라 검색 가능한 row list로 표시한다. 각 row는 백업 이름/생성 시간/만들어진 이유/파일 수/저장 효율을 우선 보여준다.
- 내부 column 이름은 기본 화면에 그대로 노출하지 않는다. 예: `checkpoint_id`는 “저장본 ID”, `trigger`는 “만들어진 이유”, `stored_size_bytes`는 “실제 저장 크기”로 표시한다.
- `checkpoint_id`, `object_hash`, `ref_count`처럼 복원 무결성과 관련된 값은 상세 패널의 “고급 정보” 또는 “복원 내부값” 영역으로 접는다.
- selected row 상세 패널에는 사람이 먼저 확인할 정보와 내부값을 분리한다.
  - 먼저 표시: 표시 이름, 생성 시간, 만들어진 이유, git commit, 파일 수, 변경/재사용 파일 수, 원본 크기, 실제 저장 크기.
  - 접어서 표시: 저장본 ID, parent ID, engine version, object hash 관련 요약, schema/debug 정보.
- 긴 git commit message와 긴 path/hash 값은 한 줄 요약 + 복사 버튼 또는 펼치기 UI로 처리한다.
- 경고/상태는 badge로 표시한다: `Rust v2`, `자동 백업`, `수동 백업`, `읽기 전용`, `schema 경고`, `DB 없음`.
- Object store는 파일 해시 목록부터 보여주지 않는다. 먼저 “얼마나 중복 제거됐는지”, “object store가 존재하는지”, “참조 수가 정상 범위인지”를 요약한다.
- 빈 상태와 오류 상태도 초보자가 이해할 문장으로 보여준다. 예: “아직 Rust 백업 DB가 없어요. 백업을 먼저 만들어 주세요.”
- 첫 구현에서 dense grid/table은 보조적인 고급 보기로도 넣지 않는다. 필요한 경우 후속 phase에서 export/read-only advanced view로 분리한다.

### UX

- 기본은 읽기 전용이다.
- DB row를 선택하면 오른쪽 또는 하단에 상세 정보를 보여준다.
- 위험한 내부 필드는 “복원에 쓰이는 값” 배지를 붙여 편집할 수 없음을 분명히 한다.
- 새로고침 버튼은 inspect API를 다시 호출한다.
- 편집 버튼은 첫 구현에 넣지 않는다.

파괴적 표현을 피한다. 예를 들어 “DB 수정” 대신 “DB 상태 보기”, “백업 DB rows”, “저장소 요약”처럼 읽기 전용 표현을 사용한다.

## Error handling

- DB 파일이 없으면 “아직 Rust 백업 DB가 없어요. 백업을 먼저 만들어 주세요.”를 표시한다.
- Rust 엔진을 찾지 못하면 “백업 관리 DB를 읽을 수 없어요. 설치된 앱/CLI의 백업 엔진을 확인해 주세요.”를 표시한다.
- schema version이 예상보다 높으면 읽기 전용 모드로만 연다.
- DB lock 때문에 read가 실패하면 “다른 백업 작업이 끝난 뒤 다시 새로고침해 주세요.”를 표시한다.

## Security / Safety

- React webview에는 SQL 실행 권한을 주지 않는다.
- `run_vib`로 raw SQL을 실행하는 명령은 만들지 않는다.
- Tauri command를 만들 경우에도 command 이름은 `backup_db_viewer_*`처럼 목적을 좁힌다.
- 모든 path는 project root 아래 `.vibelign/vibelign.db`로만 resolve한다.
- `.vibelign` 전체 파일 브라우저를 열지 않는다.
- DB Viewer 진입 시 “읽기 전용입니다. 복원에 쓰이는 값은 수정하지 않습니다.” 안내를 보여준다.

## Testing

### Rust engine tests

- DB viewer inspect returns DB summary
- missing DB returns `db_exists=false`
- inspect includes checkpoint row summaries
- inspect includes CAS/object-store summaries
- inspect does not mutate DB file

### Python wrapper tests

- request builder emits expected `backup_db_viewer_*` or inspect command
- response parser handles inspect success
- Rust unavailable warning maps to user-readable error

### GUI tests

- DB Viewer opens as BACKUPS child menu
- inspect data renders DB status and rows
- row selection renders checkpoint details
- no editable form controls are present in first implementation
- failed refresh displays error without clearing the last successful data

## Rollout plan

1. Add Rust read-only DB viewer module under `vibelign-core/src/backup/db_viewer.rs`.
2. Add IPC inspect request/response variant.
3. Add Python request/response wrapper.
4. Add GUI lib wrapper in `vibelign-gui/src/lib/vib.ts`.
5. Add BACKUPS child menu and DB Viewer panel component.
6. Add targeted tests.

## 첫 구현에서 고정한 결정

The following decisions are intentionally fixed for the first implementation:

- No raw SQL mode.
- No password prompt.
- No DB editing in the first implementation.
- No editing `trigger` or git metadata.
- No editing `checkpoint_files` or `cas_objects`.
- Notes/tags/archived are out of scope for this DB viewer spec.

If future users need lower-level DB repair, it should be a separate “repair tool” spec with export/import, checksum validation, dry-run, and explicit recovery workflow.
