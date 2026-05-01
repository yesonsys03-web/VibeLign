# Backup DB Viewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Source spec: `docs/superpowers/specs/2026-05-01-backup-db-viewer-design.md`.

**Goal:** Add a read-only, readable Backup DB Viewer under BACKUPS that summarizes `.vibelign/vibelign.db` and Rust object-store state without exposing raw SQL or editable DB controls.

**DB growth policy:** Checkpoint/CAS retention is not enough for SQLite file growth. The viewer must expose `vibelign.db`, `vibelign.db-wal`, `vibelign.db-shm`, and their total size. It warns at 64MB and strong-warns at 256MB, but it must not run `VACUUM` or `wal_checkpoint` from this read-only viewer. Actual compaction belongs in the CLI-only `vib backup-db-maintenance` command with lock checks, dry-run-first behavior, raw DB-file backup, WAL truncation, conditional VACUUM, and recovery reporting.

**Architecture:** Rust owns all SQLite reads through a new `BackupDbViewerInspect` IPC request and returns a shaped, human-readable inspect payload. Python adds request/response/router/CLI JSON plumbing without a Python fallback inspector. The GUI calls the JSON command through `vib.ts` and renders cards, searchable rows, badges, and a detail panel inside the existing BACKUPS page.

**Tech Stack:** Rust (`rusqlite`, `serde`, existing IPC protocol), Python checkpoint engine wrappers, Tauri `run_vib`, React/TypeScript, existing `brutalism.css` UI primitives.

---

## Non-negotiable constraints

- Keep the existing BACKUPS backup list/restore screen intact.
- Add `Backup DB Viewer` as a BACKUPS child view, not a replacement page.
- No raw SQL input, no arbitrary SQL execution, no DB editing, no `run_vib` raw SQL escape hatch.
- No DB compaction action in the viewer. `VACUUM`, `PRAGMA wal_checkpoint(TRUNCATE)`, and `incremental_vacuum` are out of scope for this screen.
- React never opens `.vibelign/vibelign.db` directly and never sends SQL strings.
- First implementation reads only `root/.vibelign/vibelign.db` and object-store metadata under `root/.vibelign/rust_objects/blake3`.
- First implementation reports SQLite management-file sizes: `vibelign.db`, `vibelign.db-wal`, `vibelign.db-shm`, and total bytes.
- Use readable labels in the GUI: `checkpoint_id` → `저장본 ID`, `trigger` → `만들어진 이유`, `stored_size_bytes` → `실제 저장 크기`.
- Do not show a dense raw table/grid in the first implementation.
- Keep `vibelign-gui/src/pages/BackupDashboard.tsx` as a page shell and avoid bloating `vibelign-gui/src/lib/vib.ts` beyond typed wrappers.
- Do not use `as any`, `@ts-ignore`, or `@ts-expect-error`.
- Add anchors to new Rust/Python source files if the surrounding project convention requires them.
- The viewer must tolerate partially initialized or older SQLite DB files. It must not assume every v2/v3 table or column exists.
- The GUI parser must normalize every snake_case field, including nested `retention_policy` and `object_store` values, before exposing camelCase TypeScript types.

## Target file structure

Rust:

```text
vibelign-core/src/backup/
├─ db_viewer.rs        # new read-only inspect queries and response structs
└─ mod.rs             # exports db_viewer

vibelign-core/src/ipc/protocol.rs  # adds BackupDbViewerInspect request + dispatch
```

Python:

```text
vibelign/core/checkpoint_engine/
├─ requests.py                 # backup_db_viewer_inspect_request(root)
├─ responses.py                # parse_backup_db_viewer_inspect(response)
├─ rust_engine.py              # inspect_backup_db_with_rust(root)
├─ rust_checkpoint_engine.py   # adapter method; no Python fallback
├─ python_engine.py            # raises clear RuntimeError for unsupported inspect
├─ contracts.py                # CheckpointEngine protocol method
└─ router.py                   # inspect_backup_db(root)

vibelign/commands/vib_backup_db_viewer_cmd.py  # new CLI JSON command wrapper
vibelign/cli/cli_core_commands.py              # subcommand registration
```

GUI:

```text
vibelign-gui/src/lib/vib.ts
vibelign-gui/src/pages/BackupDashboard.tsx
vibelign-gui/src/components/backup-dashboard/
├─ BackupDashboard.tsx
├─ BackupDbViewer.tsx
├─ BackupDbSummaryCards.tsx
├─ BackupDbRowList.tsx
├─ BackupDbDetailPanel.tsx
└─ backupDbModel.ts
```

Tests:

```text
tests/test_checkpoint_rust_engine.py
tests/test_checkpoint_engine_router.py
tests/test_gui_cli_contracts.py
vibelign-core/src/backup/db_viewer.rs  # module tests
```

---

## Task 1: Rust read-only inspect module

**Files:**

- Create: `vibelign-core/src/backup/db_viewer.rs`
- Modify: `vibelign-core/src/backup/mod.rs`
- Test: module tests inside `vibelign-core/src/backup/db_viewer.rs`

- [ ] **Step 1: Write failing Rust tests for missing DB, partial DB, schema compatibility, and read-only summary**

Add tests in the new file with fixtures that create a temporary project root. The first test asserts a missing DB returns `db_exists=false`; the second creates a partial SQLite file with only `db_meta` and asserts the viewer does not crash; the third initializes schema, inserts one Rust v2 checkpoint, one CAS object, one retention row, then verifies counts and row summaries.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use crate::db::schema::initialize;
    use rusqlite::{params, Connection};
    use tempfile::tempdir;

    #[test]
    fn inspect_missing_db_returns_empty_readable_state() {
        let dir = tempdir().unwrap();
        let report = inspect(dir.path()).unwrap();

        assert!(!report.db_exists);
        assert_eq!(report.checkpoint_count, 0);
        assert_eq!(report.cas_object_count, 0);
        assert!(report.checkpoints.is_empty());
        assert!(report.warnings.iter().any(|warning| warning.contains("Rust backup DB")));
    }

    #[test]
    fn inspect_partial_db_with_only_db_meta_returns_warning_not_error() {
        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let conn = Connection::open(db_dir.join("vibelign.db")).unwrap();
        conn.execute("CREATE TABLE db_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)", []).unwrap();
        conn.execute("INSERT INTO db_meta (key, value) VALUES ('schema_version', '1')", []).unwrap();
        conn.execute("INSERT INTO db_meta (key, value) VALUES ('auto_backup_on_commit', '1')", []).unwrap();

        let report = inspect(dir.path()).unwrap();

        assert!(report.db_exists);
        assert_eq!(report.schema_version.as_deref(), Some("1"));
        assert_eq!(report.checkpoint_count, 0);
        assert_eq!(report.cas_object_count, 0);
        assert!(report.auto_backup_on_commit);
        assert!(report.warnings.iter().any(|warning| warning.contains("table") || warning.contains("schema")));
    }

    #[test]
    fn inspect_summarizes_checkpoints_retention_and_cas_without_writing() {
        let dir = tempdir().unwrap();
        let db_dir = dir.path().join(".vibelign");
        std::fs::create_dir_all(&db_dir).unwrap();
        let db_path = db_dir.join("vibelign.db");
        let before_modified;

        {
            let conn = Connection::open(&db_path).unwrap();
            initialize(&conn).unwrap();
            conn.execute(
                "UPDATE db_meta SET value='1' WHERE key='auto_backup_on_commit'",
                [],
            ).unwrap();
            conn.execute(
                "INSERT INTO checkpoints (checkpoint_id, created_at, message, pinned, total_size_bytes, file_count, engine_version, parent_checkpoint_id, original_size_bytes, stored_size_bytes, reused_file_count, changed_file_count, trigger, git_commit_sha, git_commit_message)
                 VALUES (?1, ?2, ?3, 0, ?4, ?5, 'rust-v2', NULL, ?6, ?7, ?8, ?9, 'post_commit', ?10, ?11)",
                params!["cp-1", "2026-05-01T10:00:00Z", "auto backup", 120_i64, 3_i64, 120_i64, 40_i64, 2_i64, 1_i64, "abcdef123456", "save work"],
            ).unwrap();
            conn.execute(
                "INSERT INTO checkpoint_files (checkpoint_id, relative_path, hash, size, storage_path, object_hash) VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params!["cp-1", "src/main.rs", "hash-a", 40_i64, "cas:object-a", "object-a"],
            ).unwrap();
            conn.execute(
                "INSERT INTO cas_objects (hash, storage_path, ref_count, size, backend, compression, stored_size) VALUES (?1, ?2, ?3, ?4, 'local', 'none', ?5)",
                params!["object-a", "blake3/ob/je/object-a", 2_i64, 40_i64, 40_i64],
            ).unwrap();
        }

        before_modified = std::fs::metadata(&db_path).unwrap().modified().unwrap();
        let report = inspect(dir.path()).unwrap();
        let after_modified = std::fs::metadata(&db_path).unwrap().modified().unwrap();

        assert!(report.db_exists);
        assert_eq!(report.checkpoint_count, 1);
        assert_eq!(report.rust_v2_count, 1);
        assert_eq!(report.legacy_count, 0);
        assert_eq!(report.cas_object_count, 1);
        assert_eq!(report.cas_ref_count, 2);
        assert_eq!(report.total_original_size_bytes, 120);
        assert_eq!(report.total_stored_size_bytes, 40);
        assert!(report.auto_backup_on_commit);
        assert_eq!(report.checkpoints[0].checkpoint_id, "cp-1");
        assert_eq!(report.checkpoints[0].display_name, "auto backup");
        assert_eq!(report.checkpoints[0].trigger_label, "코드 저장 뒤 자동 보관");
        assert_eq!(before_modified, after_modified);
    }
}
```

- [ ] **Step 2: Run the focused Rust test and confirm it fails**

Run:

```bash
rtk cargo test backup::db_viewer --manifest-path vibelign-core/Cargo.toml
```

Expected: FAIL because `vibelign-core/src/backup/db_viewer.rs` and `inspect` do not exist yet.

- [ ] **Step 3: Implement read-only structs and query logic**

Create `vibelign-core/src/backup/db_viewer.rs` with `serde::Serialize` structs and `inspect(root: &Path) -> Result<BackupDbViewerInspectReport, String>`. Use `Connection::open_with_flags` with `SQLITE_OPEN_READ_ONLY`, set `PRAGMA query_only=ON`, and only query allowlisted tables. Also stat `vibelign.db`, `vibelign.db-wal`, and `vibelign.db-shm` so the UI can separate SQLite management-file growth from CAS/object-store growth.

Required public structs:

```rust
#[derive(Debug, Clone, serde::Serialize)]
pub struct BackupDbViewerInspectReport {
    pub db_exists: bool,
    pub db_path: String,
    pub db_file: BackupDbViewerDbFileStats,
    pub schema_version: Option<String>,
    pub checkpoint_count: i64,
    pub rust_v2_count: i64,
    pub legacy_count: i64,
    pub cas_object_count: i64,
    pub cas_ref_count: i64,
    pub total_original_size_bytes: i64,
    pub total_stored_size_bytes: i64,
    pub auto_backup_on_commit: bool,
    pub retention_policy: Option<BackupDbViewerRetentionPolicy>,
    pub object_store: BackupDbViewerObjectStore,
    pub checkpoints: Vec<BackupDbViewerCheckpointRow>,
    pub warnings: Vec<String>,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct BackupDbViewerDbFileStats {
    pub database_bytes: i64,
    pub wal_bytes: i64,
    pub shm_bytes: i64,
    pub total_bytes: i64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct BackupDbViewerRetentionPolicy {
    pub keep_latest: i64,
    pub keep_daily_days: i64,
    pub keep_weekly_weeks: i64,
    pub max_total_size_bytes: i64,
    pub max_age_days: i64,
    pub min_keep: i64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct BackupDbViewerObjectStore {
    pub exists: bool,
    pub path: String,
    pub compression_summary: Vec<BackupDbViewerCompressionSummary>,
    pub stored_size_bytes: i64,
    pub original_size_bytes: i64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct BackupDbViewerCompressionSummary {
    pub compression: String,
    pub object_count: i64,
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct BackupDbViewerCheckpointRow {
    pub checkpoint_id: String,
    pub display_name: String,
    pub created_at: String,
    pub pinned: bool,
    pub trigger: Option<String>,
    pub trigger_label: String,
    pub git_commit_sha: Option<String>,
    pub git_commit_message: Option<String>,
    pub file_count: i64,
    pub total_size_bytes: i64,
    pub original_size_bytes: i64,
    pub stored_size_bytes: i64,
    pub reused_file_count: i64,
    pub changed_file_count: i64,
    pub engine_version: Option<String>,
    pub parent_checkpoint_id: Option<String>,
    pub internal_badges: Vec<String>,
}
```

Required query behavior:

- If `root/.vibelign/vibelign.db` does not exist, return `db_exists=false` with zero counts and a warning.
- Resolve the DB path as `root/.vibelign/vibelign.db` only. Reuse the project’s path-guard style from `vibelign-core/src/security/path_guard.rs` where applicable so symlink/path escape cannot redirect the viewer to another DB.
- Before querying optional tables/columns, inspect `sqlite_master` and `PRAGMA table_info`. If a table or migrated column is absent, return 0/`None` for that section plus a warning instead of failing.
- Read `db_meta.schema_version` and `db_meta.auto_backup_on_commit`.
- Compare `db_meta.schema_version` with the current engine schema version; if the DB is newer than the current engine, keep read-only behavior and add a warning.
- Read `retention_policy` with one row, if present.
- Aggregate CAS via `COUNT(*)`, `SUM(ref_count)`, `SUM(size)`, `SUM(stored_size)` from `cas_objects` when those columns exist.
- Return compression as `compression_summary` grouped by `cas_objects.compression`; do not collapse the whole store into one `compression_label`.
- Aggregate checkpoints via `COUNT(*)`, `SUM(original_size_bytes)`, `SUM(stored_size_bytes)`, and count `engine_version='rust-v2'` vs legacy/null.
- Return checkpoint rows sorted newest-first by `created_at DESC, checkpoint_id DESC`, matching `vibelign-core/src/backup/checkpoint.rs::list`.
- Map `post_commit` to `코드 저장 뒤 자동 보관`, `safe_restore` to `복원 보호용 내부 저장본`, `manual`/null to `수동 백업`, unknown trigger to `기타`.
- Keep safe restore rows visible in DB Viewer, but mark them with an internal/protected badge so users understand why the regular BACKUPS list may not show them.
- Build `display_name` with the same intent as `vibelign-gui/src/lib/vib.ts::cleanRawBackupNote`: prefer useful git commit/message text, strip machine prefixes, and label post-commit rows as automatic backups. Add a Rust unit test for a post-commit message and a safe-restore message.
- Include badges such as `Rust v2`, `자동 백업`, `수동 백업`, `읽기 전용`.

- [ ] **Step 4: Export the module**

Modify `vibelign-core/src/backup/mod.rs`:

```rust
pub mod db_viewer;
```

- [ ] **Step 5: Run Rust tests**

Run:

```bash
rtk cargo test backup::db_viewer --manifest-path vibelign-core/Cargo.toml
rtk cargo test --manifest-path vibelign-core/Cargo.toml
```

Expected: PASS.

---

## Task 2: Rust IPC request/response wiring

**Files:**

- Modify: `vibelign-core/src/ipc/protocol.rs`
- Test: existing protocol/module tests or add focused test in `protocol.rs`

- [ ] **Step 1: Add a failing IPC serialization/dispatch test**

Add a test that deserializes this JSON and verifies it dispatches successfully against a temp root with missing DB:

```json
{"command":"backup_db_viewer_inspect","root":"/tmp/example"}
```

Expected response shape includes `status="ok"`, `result="backup_db_viewer_inspect"`, and `db_exists=false`.

- [ ] **Step 2: Run the focused IPC test and confirm it fails**

Run:

```bash
rtk cargo test ipc::protocol::backup_db_viewer --manifest-path vibelign-core/Cargo.toml
```

Expected: FAIL because the request variant does not exist.

- [ ] **Step 3: Add request variant, response variant, and dispatch**

In `EngineRequest`, add:

```rust
#[serde(rename = "backup_db_viewer_inspect")]
BackupDbViewerInspect { root: PathBuf },
```

The existing `EngineResponse::Ok` is a fixed-shape variant with named optional fields (`checkpoint_id`, `checkpoints`, `diff`, ...) that cannot carry viewer-specific fields like `db_exists`, `cas_object_count`, `total_stored_size_bytes`. Follow the `RetentionApply` → `RetentionOk` precedent and add a dedicated response variant. In `EngineResponse`, add:

```rust
#[serde(rename = "ok")]
BackupDbViewerInspectOk {
    result: String,
    #[serde(flatten)]
    report: crate::backup::db_viewer::BackupDbViewerInspectReport,
},
```

`#[serde(flatten)]` lifts every field of `BackupDbViewerInspectReport` to the top level so the JSON payload becomes `{"status":"ok","result":"backup_db_viewer_inspect","db_exists":...,"checkpoint_count":...}`, matching the protocol test in Step 1. Multiple `Serialize` variants sharing `rename = "ok"` is fine because `EngineResponse` is `Serialize`-only (deserialize lives on `EngineRequest`).

In `handle(request: EngineRequest) -> EngineResponse`, add the dispatch branch:

```rust
EngineRequest::BackupDbViewerInspect { root } => match crate::backup::db_viewer::inspect(&root) {
    Ok(report) => EngineResponse::BackupDbViewerInspectOk {
        result: "backup_db_viewer_inspect".to_string(),
        report,
    },
    Err(error) => EngineResponse::Error {
        code: "BACKUP_DB_VIEWER_INSPECT_FAILED".to_string(),
        message: error,
    },
},
```

Do not add update/write commands.

- [ ] **Step 4: Run Rust IPC and full Rust tests**

Run:

```bash
rtk cargo test ipc::protocol --manifest-path vibelign-core/Cargo.toml
rtk cargo test --manifest-path vibelign-core/Cargo.toml
```

Expected: PASS.

---

## Task 3: Python request/response/router plumbing

**Files:**

- Modify: `vibelign/core/checkpoint_engine/requests.py`
- Modify: `vibelign/core/checkpoint_engine/responses.py`
- Modify: `vibelign/core/checkpoint_engine/rust_engine.py`
- Modify: `vibelign/core/checkpoint_engine/contracts.py`
- Modify: `vibelign/core/checkpoint_engine/rust_checkpoint_engine.py`
- Modify: `vibelign/core/checkpoint_engine/python_engine.py`
- Modify: `vibelign/core/checkpoint_engine/router.py`
- Test: `tests/test_checkpoint_rust_engine.py`
- Test: `tests/test_checkpoint_engine_router.py`

- [ ] **Step 1: Add failing Python wrapper tests**

Add tests to `tests/test_checkpoint_rust_engine.py`:

```python
def test_backup_db_viewer_request_shape(tmp_path):
    from vibelign.core.checkpoint_engine.requests import backup_db_viewer_inspect_request

    assert backup_db_viewer_inspect_request(tmp_path) == {
        "command": "backup_db_viewer_inspect",
        "root": str(tmp_path),
    }


def test_parse_backup_db_viewer_inspect_response():
    from types import SimpleNamespace
    from vibelign.core.checkpoint_engine.responses import parse_backup_db_viewer_inspect

    payload = {
        "result": "backup_db_viewer_inspect",
        "db_exists": True,
        "checkpoint_count": 1,
        "checkpoints": [{"checkpoint_id": "cp-1", "display_name": "backup"}],
    }
    rust_result = SimpleNamespace(ok=True, payload=payload, error_code=None, error_message=None)

    parsed, warning = parse_backup_db_viewer_inspect(rust_result)

    assert warning is None
    assert parsed is not None
    assert parsed["db_exists"] is True
    assert parsed["checkpoint_count"] == 1
    assert parsed["checkpoints"][0]["checkpoint_id"] == "cp-1"


def test_inspect_backup_db_with_rust_calls_engine(monkeypatch, tmp_path):
    from vibelign.core.checkpoint_engine import rust_engine
    from vibelign.core.checkpoint_engine.rust_engine import RustEngineResult

    seen = {}

    def fake_call(root, request, timeout_seconds=30):
        seen["root"] = root
        seen["request"] = request
        return RustEngineResult(
            ok=True,
            payload={
                "result": "backup_db_viewer_inspect",
                "db_exists": False,
                "checkpoint_count": 0,
                "checkpoints": [],
            },
        )

    monkeypatch.setattr(rust_engine, "call_rust_engine", fake_call)

    report, warning = rust_engine.inspect_backup_db_with_rust(tmp_path)

    assert warning is None
    assert report is not None
    assert seen["root"] == tmp_path
    assert seen["request"] == {"command": "backup_db_viewer_inspect", "root": str(tmp_path)}
    assert report["db_exists"] is False
```

Add router test to `tests/test_checkpoint_engine_router.py`:

```python
def test_router_inspect_backup_db_delegates(monkeypatch, tmp_path):
    from vibelign.core.checkpoint_engine import router

    class FakeEngine:
        def inspect_backup_db(self, root):
            assert root == tmp_path
            return {"db_exists": False, "checkpoint_count": 0, "checkpoints": []}

    monkeypatch.setattr(router, "get_checkpoint_engine", lambda: FakeEngine())

    assert router.inspect_backup_db(tmp_path)["db_exists"] is False
```

The router module attribute is `_DEFAULT_ENGINE` (not `_engine`) and every router function calls through the `get_checkpoint_engine()` accessor — patch that accessor instead of poking the private name.

- [ ] **Step 2: Run failing Python tests**

Run:

```bash
uv run pytest tests/test_checkpoint_rust_engine.py::test_backup_db_viewer_request_shape tests/test_checkpoint_rust_engine.py::test_parse_backup_db_viewer_inspect_response tests/test_checkpoint_rust_engine.py::test_inspect_backup_db_with_rust_calls_engine tests/test_checkpoint_engine_router.py::test_router_inspect_backup_db_delegates -q
```

Expected: FAIL because functions/methods do not exist.

- [ ] **Step 3: Implement request and response helpers**

In `requests.py` add:

```python
def backup_db_viewer_inspect_request(root: Path | str) -> dict[str, object]:
    return {"command": "backup_db_viewer_inspect", "root": str(root)}
```

In `responses.py` add a parser that follows the existing `RustResultLike` → `tuple[T | None, str | None]` convention used by every other parser in this module (`parse_checkpoint_list`, `parse_diff`, `parse_retention`, ...). `call_rust_engine` returns a `RustEngineResult` dataclass with `.ok` / `.payload` / `.error_code` / `.error_message`, not a raw `dict`, so the parser must consume that shape:

```python
def parse_backup_db_viewer_inspect(
    result: RustResultLike,
) -> tuple[dict[str, object] | None, str | None]:
    if not result.ok:
        return None, format_error(result, "rust backup db viewer inspect failed")
    if result.payload.get("result") != "backup_db_viewer_inspect":
        return None, "RUST_ENGINE_PROTOCOL_ERROR: unexpected backup_db_viewer_inspect result"
    return dict(result.payload), None
```

- [ ] **Step 4: Implement Rust transport wrapper**

In `rust_engine.py` add the wrapper, mirroring the `tuple[T | None, str | None]` shape used by `list_checkpoints_with_rust`, `apply_retention_with_rust`, and friends:

```python
def inspect_backup_db_with_rust(
    root: Path,
) -> tuple[dict[str, object] | None, str | None]:
    request = backup_db_viewer_inspect_request(root)
    result = call_rust_engine(root, request, timeout_seconds=30)
    return parse_backup_db_viewer_inspect(result)
```

Import `backup_db_viewer_inspect_request` from `requests` and `parse_backup_db_viewer_inspect` from `responses` at the top of the module.

- [ ] **Step 5: Extend engine protocol and adapters**

In `contracts.py`, add to `CheckpointEngine`:

```python
def inspect_backup_db(self, root: Path | str) -> dict[str, object]: ...
```

In `rust_checkpoint_engine.py`, import `inspect_backup_db_with_rust` alongside the other `*_with_rust` imports and add the adapter that unwraps the tuple (matching the `diff_checkpoints` / `apply_retention` adapter style — raise on `None`, no Python fallback for inspect):

```python
def inspect_backup_db(self, root: Path) -> dict[str, object]:
    result, warning = inspect_backup_db_with_rust(root)
    if result is None:
        raise RuntimeError(warning or "Rust backup DB viewer inspect failed.")
    return result
```

In `python_engine.py`, add:

```python
def inspect_backup_db(self, root: Path) -> dict[str, object]:
    raise RuntimeError("Backup DB Viewer requires the Rust checkpoint engine")
```

In `router.py`, add — using the existing `get_checkpoint_engine()` accessor (the module attribute is `_DEFAULT_ENGINE`, and every other router function delegates through this accessor):

```python
def inspect_backup_db(root: Path | str) -> dict[str, object]:
    return get_checkpoint_engine().inspect_backup_db(Path(root))
```

- [ ] **Step 6: Run targeted Python tests**

Run:

```bash
uv run pytest tests/test_checkpoint_rust_engine.py tests/test_checkpoint_engine_router.py -q
```

Expected: PASS.

---

## Task 4: CLI JSON command for GUI consumption

**Files:**

- Create: `vibelign/commands/vib_backup_db_viewer_cmd.py`
- Modify: `vibelign/cli/cli_core_commands.py`
- Test: `tests/test_gui_cli_contracts.py`

- [ ] **Step 1: Add failing GUI CLI contract test**

Add to `tests/test_gui_cli_contracts.py`:

```python
def test_backup_db_viewer_json_contract(monkeypatch, tmp_path, capsys):
    from argparse import Namespace
    from vibelign.commands.vib_backup_db_viewer_cmd import run_vib_backup_db_viewer

    def fake_inspect(root):
        assert root == tmp_path
        return {"db_exists": False, "checkpoint_count": 0, "checkpoints": []}

    monkeypatch.setattr("vibelign.commands.vib_backup_db_viewer_cmd.inspect_backup_db", fake_inspect)

    code = run_vib_backup_db_viewer(Namespace(root=str(tmp_path), json=True))

    out = capsys.readouterr().out


    assert code == 0
    assert '"ok": true' in out
    assert '"db_exists": false' in out
    assert '"checkpoints": []' in out
```

- [ ] **Step 2: Run the failing contract test**

Run:

```bash
uv run pytest tests/test_gui_cli_contracts.py::test_backup_db_viewer_json_contract -q
```

Expected: FAIL because the command module does not exist.

- [ ] **Step 3: Implement command wrapper**

Create `vibelign/commands/vib_backup_db_viewer_cmd.py`:

```python
from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from vibelign.core.checkpoint_engine.router import inspect_backup_db
from vibelign.core.project_root import resolve_project_root


def _viewer_error_message(message: str) -> str:
    if "RUST_ENGINE_UNAVAILABLE" in message or "Rust backup DB viewer" in message:
        return "백업 관리 DB를 읽을 수 없어요. 설치된 앱/CLI의 백업 엔진을 확인해 주세요."
    if "locked" in message.lower() or "busy" in message.lower():
        return "다른 백업 작업이 끝난 뒤 다시 새로고침해 주세요."
    return f"백업 관리 DB를 읽을 수 없어요: {message}"


# === ANCHOR: VIB_BACKUP_DB_VIEWER_CMD_START ===
def run_vib_backup_db_viewer(args: Namespace) -> int:
    requested_root = Path(getattr(args, "root", ".")).resolve()
    root = resolve_project_root(requested_root)
    try:
        report = inspect_backup_db(root)
    except Exception as exc:
        message = _viewer_error_message(str(exc))
        if getattr(args, "json", False):
            print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
        else:
            print(message)
        return 1

    if getattr(args, "json", False):
        print(json.dumps({"ok": True, **report}, ensure_ascii=False))
    else:
        print("백업 관리 DB 상태를 확인했어요.")
    return 0
# === ANCHOR: VIB_BACKUP_DB_VIEWER_CMD_END ===
```

- [ ] **Step 4: Register CLI subcommand**

In `vibelign/cli/cli_core_commands.py`, add this parser block after the existing `checkpoint` command registration:

```python
    p = sub.add_parser(
        "backup-db-viewer",
        help="백업 관리 DB 상태를 읽기 전용으로 확인해요",
        description=(
            "Rust 백업 관리 DB(.vibelign/vibelign.db)를 읽기 전용으로 요약해요.\n"
            "Raw SQL 실행이나 DB 편집은 지원하지 않아요."
        ),
        epilog=(
            "이렇게 쓰세요:\n"
            "  vib backup-db-viewer --json\n"
            "  vib backup-db-viewer --root /path/to/project --json"
        ),
    )
    _ = p.add_argument("--root", default=".", help="확인할 프로젝트 루트")
    _ = p.add_argument("--json", action="store_true", help="결과를 JSON으로 반환")
    p.set_defaults(
        func=lazy_command("vibelign.commands.vib_backup_db_viewer_cmd", "run_vib_backup_db_viewer")
    )
```

Do not add `--sql`, `--edit`, or arbitrary table-name arguments.

- [ ] **Step 5: Run CLI contract tests**

Run:

```bash
uv run pytest tests/test_gui_cli_contracts.py -q
```

Expected: PASS.

---

## Task 5: TypeScript wrapper and model helpers

**Files:**

- Modify: `vibelign-gui/src/lib/vib.ts`
- Create: `vibelign-gui/src/components/backup-dashboard/backupDbModel.ts`

- [ ] **Step 1: Add typed viewer result to `vib.ts`**

Add interfaces without weakening types:

```ts
export interface BackupDbViewerCheckpointRow {
  checkpointId: string;
  displayName: string;
  createdAt: string;
  pinned: boolean;
  trigger?: string | null;
  triggerLabel: string;
  gitCommitSha?: string | null;
  gitCommitMessage?: string | null;
  fileCount: number;
  totalSizeBytes: number;
  originalSizeBytes: number;
  storedSizeBytes: number;
  reusedFileCount: number;
  changedFileCount: number;
  engineVersion?: string | null;
  parentCheckpointId?: string | null;
  internalBadges: string[];
}

export interface BackupDbViewerInspectResult {
  dbExists: boolean;
  dbPath: string;
  schemaVersion?: string | null;
  checkpointCount: number;
  rustV2Count: number;
  legacyCount: number;
  casObjectCount: number;
  casRefCount: number;
  totalOriginalSizeBytes: number;
  totalStoredSizeBytes: number;
  autoBackupOnCommit: boolean;
  retentionPolicy?: {
    keepLatest: number;
    keepDailyDays: number;
    keepWeeklyWeeks: number;
    maxTotalSizeBytes: number;
    maxAgeDays: number;
    minKeep: number;
  } | null;
  objectStore: {
    exists: boolean;
    path: string;
    compressionSummary: Array<{
      compression: string;
      objectCount: number;
    }>;
    storedSizeBytes: number;
    originalSizeBytes: number;
  };
  checkpoints: BackupDbViewerCheckpointRow[];
  warnings: string[];
}
```

- [ ] **Step 2: Add snake_case to camelCase parser**

Add raw response interfaces and parser helpers near the existing `RawCheckpointEntry` block in `vib.ts`:

```ts
interface RawBackupDbViewerCheckpointRow {
  checkpoint_id?: string | null;
  display_name?: string | null;
  created_at?: string | null;
  pinned?: boolean | number | null;
  trigger?: string | null;
  trigger_label?: string | null;
  git_commit_sha?: string | null;
  git_commit_message?: string | null;
  file_count?: number | null;
  total_size_bytes?: number | null;
  original_size_bytes?: number | null;
  stored_size_bytes?: number | null;
  reused_file_count?: number | null;
  changed_file_count?: number | null;
  engine_version?: string | null;
  parent_checkpoint_id?: string | null;
  internal_badges?: string[] | null;
}

interface RawBackupDbViewerInspectResult {
  ok?: boolean;
  error?: string;
  db_exists?: boolean;
  db_path?: string | null;
  schema_version?: string | null;
  checkpoint_count?: number | null;
  rust_v2_count?: number | null;
  legacy_count?: number | null;
  cas_object_count?: number | null;
  cas_ref_count?: number | null;
  total_original_size_bytes?: number | null;
  total_stored_size_bytes?: number | null;
  auto_backup_on_commit?: boolean;
  retention_policy?: RawBackupDbViewerRetentionPolicy | null;
  object_store?: RawBackupDbViewerObjectStore | null;
  checkpoints?: RawBackupDbViewerCheckpointRow[] | null;
  warnings?: string[] | null;
}

interface RawBackupDbViewerRetentionPolicy {
  keep_latest?: number | null;
  keep_daily_days?: number | null;
  keep_weekly_weeks?: number | null;
  max_total_size_bytes?: number | null;
  max_age_days?: number | null;
  min_keep?: number | null;
}

interface RawBackupDbViewerCompressionSummary {
  compression?: string | null;
  object_count?: number | null;
}

interface RawBackupDbViewerObjectStore {
  exists?: boolean;
  path?: string | null;
  compression_summary?: RawBackupDbViewerCompressionSummary[] | null;
  stored_size_bytes?: number | null;
  original_size_bytes?: number | null;
}

function readNumber(value: number | null | undefined): number {
  return typeof value === "number" ? value : 0;
}

function normalizeRetentionPolicy(raw?: RawBackupDbViewerRetentionPolicy | null): BackupDbViewerInspectResult["retentionPolicy"] {
  if (!raw) return null;
  return {
    keepLatest: readNumber(raw.keep_latest),
    keepDailyDays: readNumber(raw.keep_daily_days),
    keepWeeklyWeeks: readNumber(raw.keep_weekly_weeks),
    maxTotalSizeBytes: readNumber(raw.max_total_size_bytes),
    maxAgeDays: readNumber(raw.max_age_days),
    minKeep: readNumber(raw.min_keep),
  };
}

function normalizeObjectStore(raw?: RawBackupDbViewerObjectStore | null): BackupDbViewerInspectResult["objectStore"] {
  return {
    exists: raw?.exists === true,
    path: raw?.path ?? "",
    compressionSummary: (raw?.compression_summary ?? []).map((item) => ({
      compression: item.compression ?? "unknown",
      objectCount: readNumber(item.object_count),
    })),
    storedSizeBytes: readNumber(raw?.stored_size_bytes),
    originalSizeBytes: readNumber(raw?.original_size_bytes),
  };
}

function normalizeBackupDbViewerRow(raw: RawBackupDbViewerCheckpointRow): BackupDbViewerCheckpointRow {
  return {
    checkpointId: raw.checkpoint_id ?? "",
    displayName: raw.display_name ?? "메모 없는 저장본",
    createdAt: raw.created_at ?? "",
    pinned: raw.pinned === true || raw.pinned === 1,
    trigger: raw.trigger ?? null,
    triggerLabel: raw.trigger_label ?? "수동 백업",
    gitCommitSha: raw.git_commit_sha ?? null,
    gitCommitMessage: raw.git_commit_message ?? null,
    fileCount: readNumber(raw.file_count),
    totalSizeBytes: readNumber(raw.total_size_bytes),
    originalSizeBytes: readNumber(raw.original_size_bytes),
    storedSizeBytes: readNumber(raw.stored_size_bytes),
    reusedFileCount: readNumber(raw.reused_file_count),
    changedFileCount: readNumber(raw.changed_file_count),
    engineVersion: raw.engine_version ?? null,
    parentCheckpointId: raw.parent_checkpoint_id ?? null,
    internalBadges: Array.isArray(raw.internal_badges) ? raw.internal_badges : [],
  };
}

function parseBackupDbViewerInspectResult(raw: RawBackupDbViewerInspectResult): BackupDbViewerInspectResult {
  if (raw.ok === false) throw new Error(raw.error ?? "Backup DB Viewer 실패");
  return {
    dbExists: raw.db_exists === true,
    dbPath: raw.db_path ?? "",
    schemaVersion: raw.schema_version ?? null,
    checkpointCount: readNumber(raw.checkpoint_count),
    rustV2Count: readNumber(raw.rust_v2_count),
    legacyCount: readNumber(raw.legacy_count),
    casObjectCount: readNumber(raw.cas_object_count),
    casRefCount: readNumber(raw.cas_ref_count),
    totalOriginalSizeBytes: readNumber(raw.total_original_size_bytes),
    totalStoredSizeBytes: readNumber(raw.total_stored_size_bytes),
    autoBackupOnCommit: raw.auto_backup_on_commit === true,
    retentionPolicy: normalizeRetentionPolicy(raw.retention_policy),
    objectStore: normalizeObjectStore(raw.object_store),
    checkpoints: (raw.checkpoints ?? []).map(normalizeBackupDbViewerRow),
    warnings: raw.warnings ?? [],
  };
}
```

- [ ] **Step 3: Add wrapper function**

Add:

```ts
export async function backupDbViewerInspect(cwd: string): Promise<BackupDbViewerInspectResult> {
  const res = await runVib(["backup-db-viewer", "--json"], cwd);
  if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
  const parsed = JSON.parse(res.stdout) as RawBackupDbViewerInspectResult;
  return parseBackupDbViewerInspectResult(parsed);
}
```

This uses the existing `runVib(args, cwd)` signature so Tauri sets both `cwd` and `VIBELIGN_PROJECT_ROOT` consistently.

- [ ] **Step 4: Add UI model helpers**

Create `backupDbModel.ts` with pure helpers:

```ts
import type { BackupDbViewerCheckpointRow, BackupDbViewerInspectResult } from '../../lib/vib';

export function filterBackupDbRows(rows: BackupDbViewerCheckpointRow[], query: string): BackupDbViewerCheckpointRow[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return rows;
  return rows.filter((row) => [
    row.displayName,
    row.checkpointId,
    row.triggerLabel,
    row.gitCommitSha ?? '',
    row.gitCommitMessage ?? '',
  ].some((value) => value.toLowerCase().includes(normalized)));
}

export function storageEfficiencyPercent(report: BackupDbViewerInspectResult): number {
  if (report.totalOriginalSizeBytes <= 0) return 0;
  const saved = report.totalOriginalSizeBytes - report.totalStoredSizeBytes;
  return Math.max(0, Math.round((saved / report.totalOriginalSizeBytes) * 100));
}
```

- [ ] **Step 5: Run TypeScript check**

Run:

```bash
npm --prefix vibelign-gui run build
```

Expected: PASS or fail only on pre-existing unrelated issues. Fix type errors caused by this task before continuing.

There is no current React unit-test runner in `vibelign-gui/package.json`. Do not claim automated component behavior coverage unless this plan is extended to add a frontend test runner. For the first implementation, GUI verification is TypeScript/Vite build plus the manual smoke check in Task 7.

---

## Task 6: Readable React child view

**Files:**

- Modify: `vibelign-gui/src/pages/BackupDashboard.tsx`
- Modify: `vibelign-gui/src/components/backup-dashboard/BackupDashboard.tsx`
- Create: `vibelign-gui/src/components/backup-dashboard/BackupDbViewer.tsx`
- Create: `vibelign-gui/src/components/backup-dashboard/BackupDbSummaryCards.tsx`
- Create: `vibelign-gui/src/components/backup-dashboard/BackupDbRowList.tsx`
- Create: `vibelign-gui/src/components/backup-dashboard/BackupDbDetailPanel.tsx`

- [ ] **Step 1: Add child-view state in the page shell**

In `vibelign-gui/src/pages/BackupDashboard.tsx`, add this state next to the existing backup page state:

```ts
const [activeChildView, setActiveChildView] = useState<'list' | 'db-viewer'>('list');
```

Pass `activeChildView` and `onActiveChildViewChange` to `BackupDashboardView`.

- [ ] **Step 2: Add tabs without replacing the existing backup dashboard**

In `BackupDashboard.tsx`, render two small `.nav-tab`/button controls at the top of the BACKUPS content:

```tsx
<div className="nav-tabs" aria-label="Backup child views">
  <button className={activeChildView === 'list' ? 'nav-tab active' : 'nav-tab'} onClick={() => onActiveChildViewChange('list')}>백업 목록</button>
  <button className={activeChildView === 'db-viewer' ? 'nav-tab active' : 'nav-tab'} onClick={() => onActiveChildViewChange('db-viewer')}>Backup DB Viewer</button>
</div>
```

When `activeChildView === 'list'`, render the existing dashboard exactly as before. When `db-viewer`, render `BackupDbViewer`.

- [ ] **Step 3: Implement `BackupDbViewer.tsx` container**

The container loads `backupDbViewerInspect`, keeps last successful data during refresh errors, and renders:

- Read-only notice alert.
- `BackupDbSummaryCards`.
- Search input + `BackupDbRowList`.
- `BackupDbDetailPanel` for selected row.
- Error/empty states in Korean.

- [ ] **Step 4: Implement summary cards**

`BackupDbSummaryCards.tsx` renders feature-card/card blocks for:

- 전체 백업 수.
- Rust v2 백업 수.
- Object 수.
- 원본 대비 저장 효율.
- 자동 백업 상태.

Use `.feature-card`, `.badge`, and the existing exported `formatBytes` from `vibelign-gui/src/components/backup-dashboard/model.ts`.

- [ ] **Step 5: Implement searchable row list**

`BackupDbRowList.tsx` renders button rows, not a raw table. Each row shows:

- `displayName`.
- `createdAt`.
- `triggerLabel`.
- `fileCount`.
- `storedSizeBytes`.
- badges from `internalBadges`.

- [ ] **Step 6: Implement detail panel with progressive disclosure**

`BackupDbDetailPanel.tsx` shows primary info first and internal values in `<details>`:

Primary:

- 표시 이름.
- 생성 시간.
- 만들어진 이유.
- git commit summary.
- 파일 수.
- 변경/재사용 파일 수.
- 원본 크기 / 실제 저장 크기.

Advanced `<details>`:

- 저장본 ID.
- parent ID.
- engine version.
- schema/debug info supplied by the selected row.

Do not add form inputs, editable textareas, or save buttons.

- [ ] **Step 7: Run GUI build**

Run:

```bash
npm --prefix vibelign-gui run build
```

Expected: PASS.

---

## Task 7: End-to-end verification and safety checks

**Files:**

- Test-only changes if needed: `tests/test_gui_cli_contracts.py`, `tests/test_checkpoint_rust_engine.py`
- No new feature files unless verification exposes a direct bug.

- [ ] **Step 1: Run Rust verification**

Run:

```bash
rtk cargo test --manifest-path vibelign-core/Cargo.toml
```

Expected: PASS.

- [ ] **Step 2: Run Python verification**

Run:

```bash
uv run pytest tests/test_checkpoint_rust_engine.py tests/test_checkpoint_engine_router.py tests/test_gui_cli_contracts.py -q
```

Expected: PASS.

- [ ] **Step 3: Run GUI verification**

Run:

```bash
npm --prefix vibelign-gui run build
```

Expected: PASS.

- [ ] **Step 4: Manual smoke check in GUI**

Run the desktop app in the existing dev flow and verify:

- BACKUPS still opens the original backup list by default.
- `Backup DB Viewer` child tab opens without replacing the original list.
- Missing DB shows “아직 Rust 백업 DB가 없어요. 백업을 먼저 만들어 주세요.”
- Existing DB shows summary cards and a searchable row list.
- Selecting a row updates the detail panel.
- No visible raw SQL input, edit button, save button, or dense raw DB grid exists.

- [ ] **Step 5: Git diff review**

Run:

```bash
rtk git diff -- vibelign-core/src/backup/db_viewer.rs vibelign-core/src/backup/mod.rs vibelign-core/src/ipc/protocol.rs vibelign/core/checkpoint_engine/requests.py vibelign/core/checkpoint_engine/responses.py vibelign/core/checkpoint_engine/rust_engine.py vibelign/core/checkpoint_engine/contracts.py vibelign/core/checkpoint_engine/rust_checkpoint_engine.py vibelign/core/checkpoint_engine/python_engine.py vibelign/core/checkpoint_engine/router.py vibelign/commands/vib_backup_db_viewer_cmd.py vibelign/cli/cli_core_commands.py vibelign-gui/src/lib/vib.ts vibelign-gui/src/pages/BackupDashboard.tsx vibelign-gui/src/components/backup-dashboard
```

Expected: diff contains only Backup DB Viewer feature work.

---

## Spec coverage checklist

- BACKUPS child menu: Task 6.
- Existing backup screen preserved: Task 6, Step 2 and Task 7 smoke check.
- Read-only DB inspect: Tasks 1–4.
- No raw SQL: constraints, Task 2, Task 4, Task 7 smoke check.
- React does not open DB directly: Tasks 3–5.
- Summary cards/searchable rows/detail panel readability: Tasks 5–6.
- Object store summary: Task 1 and Task 6.
- Retention policy summary: Task 1 and Task 6.
- Missing DB / Rust unavailable errors: Tasks 1, 4, 7.
- No edit controls: Task 6 and Task 7 smoke check.
