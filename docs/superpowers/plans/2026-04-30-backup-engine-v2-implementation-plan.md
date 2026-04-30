# Backup Engine v2 Implementation Plan

> **For agentic workers:** implement this plan task-by-task. Use checkbox (`- [ ]`) tracking. Do not collapse phases into one large change. The source design is `docs/superpowers/specs/2026-04-30-backup-engine-v2-design.md`.

## Goal

Turn the Rust/SQLite backup engine into a fast, storage-efficient, safe backup system with a beginner-friendly `BACKUPS` dashboard.

The finished system must support:

- CAS-backed file storage.
- Incremental backups.
- Streaming and deterministic snapshots.
- Full restore and selected-file restore.
- Restore preview and restore file suggestions.
- Commit-triggered automatic backups.
- Automatic cleanup policy for growing backup data.
- Mac and Windows edge-case safety.
- 0 byte file correctness.
- A full-screen `BACKUPS` dashboard that absorbs the old `Checkpoints` entry point.

## Non-negotiable constraints

- Do not put everything into one file.
- Keep `vibelign-core/src/backup/checkpoint.rs` as a thin compatibility/wiring layer.
- Keep `vibelign-gui/src/pages/BackupDashboard.tsx` as a page shell only.
- Do not put all GUI logic into `vibelign-gui/src/lib/vib.ts`.
- Do not put tests into one giant integration file.
- Do not expose internal terms such as `SHA`, `hash`, `trigger`, `checkpoint`, `diff`, `preview`, or `ledger` in user-facing Korean copy.
- Preserve existing `vib checkpoint`, `vib history`, and `vib undo` behavior. `vib undo` in v2 internally calls safe full restore against the latest v2 checkpoint; legacy-only DBs fall back to the v1 restore path.
- Do not rewrite the whole engine to async/Tokio in this work.
- Do not import legacy JSON backups in v2 MVP.
- Every new Rust/Python source file must include `=== ANCHOR: <NAME>_START ===` / `=== ANCHOR: <NAME>_END ===` boundaries so `vib guard --strict` keeps passing.
- Engine version discriminator is `checkpoints.engine_version` only; do not branch restore behavior on `object_hash IS NULL`.
- Do not introduce a Rust `commit_auto_backup.rs` module. Pass `trigger`, `git_commit_sha`, `git_commit_message` through the existing `CheckpointCreate` request payload.
- Design every new boundary for extension: local CAS is the only v2 MVP backend, but `create.rs`, `restore/*`, `retention.rs`, Python bridge helpers, and GUI panels must not assume cloud sync, encryption, or remote storage can never exist.

Release split:

- Engine MVP = Phases 1–7. Ship to CLI/MCP first.
- Dashboard MVP = Phases 8–9. Ship after Engine MVP is stable.

## Target module structure

Rust:

```text
vibelign-core/src/backup/
├─ mod.rs
├─ cas.rs
├─ snapshot.rs
├─ checkpoint.rs
├─ create.rs
├─ restore/
│  ├─ mod.rs
│  ├─ full.rs
│  ├─ files.rs
│  └─ preview.rs
├─ diff.rs
├─ stats.rs
├─ suggestions.rs
└─ retention.rs
```

> Rust 쪽에 `commit_auto_backup.rs`는 두지 않는다. trigger / git metadata는 `CheckpointCreate` request payload로 받아 `create.rs`가 그대로 row에 기록한다. post-commit 자동 백업의 트리거/dedupe/no-changes 처리는 모두 Python `auto_backup.py`가 담당한다.

Extension seams to preserve:

- `cas.rs` exposes object operations; other modules must not hard-code `.vibelign/rust_objects/` layout except through CAS helpers.
- `create.rs` accepts backup metadata through request payloads, not through separate code paths for manual, post-commit, scheduled, or future remote-triggered backups.
- `restore/*` resolves object content through CAS APIs so future remote/encrypted objects can slot in behind the same contract.
- `retention.rs` returns cleanup plans and calls CAS/object deletion APIs; it must not directly encode backend-specific delete behavior.
- `ipc/protocol.rs` changes are additive only. New fields may be optional; existing field names and meanings must remain stable.
- GUI additions use new `components/backup-dashboard/*` panels instead of expanding `BackupDashboard.tsx` or `vib.ts`.

Python bridge:

```text
vibelign/core/checkpoint_engine/
├─ rust_engine.py
├─ requests.py
├─ responses.py
└─ auto_backup.py
```

GUI:

```text
vibelign-gui/src/pages/
└─ BackupDashboard.tsx

vibelign-gui/src/components/backup-dashboard/
├─ SafetySummary.tsx
├─ StorageSavings.tsx
├─ DateGraph.tsx
├─ BackupFlow.tsx
├─ RestoreSuggestions.tsx
├─ FileHistoryTable.tsx
├─ RestorePreviewPanel.tsx
└─ CleanupInsight.tsx
```

## Phase order

1. Schema and compatibility foundation.
2. CAS storage.
3. Snapshot and incremental backup creation.
4. Restore, diff, preview, and file suggestions.
5. Retention and cleanup policy.
6. Commit-triggered automatic backup.
7. Python bridge and CLI/MCP integration.
8. GUI `BACKUPS` dashboard.
9. Cross-platform and release verification.

Each phase must be independently reviewable and revertible.

---

## Phase 1: Schema and compatibility foundation

**Purpose:** Add the database columns and protocol shapes needed by v2 without breaking v1 restore paths.

**Files:**

- Modify: `vibelign-core/src/db/schema.rs`
- Modify: `vibelign-core/src/ipc/protocol.rs`
- Modify: `vibelign-core/src/backup/mod.rs`
- Modify: `vibelign-core/src/backup/checkpoint.rs` only for wiring/compatibility
- Add tests near existing Rust DB/backup tests

- [ ] Add an idempotent migration runner gated by `db_meta.schema_version`. `apply_migrations(conn, target=2)` reads the current version, applies the v2 ALTERs only when needed, and writes `schema_version='2'`. Calling it twice on the same DB must not raise `duplicate column`.
- [ ] In the v2 migration step, add columns:
  - `checkpoint_files.object_hash`
  - `checkpoints.engine_version`
  - `checkpoints.parent_checkpoint_id`
  - `checkpoints.original_size_bytes`
  - `checkpoints.stored_size_bytes`
  - `checkpoints.reused_file_count`
  - `checkpoints.changed_file_count`
  - `checkpoints.trigger`
  - `checkpoints.git_commit_sha`
  - `checkpoints.git_commit_message`
- [ ] In the v2 migration step, update `retention_policy` defaults: `min_keep = 20`, `max_total_size_bytes = 1073741824` (1 GiB). Existing user-edited values must not be overwritten — only rows still at the old defaults are migrated.
- [ ] Treat `checkpoints.engine_version` as the **single** version discriminator. v1 rows have `engine_version IS NULL` and continue to use the legacy restore path. The legacy path must not branch on `object_hash`.
- [ ] v2 rows must store `checkpoint_files.storage_path = 'cas:<full_hash>'` (sentinel) so legacy `''`/real-path values stay distinguishable.
- [ ] Add optional future-extension columns only if cheap and nullable (`cas_objects.backend DEFAULT 'local'`, `cas_objects.object_uri`, or equivalent). If deferred, document the exact migration path in a schema comment/test fixture so remote/encrypted backends can be added without rewriting checkpoint rows.
- [ ] Add `db_meta` row `auto_backup_on_commit` (`'1' | '0'`) for the post-commit toggle. Default `'1'` when `vib start` runs inside a Git repo, else `'0'`.
- [ ] Extend the existing `CheckpointCreate` request shape with optional `trigger`, `git_commit_sha`, `git_commit_message` fields. Do **not** add the diff / preview / suggestions / cleanup IPC commands in this phase — each later phase defines its own IPC request/response struct alongside its implementation.
- [ ] Keep existing `CheckpointCreate` and restore response fields stable (additive only).
- [ ] Extend `vibelign/commands/vib_start_cmd.py:_ensure_gitignore_entry` to add `.vibelign/rust_checkpoints/` and `.vibelign/rust_objects/` alongside the existing `.vibelign/checkpoints/` line. Idempotent — only append the lines that are missing. Existing `vib start` users must pick this up on the next run.
- [ ] Update `vibelign/core/local_checkpoints.RetentionPolicy` dataclass defaults so `min_keep = 20` and `max_total_size_bytes = 1073741824`. The dataclass and the `retention_policy` SQL row must agree; `prune_checkpoints(root, DEFAULT_RETENTION_POLICY)` callers must not pick up pre-v2 numbers.
- [ ] In the same migration step, NFC-normalize `relative_path` on legacy v1 rows: `UPDATE checkpoint_files SET relative_path = nfc(relative_path) WHERE checkpoint_id IN (legacy_ids)`. If two NFC outputs collide inside the same checkpoint, abort the migration with a clear user-facing error rather than silently dropping rows.
- [ ] Add a doctor check (or `vib doctor` subroutine) that warns when project root sits under iCloud Drive (`~/Library/Mobile Documents/`), an SMB/NFS mount (`/Volumes/`), or a UNC path. Do not auto-disable; emit a single advisory line.
- [ ] Add tests for migration idempotency (run `apply_migrations` twice, confirm schema and defaults), legacy `engine_version IS NULL` row preservation, v2 sentinel write/read, NFC backfill, and `.gitignore` idempotent insert.

**Verification:**

```bash
cargo test --manifest-path vibelign-core/Cargo.toml
python -m pytest tests/test_checkpoint_cmd_wrapper.py tests/test_mcp_checkpoint_handlers.py -q
```

**Exit criteria:**

- Old backup rows still restore.
- New columns exist with safe defaults.
- Existing Python/CLI checkpoint tests pass unchanged or with additive assertions only.

---

## Phase 2: CAS storage

**Purpose:** Store identical file contents once and make object lifecycle safe.

**Files:**

- Modify: `vibelign-core/src/backup/cas.rs`
- Modify: `vibelign-core/src/backup/mod.rs`
- Add focused Rust tests for CAS behavior

- [ ] Implement object path layout: `.vibelign/rust_objects/blake3/ab/cd/<full_hash>`.
- [ ] Keep object path layout private to `cas.rs`; callers receive resolved paths or object handles, not shard paths.
- [ ] Implement `store_object`, `resolve_object`, `increment_ref`, `decrement_ref`, and `prune_unreferenced`.
- [ ] Use atomic write flow: tempfile + rename. If rename fails because the destination exists, treat as success (concurrent storer won the race) and skip fs write.
- [ ] On insert race, use `INSERT INTO cas_objects ... ON CONFLICT(hash) DO UPDATE SET ref_count = ref_count + 1`. Never decrement below zero (add `CHECK(ref_count >= 0)` if SQLite version supports it, otherwise a debug assertion).
- [ ] Prevent path traversal and symlink escape.
- [ ] Treat 0 byte files as real files:
  - Store BLAKE3 empty input hash.
  - Persist `size = 0` row.
  - Restore as an actual empty file.
- [ ] Keep `size == 0`, empty content, empty path, and missing file as different states.
- [ ] Cross-platform smoke (one test each): Windows-style `\\` relative path stored as canonical `/` form; macOS NFC vs NFD filename input collapses to one CAS row.

**Verification:**

```bash
cargo test --manifest-path vibelign-core/Cargo.toml backup::cas
```

**Exit criteria:**

- Identical content stores one object.
- Ref counts increment and decrement correctly.
- 0 byte files store and restore correctly.
- Unreferenced objects prune only when `ref_count == 0`.

---

## Phase 3: Snapshot and incremental backup creation

**Purpose:** Build deterministic file snapshots and create backups that reuse unchanged CAS objects.

**Files:**

- Modify: `vibelign-core/src/backup/snapshot.rs`
- Add: `vibelign-core/src/backup/create.rs`
- Modify: `vibelign-core/src/backup/checkpoint.rs` as a thin delegator
- Modify: `vibelign-core/Cargo.toml` only if a small parallelism dependency is required
- Add focused Rust tests for snapshot and create planner behavior

- [ ] Replace whole-file memory reads for hashing with buffered streaming hash.
- [ ] Add bounded parallel hashing using `rayon` or a small standard-thread approach.
- [ ] Sort results by normalized `relative_path` before DB writes and IPC output.
- [ ] Exclude `.git`, `.vibelign/vibelign.db`, `.vibelign/rust_checkpoints/`, and `.vibelign/rust_objects/`.
- [ ] Implement incremental planner using `relative_path + hash + size`.
- [ ] Store changed/new files in CAS and reuse unchanged objects.
- [ ] Record `original_size_bytes`, `stored_size_bytes`, `reused_file_count`, and `changed_file_count`.
- [ ] Preserve `no_changes` behavior without making it slower.
- [ ] Handle race cases where a file is deleted or changed during snapshot by returning a clear internal warning/failure state.

**Verification:**

```bash
cargo test --manifest-path vibelign-core/Cargo.toml backup::snapshot
cargo test --manifest-path vibelign-core/Cargo.toml backup::create
```

**Exit criteria:**

- Large files are not read fully into memory.
- Parallel output is deterministic.
- Unchanged files reuse object hashes.
- 0 byte unchanged files are reused, not skipped.
- Performance target on the benchmark fixture (10k files / ≈500 MB):
  - Cold create: at least 30% faster than the v1 whole-file-read baseline.
  - Warm create (`no_changes`): within ±5% of v1 baseline.
  - The benchmark harness lives next to existing `tests/test_bench_*` fixtures; record numbers in `tests/benchmark/patch_accuracy_baseline.json`-style snapshot.

---

## Phase 4: Restore, diff, preview, and file suggestions

**Purpose:** Let users see what will change before restore and restore selected files safely.

**Files:**

- Add: `vibelign-core/src/backup/restore/mod.rs`
- Add: `vibelign-core/src/backup/restore/full.rs`
- Add: `vibelign-core/src/backup/restore/files.rs`
- Add: `vibelign-core/src/backup/restore/preview.rs`
- Add: `vibelign-core/src/backup/diff.rs`
- Add: `vibelign-core/src/backup/suggestions.rs`
- Modify: `vibelign-core/src/ipc/protocol.rs`
- Modify: `vibelign-core/src/backup/checkpoint.rs` only to call new modules

- [ ] Implement v1/v2 dual restore path.
- [ ] Implement full restore from CAS.
- [ ] Implement selected-file restore.
- [ ] Implement restore preview that never writes files.
- [ ] Implement selected-file restore preview that includes only selected files.
- [ ] Implement checkpoint-to-checkpoint diff with `added`, `modified`, `deleted`, and `unchanged` classification.
- [ ] Implement restore suggestions for recently changed, missing, and high-change files.
- [ ] Ensure diff distinguishes:
  - Empty file added.
  - Empty file restored.
  - Non-empty file changed to empty.
  - Deleted file.
- [ ] Ensure all restore writes validate normalized paths against project root immediately before writing.
- [ ] Implement suggestion algorithm per design §5: cap = 5 (configurable 3–10), priority order `missing_now > recently_changed (≤30 min) > high_change > changed_on_date`, stable secondary sort by `relative_path`. For legacy v1 checkpoints (no parent / no diff context), return empty `suggestions` plus a `legacy_notice` string.
- [ ] Cross-platform smoke (one test each): Windows backslash `relative_paths` input refuses path traversal during selected-file restore; long-path canonical write succeeds on macOS via `PathBuf` round-trip.

**Verification:**

```bash
cargo test --manifest-path vibelign-core/Cargo.toml backup::restore
cargo test --manifest-path vibelign-core/Cargo.toml backup::diff
cargo test --manifest-path vibelign-core/Cargo.toml backup::suggestions
```

**Exit criteria:**

- Preview changes no files.
- Selected-file restore changes only selected files.
- Restore suggestions include plain-language reason codes for the GUI/Python layer to translate.
- Legacy rows still restore.

---

## Phase 5: Retention and cleanup policy

**Purpose:** Prevent backup data from growing forever while preserving important restore points.

**Files:**

- Modify: `vibelign-core/src/backup/retention.rs`
- Modify: `vibelign-core/src/backup/cas.rs` for prune integration with `retention.rs`
- Modify: `vibelign-core/src/ipc/protocol.rs`
- Add focused retention tests

- [ ] Implement default policy:
  - Never auto-delete protected backups.
  - Always keep recent 20 backups.
  - Keep recent 7 days where possible.
  - Keep at least one daily representative for 30 days.
  - Keep at least one weekly representative for 12 weeks.
  - Keep at least one monthly representative for 12 months.
  - Prefer pruning unprotected automatic backups before user-created backups.
  - Start with 1GB project soft cap stored in `retention_policy.max_total_size_bytes`; later UI/config work may expose the value, but this phase hardcodes the default and DB storage.
- [ ] Implement planner before deletion.
- [ ] Keep retention decisions backend-agnostic: retention chooses checkpoint/object hashes to remove, while CAS/object layer performs local deletion now and can later perform remote deletion/sync cleanup.
- [ ] Return planned bytes vs actually reclaimed bytes separately.
- [ ] Protect safe-restore checkpoints inside their protected window.
- [ ] Do not delete a CAS object still referenced by any remaining backup.
- [ ] Run cleanup in two stages so a crash cannot leave `cas_objects.ref_count` drifted:
  1. **Single SQL transaction**: validate plan, then atomically `DELETE FROM checkpoint_files WHERE checkpoint_id IN (...)` → `UPDATE cas_objects SET ref_count = ref_count - n WHERE hash IN (...)` → `DELETE FROM checkpoints WHERE checkpoint_id IN (...)`. Commit.
  2. **Separate fs stage**: query `ref_count = 0` rows, unlink each object file, then `DELETE FROM cas_objects` for that hash. Failures here surface as `partial_failure` but DB is already consistent — the next cleanup retries the same hashes safely.
- [ ] Return `partial_failure` when object deletion fails; do not pretend cleanup fully succeeded.
- [ ] Check free disk before backup and before safe restore. If free disk is under 1GB, warn or abort safe restore.
- [ ] Add a free-disk-space crate dependency to `vibelign-core/Cargo.toml` (`fs2` or `sysinfo`). Standard library does not expose a portable free-bytes call — without this the disk-guard branch cannot ship.
- [ ] Raise SQLite `busy_timeout` to 15s for backup operations (cleanup transaction in particular). The current 5s default is fine for read paths but can be exceeded when `vib undo`/`vib checkpoint` collide with a running cleanup on slower disks.

**Verification:**

```bash
cargo test --manifest-path vibelign-core/Cargo.toml backup::retention
```

**Exit criteria:**

- Protected backups never prune.
- `min_keep` is respected.
- Auto backups prune before manual backups when all else is equal.
- Ref counts remain consistent after cleanup and partial failure tests.

---

## Phase 6: Commit-triggered automatic backup

**Purpose:** Create backups automatically after commit without blocking the user's Git workflow.

**Files:**

- Add: `vibelign/core/checkpoint_engine/auto_backup.py`
- Modify: `vibelign/core/git_hooks.py`
- Modify: `vibelign/cli/cli_command_groups.py`
- Add: `vibelign/commands/internal_post_commit_cmd.py` as the single combined post-commit entrypoint
- Modify: `vibelign/commands/internal_record_commit_cmd.py` only if shared helper extraction is needed for the combined entrypoint
- Add/modify: `tests/test_git_hooks_post_commit.py`

> No Rust `commit_auto_backup.rs` file. Phase 1 already added `trigger / git_commit_sha / git_commit_message` to the `CheckpointCreate` request, and Phase 3's `create.rs` writes them to the new columns. Python is the only orchestrator.

- [ ] Extend post-commit hook with an idempotent VibeLign block. Update the hook marker from `v1` to `v2` and add an upgrade path so that an installed `v1` block is rewritten to `v2` on the next `vib start` (the existing `_POST_COMMIT_MARKER` is a literal string match — use a regex that accepts both `v1` and `v2` for detection, then write `v2` content).
- [ ] Preserve any existing user hook content.
- [ ] Use a **single combined entrypoint** for the post-commit work, e.g. `_internal_post_commit "$sha"` that reads the commit message from stdin, writes the work_memory record, then performs the backup. Do not pipe stdin to two consecutive `vib _internal_*` commands — the second one would read an empty stdin. Inside the entrypoint, sequence the two operations so `work_memory.json` is written exactly once (no race on `recent_events[]`).
- [ ] Fix the python fallback chain in the hook script: try `python` → `py -3` → `python3` → fail silently. Windows default installs do not put `python3` on PATH; the existing hook is already broken on Windows and v2 inherits that bug if not corrected.
- [ ] Pass commit sha + message into `CheckpointCreate` payload as `trigger='post_commit'`, `git_commit_sha`, `git_commit_message`. Do **not** use `git_commit_message` as a dedupe key — Git Bash on Windows can rewrite line endings during the stdin pipe; dedupe must remain `matches_latest_snapshot()` only.
- [ ] Skip duplicate automatic backup when snapshot has no changes (Rust returns `no_changes`, Python treats it as success).
- [ ] Ensure hook failure never fails the already-completed commit. Wrap the entrypoint in a top-level `try/except: return`.
- [ ] Read/write `auto_backup_on_commit` from the `db_meta` row added in Phase 1. Default value `'1'` (enabled) for `vib start` inside a Git repo. Add the toggle to the existing `vib config` command (`vib config auto-backup on|off`); do **not** invent a new `vib settings` group.
- [ ] Raise the `rust_engine.py` subprocess timeout for backup-class commands (`checkpoint_create`, `checkpoint_restore_*`, `retention_apply`) from 30s to 90s. AV scanning on Windows + cold v2 backup on a 50k-file project routinely passes 30s; the auto-backup must not silently die at the timeout.
- [ ] Cross-platform smoke (one test each): post-commit hook block round-trips correctly on Windows line endings (CRLF preserved) and the python fallback chain finds `python` when `python3` is absent; macOS hook with executable bit unchanged after VibeLign block insert.

**Verification:**

```bash
python -m pytest tests/test_git_hooks.py tests/test_git_hooks_post_commit.py -q
cargo test --manifest-path vibelign-core/Cargo.toml backup::create
```

**Exit criteria:**

- Commit creates a non-fatal automatic backup.
- Duplicate snapshot creates no duplicate backup.
- Existing hook content is preserved.

---

## Phase 7: Python bridge, CLI, and MCP integration

**Purpose:** Expose the Rust engine additions through Python, CLI, and MCP without bloating existing wrappers.

**Files:**

- Modify: `vibelign/core/checkpoint_engine/rust_engine.py` as a thin compatibility wrapper
- Add: `vibelign/core/checkpoint_engine/requests.py`
- Add: `vibelign/core/checkpoint_engine/responses.py`
- Modify: `vibelign/mcp/mcp_checkpoint_handlers.py`
- Modify CLI command modules only where necessary
- Add/modify Python tests for bridge and MCP contracts

- [ ] Inventory check before edits. The package already contains `rust_engine.py`, `rust_checkpoint_engine.py`, `router.py`, `shadow_runner.py`, `python_engine.py`, `contracts.py`. Each file's responsibility after Phase 7 must be one of:
  - `contracts.py` → unchanged Protocol definitions.
  - `python_engine.py` → unchanged legacy Python implementation.
  - `rust_engine.py` → thin compatibility wrapper that delegates to `requests.py` + `responses.py`.
  - `rust_checkpoint_engine.py` → adapter that implements the `CheckpointEngine` Protocol on top of `rust_engine.py`.
  - `router.py` → unchanged routing logic between Python and Rust engines.
  - `shadow_runner.py` → unchanged shadow comparison harness.
  - `requests.py` (new) → request payload construction for every IPC command.
  - `responses.py` (new) → response parsing/validation for every IPC command.
  - `auto_backup.py` (new, from Phase 6) → post-commit auto backup orchestration.
  - Document this mapping in a short header comment in `__init__.py` so it does not drift.
- [ ] Move request payload construction into `requests.py`.
- [ ] Move response parsing and validation into `responses.py`.
- [ ] Add Python helpers for stats, diff, restore preview, selected-file restore preview, restore suggestions, and cleanup plan/apply.
- [ ] Keep Python bridge helpers one-command-per-request and response-shape stable so future sync/encryption commands can be added as new helpers without changing existing call sites.
- [ ] Keep existing CLI output compatible.
- [ ] Add optional saved/reused/storage-saved fields when available.
- [ ] Extend `vibelign/core/local_checkpoints.CheckpointSummary` with an optional `trigger: str | None = None` field and surface it through `router.list_checkpoints` / `rust_checkpoint_engine`. Update `vib_history_cmd._clean_msg` (and the duplicated copy in `vib_undo_cmd`) so messages from `trigger='post_commit'` rows are rendered as `"코드 저장 후 자동 백업"` plus a short suffix from the user's commit summary, never the raw `auto backup after commit abc1234 — ...` internal string. `trigger='safe_restore'` rows are filtered out of `vib history` and `vib undo` listings entirely (visible only in the GUI dashboard).
- [ ] Default the existing `vibelign/core/checkpoint_engine/shadow_runner.py` to **disabled** for v2 callers. Activate only when the env var `VIBELIGN_SHADOW_COMPARE=1` is set so it stays available for v1↔v2 parity debugging without paying the cost (extra `/tmp` snapshot + duplicate CAS write) on every commit. Do not delete the file.
- [ ] Use easy Korean copy in user-facing outputs.
- [ ] Do not expose internal Rust/DB terms directly.

**Verification:**

```bash
python -m pytest tests/test_checkpoint_cmd_wrapper.py tests/test_mcp_checkpoint_handlers.py tests/test_gui_cli_contracts.py -q
```

**Exit criteria:**

- Python can call every new Rust command.
- Existing checkpoint commands still work.
- MCP and GUI contracts use stable snake_case JSON.

---

## Phase 8: GUI `BACKUPS` dashboard

**Purpose:** Replace the small checkpoint-only experience with a full-screen beginner-friendly backup dashboard.

**Files:**

- Modify: `vibelign-gui/src/App.tsx`
- Add: `vibelign-gui/src/pages/BackupDashboard.tsx`
- Add directory: `vibelign-gui/src/components/backup-dashboard/`
- Add components:
  - `SafetySummary.tsx`
  - `StorageSavings.tsx`
  - `DateGraph.tsx`
  - `BackupFlow.tsx`
  - `RestoreSuggestions.tsx`
  - `FileHistoryTable.tsx`
  - `RestorePreviewPanel.tsx`
  - `CleanupInsight.tsx`
- Modify: `vibelign-gui/src/lib/vib.ts` only for thin API calls/types
- Remove the top-level user-facing route to `vibelign-gui/src/pages/Checkpoints.tsx`; reuse small list/timeline pieces inside `BackupDashboard.tsx` only after extracting them into `components/backup-dashboard/`

- [ ] Remove top-level `Checkpoints` nav tab.
- [ ] Add `BACKUPS` nav tab to the right of `DOCS VIEWER`.
- [ ] Make `BackupDashboard.tsx` assemble sections but not own heavy data shaping.
- [ ] Add safety state section.
- [ ] Add storage savings section.
- [ ] Add date graph/calendar graph section.
- [ ] Add backup flow section with automatic backup labels.
- [ ] Add restore suggestions before full file list.
- [ ] Add file history table with search.
- [ ] Add restore preview panel.
- [ ] Add cleanup insight panel showing policy, reclaimable space, protected count, and last cleanup result.
- [ ] Reserve dashboard extension points by keeping each section independent; future sync/encryption/cloud panels must be addable as sibling components, not modifications to every existing section.
- [ ] Ensure selected-file restore always says the equivalent of “other files stay as they are.”
- [ ] Use middle-school-level Korean for all user-facing backup copy.
- [ ] Add an automated banned-word lint covering every string under `vibelign-gui/src/components/backup-dashboard/` and `vibelign-gui/src/pages/BackupDashboard.tsx`. Banned tokens: `SHA`, `hash`, `해시`, `trigger`, `트리거`, `checkpoint`, `체크포인트`, `diff`, `디프`, `preview`, `프리뷰`, `ledger`, `레저`, `post_commit`, `commit-backed`. Wire the lint into `npm run lint` so Phase 8 verification fails fast on violations.

**Verification:**

```bash
npm run build --prefix vibelign-gui
npm run lint --prefix vibelign-gui
python -m pytest tests/test_gui_cli_contracts.py -q
```

**Exit criteria:**

- `BACKUPS` is the single user-facing backup entry point.
- No narrow home-card-only backup UX.
- Dashboard numbers match engine JSON fixtures.
- Internal terms are not shown in Korean UI copy.

---

## Phase 9: Cross-platform and release verification

**Purpose:** Prove the backup engine works on macOS and Windows before release.

**Files:**

- Add/modify Rust cross-platform backup tests
- Add/modify Python cross-platform tests near `tests/test_cross_platform_paths.py`
- Add CI workflow updates when CI config exists; if no CI config exists, add a release-check note documenting the exact macOS and Windows manual commands from this phase

- [ ] Add path normalization tests for `/` and `\\`.
- [ ] Add Windows drive-letter and UNC escape tests.
- [ ] Add macOS Unicode normalization tests.
- [ ] Add case-only rename tests.
- [ ] Add read-only, hidden, and executable-bit behavior tests.
- [ ] Add symlink, broken symlink, and Windows junction/reparse-point tests where platform support allows.
- [ ] Add locked-file behavior test for Windows.
- [ ] Add long-path behavior test. On Windows the restore/write paths must use the `\\?\` long-path prefix when the resolved path exceeds 240 chars, or fail fast with a user-safe message. Document the registry `LongPathsEnabled` toggle in release notes for users who can opt in system-wide.
- [ ] Add a "snapshot skipped[] propagation" test: a file held with an exclusive Windows lock during snapshot collection is reported in the `skipped[]` field rather than silently dropped, and the CLI/GUI surface a "1 file could not be read" notice.
- [ ] Add 0 byte transition tests:
  - Missing → 0 byte file.
  - 0 byte → non-empty.
  - Non-empty → 0 byte.
  - 0 byte → deleted.
- [ ] Add timezone/DST fixture for dashboard date grouping.
- [ ] Add SQLite interruption/transaction safety test by injecting a failure between SQL transaction commit and fs unlink in retention cleanup.
- [ ] Run macOS CI/test pass.
- [ ] Run Windows CI/test pass.

**Verification:**

```bash
cargo test --manifest-path vibelign-core/Cargo.toml
python -m pytest tests/test_cross_platform_paths.py tests/test_checkpoint_cmd_wrapper.py tests/test_mcp_checkpoint_handlers.py -q
npm run build --prefix vibelign-gui
```

**Exit criteria:**

- macOS and Windows test suites pass.
- File path, Unicode, 0 byte, locked file, symlink, and cleanup policy cases are covered.
- Release notes can truthfully say the backup engine handles Mac/Windows edge cases.

---

## Final acceptance checklist

- [ ] Existing `vib checkpoint`, `vib history`, and `vib undo` still work.
- [ ] New backups use CAS and show scanned/changed/reused/storage-saved numbers.
- [ ] 0 byte files are backed up, diffed, and restored correctly.
- [ ] Full restore and selected-file restore both support preview.
- [ ] Restore suggestions appear before the full file list.
- [ ] Commit-triggered automatic backup works and never blocks Git commit completion.
- [ ] Retention prevents unbounded growth while preserving protected/recent/representative backups.
- [ ] `BACKUPS` absorbs the old top-level `Checkpoints` entry.
- [ ] Dashboard copy avoids difficult internal terms.
- [ ] macOS and Windows verification passes.
- [ ] No phase leaves major logic concentrated in `checkpoint.rs`, `BackupDashboard.tsx`, `vib.ts`, or one giant test file.
- [ ] Future cloud sync, encryption, remote storage, and scheduled backup can be added through new modules/panels/optional fields without rewriting existing v2 checkpoint rows or bloating core wiring files.

---

## Review feedback applied (2026-04-30)

The plan was updated in-place to address the design review. Quick map:

| # | Issue | Fix location |
|---|---|---|
| 1 | No schema migration runner — re-running ALTERs would error out | Phase 1 — `apply_migrations(conn, target=2)` gated by `db_meta.schema_version` |
| 2 | Dual v1/v2 discriminator (`engine_version` vs `object_hash IS NULL`) | Non-negotiable constraints + Phase 1 — `checkpoints.engine_version` only |
| 3 | `commit_auto_backup.rs` had no real responsibility | Module structure + Phase 6 — Rust file removed; trigger metadata flows through `CheckpointCreate` payload |
| 4 | Default mismatches (`min_keep` 10 vs 20, `max_total_size_bytes` 2 GiB vs 1 GiB) | Phase 1 — v2 migration updates `retention_policy` defaults |
| 5 | Phase 1 IPC types pre-defined → forced rework | Phase 1 — only `CheckpointCreate` field additions; later phases own their own IPC |
| 6 | Existing 6 Python bridge files unmapped | Phase 7 — explicit responsibility table |
| 7 | Cleanup transaction order could drift `ref_count` on crash | Phase 5 — single SQL tx (rows + ref_count), separate fs unlink stage |
| 8 | Selected-file safety scope ambiguous | Design §6 + (already implicit in Phase 4/5) — safety checkpoint is always full project |
| 9 | v2 `storage_path` could collide with legacy NULL/empty | Phase 1 — `cas:<full_hash>` sentinel |
| 10 | Suggestions algorithm missing cap / sort / legacy fallback | Phase 4 — design §5 spec referenced |
| 11 | Cross-platform validation only at the end | Phases 2/4/6 — one platform smoke each, Phase 9 stays the comprehensive matrix |
| 12 | `auto_backup_on_commit` storage location undefined | Phase 1 + Phase 6 — `db_meta` row |

Additional reinforcements:

- CAS concurrency rule (`ON CONFLICT DO UPDATE`, idempotent rename) — Phase 2.
- Quantitative perf target (10k files, +30% cold, ±5% warm) — Phase 3.
- Banned-word lint for Korean UI copy — Phase 8.
- Anchor convention enforced for new source files — Non-negotiable constraints.
- `vib undo` semantics in v2 documented — Non-negotiable constraints.
- Engine MVP / Dashboard MVP release split — Non-negotiable constraints.

---

## Review feedback round 2 — VibeLign command surface & platform edges

| # | Issue | Fix location |
|---|---|---|
| B1 | `.vibelign/rust_objects/` would leak BLAKE3 blobs into git | Phase 1 — extend `_ensure_gitignore_entry` |
| B2 | Post-commit hook `python3` fallback unreachable on Windows | Phase 6 — fallback chain `python` → `py -3` → `python3` |
| B3 | stdin pipe shared between two `vib _internal_*` commands | Phase 6 — single combined `_internal_post_commit` entrypoint |
| B4 | The old settings-style auto-backup command does not exist | Phase 6 — reuse `vib config auto-backup on|off` |
| B5 | Free-disk-space crate missing | Phase 5 — add `fs2`/`sysinfo` dependency |
| C1 | `work_memory.json` race between record and backup | Phase 6 — single entrypoint serialises writes |
| C2 | Silent `vib undo` semantic change | Design §6 — safety checkpoint hidden from history/undo, advisory line on first use |
| C3 | `_clean_msg` exposes raw `auto backup after commit ...` | Phase 7 — extend `CheckpointSummary` with `trigger`, update `_clean_msg`, hide `safe_restore` rows from CLI |
| C4 | `RetentionPolicy` dataclass default not aligned with DB default | Phase 1 — also update dataclass defaults |
| C5 | `shadow_runner.py` blowing up disk on every commit | Phase 7 — default off, opt-in via `VIBELIGN_SHADOW_COMPARE=1` |
| C6 | SQLite busy_timeout 5s vs concurrent backup ops | Phase 5 — raise to 15s for backup operations |
| M1 | iCloud / SMB / NFS host of `.vibelign/vibelign.db` corrupts WAL | Phase 1 — doctor warning, no auto-disable |
| M2 | v1 NFD vs v2 NFC `relative_path` mismatch | Phase 1 — NFC backfill in migration, abort on collision |
| M3 | macOS case-only rename precedence undefined | Phase 9 — "last `WalkDir` stat wins" rule documented in tests |
| M4 | macOS SMB chmod silently fails | Existing `chmod-failed` status preserved; Phase 9 verifies no regression |
| W1 | Windows NTFS 260-char path limit | Phase 9 — `\\?\` prefix on resolved restore paths > 240 chars |
| W2 | Windows locked files silently skipped during snapshot | Design §1 — snapshot returns `skipped[]`; Phase 9 — propagation test |
| W3 | Non-ASCII cwd encoding | Existing `encoding="utf-8"` on `subprocess.run`; Phase 7 — apply to all new bridge calls |
| W4 | Windows AV scan exceeds 30s subprocess timeout | Phase 6 — backup-class timeout raised to 90s |
| W5 | `.exe.sha256` manifest distribution | Release notes only — no design change |
| W6 | Git Bash CRLF rewrites commit message bytes | Design §7 — message is metadata-only, not a dedupe key |
