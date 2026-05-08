# Error Reporting Implementation Plan

> **Status:** ready for Phase 1 / Phase 1.5 / Phase 2 implementation after policy review.
> **Source spec:** `docs/superpowers/specs/2026-05-06-error-reporting-policy-design.md`
> **Scope:** this plan covers spec Phase 1 (CLI core), Phase 1.5 (backup exclusion), Phase 2 (GUI capture). Spec Phase 3 (`vib report-bug`), Phase 4 (GUI bug report button), Phase 5 (doctor / manual integration) are **out of scope here** and tracked in a follow-up plan. Phase 3 acceptance items in spec §7 are intentionally deferred.
> **Release rule:** Phase 1 and Phase 1.5 may be separate PRs, but they must ship in the same release tag / PyPI package / GUI bundle.

**Goal:** implement local-first error reporting for VibeLign without weakening the privacy contract: CLI and GUI error payloads are redacted by the Python canonical writer before any JSONL write, logs stay local, and logs/reports never bloat checkpoint backups.

**Architecture in one line:** CLI and GUI both funnel error payloads through `vibelign/core/error_log.py` for canonical redaction and JSONL append; GUI only buffers in memory before async flushing to an internal CLI command; Rust backup snapshots exclude generated logs/reports.

**Tech Stack:** Python 3.10+, pytest, Rust/Tauri, React/TypeScript, Cargo tests.

---

## Non-Goals

- [ ] Remote error aggregation (Sentry/Bugsnag/PostHog)
- [ ] Usage telemetry
- [ ] User identifiers
- [ ] GUI dashboard for error statistics
- [ ] Direct GUI JSONL writes that bypass Python canonical redaction
- [ ] Public exposure of the internal GUI logging command

---

## Global Invariants

- [ ] Raw error payloads never touch disk before canonical redaction.
- [ ] Tier 1 has zero network calls in the error-reporting code paths.
- [ ] Logging is best-effort: reporter failure must not hide the original exception or freeze the GUI.
- [ ] `error_log.py` is the single source of truth for token-prefix/path/IP/internal-host redaction.
- [ ] Phase 1 and Phase 1.5 ship in the same release.
- [ ] `.vibelign/logs/` and `.vibelign/reports/` are gitignored and excluded from backup snapshots.
- [ ] JSONL truncation never creates invalid JSON; truncate field values before final serialization, not raw serialized bytes/lines.
- [ ] GUI errors without an active project root are silently dropped unless a future spec defines an app-global log location.
- [ ] Error logging is invisible to realtime watch: `.vibelign/logs/` and `.vibelign/reports/` writes must not trigger watch code-map refresh, watch work-memory events, or GUI watch log/error streams.
- [ ] Error reporter failures do not write to stderr/stdout in watch subprocess contexts; otherwise GUI watch treats stderr as `watch_error` and stops the watcher.

---

## Phase 1 — Python Core Error Logging MVP

**Purpose:** capture CLI unhandled exceptions into local JSONL with canonical redaction before disk.

### Files

**Create:**
- `vibelign/core/error_log.py`
- `vibelign/core/file_lock.py`
- `vibelign/core/config_loader.py`
- `tests/test_error_log.py`

**Modify:**
- `vibelign/cli/cli_runtime.py`
- `vibelign/commands/vib_start_cmd.py`
- `vibelign/__init__.py` (only if `__version__` fallback needs touching — read-only reference otherwise)
- `tests/test_vib_cli_runtime.py`

### Steps

- [ ] Add `vibelign/core/file_lock.py`.
  - POSIX: `fcntl.flock(fd, LOCK_EX)`.
  - Windows: `msvcrt.locking(fd, LK_LOCK, 1)` with a practical one-byte lock.
  - Timeout after 5 seconds; timeout means silent skip.

- [ ] Add `vibelign/core/config_loader.py`.
  - Read `.vibelign/config.yaml`.
  - Support nested `error_reporting.local_log`.
  - Default to `true` when missing/malformed.
  - Preserve existing top-level config behavior.
  - Do not add a YAML dependency unless this plan is explicitly revised; implement the minimal nested reader needed for this flag, matching the repository's current line-based config style.

- [ ] Add `vibelign/core/error_log.py`.
  - `record_cli_error(root, exc_info, argv)`.
  - `record_gui_error(root, payload)` interface reserved for Phase 2.
  - Canonical redaction = `redact_memory_text` + token-prefix hardening + Windows-broad path hardening (covers `_LOCAL_PATH_RE`, `_PRIVATE_IP_RE`, `_INTERNAL_HOST_RE` already in `redact_memory_text`).
  - Preserve traceback frame/line boundaries.
  - UTC timestamp and UTC file date.
  - JSONL append with UTF-8 + `json.dumps(..., ensure_ascii=False)` + `open(path, "a", encoding="utf-8", newline="")` (or `"ab"` binary append) — explicitly disable Windows `\n` → `\r\n` translation. Single source of writer in `error_log.py`.
  - 8KB line cap with `…[truncated]`.
  - Preserve valid JSONL under truncation: truncate oversized string fields before final `json.dumps`, then assert each emitted line is parseable JSON.
  - 1000-line per-file overflow via suffix files (`cli-error-YYYYMMDD-2.jsonl`).
  - Thread-local `_reporting_in_progress` recursion guard.
  - `vib_version` resolution chain: `importlib.metadata.version("vibelign")` first, then `vibelign.__version__`, finally `"unknown"` — single helper, no other call site duplicates this.
  - 30-day retention sweep on each write call: enumerate `cli-error-*.jsonl` / `gui-error-*.jsonl` (including `-N` suffix groups) older than 30 days by UTC file-date prefix and `os.unlink()` (hard delete, no archive). Sweep is best-effort: failure does not raise.

- [ ] Wire CLI exception capture in `vibelign/cli/cli_runtime.py`.
  - Stay inside `CLI_RUNTIME_RUN_CLI_START/END`.
  - Do not create new anchors.
  - Preserve original exception behavior / exit code.
  - If logging fails, continue original failure path.

- [ ] Update `vibelign/commands/vib_start_cmd.py` gitignore defaults.
  - Add `.vibelign/logs/`.
  - Add `.vibelign/reports/`.
  - Preserve existing entries.

### Tests

- [ ] `tests/test_error_log.py::test_record_cli_error_writes_jsonl`
- [ ] `tests/test_error_log.py::test_redacts_token_prefix_before_disk`
- [ ] `tests/test_error_log.py::test_redacts_windows_broad_paths`
- [ ] `tests/test_error_log.py::test_redacts_private_ip_before_disk`
- [ ] `tests/test_error_log.py::test_redacts_internal_host_before_disk`
- [ ] `tests/test_error_log.py::test_preserves_traceback_lines`
- [ ] `tests/test_error_log.py::test_korean_message_stays_utf8`
- [ ] `tests/test_error_log.py::test_long_line_truncates_at_8kb`
- [ ] `tests/test_error_log.py::test_utc_rotation_and_suffix_overflow`
- [ ] `tests/test_error_log.py::test_30day_retention_sweep_deletes_old_files`
- [ ] `tests/test_error_log.py::test_vib_version_fallback_chain`
- [ ] `tests/test_error_log.py::test_jsonl_no_crlf_translation_on_windows` (use `"\r\n" not in raw_bytes`-style assertion or `newline=""` invariant)
- [ ] `tests/test_error_log.py::test_atomic_append_under_concurrent_writers` (multi-process / multi-thread, validates Cross-Phase Matrix "Atomic append")
- [ ] `tests/test_error_log.py::test_config_local_log_false_disables_write`
- [ ] `tests/test_error_log.py::test_writer_failure_does_not_mask_original_exception`
- [ ] `tests/test_vib_cli_runtime.py` covers unhandled exception reporting path.
- [ ] `tests/test_watch_engine.py` covers `.vibelign/logs/*.jsonl` and `.vibelign/reports/*.md` as non-watchable paths, extending the existing `.vibelign/watch_state.json` skip coverage.

### Verification

```bash
pytest tests/test_error_log.py tests/test_vib_cli_runtime.py
```

### Phase 1 Exit Criteria

- [ ] CLI unhandled exception writes masked `cli-error-*.jsonl`.
- [ ] Raw token/path/IP/internal host never appears on disk.
- [ ] `error_reporting.local_log: false` disables writes.
- [ ] Logging failure does not alter the original CLI failure.
- [ ] Files older than 30 days (UTC) are deleted on next write call (hard delete, all suffix groups).
- [ ] `vib_version` field is populated via the documented fallback chain even when `importlib.metadata` lookup fails.
- [ ] Concurrent writers (CLI + MCP server + GUI flush subprocess) produce no torn JSONL lines.

---

## Phase 1.5 — Backup Exclusion Hardening

**Purpose:** prevent local logs/reports from bloating checkpoint backup DBs.

**Release gate:** Phase 1 and Phase 1.5 must publish together.

### Files

**Modify:**
- `vibelign-core/src/backup/snapshot.rs`

### Steps

- [ ] Add snapshot prefix exclusions for:
  - `.vibelign/logs/`
  - `.vibelign/reports/`

- [ ] Preserve existing allowed `.vibelign` files such as anchor/project metadata.

- [ ] Add Rust regression tests in the existing snapshot test module.

### Tests

- [ ] `.vibelign/logs/cli-error-X.jsonl` is excluded from collection.
- [ ] `.vibelign/reports/bug-X.md` is excluded from collection.
- [ ] Existing expected `.vibelign` metadata inclusion/exclusion behavior remains unchanged.

### Verification

```bash
cargo test
```

### Release Gate

- [ ] Rust core artifact changed ⇒ patch version bump.
- [ ] PyPI version, GUI bundle version, Rust crate artifact, and release tag are aligned.
- [ ] Phase 1 must not be released without this phase.

---

## Phase 2 — GUI Error Capture + Async Flush

**Purpose:** capture GUI errors without freezing the UI, while preserving Python canonical redaction-before-disk.

### Files

**Create:**
- `vibelign-gui/src/lib/errorReporter.ts`
- `vibelign/commands/vib_log_gui_error_cmd.py`
- `tests/test_vib_log_gui_error_cmd.py`

**Modify:**
- `vibelign-gui/src-tauri/src/lib.rs`
- `vibelign-gui/src/App.tsx`
- `vibelign/cli/cli_command_groups.py`
- `vibelign/cli/cli_completion.py`
- `tests/test_vib_cli_completion.py`

### Steps

- [ ] Add `vibelign/commands/vib_log_gui_error_cmd.py`.
  - Internal command only.
  - Accept batched JSON array from stdin.
  - Pass each payload through `error_log.py record_gui_error`.
  - Do not expose in help, completion, README, or public docs.
  - If hiding is awkward, use `_log-gui-error` internal prefix.

- [ ] Register the internal command in `vibelign/cli/cli_command_groups.py`.
  - Keep it out of user-facing command lists.
  - Keep it out of completion generation.
  - Add the subparser with `help=argparse.SUPPRESS`, and update `vibelign/cli/cli_completion.py` so `parse_commands()` filters suppressed subcommands before generating shell/PowerShell completions.
  - Existing hidden commands (`pre-check`, `mcp`, `_internal_record_commit`, `_internal_post_commit`) must also stay out of generated completions after this change.

- [ ] Add `vibelign-gui/src/lib/errorReporter.ts`.
  - Capture `window.onerror`.
  - Capture `unhandledrejection`.
  - Accept React `ErrorBoundary.componentDidCatch(error, info)` events.
  - Require an active `projectDir` / project root before forwarding; before onboarding/project selection, silently drop GUI errors to preserve the project-local `.vibelign/logs/` contract.

- [ ] Update `vibelign-gui/src-tauri/src/lib.rs`.
  - Add `record_gui_error` Tauri command.
  - Sync work: push raw payload into `Mutex<VecDeque<...>>` only.
  - Flush trigger: 10 items or 5 seconds.
  - Flush work: `tauri::async_runtime::spawn` background task. Do not add a direct `tokio` dependency solely for this reporter unless implementation proves Tauri's runtime insufficient.
  - If the flush uses synchronous `std::process::Command` / blocking stdin writes, run that subprocess I/O inside `tauri::async_runtime::spawn_blocking` (or an equivalent blocking lane) so the async runtime worker is not occupied by process I/O.
  - Spawn `vib log-gui-error --batch` once per batch.
  - Reporter recursion guard: two-stage. (a) entire reporter body wrapped in Rust `catch_unwind` / `Result` so panics never reach the Tauri runtime, (b) module-level `AtomicBool` (e.g. `static REPORTING_IN_PROGRESS: AtomicBool`) consulted with `compare_exchange` — if already true, silent skip. Mirrors the Python `_reporting_in_progress` thread-local.
  - Windows subprocess hardening:
    - Reuse existing `vibelign-gui/src-tauri/src/vib_path.rs` helpers, especially `vib_path::find_runtime_vib()`, instead of adding a new `which` crate or duplicating sidecar/PATH lookup logic.
    - Preserve the existing bundled-vib-first behavior and Windows path normalization in `vib_path.rs`; if no runtime `vib` is found, silently drop the batch.
    - Apply the existing Windows no-console pattern (`CREATE_NO_WINDOW` / helper equivalent) to avoid console flicker on each 5-second flush. Mirrors `vibelign.core.structure_policy.WINDOWS_SUBPROCESS_FLAGS`.
  - Buffer cap: 1000 items; drop oldest beyond cap.
  - On subprocess failure: silent drop, never write raw payload to disk.

- [ ] Update `vibelign-gui/src/App.tsx`.
  - Add `componentDidCatch(error, info)` forwarding.

### Tests

- [ ] `tests/test_vib_log_gui_error_cmd.py` verifies stdin batch → canonical redact → GUI JSONL write.
- [ ] `tests/test_vib_log_gui_error_cmd.py` verifies raw token/path/IP does not appear on disk.
- [ ] `tests/test_vib_cli_completion.py` verifies the new internal command is not exposed.
- [ ] `tests/test_vib_cli_completion.py` verifies existing suppressed commands (`pre-check`, `mcp`, `_internal_record_commit`, `_internal_post_commit`) are not exposed by shell or PowerShell completion generation.
- [ ] `vibelign-gui/scripts/test-error-reporter.mjs` verifies browser-side capture path.
- [ ] Browser-side test verifies GUI errors are dropped before `projectDir` is available.
- [ ] Rust tests verify buffer cap and batching behavior.
- [ ] Rust test/code inspection verifies synchronous subprocess I/O is isolated in a blocking lane, not executed directly on the async runtime worker.
- [ ] Rust test verifies `REPORTING_IN_PROGRESS` AtomicBool guard prevents reporter recursion (a reporter-induced panic does not re-enter the reporter).
- [ ] Rust test verifies `vib_path::find_runtime_vib()` integration falls back gracefully (bundled/runtime path → silent drop) without surfacing errors to the GUI thread.
- [ ] Burst scenario: 1000 errors/sec does not materially increase GUI frame time.

### Verification

```bash
pytest tests/test_vib_log_gui_error_cmd.py tests/test_vib_cli_completion.py
cargo test
```

### Phase 2 Exit Criteria

- [ ] GUI `throw new Error("test")` writes `gui-error-*.jsonl` via Python canonical writer.
- [ ] Raw GUI payload never touches disk.
- [ ] Internal command is not user-visible.
- [ ] GUI remains responsive during burst.
- [ ] Background subprocess failures do not affect GUI flow.
- [ ] GUI watch remains running when error reporter internals fail silently; reporter failures must not emit stderr into the existing `watch_error` channel.

---

## Cross-Phase Verification Matrix

| Guarantee | Phase | Verification |
|---|---:|---|
| CLI JSONL written | 1 | `pytest tests/test_error_log.py` |
| GUI JSONL written | 2 | `pytest tests/test_vib_log_gui_error_cmd.py` + GUI smoke |
| Raw secret never on disk | 1, 2 | secret fixtures + file inspection |
| Local logging can be disabled | 1 | nested config test |
| Logs/reports excluded from backups | 1.5 | `cargo test` snapshot regression |
| Internal command not exposed | 2 | CLI help/completion tests, including suppressed-command completion filtering |
| GUI rootless errors dropped | 2 | browser-side reporter test before project selection |
| Watch compatibility | 1, 2 | watch path-skip tests + reporter-failure stderr silence test |
| No network in error-reporting paths | 1, 2, 3 | scoped grep/code review |
| Windows-safe filenames | 1, 3 | filename regex test |
| UTF-8 round-trip | 1, 2 | Korean fixture test |
| Atomic append | 1, 2 | multi-process write test |

---

## Go / No-Go Gates

### Go

- [ ] Phase 1 and Phase 1.5 tests pass.
- [ ] No raw secret appears in CLI/GUI logs.
- [ ] `.vibelign/logs/` and `.vibelign/reports/` are gitignored and backup-excluded.
- [ ] Internal GUI logging command is hidden.
- [ ] Suppressed/internal commands are absent from generated shell and PowerShell completions.
- [ ] Error logging does not produce watch-triggered code-map refreshes or GUI `watch_error` events.
- [ ] GUI burst does not block main thread.

### No-Go

- [ ] GUI writes JSONL directly without Python canonical writer.
- [ ] Phase 1 ships without Phase 1.5.
- [ ] `log-gui-error` appears in public help/completion/README.
- [ ] Existing suppressed commands remain visible in generated completion scripts after this change.
- [ ] Writing `.vibelign/logs/*.jsonl` or `.vibelign/reports/*.md` causes realtime watch to refresh code-map or stop GUI watch.
- [ ] Any raw token/path/IP/internal host is observed in `.vibelign/logs/` or `.vibelign/reports/`.
- [ ] Error-reporting Tier 1/2 paths include external network calls.

---

## Implementation Order

1. `file_lock.py`
2. `config_loader.py`
3. `error_log.py`
4. CLI runtime exception capture
5. `vib_start_cmd.py` gitignore additions
6. Phase 1 tests
7. Rust backup snapshot exclusions
8. Cargo tests
9. Internal `log-gui-error` command
10. Completion filtering for suppressed/internal commands
11. GUI reporter library
12. Tauri buffer/async flush using existing `vib_path` runtime resolution
13. React ErrorBoundary forwarding
14. Phase 2 tests and GUI smoke

---

## Notes for Implementers

- Keep patches small and anchored.
- Do not introduce `as any`, `@ts-ignore`, or empty catch blocks.
- Do not broaden this work into remote telemetry.
- Do not make the GUI command public for convenience.
- Do not duplicate existing GUI `vib` runtime path resolution; reuse `vibelign-gui/src-tauri/src/vib_path.rs`.
- Do not add PyYAML or a `which` crate unless a concrete implementation blocker requires it and this plan is updated.
- Do not release Phase 1 without Phase 1.5.
