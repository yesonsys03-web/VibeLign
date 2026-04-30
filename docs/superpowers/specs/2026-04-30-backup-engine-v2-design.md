# Backup Engine v2 설계

> **Status:** design approved. Implementation plan exists at `docs/superpowers/plans/2026-04-30-backup-engine-v2-implementation-plan.md`.

## 문제

Rust/SQLite 체크포인트 엔진은 이미 `vibelign-core/src/backup/`에 들어왔지만, 현재 저장 방식은 아직 Rust 전환의 장점을 충분히 보여주지 못한다.

- `snapshot.rs`는 `WalkDir`로 파일을 순회하고 파일 전체를 메모리로 읽어 `blake3` 해시를 계산한다.
- `checkpoint.rs`는 체크포인트마다 파일을 `.vibelign/rust_checkpoints/<checkpoint_id>/files`에 다시 복사한다.
- `cas.rs`는 존재하지만 `cas_enabled() == false`인 stub 상태다.
- SQLite schema에는 `cas_objects`, `retention_policy`가 이미 있지만 실제 엔진 기능으로 충분히 연결되어 있지 않다.
- 복원은 동작하지만, 사용자가 복원 전에 무엇이 바뀌는지 확인하거나 안전 복원용 checkpoint를 자동으로 남기는 UX는 부족하다.

사용자가 Rust 엔진으로 교체한 효과를 체감하려면 백업이 **빠르고, 저장공간을 적게 쓰고, 복원 전에 예측 가능하고, 자동으로 정리되는** 방향으로 발전해야 한다.

## 목표

Backup Engine v2의 목표는 VibeLign의 체크포인트 기능을 “AI가 망친 코드를 안전하게 되돌리는 고속 타임머신”으로 만드는 것이다.

핵심 원칙:

- Rust 전환의 장점은 CLI 출력과 GUI에서 체감 가능해야 한다.
- 기존 `vib checkpoint`, `vib history`, `vib undo` 사용자 경험은 깨지지 않아야 한다.
- 새 기능은 SQLite schema와 IPC contract를 통해 CLI/GUI가 모두 재사용할 수 있어야 한다.
- 저장소 최적화(CAS/증분)와 복원 안전성(dry-run/safety checkpoint)은 같은 데이터 모델 위에서 동작해야 한다.
- 사용자가 백업 버튼을 누르지 않아도, commit처럼 명확한 저장 시점에서는 자동 백업이 만들어져야 한다.
- 과도한 비동기 런타임 도입보다 현재 동기식 IPC 구조에 맞는 작은 병렬화부터 시작한다.
- 사용자에게 보이는 모든 말은 중학생도 이해할 수 있는 수준으로 쓴다. 어려운 내부 용어는 화면에 직접 노출하지 않는다.
- 구현은 파일 하나에 몰아넣지 않는다. 백업 기능은 역할별 폴더와 작은 모듈로 나눠서 만든다.
- v2 MVP는 local CAS만 구현하지만, 나중에 cloud sync, encryption, remote storage, policy plugin을 붙일 수 있게 contract와 module boundary를 열어 둔다.

사용자에게 보이는 말 규칙:

| 내부 용어 | 사용자에게 보이는 말 |
|---|---|
| checkpoint | 백업 / 저장점 |
| commit | 저장한 코드 기록 / 코드 저장 기록 |
| commit SHA / hash | 저장 기록 번호 |
| trigger | 만들어진 이유 |
| post_commit | 코드 저장 후 자동 백업 |
| commit-backed | 코드 저장과 연결된 백업 |
| snapshot | 그때의 파일 모습 |
| CAS object | 중복 없이 보관한 파일 |
| diff | 바뀐 내용 |
| restore preview | 되돌리기 전에 미리보기 |
| full restore | 전체 되돌리기 |
| file restore | 선택한 파일만 되돌리기 |
| File Audit Ledger | 파일별 백업 기록 |
| raw JSON / DB / IPC | 화면에 표시하지 않음 |

주의:

- 위 왼쪽 칸의 내부 용어는 개발 문서와 코드에서만 사용한다.
- GUI, 도움말, 알림, 버튼, 카드 제목에는 오른쪽 칸의 쉬운 말을 사용한다.
- “커밋”, “SHA”, “해시”, “트리거”, “체크포인트”, “디프”, “프리뷰”, “레저” 같은 말을 사용자에게 그대로 보여주지 않는다.
- 기술적으로 정확한 말보다 사용자가 바로 이해하는 말이 우선이다.

## 핵심 변경

### 1. CAS 저장소를 실제 기능으로 승격

현재 `vibelign-core/src/backup/cas.rs`는 stub이다. 이 모듈을 백업 object 저장소로 확장한다.

초기 API:

```rust
pub struct CasObject {
    pub hash: String,
    pub storage_path: String,
    pub size: u64,
    pub ref_count: u32,
}

pub fn store_object(root: &Path, conn: &Connection, source: &Path, hash: &str) -> Result<CasObject, BackupError>;
pub fn resolve_object(root: &Path, conn: &Connection, hash: &str) -> Result<PathBuf, BackupError>;
pub fn increment_ref(conn: &Connection, hash: &str) -> Result<(), BackupError>;
pub fn decrement_ref(conn: &Connection, hash: &str) -> Result<(), BackupError>;
pub fn prune_unreferenced(root: &Path, conn: &Connection) -> Result<PruneResult, BackupError>;
```

저장 위치:

```text
.vibelign/rust_objects/blake3/ab/cd/<full_hash>
```

해시 앞 2~4글자를 shard directory로 사용해 단일 디렉터리 파일 수 폭증을 방지한다.

0 byte 파일 규칙:

- Rust는 0 byte 파일을 문제없이 읽고 쓸 수 있다. 위험은 Rust가 아니라 백업 로직이 `size == 0`을 “없는 파일”처럼 잘못 처리하는 데 있다.
- 빈 파일도 정상 파일이다. snapshot, CAS 저장, diff, restore, Dashboard 기록에 모두 포함한다.
- 빈 파일의 hash는 BLAKE3 empty input hash로 계산하고, `size = 0`인 CAS object row를 만든다.
- `size == 0`, 빈 content, 빈 `storage_path`, missing file을 서로 다른 상태로 취급한다.
- restore는 0 byte 파일을 실제 빈 파일로 다시 생성해야 하며, 삭제된 파일로 오해하면 안 된다.

동시성 규칙:

- 두 프로세스가 같은 hash를 동시에 `store_object`하는 경우는 정상 시나리오다 (체크포인트 두 개가 같은 unchanged 파일을 가리킬 때). 후착 프로세스는 기존 row의 `ref_count`만 +1 하고 fs write는 건너뛴다.
- `INSERT INTO cas_objects ... ON CONFLICT(hash) DO UPDATE SET ref_count = ref_count + 1` 형태의 SQL을 사용한다.
- fs write는 `tempfile + atomic rename` 패턴으로, rename 실패(이미 존재) 시 무시하고 계속 진행한다.
- ref_count는 항상 SQL 트랜잭션 안에서만 갱신한다. 음수가 되는 경로는 만들지 않는다 (안전장치로 `CHECK(ref_count >= 0)` 도 둘 수 있음).

잠긴 파일 / 읽기 실패 처리:

- snapshot 수집 중 다른 프로세스가 파일을 잠갔거나 권한 문제로 read 실패하면 해당 파일은 backup row에서 빠진다.
- 단순 skip 하지 않고 결과 타입에 `skipped: Vec<{relative_path, reason}>` 필드를 둔다. CLI/GUI는 "이번 백업에서 1개 파일을 읽지 못했어요" 같이 사용자에게 표시한다.
- 자동 백업(post_commit)은 skip된 파일이 있어도 backup 자체는 성공으로 처리하지만, 마지막 1회의 skip 목록은 db_meta에 캐시해 다음 회차 dashboard에서 안내할 수 있게 한다.
- restore 시 잠긴 파일 write 실패는 명확한 `partial_failure` 로 분류한다. backup 시 skip과 restore 시 fail은 다른 카테고리로 다룬다.

### 2. 체크포인트 파일은 object를 참조

현재 `checkpoint_files.storage_path`는 checkpoint별 복사본 경로를 저장한다. v2에서는 각 checkpoint file row가 CAS object를 참조한다.

권장 schema 확장:

```sql
ALTER TABLE checkpoint_files ADD COLUMN object_hash TEXT;
ALTER TABLE checkpoints ADD COLUMN engine_version TEXT DEFAULT 'rust-v2';
ALTER TABLE checkpoints ADD COLUMN parent_checkpoint_id TEXT;
ALTER TABLE checkpoints ADD COLUMN original_size_bytes INTEGER DEFAULT 0;
ALTER TABLE checkpoints ADD COLUMN stored_size_bytes INTEGER DEFAULT 0;
ALTER TABLE checkpoints ADD COLUMN reused_file_count INTEGER DEFAULT 0;
ALTER TABLE checkpoints ADD COLUMN changed_file_count INTEGER DEFAULT 0;
ALTER TABLE checkpoints ADD COLUMN trigger TEXT DEFAULT 'manual';
ALTER TABLE checkpoints ADD COLUMN git_commit_sha TEXT;
ALTER TABLE checkpoints ADD COLUMN git_commit_message TEXT;
```

스키마 마이그레이션 규칙:

- `db_meta.schema_version`을 단일 게이트로 사용한다.
- 마이그레이션은 idempotent runner로 적용한다. 예: `apply_migrations(conn, target=2)`가 현재 버전을 읽고 부족한 ALTER만 실행한 뒤 `schema_version`을 갱신.
- 같은 DB가 두 번 열리거나 ALTER가 두 번 호출돼도 SQLite `duplicate column` 에러로 죽지 않아야 한다.
- `schema.rs`의 `INSERT OR IGNORE INTO db_meta ('schema_version', '1')` 라인은 그대로 두되, 신규 ALTER는 마이그레이션 러너로만 적용한다.
- 미래 v3 추가도 같은 러너로 진행한다.

호환성 규칙 (단일 source of truth):

- 엔진 버전 식별자는 `checkpoints.engine_version` **하나만** 사용한다. `'rust-v2'`이면 CAS 경로, 그 외(`NULL` 포함)는 legacy v1 경로.
- `checkpoint_files.object_hash`는 "어디에 저장됐는지"만 알려주고, restore 경로 선택에는 사용하지 않는다.
- v2 row의 `checkpoint_files.storage_path`는 빈 값을 두지 않는다. 대신 `cas:<full_hash>` 형태의 sentinel 문자열을 박아 둔다. legacy `''`(NULL/빈값/실제 경로)와 명확히 구분된다.
- legacy v1 row(`engine_version IS NULL`, `object_hash IS NULL`, `storage_path` 가 실제 디스크 경로)는 그대로 둔다. v2 코드는 절대 v1 row를 in-place 변환하지 않는다.
- `trigger`는 `manual | post_commit | safe_restore | system` 중 하나를 사용한다.
- `git_commit_sha`와 `git_commit_message`는 `trigger='post_commit'` checkpoint에서만 채운다.

### 3. 증분 체크포인트

증분성의 기준은 `relative_path + hash + size`이다.

생성 흐름:

```text
collect snapshot
  -> latest checkpoint file index 조회
  -> unchanged: 기존 object_hash 재사용 + ref_count 증가
  -> changed/new: CAS object 저장 + checkpoint_files row 생성
  -> deleted: 새 checkpoint에는 row를 만들지 않음
```

`matches_latest_snapshot()`는 유지하되, v2에서는 단순히 “생성 생략” 판단만 담당한다. 저장 재사용은 별도 incremental planner가 담당한다.

새 내부 타입:

```rust
pub enum FileChangeKind {
    Added,
    Modified,
    Unchanged,
    Deleted,
}

pub struct PlannedCheckpointFile {
    pub relative_path: String,
    pub hash: String,
    pub size: u64,
    pub object_hash: String,
    pub change_kind: FileChangeKind,
}
```

생성 중인 checkpoint snapshot에서는 삭제 파일 row를 만들지 않는다. 다만 diff/history/dashboard에서는 이전 checkpoint에는 있었지만 현재 snapshot에는 없는 파일을 `Deleted`로 계산한다. UI에서는 `Unchanged`를 “재사용됨”으로 표시한다.

### 4. 병렬 스냅샷과 스트리밍 해시

초기 v2는 Tokio 기반 전체 async rewrite를 하지 않는다. 현재 엔진은 stdin/stdout JSON IPC로 동작하므로, 작은 의존성 추가와 제한된 병렬화가 더 안전하다.

권장 방향:

- `rayon` 또는 표준 thread pool로 파일 해싱 병렬화
- 큰 파일은 `fs::read` 대신 `blake3::Hasher` + buffered streaming으로 처리
- 결과는 `relative_path` 기준 정렬해 deterministic output 유지
- 읽기 실패 파일은 기존처럼 건너뛰되, 향후 warning 수집 가능하도록 내부 결과 타입을 분리

초기 성능 목표:

- 작은 프로젝트에서는 기존 대비 동작 차이가 없어야 한다.
- 큰 프로젝트에서는 체크포인트 생성 시간이 눈에 띄게 줄어야 한다.
- 병렬화 때문에 checkpoint row 순서나 출력 순서가 흔들리면 안 된다.

### 5. Checkpoint Diff API

복원 UX와 GUI 타임라인을 위해 checkpoint 간 차이를 엔진 API로 제공한다.

IPC 확장:

```rust
CheckpointDiff {
    root: PathBuf,
    from_checkpoint_id: String,
    to_checkpoint_id: String,
}

CheckpointRestorePreview {
    root: PathBuf,
    checkpoint_id: String,
}

CheckpointRestoreFilesPreview {
    root: PathBuf,
    checkpoint_id: String,
    relative_paths: Vec<String>,
}

CheckpointRestoreFilesSafe {
    root: PathBuf,
    checkpoint_id: String,
    relative_paths: Vec<String>,
}

CheckpointRestoreSuggestions {
    root: PathBuf,
    checkpoint_id: String,
}

CheckpointStats {
    root: PathBuf,
}

CheckpointFiles {
    root: PathBuf,
    checkpoint_id: String,
}

CheckpointFileHistory {
    root: PathBuf,
    relative_path: String,
}
```

`CheckpointStats`는 Dashboard가 별도 DB query를 직접 만들지 않도록 날짜별 집계까지 포함한다.

```json
{
  "last_checkpoint_at": "2026-04-30T12:01:02Z",
  "checkpoint_count": 12,
  "original_size_bytes": 195140608,
  "stored_size_bytes": 2516582,
  "saved_size_bytes": 192624026,
  "daily": [
    {
      "date": "2026-04-30",
      "checkpoint_count": 3,
      "changed_file_count": 42,
      "new_storage_bytes": 2516582,
      "saved_size_bytes": 192624026
    }
  ]
}
```

날짜는 local UI에서 보기 좋게 렌더링하되, 엔진 응답은 ISO date string(`YYYY-MM-DD`)로 고정한다.

Diff 응답 필드:

```json
{
  "added": [{"relative_path": "...", "size": 123}],
  "modified": [{"relative_path": "...", "before_size": 10, "after_size": 20}],
  "deleted": [{"relative_path": "...", "size": 99}],
  "summary": {
    "added_count": 1,
    "modified_count": 1,
    "deleted_count": 1,
    "net_size_bytes": 34
  }
}
```

Restore preview는 “현재 작업공간”과 “대상 checkpoint”를 비교한다. 이 API는 실제 파일을 변경하지 않는다.

선택 파일 복원 preview는 선택한 파일만 비교한다.

```json
{
  "checkpoint_id": "20260430T120102Z",
  "selected_files": [
    {
      "relative_path": "src/app.py",
      "status": "will_replace",
      "current_size": 1500,
      "backup_size": 1234
    }
  ],
  "summary": {
    "replace_count": 1,
    "restore_missing_count": 0,
    "delete_count": 0
  }
}
```

되돌릴 파일 추천 API는 사용자가 파일명을 몰라도 후보를 고를 수 있도록 만든다.

```json
{
  "checkpoint_id": "20260430T120102Z",
  "suggestions": [
    {
      "relative_path": "src/app.py",
      "reason_code": "recently_changed",
      "plain_reason": "방금 가장 많이 바뀐 파일이에요.",
      "risk_level": "medium",
      "changed_at": "2026-04-30T12:01:02Z"
    }
  ]
}
```

추천 기준:

- 최근 백업에서 새로 바뀐 파일
- 삭제된 파일 또는 현재는 없지만 예전 백업에는 있는 파일
- 변경량이 큰 파일
- 사용자가 선택한 날짜/저장점에서 바뀐 파일
- 되돌리기 전 미리보기에서 삭제/교체 영향이 큰 파일
- 향후 guard/doctor 결과와 연결되면 “문제와 관련 있어 보이는 파일”도 후보로 올린다.

추천 알고리즘 명세:

- 후보 상한: 기본 5개 (사용자 설정으로 3~10 범위 조정 가능).
- 정렬 우선순위 (점수 높은 순):
  1. 현재 작업공간엔 없지만 대상 checkpoint에는 있는 파일 — `reason_code = "missing_now"`, `risk_level = "high"`
  2. 직전 30분 이내에 변경된 파일 — `reason_code = "recently_changed"`, `risk_level = "medium"`
  3. 변경량(`abs(after_size - before_size)`) 상위 — `reason_code = "high_change"`, `risk_level = "medium"`
  4. 사용자가 선택한 날짜에 변경된 파일 — `reason_code = "changed_on_date"`, `risk_level = "low"`
  5. 동일 점수일 때는 `relative_path` 사전식으로 안정 정렬.
- legacy v1 checkpoint(parent 정보 없음, diff 계산 불가): 추천을 비활성화하고 `suggestions = []`, `legacy_notice = "이 시점 백업은 추천을 제공할 수 없어요. 전체 파일 목록에서 직접 골라 주세요."` 한 줄을 함께 반환한다.

파일 단위 기록 API:

```json
{
  "checkpoint_id": "20260430T120102Z",
  "files": [
    {
      "relative_path": "src/app.py",
      "change_kind": "modified",
      "size": 1234,
      "hash": "blake3:...",
      "backed_up_at": "2026-04-30T12:01:02Z"
    }
  ]
}
```

`CheckpointFileHistory`는 특정 파일이 어떤 checkpoint에서 추가/수정/삭제/재사용되었는지 시간순으로 보여준다.

```json
{
  "relative_path": "src/app.py",
  "history": [
    {
      "checkpoint_id": "20260430T120102Z",
      "created_at": "2026-04-30T12:01:02Z",
      "change_kind": "modified",
      "size": 1234
    }
  ]
}
```

### 6. 안전 복원

`CheckpointRestore`는 기본 동작을 갑자기 바꾸지 않는다. 대신 새 안전 경로를 추가한다.

복원 방식은 두 가지를 모두 지원한다.

1. 전체 되돌리기
   - 선택한 저장점의 전체 파일 모습으로 프로젝트를 되돌린다.
   - AI가 여러 파일을 크게 망쳤을 때 쓰는 강한 복구 기능이다.
2. 선택한 파일만 되돌리기
   - 파일별 백업 기록에서 고른 파일만 되돌린다.
   - 나머지 파일은 그대로 둔다.
   - 코드를 모르는 사용자가 “이 파일 하나만 예전으로 돌리고 싶다”를 할 수 있게 한다.
3. 추천받아서 되돌리기
   - VibeLign이 먼저 되돌릴 만한 파일을 3~5개 추천한다.
   - 사용자는 파일명을 몰라도 추천 이유를 보고 고를 수 있다.
   - 추천은 “최근에 바뀜”, “없어진 파일”, “많이 바뀐 파일”처럼 쉬운 이유로 설명한다.

새 동작:

- `CheckpointRestorePreview`: 복원 전 변경 예정 파일을 보여준다.
- `CheckpointRestoreSafe`: 복원 전 safety checkpoint를 자동 생성한 뒤 restore한다.
- `CheckpointRestoreFilesPreview`: 선택한 파일만 되돌리면 무엇이 바뀌는지 보여준다.
- `CheckpointRestoreFilesSafe`: 복원 전 안전 백업을 만든 뒤 선택한 파일만 되돌린다.
- `CheckpointRestoreSuggestions`: 되돌릴 만한 파일 후보와 쉬운 이유를 보여준다.
- 기존 `CheckpointRestore`: 하위 호환을 위해 현재 동작 유지.

안전 복원 메시지:

```text
pre-restore safety checkpoint before restoring <checkpoint_id>
```

주의:

- safety checkpoint 생성이 실패하면 safe restore는 중단한다.
- legacy restore는 기존처럼 동작한다.
- 보호 파일 정책과 연결하는 것은 후속 단계로 둔다. v2 MVP에서는 checkpoint snapshot 기준 복원 안정성에 집중한다.
- 선택한 파일만 되돌릴 때도 먼저 안전 백업을 만든다.
- 선택한 파일이 현재 없으면 “없어진 파일을 다시 가져오기”로 표시한다.
- 선택한 파일을 되돌리면 현재 내용이 바뀌는 경우, 되돌리기 전에 미리보기에서 분명히 알려준다.
- 폴더 단위 복원은 v2 첫 구현에서는 선택 사항이다. MVP는 파일 단위 복원부터 시작한다.
- 추천은 자동 선택이 아니다. 사용자가 직접 확인하고 고르게 한다.
- 추천 이유는 개발자 용어가 아니라 “방금 많이 바뀜”, “지금은 없지만 예전에는 있었음”, “이 날짜에 바뀜”처럼 쉬운 말로 표시한다.
- 선택한 파일만 되돌릴 때의 안전 백업 범위는 **선택 파일이 아니라 항상 전체 프로젝트 snapshot**이다. CAS 덕분에 추가 비용은 사실상 없으며, undo 의미(이 시점 직전의 전체 상태로 복귀)가 보존된다.
- 기존 `vib undo`는 v2에서도 동일한 사용자 명령 표면을 유지한다. 내부적으로는 가장 최근 v2 checkpoint 기준 safe full restore와 동일한 경로를 사용한다 (legacy DB만 있는 프로젝트에서는 v1 restore로 fallback).
- safe restore가 사전에 만든 안전 백업(`trigger='safe_restore'`)은 `vib history` / `vib undo` 목록에서는 **숨긴다**. 사용자가 "되돌렸더니 체크포인트가 갑자기 하나 더 생겼다"고 혼란스러워하지 않도록, retention 보호 윈도 안에서만 내부적으로 보존되고 GUI Backup Dashboard 의 "되돌리기 전 자동 백업" 영역에서만 노출한다. CLI 첫 사용 시 `vib undo` 종료 메시지에 한 줄로 "혹시 잘못 되돌리면 `vib undo --pre-restore`로 되살릴 수 있어요" 안내를 추가한다.

### 7. Commit-triggered Auto Backup

사용자는 백업 버튼을 일일이 누르지 않는다. 대신 Git commit은 “이 시점은 보존할 가치가 있다”는 강한 신호이므로, commit 직후 자동 백업을 만든다.

기존 코드에는 이미 `vibelign/core/git_hooks.py`의 `install_post_commit_record_hook()`가 있고, `vib start`가 Git 저장소에서 post-commit 훅을 설치한다. v2에서는 이 훅을 확장해 commit 메시지 기록뿐 아니라 자동 백업까지 수행한다.

동작 흐름:

```text
git commit 완료
  -> post-commit hook 실행
  -> commit sha / message 수집
  -> _internal_record_commit 으로 work_memory 기록
  -> _internal_post_commit_backup 으로 checkpoint 생성
  -> checkpoint trigger='post_commit', git_commit_sha/message 저장
```

내부 자동 백업 메시지:

```text
auto backup after commit abc1234 — feat: login flow
```

사용자에게 보이는 메시지는 위 내부 문구를 그대로 쓰지 않는다.

```text
코드를 저장한 뒤 자동으로 백업했어요.
저장 기록 번호: abc1234
메모: login flow
```

안전 규칙:

- post-commit backup은 절대 commit 성공을 실패로 바꾸지 않는다. 모든 오류는 non-fatal이어야 한다.
- Rust engine이 없거나 실패하면 조용히 Python fallback 또는 no-op로 끝난다.
- 현재 snapshot이 최신 checkpoint와 같으면 `no_changes`로 새 checkpoint를 만들지 않는다.
- `.git`, `.vibelign/vibelign.db`, `.vibelign/rust_checkpoints/`, `.vibelign/rust_objects/`는 snapshot 대상에서 제외한다.
- 사용자가 명시적으로 끌 수 있도록 `auto_backup_on_commit` 설정을 둔다. 기본값은 Git 저장소에서 `vib start` 시 enabled다.
- 설정은 `db_meta` 테이블의 `auto_backup_on_commit` row(값 `'1' | '0'`)로 통일한다. 새 config 파일을 만들지 않는다. CLI에서는 기존 `vib config` 트리에 `vib config auto-backup on|off` 명령을 추가해 토글한다.
- 외부 사용자의 기존 post-commit hook은 보존하고, VibeLign block은 기존 방식처럼 prepend/idempotent로 관리한다.
- 자동 백업 트리거 흐름은 Python 쪽이 모두 담당한다. Rust 엔진에는 별도 `commit_auto_backup.rs` 모듈을 두지 않는다. trigger / git metadata는 기존 `CheckpointCreate` request payload에 필드를 추가해 전달하고, Rust는 받은 메타를 row에 그대로 기록만 한다.

post-commit hook 구현 규칙:

- 한 번의 commit에 대해 stdin은 단일 명령에만 흘린다. 기존 `_internal_record_commit`이 commit 메시지를 stdin으로 받고 있으므로, **자동 백업은 별도 stdin 파이프를 만들지 않는다**. `_internal_record_commit` 안에서 record 처리가 끝난 뒤 같은 프로세스가 `_internal_post_commit_backup` 로직을 이어서 실행하거나, 단일 새 entrypoint(`_internal_post_commit`) 가 record + backup 을 차례로 수행한다.
- 두 작업이 모두 `work_memory.json` 의 `recent_events[]` 에 row를 추가하므로, 동일 hook turn 안에서는 단일 writer로 직렬 실행한다. 같은 파일을 두 프로세스가 동시 갱신해서 race가 나는 경로를 만들지 않는다.
- python 폴백은 `python` → `py -3` → `python3` 순서로 시도한다. Windows 기본 설치는 `python3` 이 PATH에 없는 경우가 많기 때문이다.
- Windows Git Bash 의 stdin pipe 는 LF/CRLF 변환이 끼어들 수 있다. `git_commit_message` 를 dedupe key로 쓰지 않는다 — dedupe 는 `matches_latest_snapshot()` 결과만 사용한다.
- `auto_backup_on_commit='1'` 토글을 위한 사용자 명령은 기존 `vib config` 트리에 `vib config auto-backup on|off` 형태로 추가한다 (새 `vib settings` 그룹을 만들지 않는다).
- Rust 엔진 호출의 default timeout(`rust_engine.py` 의 30s)은 자동 백업/복원 같은 backup 계열 명령에 한해 90s 로 상향한다. Windows realtime AV 가 `.vibelign/rust_objects/` 를 처음 scan할 때 30s 를 초과할 수 있기 때문이다.

사용자 화면 표시:

- 코드 저장 후 자동으로 만들어진 백업은 “코드 저장 후 자동 백업” 표시를 붙인다.
- 시간 흐름 영역에는 어려운 SHA 대신 “저장 기록 번호”와 사용자가 쓴 첫 줄을 “메모”로 표시한다.
- 날짜 그래프에는 “직접 만든 백업”과 “코드 저장 후 자동 백업”을 구분할 수 있는 색/패턴을 둔다.
- 파일별 백업 기록에서는 특정 파일 변경이 “코드 저장과 연결된 백업”인지 표시한다.

코알못용 문장 예시:

```text
코드를 저장할 때 자동으로 백업했어요.
저장 기록 번호 abc1234 시점으로 돌아갈 수 있어요.
이 자동 백업에는 12개 파일 변경이 기록되어 있어요.
```

### 8. Retention policy 자동 적용

`retention.rs`의 `RetentionPolicy`를 실제 pruning planner로 확장한다.

정책 우선순위:

1. 보호된 백업은 삭제하지 않는다.
2. `min_keep`보다 적게 남기지 않는다.
3. `keep_latest`를 우선 보존한다.
4. daily/weekly representative checkpoint를 보존한다.
5. `max_age_days`와 `max_total_size_bytes`를 적용한다.

초기 기본 정책:

- 사용자가 별표/보호 표시한 백업은 절대 자동 삭제하지 않는다.
- 최근 20개 백업은 항상 남긴다 (`min_keep` default = **20**, 기존 schema의 `10`은 v2 마이그레이션에서 갱신).
- 최근 7일 백업은 가능하면 모두 남긴다.
- 최근 30일은 하루에 대표 백업 1개 이상 남긴다.
- 최근 12주는 주마다 대표 백업 1개 이상 남긴다.
- 최근 12개월은 달마다 대표 백업 1개 이상 남긴다.
- 자동 백업이 너무 많이 쌓이면 직접 만든 백업보다 먼저 정리 후보가 된다.
- 기본 저장공간 한도는 프로젝트별 1GB soft cap으로 시작하되 설정에서 바꿀 수 있게 한다 (`max_total_size_bytes` default = **1 GiB**, 기존 schema의 `2 GiB`는 v2 마이그레이션에서 갱신).
- soft cap 초과 시 즉시 무조건 삭제하지 않고, planner가 “정리하면 얼마나 줄어드는지”를 계산한 뒤 안전한 후보만 정리한다.
- free disk가 1GB 미만이면 새 백업 생성 전에 경고를 남기고, 사전 백업이 필요한 복원 작업은 중단한다.

삭제 후보 우선순위:

1. 보호되지 않은 오래된 자동 백업
2. 같은 날에 여러 개 있는 자동 백업 중 대표가 아닌 것
3. 오래된 직접 백업 중 대표가 아닌 것
4. 큰 object를 유일하게 참조하지만 오래되고 보호되지 않은 백업

삭제하면 안 되는 것:

- 사용자가 보호한 백업
- 최근 `min_keep` 범위 안의 백업
- safe restore 직전에 만든 안전 백업
- 삭제 후 남은 백업이 복원 불가능해지는 CAS object
- 현재 복원/미리보기 작업이 참조 중인 백업

초기 API:

```rust
pub fn plan_retention(checkpoints: &[ListedCheckpoint], policy: RetentionPolicy) -> RetentionPlan;
pub fn apply_retention(root: &Path, conn: &Connection, policy: RetentionPolicy) -> Result<PruneResult, BackupError>;
```

CAS와 연결되는 규칙:

- checkpoint 삭제 시 관련 `checkpoint_files.object_hash`의 ref_count를 감소시킨다.
- ref_count가 0인 object만 실제 파일 삭제 대상이다.
- 삭제 결과는 checkpoint 삭제 bytes와 object 삭제 bytes를 구분해 기록한다.
- cleanup transaction 순서:
  1. **단일 SQL transaction** 안에서 `DELETE FROM checkpoint_files WHERE checkpoint_id IN (...)` → `UPDATE cas_objects SET ref_count = ref_count - n WHERE hash IN (...)` → `DELETE FROM checkpoints WHERE checkpoint_id IN (...)` 를 atomic 하게 실행한다. 트랜잭션 커밋 직전 크래시는 전부 롤백되므로 ref_count drift가 생기지 않는다.
  2. transaction commit 이후, 별도 단계에서 `ref_count = 0` row를 조회해 fs unlink → `DELETE FROM cas_objects`. 이 단계의 fs 실패는 `partial_failure`로 반환하되 DB는 이미 정합 상태다 (다음 cleanup이 같은 row를 다시 시도).
- object 파일 삭제가 실패하면 DB 삭제도 성공처럼 표시하지 않는다. 실패한 항목을 `partial_failure`로 반환한다.
- 정리 결과에는 “백업 몇 개 정리”, “실제로 줄어든 용량”, “보호돼서 남긴 백업 수”를 포함한다.

사용자 화면 표시:

- “오래된 백업을 자동으로 정리해요.”
- “최근 백업과 보호한 백업은 남겨둬요.”
- “정리하면 약 320 MB를 줄일 수 있어요.”
- “이 백업은 보호되어 자동 정리되지 않아요.”
- “공간이 부족해서 새 백업을 만들기 어려워요. 오래된 백업을 정리해보세요.”

### 9. 코알못용 Backup Dashboard

백업 데이터는 “저장되어 있다”만으로는 충분하지 않다. 코드를 잘 모르는 사용자는 백업 파일이나 DB row를 직접 확인할 수 없으므로, VibeLign은 백업 상태를 **눈으로 믿을 수 있게** 보여줘야 한다.

현재 GUI의 `Checkpoints.tsx`는 체크포인트 목록과 복원 버튼 중심이다. 이 화면은 작은 목록/작업 화면으로는 충분하지만, 백업 데이터를 자세히 이해하기 위한 대시보드로는 공간이 부족하다.

v2에서는 백업 데이터를 `DOCS VIEWER`처럼 독립 메뉴로 승격한다. 기존 상단 `Checkpoints` 메뉴는 `BACKUPS` 안으로 흡수하고, `App.tsx`의 상단 nav에서 `DOCS VIEWER` 오른쪽에 `BACKUPS` 메뉴를 추가한다. `BackupDashboard.tsx`는 전체 화면을 사용해 백업 상태, 기록, 생성, 복원을 모두 시각적으로 보여준다.

대시보드의 핵심 질문:

- 지금 내 프로젝트는 안전하게 백업되어 있나?
- 마지막 백업은 언제 만들어졌나?
- 마지막 코드 저장 기록이 자동 백업으로 연결됐나?
- 이번 백업에서 실제로 바뀐 파일은 무엇인가?
- 어떤 파일이 각 백업에 포함됐고, 언제 추가/수정/삭제됐나?
- 날짜별로 백업이 얼마나 꾸준히 쌓였나?
- 백업 데이터가 얼마나 쌓였고, Rust 엔진이 얼마나 절약했나?
- 복원하면 어떤 파일이 바뀌거나 사라지나?
- 전체를 되돌릴지, 선택한 파일만 되돌릴지 고를 수 있나?
- 어떤 파일을 되돌려야 할지 VibeLign이 쉽게 추천해주나?
- 오래된 백업은 자동으로 정리되고 있나?

권장 화면 구조:

```text
Backup Dashboard
├─ 안전 상태
│  ├─ 마지막 백업 시각
│  ├─ 현재 변경사항 보호 상태
│  ├─ 되돌릴 수 있는 저장점 수
│  └─ 백업 상태 표시
├─ 아낀 용량
│  ├─ 원본 누적 용량
│  ├─ 실제 저장 용량
│  ├─ 절약된 용량
│  └─ 다시 쓴 파일 수
├─ 날짜 그래프
│  ├─ 날짜별 백업 개수
│  ├─ 날짜별 변경 파일 수
│  ├─ 날짜별 새로 저장한 용량
│  └─ 선택 날짜의 백업 목록
├─ 백업 흐름
│  ├─ 백업 카드 목록
│  ├─ 변경 파일 수 / 메시지 / 생성 시각
│  └─ 보호됨 / 안전 복원 / 코드 저장과 연결됨 상태
├─ 파일별 백업 기록
│  ├─ 백업된 전체 파일 목록
│  ├─ 되돌릴 파일 추천
│  ├─ 파일별 추가/수정/삭제/재사용 기록
│  ├─ 백업별 파일 검색/필터
│  ├─ 파일 클릭 시 시간순 변경 이력
│  └─ 선택한 파일만 되돌리기
├─ 되돌리기 전 미리보기
│  ├─ 추가 파일
│  ├─ 수정 파일
│  ├─ 삭제 예정 파일
│  ├─ 선택한 파일만 되돌릴 때 바뀌는 내용
│  └─ 되돌리기 전 위험 알림
└─ 오래된 백업 정리 안내
   ├─ 자동 정리 규칙 요약
   ├─ 정리 가능 용량
   └─ 지우지 않도록 보호한 백업
```

대시보드는 개발자용 로그가 아니라 “백업 영수증”처럼 보여야 한다.

예시 문구:

```text
안전함 — 4분 전에 백업했어요.
마지막 코드 저장 기록도 자동으로 백업됐어요.
이번 백업은 17개 파일만 새로 저장했고, 1,267개 파일은 재사용했어요.
총 183.7 MB를 아꼈어요.
이 시점으로 복원하면 3개 파일이 바뀌고 1개 파일이 삭제돼요.
```

초기 구현은 기존 `Checkpoints.tsx`에 모든 것을 끼워 넣지 않는다. `Checkpoints.tsx`는 필요하면 `BackupDashboard.tsx` 내부의 timeline/list 컴포넌트로 분해해 재사용하되, 상단 메뉴의 사용자-facing 진입점은 `BACKUPS` 하나로 통합한다.

네비게이션 위치:

```text
홈 | Doctor | 메뉴얼 | 폴더열기 | DOCS VIEWER | BACKUPS
```

`BACKUPS`는 작은 Home 카드나 기존 `Checkpoints` 메뉴의 보조 화면이 아니라 백업 기능의 단일 전체 페이지다. 코드를 모르는 사용자가 저장된 데이터의 양, 변경 흐름, 복원 결과를 넓은 화면에서 읽어야 하기 때문이다.

날짜별 그래프는 대시보드의 핵심 시각화로 둔다. 목적은 “멋진 차트”가 아니라 사용자가 백업 습관과 복원 지점을 빠르게 이해하게 하는 것이다.

권장 그래프:

- 최근 30일 달력 그래프: 백업이 있는 날을 색 농도로 표시
- 날짜별 막대 그래프: 해당 날짜의 백업 수와 변경 파일 수 표시
- 아낀 용량 그래프: 시간이 지나며 절약된 용량이 얼마나 쌓였는지 표시
- 날짜 클릭 시 해당 날짜의 백업 목록만 보여주기

코알못용 문장 예시:

```text
이번 주에는 5번 백업했어요.
화요일에 변경이 가장 많았어요 — 42개 파일이 바뀌었습니다.
4월 30일 백업으로 돌아갈 수 있는 저장점이 3개 있어요.
```

파일별 백업 기록은 대시보드의 상세 탐색 영역이다. 사용자는 날짜 그래프나 백업 흐름에서 저장점을 선택한 뒤, 해당 시점에 백업된 파일과 변경된 파일을 모두 볼 수 있어야 한다.

파일이 많을 때는 목록을 먼저 보여주지 않는다. 먼저 “되돌릴 파일 추천”을 보여준다.

추천 카드 예시:

```text
되돌릴 만한 파일 3개를 찾았어요.

1. src/app.py
   방금 가장 많이 바뀐 파일이에요.

2. pages/login.py
   로그인 화면과 관련 있어 보여요.

3. config.py
   지금은 없지만 예전 백업에는 있어요.
```

추천 카드의 버튼:

- 이 파일만 되돌리기
- 이 파일이 뭔지 보기
- 추천에서 숨기기
- 전체 파일 목록 보기

필수 필터:

- 전체 파일
- 새로 추가된 파일
- 수정된 파일
- 삭제 예정/삭제된 파일
- 재사용된 파일
- 파일명 검색
- 확장자/폴더별 그룹

목록 UX 규칙:

- 기본은 추천 카드 3~5개만 보여준다.
- 전체 파일 목록은 접힌 상태로 둔다.
- 검색창 placeholder는 “파일 이름을 몰라도 괜찮아요. 아래 추천을 먼저 보세요.”로 둔다.
- 추천 이유는 한 줄로 끝낸다.
- 사용자가 파일을 선택하면 “이 파일만 되돌리면 다른 파일은 그대로 둡니다”를 항상 표시한다.

코알못용 문장 예시:

```text
이 백업에는 1,284개 파일이 들어 있어요.
그중 17개 파일이 새로 바뀌었고, 1,267개 파일은 이전 백업과 같아요.
`src/app.py`는 4월 28일, 4월 30일에 수정된 기록이 있어요.
이 파일만 4월 30일 모습으로 되돌릴 수 있어요.
```

복원 UX 권장안:

- 기본 큰 버튼은 “전체 되돌리기”로 둔다.
- 파일별 백업 기록에서는 각 파일 옆에 “이 파일만 되돌리기”를 둔다.
- 여러 파일을 체크하면 “선택한 파일 3개 되돌리기”를 보여준다.
- “전체 되돌리기”는 더 위험하므로 확인 화면을 한 번 더 보여준다.
- “선택한 파일만 되돌리기”도 현재 파일을 바꾸므로 항상 되돌리기 전 미리보기를 먼저 보여준다.
- 사용자가 이해할 수 있게 “다른 파일은 그대로 둬요” 문장을 함께 보여준다.

코알못용 문장 예시:

```text
전체를 되돌릴까요, 이 파일만 되돌릴까요?
어떤 파일인지 모르겠다면 추천 파일부터 볼 수 있어요.
이 파일만 되돌리면 다른 파일은 그대로 둡니다.
되돌리기 전에 지금 상태도 한 번 더 백업해둘게요.
```

## 사용자에게 보여줄 결과

내부 백업 생성 결과는 Rust 엔진의 효과를 숫자로 담아야 한다.

내부 출력 예시:

```text
Backup created: 20260430T120102Z
Files scanned: 1,284
Changed files: 17
Reused files: 1,267
Original size: 186.1 MB
New storage: 2.4 MB
Space saved: 183.7 MB
```

GUI에서는 같은 정보를 카드로 보여줄 수 있다.

- 변경 파일 수
- 재사용 파일 수
- 새로 저장한 용량
- 절약한 누적 용량
- 복원 전 변경 예정 파일

코알못용 Backup Dashboard에서는 위 숫자를 raw metric이 아니라 “안전 상태 설명”으로 번역한다.

- `last_checkpoint_age_minutes` → “4분 전에 백업했어요”
- `checkpoint_count` → “돌아갈 수 있는 저장점 12개”
- `trigger='post_commit'` + `git_commit_sha` → “코드를 저장할 때 자동으로 백업했어요”
- `daily_checkpoint_counts` → “이번 주에는 5번 백업했어요”
- `daily_changed_file_counts` → “화요일에 변경이 가장 많았어요”
- `checkpoint_files[]` → “이 백업에는 1,284개 파일이 들어 있어요”
- `file_history[]` → “이 파일은 4월 30일에 수정됐어요”
- `restore_files_preview.selected_files[]` → “이 파일만 되돌리면 다른 파일은 그대로 둡니다”
- `restore_suggestions[]` → “되돌릴 만한 파일 3개를 찾았어요”
- `stored_size_bytes / original_size_bytes` → “183.7 MB 절약”
- `changed_file_count` → “이번에 실제로 바뀐 파일 17개”
- `restore_preview.deleted_count` → “복원하면 사라질 파일 1개”

대시보드에서 숫자는 보조 정보이고, 1차 표현은 사용자가 바로 이해하는 문장이어야 한다.

## 수정 대상 파일

구현 시 가장 중요한 구조 원칙:

- `checkpoint.rs`, `protocol.rs`, `BackupDashboard.tsx`, `vib.ts` 같은 기존 큰 파일에 기능을 계속 몰아넣지 않는다.
- 새 기능은 “저장”, “복원”, “추천”, “통계”, “화면 표시”처럼 바뀌는 이유가 같은 단위로 나눈다.
- 기존 파일은 가능하면 얇은 연결부로 유지하고, 실제 로직은 새 하위 모듈에 둔다.
- 한 파일이 두 번째 책임을 갖기 시작하면 새 파일로 뺀다.
- 테스트도 기능별 파일로 나눈다.

권장 Rust 백업 모듈 구조:

```text
vibelign-core/src/backup/
├─ mod.rs
├─ cas.rs                  # 중복 없이 보관하는 파일 저장소
├─ snapshot.rs             # 그때의 파일 모습 수집
├─ checkpoint.rs           # 기존 공개 함수 연결부, 점점 얇게 유지
├─ create.rs               # 백업 만들기 (trigger / git metadata는 request payload로 받는다)
├─ restore/
│  ├─ mod.rs
│  ├─ full.rs              # 전체 되돌리기
│  ├─ files.rs             # 선택한 파일만 되돌리기
│  └─ preview.rs           # 되돌리기 전 미리보기
├─ diff.rs                 # 바뀐 내용 계산
├─ stats.rs                # 날짜별/용량/개수 통계
├─ suggestions.rs          # 되돌릴 파일 추천
└─ retention.rs            # 오래된 백업 정리
```

> `commit_auto_backup.rs`는 두지 않는다. post-commit 자동 백업의 트리거/dedupe 책임은 Python (`vibelign/core/checkpoint_engine/auto_backup.py`)이 담당하고, Rust는 `CheckpointCreate` request에 `trigger`, `git_commit_sha`, `git_commit_message` 필드가 추가된 형태만 받아 row에 기록한다.

확장성을 위한 boundary:

- `cas.rs`는 v2에서는 local file CAS만 구현한다. 하지만 외부에는 “hash로 object 저장/조회/refcount/prune” API만 노출해 future backend를 바꿔도 `create.rs`, `restore/*`, `retention.rs`가 직접 파일 경로 구조에 의존하지 않게 한다.
- `create.rs`는 백업 생성 orchestration만 담당한다. commit 자동 백업, 수동 백업, 향후 scheduled backup은 모두 같은 `CheckpointCreate` payload로 들어와야 한다.
- `restore/*`는 object가 local file인지 remote object인지 알지 않는다. 항상 CAS resolve API를 통해 읽는다.
- `retention.rs`는 “무엇을 지울지” plan만 만들고, storage backend별 실제 삭제는 CAS/object layer가 담당한다.
- `stats.rs`, `diff.rs`, `suggestions.rs`는 DB row와 normalized relative path만 사용한다. GUI 전용 표현이나 특정 화면 문장을 넣지 않는다.
- `ipc/protocol.rs`는 additive versioning만 허용한다. 기존 request/response field를 삭제하거나 의미를 바꾸지 않는다.
- 새 metadata는 먼저 `checkpoint_metadata` 또는 `db_meta` 확장 row로 들어가야 한다. 핵심 table column은 query 성능이나 정렬 기준이 명확할 때만 추가한다.
- 향후 encryption/cloud/remote sync는 `cas_objects`에 `backend`, `object_uri`, `encryption_key_id`, `sync_state` 같은 optional field를 추가하는 방식으로 확장한다. v2 MVP 구현은 이 값을 요구하지 않는다.

권장 Python bridge 구조:

```text
vibelign/core/checkpoint_engine/
├─ rust_engine.py          # 기존 호환 wrapper, 얇게 유지
├─ requests.py             # Rust engine 요청 payload 생성
├─ responses.py            # 응답 파싱/검증
└─ auto_backup.py          # 코드 저장 후 자동 백업 진입점
```

권장 GUI 구조:

```text
vibelign-gui/src/pages/
└─ BackupDashboard.tsx     # 페이지 조립만 담당

vibelign-gui/src/components/backup-dashboard/
├─ SafetySummary.tsx       # 안전 상태
├─ StorageSavings.tsx      # 아낀 용량
├─ DateGraph.tsx           # 날짜 그래프
├─ BackupFlow.tsx          # 백업 흐름
├─ RestoreSuggestions.tsx  # 되돌릴 파일 추천
├─ FileHistoryTable.tsx    # 파일별 백업 기록
├─ RestorePreviewPanel.tsx # 되돌리기 전 미리보기
└─ CleanupInsight.tsx      # 오래된 백업 정리 안내
```

GUI 확장 규칙:

- `BackupDashboard.tsx`는 data fetch + section composition만 담당한다.
- 새 카드나 그래프는 `components/backup-dashboard/` 아래 독립 컴포넌트로 추가한다.
- 화면 문장 변환은 컴포넌트 내부에 흩뿌리지 말고 작은 formatter/helper로 모은다.
- remote sync, encryption, cloud status 같은 후속 기능은 새 panel(`SyncStatusPanel.tsx`, `EncryptionStatusPanel.tsx` 등)로 붙인다. 기존 Safety/Storage/History 컴포넌트에 억지로 섞지 않는다.
- GUI는 Rust DB를 직접 읽지 않는다. 반드시 Python bridge/IPC JSON contract를 통해 데이터를 받는다.

금지:

- `checkpoint.rs`에 CAS/복원/추천/통계/정리 로직을 모두 넣기
- `BackupDashboard.tsx` 하나에 화면 전체 UI와 데이터 가공 로직을 모두 넣기
- `vib.ts`에 백업 응답 타입/파싱/화면용 문장 변환을 모두 넣기
- 테스트를 하나의 거대한 통합 테스트 파일에만 몰아넣기

| 파일 | 변경 내용 |
|---|---|
| `vibelign-core/src/backup/cas.rs` | CAS object 저장/조회/refcount/prune 구현 |
| `vibelign-core/src/backup/checkpoint.rs` | 기존 공개 함수 연결부로 유지, 새 모듈 호출만 담당 |
| `vibelign-core/src/backup/create.rs` | 백업 만들기와 증분 계획 구현 |
| `vibelign-core/src/backup/restore/full.rs` | 전체 되돌리기 구현 |
| `vibelign-core/src/backup/restore/files.rs` | 선택한 파일만 되돌리기 구현 |
| `vibelign-core/src/backup/restore/preview.rs` | 되돌리기 전 미리보기 구현 |
| `vibelign-core/src/backup/diff.rs` | 바뀐 내용 계산 |
| `vibelign-core/src/backup/stats.rs` | 날짜별/용량/개수 통계 계산 |
| `vibelign-core/src/backup/suggestions.rs` | 되돌릴 파일 추천 계산 |
| `vibelign-core/src/backup/snapshot.rs` | 스트리밍 해시와 병렬 수집 도입 |
| `vibelign-core/src/backup/retention.rs` | retention planner/apply 구현 |
| `vibelign-core/src/db/schema.rs` | v2 column migration 추가 |
| `vibelign-core/src/ipc/protocol.rs` | diff/preview/stats/safe restore 명령 추가 |
| `vibelign-core/Cargo.toml` | 병렬화/오류 타입 의존성 추가 여부 검토 |
| `vibelign/core/checkpoint_engine/rust_engine.py` | 기존 호환 wrapper로 유지, 새 요청/응답 helper 호출 |
| `vibelign/core/checkpoint_engine/requests.py` | Rust engine 요청 payload 생성 |
| `vibelign/core/checkpoint_engine/responses.py` | Rust engine 응답 파싱/검증 |
| `vibelign/core/checkpoint_engine/auto_backup.py` | 코드 저장 후 자동 백업 Python 진입점 |
| `vibelign/core/git_hooks.py` | post-commit 훅에 자동 checkpoint block 추가 |
| `vibelign/cli/cli_command_groups.py` | `_internal_post_commit_backup` 내부 명령 등록 |
| `vibelign/commands/internal_record_commit_cmd.py` | commit 기록과 자동 backup entrypoint 분리/연결 |
| `vibelign/mcp/mcp_checkpoint_handlers.py` | MCP checkpoint 출력에 저장공간/재사용 지표 반영 |
| `vibelign-gui/src/lib/vib.ts` | GUI에서 새 checkpoint/diff/preview 명령 호출 |
| `vibelign-gui/src/App.tsx` | 상단 `Checkpoints` 메뉴 제거, `DOCS VIEWER` 오른쪽에 독립 `BACKUPS` 메뉴와 page route 추가 |
| `vibelign-gui/src/pages/BackupDashboard.tsx` | 전체 화면 백업 데이터 대시보드 조립만 담당 |
| `vibelign-gui/src/components/backup-dashboard/*` | 안전 상태/아낀 용량/날짜 그래프/파일 기록/추천/미리보기 컴포넌트 분리 |
| `vibelign-gui/src/pages/Checkpoints.tsx` | 필요 시 `BackupDashboard.tsx` 내부 timeline/list 컴포넌트로 흡수하거나 제거 |
| `vibelign-gui/src/components/cards/backup/CheckpointCard.tsx` | checkpoint 생성 결과의 저장공간 절약 지표 표시 |

## 건드리지 않는 것

- 기존 JSON checkpoint를 자동 import하는 마이그레이션은 v2 MVP 범위에서 제외한다.
- cloud backup, remote sync, encryption은 별도 후속 기능으로 둔다. 단, v2 MVP module/API boundary는 이 기능들이 나중에 들어와도 `checkpoint.rs`, `BackupDashboard.tsx`, `vib.ts`를 다시 비대하게 만들지 않도록 유지한다.
- 전체 엔진을 async/Tokio로 재작성하지 않는다.
- 기존 `CheckpointRestore`의 contract를 breaking change로 바꾸지 않는다.
- GUI 디자인 개편은 엔진 API가 안정된 뒤 별도 설계로 진행한다.
- Backup Dashboard는 새 디자인 시스템을 만들지 않고 기존 card/checkpoint/brutalism 스타일을 확장한다.
- Backup Dashboard를 좁은 Home card 안에 욱여넣지 않는다. Home card는 생성/바로가기 수준만 담당한다.
- 상단 메뉴에 `Checkpoints`와 `BACKUPS`를 동시에 남기지 않는다. 백업 관련 사용자-facing 진입점은 `BACKUPS`로 통합한다.
- post-commit 자동 백업은 사용자의 commit을 막거나 실패시키지 않는다. 실패해도 조용히 기록만 남기거나 no-op한다.
- Dashboard/GUI 문구에는 `trigger`, `post_commit`, `SHA`, `hash`, `commit-backed`, `checkpoint`, `snapshot`, `diff`, `preview`, `ledger` 같은 내부 용어를 그대로 노출하지 않는다. 한국어로도 “트리거”, “해시”, “체크포인트”, “디프”, “프리뷰”, “레저”처럼 옮겨 적지 않는다.

## Phase 계획

### Phase 1 — Schema and compatibility foundation

- idempotent `apply_migrations(conn, target=2)` 러너 추가
- v2 schema column 추가 및 `db_meta.schema_version` 갱신
- `checkpoints.engine_version`을 v1/v2 단일 식별자로 사용
- `CheckpointCreate` request에 `trigger`, `git_commit_sha`, `git_commit_message` 추가
- `.gitignore`, retention default, NFC legacy path backfill, doctor warning 정리

성공 기준:

- migration을 두 번 실행해도 `duplicate column` 오류가 없다.
- legacy row는 `engine_version IS NULL` 기준으로 v1 restore path를 탄다.
- 기존 `vib checkpoint`, `vib history`, `vib undo` 사용자 경험이 깨지지 않는다.

### Phase 2 — CAS storage

- `cas.rs` 구현
- `cas_objects` row 생성/조회/refcount 갱신
- `.vibelign/rust_objects/blake3/ab/cd/<full_hash>` 저장 위치 확정
- 0 byte 파일, 동시 저장 race, symlink escape 테스트 추가

성공 기준:

- 같은 hash는 한 번만 저장된다.
- ref_count가 정확히 증가/감소한다.
- 0 byte 파일이 실제 빈 파일로 저장/복원된다.
- path traversal이나 symlink escape가 불가능하다.

### Phase 3 — Snapshot and incremental backup creation

- `snapshot.rs`에 streaming hash와 bounded parallel hashing 도입
- `create.rs`에 증분 백업 planner 구현
- `checkpoint.rs`는 thin delegator로 유지
- `original_size_bytes`, `stored_size_bytes`, `reused_file_count`, `changed_file_count` 기록

성공 기준:

- 큰 파일을 한 번에 메모리로 읽지 않는다.
- snapshot 결과 순서가 deterministic하다.
- unchanged file은 CAS object를 재사용한다.
- `no_changes` 판단은 기존보다 느려지지 않는다.

### Phase 4 — Restore, diff, preview, and file suggestions

- `restore/full.rs`, `restore/files.rs`, `restore/preview.rs` 구현
- `diff.rs`에 checkpoint 간 diff 계산 추가
- `suggestions.rs`에 되돌릴 파일 추천 계산 추가
- 관련 IPC request/response는 이 phase에서 추가

성공 기준:

- preview는 파일을 변경하지 않는다.
- 선택한 파일만 되돌리기 preview는 선택하지 않은 파일을 결과에 포함하지 않는다.
- legacy checkpoint도 restore 가능하다.
- 되돌릴 파일 추천은 cap/sort/legacy fallback 규칙을 따른다.

### Phase 5 — Retention and cleanup policy

- `retention.rs`에 retention planner/apply 구현
- CAS ref_count 기반 object prune 연결
- free disk guard와 backup operation busy timeout 조정
- planned bytes와 actually reclaimed bytes를 분리해 반환

성공 기준:

- 보호된 백업은 삭제되지 않는다.
- `min_keep`, daily/weekly/monthly 대표 백업 보존 규칙을 지킨다.
- cleanup crash/partial failure 후에도 `cas_objects.ref_count`가 drift되지 않는다.
- retention 적용 후에도 남은 checkpoint는 모두 restore 가능하다.

### Phase 6 — Commit-triggered automatic backup

- post-commit hook을 v2 block으로 upgrade
- 단일 `_internal_post_commit` entrypoint로 commit 기록과 자동 백업을 직렬 실행
- Python `checkpoint_engine/auto_backup.py`가 orchestration 담당
- `vib config auto-backup on|off` 토글 추가
- backup-class Rust subprocess timeout을 90초로 상향

성공 기준:

- commit 후 자동 checkpoint가 생성된다.
- commit이 이미 끝난 뒤 실행되므로, 자동 백업 실패가 Git workflow를 방해하지 않는다.
- 같은 snapshot이면 중복 checkpoint가 생성되지 않는다.
- Windows Python fallback chain과 CRLF hook case가 테스트된다.

### Phase 7 — Python bridge, CLI, and MCP integration

- `rust_engine.py`는 thin wrapper로 유지하고 request/response parsing을 `requests.py`, `responses.py`로 분리
- MCP/CLI가 stats, diff, preview, selected restore, suggestions, cleanup 명령을 호출 가능하게 연결
- `CheckpointSummary.trigger`를 통해 자동 백업/안전 복원 표시를 쉬운 말로 정리
- `shadow_runner.py`는 v2 default off, `VIBELIGN_SHADOW_COMPARE=1`에서만 활성화

성공 기준:

- Python이 모든 새 Rust command를 호출할 수 있다.
- MCP와 GUI contract는 stable snake_case JSON을 사용한다.
- CLI에는 raw internal 용어가 노출되지 않는다.

### Phase 8 — GUI `BACKUPS` dashboard

- `App.tsx`에서 기존 `checkpoints` nav tab을 제거하고 `BACKUPS` nav tab 추가
- `BackupDashboard.tsx`는 page shell만 담당
- `SafetySummary.tsx`, `StorageSavings.tsx`, `DateGraph.tsx`, `BackupFlow.tsx`, `RestoreSuggestions.tsx`, `FileHistoryTable.tsx`, `RestorePreviewPanel.tsx`, `CleanupInsight.tsx`로 분리
- banned-word lint를 `npm run lint`에 연결

성공 기준:

- `BACKUPS`가 단일 사용자-facing 백업 진입점이다.
- 코드를 모르는 사용자가 “백업이 됐는지 / 언제 됐는지 / 복원하면 무엇이 바뀌는지”를 한눈에 이해한다.
- 전체 파일 목록보다 “되돌릴 파일 추천”이 먼저 보인다.
- Dashboard 숫자는 엔진 JSON fixture와 일치한다.

### Phase 9 — Cross-platform and release verification

- macOS/Windows path normalization, Unicode, case-only rename, long path, locked file, symlink/junction 테스트 추가
- 0 byte transition 테스트 추가
- timezone/DST 날짜 grouping fixture 추가
- SQLite interruption/transaction safety 테스트 추가
- macOS와 Windows CI/test pass 확보

성공 기준:

- macOS와 Windows test suite가 모두 통과한다.
- file path, Unicode, 0 byte, locked file, symlink, cleanup policy case가 커버된다.
- release note에 Mac/Windows edge case 처리 사실을 안전하게 쓸 수 있다.

## 테스트

Rust core 테스트:

- CAS stores identical content once
- CAS ref_count increments/decrements across checkpoint create/prune
- Incremental checkpoint reuses unchanged object
- Restore from CAS reproduces exact files
- CAS stores and restores 0 byte files as real files, not missing files
- Incremental checkpoint reuses unchanged 0 byte files without duplicating rows
- Diff distinguishes empty file added/modified/restored from deleted file
- Restore removes files absent from target checkpoint
- Snapshot streaming hash equals previous `blake3::hash(fs::read())` result
- Parallel snapshot output is sorted and deterministic
- Diff reports added/modified/deleted correctly
- Restore preview does not modify workspace
- File restore preview does not include unselected files
- File restore restores selected files only and leaves other files unchanged
- Restore suggestions return recently changed, missing, and high-change files with plain-language reasons
- Safe restore creates pre-restore checkpoint before mutation
- Post-commit hook creates non-fatal auto checkpoint with commit metadata
- Post-commit auto backup skips duplicate checkpoint when snapshot has no changes
- Retention never deletes protected backups
- Retention does not prune below `min_keep`
- Retention keeps recent, daily, weekly, and monthly representative backups according to the default policy
- Retention prunes unprotected auto backups before user-created backups
- Retention does not delete safe-restore checkpoints before they age out of the protected window
- Retention reports planned vs actually reclaimed bytes separately
- Retention partial object-delete failure does not leave DB ref_count inconsistent
- Cross-platform path normalization treats `/` and `\\` consistently in stored `relative_path`
- Windows drive-letter and UNC-style inputs cannot escape the project root during restore
- macOS Unicode-normalized filenames do not create duplicate backup rows for the same visible path
- Case-only filename changes are detected safely on case-insensitive filesystems
- Read-only files, hidden files, and executable-bit changes restore predictably on supported platforms
- Symlinks and junction-like paths never allow backup or restore outside the project root
- Locked files on Windows fail with a clear partial-restore error and leave other files consistent
- Very long paths are either supported through canonical APIs or fail with a clear user-safe message

Integration 테스트:

- IPC `CheckpointCreate` still supports existing response fields
- IPC new commands return stable snake_case JSON
- Legacy checkpoint rows with `engine_version IS NULL` still restore through the v1 path
- `vib checkpoint` output can show saved/reused storage stats when available
- Backup Dashboard renders last backup age, checkpoint count, storage saved, and restore preview from JSON stats
- Backup Dashboard renders daily checkpoint graph from checkpoint dates and changed-file stats
- Backup Dashboard lists checkpoint files and per-file history with added/modified/deleted/reused labels
- Backup Dashboard shows restore file suggestions before the full file list
- Backup Dashboard shows automatic cleanup policy, reclaimable space, protected backup count, and last cleanup result in plain Korean
- Backup Dashboard does not expose internal terms such as SHA, trigger, post_commit, checkpoint, diff, preview, or ledger in user-facing Korean copy
- Backup Dashboard uses middle-school-level Korean labels for commit-linked backups, file history, changed content, and restore preview
- Backup Dashboard empty state explains that no checkpoint exists and recommends first action
- Git post-commit hook tests assert record and auto-backup blocks are idempotent and non-fatal
- CI runs the Rust backup test suite on macOS and Windows before release
- Windows tests cover backslash paths, read-only files, locked files, and long path behavior
- macOS tests cover Unicode filename normalization, case-only rename behavior, symlinks, and executable-bit metadata
- GUI/IPC snapshot fixtures are shared across macOS and Windows so Dashboard numbers match engine output on both platforms

## 위험과 완화

### 호스트 환경 위험 (iCloud / SMB / Antivirus / shadow_runner)

- `.vibelign/vibelign.db` 가 iCloud Drive, SMB share, NFS 등 외부 sync 위에 놓이면 SQLite WAL corruption 위험이 크다 (SQLite 공식 비지원). v2가 commit마다 자동 backup write 를 추가하면서 노출 빈도가 높아진다.
  - `vib doctor`/Phase 1 단계에서 project root 가 `~/Library/Mobile Documents/`(iCloud), `\\` UNC, `/Volumes/` 외부 share 아래에 있는지 감지해 사용자에게 한 번 경고한다.
  - 자동 비활성은 하지 않는다. 사용자가 위치를 옮기거나 무시하도록 선택권을 준다.
- Windows Defender / 사내 AV 가 `.vibelign/rust_objects/` 를 realtime scan하면 cold backup 이 30s 를 초과해 `rust_engine.py` 의 default timeout 에 걸릴 수 있다. backup 계열 명령은 90s 로 상향(§7).
- 기존 `vibelign/core/checkpoint_engine/shadow_runner.py` 는 비교용으로 전체 snapshot 을 `/tmp` 또는 `%TEMP%` 에 복사한다. v2에서는 매 commit 마다 발동되면 디스크/시간 비용이 폭증하므로, **shadow runner 는 v2 환경 default 로 비활성**한다 (`VIBELIGN_SHADOW_COMPARE=1` 환경변수일 때만 활성화). v1 한정 도구로 격리한다.
- v1 row 의 `relative_path` 는 정규화 안 된 raw 문자열, v2 는 NFC. legacy 와 v2 row 가 같은 DB에 섞이면 같은 파일이 added+deleted 로 잘못 분류된다.
  - Phase 1 마이그레이션에서 v1 `relative_path` 를 NFC 로 백필한다 (`UPDATE checkpoint_files SET relative_path = nfc(relative_path) WHERE checkpoint_id IN (legacy_ids)` 형태의 in-place migration).
  - 다만 NFC 변환으로 동일 v1 checkpoint 안에 중복 row 가 생기면 마이그레이션은 abort + 사용자에게 안내한다.

### Mac/Windows 파일시스템 차이

macOS와 Windows는 경로 구분자, 대소문자 처리, 잠긴 파일, Unicode 파일명 처리, 권한/metadata 표현이 다르다. 백업 엔진이 한쪽 기준으로만 동작하면 복원 대상이 잘못 계산되거나, 같은 파일이 중복 저장되거나, 복원이 일부만 실패할 수 있다.

완화:

- DB에는 OS별 원본 경로가 아니라 normalized `relative_path`를 저장한다.
- 저장 전 경로는 project root 기준으로 canonicalize하고, root 밖으로 나가는 경로는 거부한다.
- Windows `C:\`, UNC path, `..`, symlink/junction escape는 restore/write 전에 한 번 더 검사한다.
- 내부 비교는 `/` 기준 normalized path로 하되, 실제 파일 접근은 OS API에 맞는 `PathBuf`로 변환한다.
- macOS Unicode normalization 차이와 case-only rename은 별도 테스트 fixture로 고정한다.
- Windows에서 파일이 잠겨 있거나 read-only이면 전체 성공처럼 보이지 않게 partial failure를 명확히 반환한다.
- executable bit, hidden/read-only attribute처럼 OS마다 다르게 보이는 metadata는 v2 MVP에서 보존 범위를 명시하고, 보존하지 않는 값은 사용자-facing 복원 결과에 섞지 않는다.
- release 전 macOS와 Windows CI를 모두 통과해야 한다.

구현 중 반드시 확인할 edge case:

- 빈 프로젝트, 파일 0개, `.gitignore`만 있는 프로젝트
- 0 byte 파일, 0 byte에서 내용 있는 파일로 변경, 내용 있는 파일에서 0 byte로 변경
- 파일명에 공백, 한글, 이모지, 괄호, `#`, `%`, `&`가 들어간 경우
- 대소문자만 다른 파일명: `App.tsx` vs `app.tsx`
- macOS에서 같은 이름처럼 보이지만 Unicode normalization이 다른 파일명
- Windows 예약 이름/위험 이름: `CON`, `PRN`, `AUX`, `NUL`, `COM1`, `LPT1`
- 매우 긴 경로와 깊은 폴더
- symlink, broken symlink, Windows junction/reparse point
- restore 대상 파일이 실행 중이거나 다른 프로세스가 잠근 경우
- restore 대상 파일이 read-only/hidden인 경우
- 백업 도중 파일이 삭제되거나 수정되는 경우
- disk full, permission denied, antivirus interference 같은 중간 실패
- 줄바꿈 차이(LF/CRLF)가 diff를 불필요하게 키우는 경우
- timezone/DST 차이로 날짜 그래프가 하루 밀리는 경우
- SQLite transaction 중 interruption 또는 crash

### Refcount drift

CAS ref_count가 실제 checkpoint references와 달라지면 object가 잘못 삭제될 수 있다.

완화:

- prune 전 transaction 안에서 reference count를 갱신한다.
- debug/test helper로 DB row 기반 ref_count 재계산 검사를 둔다.

### Legacy 호환성

이미 생성된 checkpoint row는 `object_hash`가 없다.

완화:

- restore는 v1/v2 dual path를 유지한다.
- v2 checkpoint만 CAS를 필수로 요구한다.

### 병렬화로 인한 비결정성

해싱 순서가 병렬화되면 결과 순서가 흔들릴 수 있다.

완화:

- 외부로 반환하거나 DB에 저장하기 전 항상 `relative_path`로 정렬한다.

### 큰 변경 범위

CAS, 증분, 병렬화, diff, retention을 한 번에 구현하면 회귀 위험이 크다.

완화:

- Phase별로 독립 PR/commit 단위로 진행한다.
- 각 Phase는 기존 checkpoint contract를 깨지 않는 방식으로 merge 가능해야 한다.

## 완료 기준

Backup Engine v2는 다음 조건을 만족하면 완료로 본다.

- 사용자는 기존 명령을 그대로 사용하면서 저장공간 절약과 속도 개선을 체감한다.
- checkpoint 생성 결과에 scanned/changed/reused/storage saved 지표가 표시된다.
- 되돌리기 전 미리보기 또는 안전 되돌리기 경로가 제공된다.
- GUI Backup Dashboard에서 백업 안전 상태와 저장공간 절약을 비개발자도 이해할 수 있는 문장으로 보여준다.
- retention이 pinned/min_keep 규칙을 지키며 CAS object를 안전하게 정리한다.
- legacy checkpoint 복원이 깨지지 않는다.
- Rust core 테스트와 관련 CLI integration 테스트가 통과한다.

## 릴리스 분할

`v2`를 한 번의 큰 릴리스로 묶지 않는다.

- **v2-Engine MVP**: Phase 1–7 (스키마 마이그레이션 + CAS + 증분 + restore/preview/추천 + retention + post-commit auto-backup + Python bridge). CLI/MCP 표면은 이 시점에 완결.
- **v2-Dashboard MVP**: Phase 8 + Phase 9. Engine MVP가 안정된 뒤에 Dashboard 작업을 시작해 회귀 위험을 줄인다.

각 MVP는 별도 릴리스 노트로 출시한다. Engine MVP는 Dashboard 없이도 사용자가 CLI/MCP에서 새 동작을 즉시 누릴 수 있도록 만든다.

## 검토 피드백 반영 (2026-04-30)

리뷰에서 발견된 12개 이슈에 대한 해결책을 한 곳에 정리한다. 본문 해당 절은 이미 갱신되어 있다.

| # | 이슈 | 해결 |
|---|---|---|
| 1 | 스키마 마이그레이션 전략 부재 (재실행 시 `duplicate column`) | `db_meta.schema_version` 단일 게이트 + idempotent `apply_migrations` 러너 도입 (§2 스키마 마이그레이션 규칙) |
| 2 | v1/v2 식별자 이중화 (`engine_version` vs `object_hash IS NULL`) | `checkpoints.engine_version`만 단일 source of truth (§2 호환성 규칙) |
| 3 | `commit_auto_backup.rs`의 책임 불명 | Rust 모듈 폐기. Python `auto_backup.py`만 남기고 Rust는 request payload 필드로 메타 받기 (§7) |
| 4 | 기본값 mismatch (`min_keep` 10 vs 20, `max_total_size_bytes` 2 GiB vs 1 GiB) | v2 마이그레이션이 `min_keep=20`, `max_total_size_bytes=1 GiB` 로 갱신 (§8) |
| 5 | Phase 1 IPC 타입 일괄 정의 → 후속 phase 재작성 강제 | 각 phase가 자신의 IPC 타입을 같이 정의 (Plan Phase 1 축소) |
| 6 | Python bridge 기존 6개 파일 정리 계획 부재 | Plan Phase 7에 inventory 단락 추가 |
| 7 | cleanup transaction 순서 부정확 (row 삭제 → ref_count 감소 사이 크래시 시 drift) | 단일 SQL transaction에서 row 삭제 + ref_count 감소 atomic 처리, fs unlink는 별도 단계 (§8 cleanup transaction 순서) |
| 8 | selected-file 안전 백업 범위 모호 | 항상 전체 프로젝트 snapshot으로 명시 (§6 주의) |
| 9 | v2 row의 `storage_path` 빈 값 가능 → 분기 3개화 | v2 row는 `cas:<full_hash>` sentinel 필수 (§2 호환성 규칙) |
| 10 | 추천 알고리즘 미정의 (상한, 정렬, legacy fallback) | 후보 5개 default, reason_code 4종, legacy v1 fallback notice 명시 (§5 추천 알고리즘 명세) |
| 11 | Phase 9 cross-platform 일괄 검증 → 늦은 발견 | Plan Phase 2/4/6에 platform smoke 1개씩 추가 |
| 12 | `auto_backup_on_commit` 저장 위치 미지정 | `db_meta` row(`'1' | '0'`)로 통일 (§7) |

추가로 반영된 보강:

- CAS 동시성 규칙: `INSERT ... ON CONFLICT(hash) DO UPDATE SET ref_count = ref_count + 1` + tempfile/atomic rename (§1 동시성 규칙)
- `vib undo`는 v2 환경에서 가장 최근 v2 checkpoint 기준 safe full restore (§6 주의)
- 릴리스 분할: v2-Engine (Phase 1–7) / v2-Dashboard (Phase 8–9)
- Korean banned-word lint와 phase별 platform smoke는 Plan에서 강제 (Plan Phase 8 / 2 / 4 / 6)

## 검토 피드백 라운드 2 (2026-04-30 — 명령 충돌/플랫폼)

리뷰 라운드 2에서 식별된 블로커/회귀 위험/플랫폼 엣지에 대한 결정.

| # | 이슈 | 해결 |
|---|---|---|
| B1 | `.vibelign/rust_objects/` 가 `.gitignore` 에 빠지면 BLAKE3 blob 이 git 에 커밋됨 | `vib_start_cmd._ensure_gitignore_entry` 가 `rust_objects/` + `rust_checkpoints/` 도 idempotent 로 추가하도록 확장 (Plan Phase 1) |
| B2 | post-commit hook 의 `python3` fallback 이 Windows 에서 실패 | hook 스크립트 fallback chain 을 `python` → `py -3` → `python3` 로 수정 (§7 / Plan Phase 6) |
| B3 | stdin pipe 를 두 명령(`_internal_record_commit` + `_internal_post_commit_backup`)에 분배 불가 | 단일 entrypoint 가 record + backup 차례로 실행 (§7 post-commit hook 구현 규칙) |
| B4 | 존재하지 않는 settings 명령을 가정 | `vib config auto-backup on|off` 로 기존 트리 재사용 (§7 / Plan Phase 6) |
| B5 | free disk 측정 의존성 부재 | `Cargo.toml` 에 `fs2` (또는 `sysinfo`) 추가 (Plan Phase 5) |
| C1 | post-commit 에서 record + backup 이 work_memory race | 단일 직렬 entrypoint 로 직렬 실행 (§7) |
| C2 | `vib undo` 가 silently safety checkpoint 추가 → 사용자 혼란 | safety checkpoint 는 history/undo 목록에서 숨김 + 첫 실행 안내 한 줄 (§6) |
| C3 | `_clean_msg` 가 v2 자동 백업 메시지 패턴을 인식 못 해 raw SHA 노출 | `CheckpointSummary` 에 `trigger` 추가, `_clean_msg` 에 자동 백업 패턴 추가 (Plan Phase 7) |
| C4 | `RetentionPolicy` dataclass default(10/2GiB) 가 DB default(20/1GiB)와 불일치 | Phase 1에서 dataclass default 도 동시 갱신 (Plan Phase 1) |
| C5 | shadow_runner 가 v2 환경에서 디스크 폭증 | default 비활성, opt-in env (`VIBELIGN_SHADOW_COMPARE=1`) (호스트 환경 위험 절) |
| C6 | SQLite busy_timeout 5s 가 v2 cleanup 트랜잭션 동시성에서 부족할 수 있음 | busy_timeout 을 backup 계열 호출에 한해 15s 로 상향 검토 (Plan Phase 5 verification) |
| M1 | iCloud / SMB 위 `.vibelign/vibelign.db` corruption 위험 | doctor / Phase 1 에서 위치 감지 후 1회 경고 (호스트 환경 위험 절) |
| M2 | v1 NFD vs v2 NFC `relative_path` 혼재 | Phase 1 마이그레이션에서 v1 row NFC 백필, 충돌 시 abort + 안내 (호스트 환경 위험 절) |
| M3 | macOS case-only rename 우선 규칙 미정 | "마지막 stat 결과 우선" — `WalkDir` 이 OS 보고대로 받은 케이스가 새 row 의 `relative_path` (Plan Phase 9 테스트) |
| M4 | macOS SMB 마운트에서 `chmod 0o755` silently 실패 | 실패 시 `chmod-failed` status 로 user-facing 경고 (이미 git_hooks.py 에 존재 — v2 변경 없음, 회귀만 검증) |
| W1 | Windows NTFS 260자 한도 — CI 깊은 경로에서 파괴 | Rust restore/write 경로에 `\\?\` long-path prefix 적용 (Plan Phase 9) |
| W2 | Windows 잠긴 파일이 snapshot 에서 silently skip | snapshot 결과 타입에 `skipped[]` 필드 추가, partial 표시 (§1 잠긴 파일 처리) |
| W3 | non-ASCII cwd encoding | `subprocess.run` 호출에 `encoding="utf-8"` 명시 (이미 `rust_engine.py` 에 적용됨, v2 신규 호출도 동일 적용) |
| W4 | AV scan 으로 30s timeout 초과 | backup 계열 timeout 을 90s 로 상향 (§7) |
| W5 | `.exe.sha256` 매니페스트 배포 누락 위험 | 릴리스 노트에 명시 — 별도 design 변경 없음 |
| W6 | Git Bash CRLF 변환으로 commit message 1byte 변형 | `git_commit_message` 를 dedupe key 로 쓰지 않음. dedupe 는 snapshot 비교만 사용 (§7) |
