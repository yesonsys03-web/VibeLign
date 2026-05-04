# VibeLign Memory + Recovery Agent Implementation Spec

Date: 2026-05-02
Status: Completed implementation baseline (rev. 5 — Phase 1–6 product baseline implemented through gated Phase 5 apply and read-only Phase 6 GUI cards; remaining unchecked items are follow-up hardening/backlog, completion trace recorded in `docs/superpowers/plans/2026-05-03-memory-recovery-agent-completion-trace.md`)
Source design: `docs/superpowers/specs/2026-05-02-vibelign-memory-recovery-agent-design.md`

> **For implementers:** build this feature in small, reversible phases. Preserve module boundaries. Do not turn existing CLI, MCP, transfer, checkpoint, or GUI files into catch-all coordinators. Every phase must leave the product usable if later phases are deferred.

## 1. Goal

Turn the Memory + Recovery Agent design into an implementation path that extends existing VibeLign strengths:

- `vib transfer --handoff` becomes a guided memory review instead of a one-shot summary writer.
- `vib recover --explain` provides a read-only recovery advisor before any destructive restore exists.
- MCP exposes safe, redacted, typed endpoints that other AI tools can ask for context and recovery options.
- Memory and recovery share structured context without allowing memory text to become executable instruction.

The finished system must support:

- Structured project memory with freshness metadata.
- Intent-aware, diff-aware recovery recommendations.
- Redacted memory summaries for CLI, handoff, and MCP.
- Preview-first recovery flows.
- Checkpoint sandwich enforcement before destructive recovery.
- Local-only P0 audit events.
- Extension seams for future GUI cards, richer privacy filters, and partial restore apply.

## 2. Non-negotiable Constraints

All phases must implement the four-step trusted shape from design §2 *Foundational Product Rule* (explain → preview → safety checkpoint → confirmed apply). Any task that breaks this shape is rejected, regardless of phase.

- Do not replace `vib transfer --handoff`; evolve it around a shared memory service.
- Do not add recovery apply before read-only recommendation quality is proven.
- Do not parse commands or file operations from memory free text.
- Do not expose raw memory, raw terminal output, full local paths, raw diffs, or secret values through MCP by default.
- Do not silently write `decisions[]`, `active_intent`, `next_action`, or user-facing relevant-file notes.
- Do not mix memory persistence, recovery planning, MCP handlers, and CLI rendering in one module.
- Do not expand entry-point files into feature logic; keep CLI/MCP handlers as wiring.
- Do not make GUI cards the source of truth; GUI reads/writes through the same service layer as CLI/MCP.
- Design every new boundary for extension: Phase 1 is read-only recovery, but data models and interfaces must not assume MCP write/apply, GUI cards, or future remote/encrypted storage can never exist.
- Keep changes additive where existing commands and MCP tools already exist.

## 3. Release Split

- **Phase 1 — Read-Only Recovery Advisor:** add `vib recover --explain` and core recovery planning without modifying files.
- **Phase 2 — Memory Core + Handoff Review:** introduce structured memory schema/service and upgrade `vib transfer --handoff` to use guided review.
- **Phase 3 — MCP Read-Only Surface:** expose `memory_summary_read`, `recovery_preview`, and safe-write `checkpoint_create` with redaction and audit events.
- **Phase 4 — Memory Hygiene + Triggers:** add stale verification, stale intent, conflict detection, and snoozable review prompts.
- **Phase 5 — Assisted Partial Recovery:** add preview-first selected-file restore/apply with checkpoint sandwich and project lock.
- **Phase 6 — GUI Agent Cards:** add Session Memory and Recovery Options cards over the stable service contracts.

Each phase must be independently reviewable and revertible.

### Completion interpretation and open hardening backlog

The Phase 1–6 baseline is considered complete for the current product slice: read-only recovery planning exists, structured memory powers handoff/review surfaces, MCP exposes safe read-only context plus gated apply, and GUI cards remain read-only presentation over service contracts.

Unchecked items in the phase task lists are **not** part of that baseline completion claim. They are follow-up hardening work needed before stronger operational claims such as release-cycle P0 SLO enforcement, generated cross-language schemas, or richer targeted-repair recommendations.

Completion state model:

| State | Current value | Meaning |
|---|---|---|
| Product baseline implemented | Yes | Phase 1–6 service/CLI/MCP/GUI slice exists as documented. |
| Recovery apply default state | Default-off | Apply remains gated by env-backed feature flag plus MCP grants. |
| Release-certified / operationally complete | No | Open hardening items 1–3 and 5 prevent release-cycle P0 SLO certification and contract-drift certification. |
| Follow-up hardening backlog open | Yes | Items below are code/test work, not additional product-planning blockers. |

Prioritized code hardening order as of rev. 5:

1. **Close the recovery lock TTL race.** `vibelign/core/recovery/locks.py` already prevents releasing another owner's lock, but `vibelign/core/recovery/apply.py` must also abort or otherwise fail safely if a selected-file restore exceeds the recovery lock TTL. Add tests that simulate a long-running restore, lock expiry, and a competing lock owner.
2. **Add audit integrity before claiming operational P0 SLOs.** Add monotonic `sequence_number` to audit rows and implement `vibelign/core/memory/aggregator.py` so release-cycle P0 occurrence summaries come from count-only audit evidence, not one-off test runs.
3. **Add audit retention.** Implement `vibelign/core/memory/retention.py` to roll `memory_audit.jsonl` while preserving active P0 aggregation windows and count-only summaries.
4. **Remove recovery apply gate ambiguity.** Treat `RecoveryApplyRequest.feature_enabled` as metadata only, or rename/remove it. The only active apply gates are env-backed `is_enabled("RECOVERY_APPLY")` and MCP capability grants.
5. **Add shared schema contracts.** Generate or maintain `memory_state.schema.json` and `recovery_plan.schema.json` so GUI/CLI/MCP contracts cannot drift silently.
6. **Wire the optional targeted-repair seam.** Integrate `patch_suggester` into Recovery Level 2 recommendations only after the safety and observability work above is complete. Item 6 also closes a CodeSpeak coherence gap: `patch_suggester` chooses the `subject` that drives AI patch accuracy, so wiring it into Level 2 lets recovery recommend repairs in the same compressed-instruction format the rest of VibeLign relies on.

Dependencies between hardening items:

- Items 2 and 3 are blocked by item 1: lock-race fixes determine what "successful `recovery_apply`" means in audit data, so audit integrity and retention must read post-fix audit rows.
- Items 4 (gate ambiguity), 5 (schema contracts), and 6 (`patch_suggester` seam) are independent of items 1–3 and can be parallelized once owners are assigned.

Until those items land, wording such as "0 P0 occurrences over a release window" means "supported by tests and count-only audit events where implemented," not full release-cycle operational certification from an aggregator.

#### Windows/macOS implementation edge-case checklist

The follow-up hardening work must be verified on Windows and macOS before it is treated as complete. Existing tests cover only generic path/lock/audit behavior (`tests/test_recovery_path_safety.py`, `tests/test_cross_platform_paths.py`, `tests/test_recovery_locks.py`, `tests/test_memory_audit.py`); the platform cases below are mostly new test requirements, not existing coverage.

1. **Recovery lock TTL race**
   - Windows: account for slow file I/O, antivirus/indexer delay, file-handle delete/rename failures, and partial JSON reads while `.vibelign/recovery/recovery.lock.json` is being rewritten.
   - macOS: account for APFS timestamp behavior, Spotlight/iCloud/Time Machine file access delays, and case-insensitive volumes.
   - Timeout policy: use `recovery.lock_timeout_seconds` with default 60 seconds, matching the source design. Projects that need longer restores raise the timeout explicitly; the system never silently extends the lock mid-restore.
   - Cooperative cancel: apply MUST check lock ownership at file boundaries (e.g., between restored files) and abort gracefully if the lock is no longer held. The preferred implementation is file-boundary cooperative cancellation; whole-restore preemption is not required unless the checkpoint engine later exposes cancellable restore hooks. The aborting apply MUST emit a `result: aborted` audit event and surface a "restore exceeded lock window" error to the caller; it MUST NOT continue restoring further files after losing ownership.
   - Required tests: long-running restore exceeds TTL; expired lock is replaced by a competing owner; original apply does not report success after losing ownership; release never deletes another owner's lock.

2. **Path safety and selected-file restore**
   - Windows: reject or safely normalize drive letters (`C:\...`, `D:/...`), UNC paths (`\\server\share`), WSL paths (`/mnt/c/...`), reserved names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`, `LPT1`), trailing dot/space names, alternate data streams (`file.txt:stream`), long paths, and case-insensitive collisions.
   - WSL execution context: the same project at `/mnt/c/...` may be opened from cmd, PowerShell, Ubuntu (WSL), or a Tauri GUI. Recovery output MUST canonicalize all four call sites to the same project-root identity before scope/lock checks, otherwise two surfaces could believe they hold different "current projects" and race on the same files.
   - macOS: handle APFS case-insensitive collisions (`Readme.md` vs `README.md`), Unicode NFC/NFD filename differences, symlink escapes outside the project root, and Finder artifacts such as `.DS_Store` / `._file`. macOS volumes default to case-insensitive (APFS/HFS+); case-sensitive APFS exists but is uncommon and must be detected at runtime with a project-root-local probe that compares two differently cased temporary names. Equality uses the case-sensitive comparator only when the probe proves the volume is case-sensitive. Internal comparison and hashing MUST normalize display paths to NFC, while actual file operations preserve the filesystem path returned by canonicalization.
   - Required tests: WSL path handling across cmd/PowerShell/Ubuntu/GUI surfaces; symlink escape rejection; Windows trailing-dot/space and ADS rejection; macOS Unicode normalization; case-insensitive collision requires review rather than automatic restore; case-sensitive APFS volume is detected and uses case-sensitive equality.

3. **Audit JSONL, aggregator, and retention**
   - Windows: tolerate file locking, partial append lines after crashes, CRLF/LF variance on read, and delayed rename/delete during rollover. Writers MUST always emit LF only — never CRLF — so audit rows remain byte-identical across platforms; readers tolerate CRLF for legacy rows but normalize to LF on the next rewrite.
   - macOS: normalize or hash Unicode paths consistently across NFC/NFD forms and avoid rollover filename collisions on case-insensitive volumes.
   - Required tests: partial/corrupt JSONL line is skipped for counting and recorded as `corrupt_rows_count`; malformed rows are copied to a local-only quarantine file under `.vibelign/recovery/` with raw sensitive content redacted before write; any corruption inside a P0-relevant event range fails that aggregation window and surfaces a plain-language "audit log needs review" warning; `sequence_number` gap/duplicate rejects the aggregation window; retention preserves active P0 windows; audit output never includes raw Windows/macOS absolute paths; writer never emits CRLF and readers normalize legacy CRLF rows on rewrite.

4. **Recovery apply gate cleanup**
   - Windows/macOS packaged GUI/MCP flows may not inherit shell environment variables the same way as CLI. Tests must prove `feature_enabled` in request payloads cannot enable apply, and that `VIBELIGN_RECOVERY_APPLY` / `is_enabled("RECOVERY_APPLY")` remains the only feature flag path alongside MCP grants.

5. **Shared schema contracts**
   - Generated schema and CLI JSON output must use UTF-8, project-relative `/` paths, and stable field names across Windows and macOS.
   - UTF-8 BOM handling: stored memory and audit files MUST be written without a BOM; parsers MUST reject a BOM in stored files because it signals corruption or accidental editor export. CLI input MAY strip a leading UTF-8 BOM before parsing to tolerate Windows editors that emit one.
   - Required tests: schema validation for Unicode file names, Windows-style input paths normalized to display paths, GUI CLI output matching `memory_state.schema.json` / `recovery_plan.schema.json`, stored audit/memory files reject BOM, CLI input strips a leading BOM without altering payload.

6. **Recovery Level 2 `patch_suggester` seam**
   - Windows: patch suggestions returning backslash or absolute paths must be normalized or rejected before they become recovery options.
   - macOS: case-only and Unicode-normalization mismatches must be marked review-needed, not auto-repairable.
   - Required tests: `patch_suggester` output is converted to project-relative display paths; absolute suggestions are rejected; macOS case/Unicode mismatch cannot bypass user review.

### Next Slice — Guided Recovery Agent Contract

After Phase 6 read-only cards, the next implementation slice should upgrade the product from passive cards to a **Guided Recovery Agent with Assisted Apply**. This is a product flow change, not permission to bypass existing apply gates.

The flow is:

```text
Explain → Recommend → Preview → Safety checkpoint → User confirmation → Limited apply → Result explanation
```

Implementation contract:

| Step | Required service output | Can modify files? | Gate |
|---|---|---:|---|
| Explain | plain-language situation summary | No | none |
| Recommend | safest option + alternatives | No | recommendation quality must be testable |
| Preview | affected paths, risk, checkpoint candidate, blocked reasons | No | typed `RecoveryPlan` / `RecoveryOption` only |
| Safety checkpoint | sandwich checkpoint ID | Checkpoint only | checkpoint engine success required |
| Confirm | selected `option_id`, `checkpoint_id`, `paths`, confirmation token | No | explicit user approval |
| Limited apply | changed-file count, safety checkpoint ID, verification recommendations | Yes | Phase 5 apply gates: grant/flag/lock/path validation/audit |

Non-goals for this slice:

- No autonomous full rollback.
- No command generation from memory or handoff free text.
- No GUI-specific second apply model.
- No raw logs or JSON as the beginner-facing explanation.

Recommended first implementation move: make the read-only `RecoveryPlan` and `RecoveryOption` user-facing enough for the GUI to render the first three steps (explain/recommend/preview) before adding any GUI apply button. The apply step should call the existing selected-file recovery service only after the same typed confirmation contract used by CLI/MCP is satisfied.

### Phase ordering vs design §6

The design lists five phases (Recovery → MCP → Memory → Apply → GUI). This implementation re-decomposes the design's "Memory" phase into two: **Phase 2 Memory Core** (storage, schema, service layer) and **Phase 4 Memory Hygiene + Triggers** (user-facing review surface). The design ordering ranks by *user value curve*; the implementation ordering adds a dependency constraint — Phase 3 MCP cannot expose `memory_summary_read` until Phase 2 has produced a structured memory store to read from. Reading both documents together: the design's "Memory" phase = implementation Phase 2 + Phase 4, with MCP (Phase 3) inserted between them because read-only MCP needs storage but does not need triggers.

## 4. Target Module Structure

Python service layer:

```text
vibelign/core/memory/
├─ __init__.py
├─ models.py
├─ store.py
├─ review.py
├─ redaction.py
├─ freshness.py
├─ audit.py
├─ aggregator.py    # follow-up hardening: P0 occurrence aggregator over memory_audit.jsonl
└─ retention.py     # follow-up hardening: audit log rollover preserving active P0 windows

vibelign/core/recovery/
├─ __init__.py
├─ models.py
├─ signals.py
├─ intent_zone.py
├─ planner.py
├─ render.py
├─ locks.py
└─ apply.py        # Phase 5 only; no destructive work before then
```

CLI wiring:

```text
vibelign/commands/
├─ vib_memory_cmd.py
└─ vib_recover_cmd.py
```

MCP wiring (matches existing flat convention — `vibelign/mcp/` already contains `mcp_anchor_handlers.py`, `mcp_checkpoint_handlers.py`, `mcp_doctor_handlers.py`, `mcp_patch_handlers.py`, `mcp_protect_handlers.py`, `mcp_transfer_handlers.py`, etc., plus a single `mcp_tool_specs.py`):

```text
vibelign/mcp/
├─ mcp_memory_handlers.py        # new — handlers for memory_summary_read, memory_full_read (later)
├─ mcp_recovery_handlers.py      # new — handlers for recovery_preview, recovery_apply (Phase 5)
└─ mcp_tool_specs.py             # existing — extend with memory and recovery tool specs additively
```

Do not introduce a `vibelign/mcp/handlers/` or `vibelign/mcp/tool_specs/` subdirectory. The existing flat convention is the source of truth for MCP module organization; restructuring is out of scope for this spec.

GUI layer, deferred until Phase 6:

```text
vibelign-gui/src/components/agent-memory/
├─ SessionMemoryCard.tsx
└─ RecoveryOptionsCard.tsx
```

Extension seams to preserve:

- `memory/store.py` owns storage format and migrations. Callers never write `work_memory.json` fields directly.
- `memory/redaction.py` wraps existing secret scanning and privacy filtering. MCP, handoff, and audit export use the same redaction contract.
- `recovery/signals.py` collects git/checkpoint/project-map/guard/explain signals. `recovery/planner.py` consumes normalized signals only.
- `recovery/intent_zone.py` owns explicit-memory and fallback inference. Recovery rendering never reimplements intent-zone logic.
- `recovery/apply.py` is absent or inert until Phase 5. Earlier phases expose preview/recommendation only.
- MCP handlers validate permissions and call services; they do not implement planning or persistence logic.
- GUI components call typed commands/services; they do not infer recovery options locally.

## 5. Data Model

### MemoryState

Structured memory is small and bounded. It is not a transcript dump.

```json
{
  "schema_version": 1,
  "active_intent": {
    "text": "Improve BACKUPS file history UX.",
    "last_updated": "2026-05-02T12:34:56Z",
    "updated_by": "vib memory review",
    "stale": false
  },
  "decisions": [],
  "relevant_files": [],
  "verification": [],
  "risks": [],
  "next_action": null,
  "observed_context": [],
  "archived_decisions": []
}
```

Rules:

- `decisions[]` are explicit only.
- `active_intent` may be proposed automatically but committed only after user confirmation.
- `relevant_files[]` has explicit and observed entries; only explicit entries become handoff truth.
- `verification[]` records command, result, timestamp, source (`explicit` or `observed`), related file scope, scope confidence, and stale status.
- `risks[]` stores unresolved warnings, skipped tests, assumptions, and redaction notes.
- `observed_context[]` stores supporting evidence such as touched files, commits, checkpoints, guard/explain summaries, and watch events.
- Caps: `decisions[]` last 50, `recent_events[]` last 200, `verification[]` last 30 per scope, `relevant_files[]` last 100.

Verification scope responsibility:

| Writer | `source` | `related_files` responsibility | Fallback |
|---|---|---|---|
| `patch_apply` / patch session | `observed` | exact patch target files | recent changed files if target metadata missing |
| `guard_check` / doctor / explain MCP capture | `observed` | files checked or changed since the checked baseline | mark `scope_unknown: true` and lower confidence |
| `transfer_set_verification` / CLI `--verification` | `explicit` when user-supplied, otherwise `observed` | optional user-provided file scope; otherwise recent changed files | mark `scope_unknown: true` |
| `vib memory review` accepted prompt | `explicit` | files the user confirms as covered by the verification | leave scope unknown only after visible warning |

Rules:

- Scope inference must happen before saving verification, not later in handoff rendering.
- Scope-unknown verification may appear in handoff, but the UI must say the covered files are unknown.
- Stale-cascade logic must prefer scoped verification; if only scope-unknown verification exists, the agent should recommend rerunning focused verification instead of claiming freshness.

### RecoveryPlan

```json
{
  "plan_id": "rec_...",
  "mode": "read_only",
  "level": 1,
  "summary": "UI files changed; one service file is outside the inferred intent zone.",
  "intent_zone": [],
  "drift_candidates": [],
  "options": [],
  "safe_checkpoint_candidate": null,
  "redaction": {
    "secret_hits": 0,
    "privacy_hits": 0,
    "summarized_fields": 0
  }
}
```

`mode` enum values:

- `read_only` — Phase 1–4 default; recommendation only, no apply path active.
- `apply_preview` — Phase 5; same shape as `read_only` but with `safe_checkpoint_candidate` populated and apply paths validated.
- `apply` — Phase 5; emitted only after successful apply; includes the safety-checkpoint ID and changed-files list.

Mode transition ownership:

- `read_only` is emitted only by `recovery/planner.py` (the read-only planner). Planner output never carries `apply_preview` or `apply`.
- `apply_preview` is emitted by the apply validation step in `recovery/apply.py` after typed-parameter validation but before destructive work begins.
- `apply` is emitted by the apply result builder after successful restore. No other module is allowed to set this value.
- GUI/MCP clients MUST treat `mode` as the rendering signal for which step of the Guided Recovery flow they are in (preview vs preflight vs result), not as a permission gate. The permission gate is always the env-backed feature flag plus per-tool grant.

`intent_zone[]` entry shape:

```json
{
  "path": "src/pages/BackupDashboard.tsx",
  "source": "explicit",
  "reason": "explicit relevant_files entry: 'owns backup dashboard state'"
}
```

Valid `source` values, in priority order matching design §5: `explicit`, `recent_patch_target`, `project_map_category`, `anchor_co_occurrence`, `diff_fallback`.

`drift_candidates[]` entry shape:

```json
{
  "path": "src/services/auth.ts",
  "why_outside_zone": "not in explicit relevant_files; project-map category 'core' differs from recent patch category 'ui'",
  "suggested_action": "review_and_revert_if_unintentional",
  "requires_user_review": true
}
```

`requires_user_review` is always `true` for drift candidates — no automatic revert path exists.

`safe_checkpoint_candidate` non-null shape:

```json
{
  "checkpoint_id": "ckpt_...",
  "created_at": "2026-05-02T11:00:00Z",
  "predates_change": true,
  "metadata_complete": true,
  "preview_available": true
}
```

If `predates_change` or `metadata_complete` is false, the candidate is reported but not selected for default rollback. `null` means no safe candidate exists — Recovery Levels 3–4 are not offered.

`RecoveryOption` shape (entries in `options[]`):

```json
{
  "option_id": "opt_...",
  "level": 1,
  "label": "Explain only — show what changed and which files look risky.",
  "affected_paths": ["src/services/auth.ts"],
  "estimated_impact": "no file changes; informational",
  "requires_sandwich": false,
  "requires_lock": false,
  "blocked_reason": null
}
```

`requires_sandwich` is `true` for Level 3–4. `requires_lock` is `true` for any apply mode. `blocked_reason` is non-null when the option is presented but cannot run (e.g., "no safe checkpoint candidate available", "Phase 5 not enabled").

ID generation rule (applies to `plan_id`, `option_id`, and any future plan-scoped ID): `<prefix>_<uuid4-without-dashes>`. Prefixes are stable: `rec` for `RecoveryPlan`, `opt` for `RecoveryOption`. IDs are generated locally and never derived from memory text or user input — this ties into Layer 4 (memory text cannot become an identifier the agent later acts on).

Rules:

- Level 0–2 plans can be produced in Phase 1.
- Level 3–4 plans may be previewed before Phase 5, but cannot apply.
- Drift candidates are suggestions, never automatic revert targets.
- If memory is empty or stale, planner falls back to diff-aware mode and says so.

### AuditEvent

Audit events prove safety gates fired. They must not contain raw memory, raw diff, full paths, terminal output, or secret values.

```json
{
  "event": "recovery_preview",
  "project_root_hash": "...",
  "tool": "vib-cli",
  "timestamp": "2026-05-02T12:34:56Z",
  "capability_grant_id": null,
  "sandwich_checkpoint_id": null,
  "paths_count": {
    "in_zone": 2,
    "drift": 1,
    "total": 3
  },
  "circuit_breaker_state": "active",
  "redaction": {
    "secret_hits": 0,
    "privacy_hits": 1,
    "summarized_fields": 2
  },
  "trigger": {
    "id": null,
    "action": null,
    "source": null
  },
  "result": "success"
}
```

`paths_count` separates in-zone vs drift to enable post-hoc accuracy measurement (§14, §15) without storing raw paths. `circuit_breaker_state` is `active` (drift labeling enabled) or `degraded` (drift labeling auto-disabled per design §7 P0 mitigation); recording the state per event lets audits prove the breaker fired at the right moment.

Phase 4 trigger events reuse the same local-only audit rail. `trigger.id` is a sanitized trigger identifier such as `stale_verification`, `trigger.action` is one of `shown`, `accepted`, `dismissed`, `snoozed`, or `ignored`, and `trigger.source` is the CLI/MCP surface that observed the event. Trigger audit rows must not store prompt text, memory text, raw paths, raw diffs, terminal output, or the user-entered reason for an action.

## 6. Storage and Migration

Phase 1 can read existing files without schema migration. Phase 2 introduces memory schema ownership.

Recommended storage:

```text
.vibelign/
├─ work_memory.json          # existing user/project memory, migrated additively
├─ memory_audit.jsonl        # local-only audit events, gitignored
└─ recovery/
   ├─ last_preview.json      # local-only, redacted/summarized
   ├─ trigger_baseline.json  # local-only derived trigger metrics snapshot
   └─ locks/                 # Phase 5 recovery lock files
```

Migration rules:

- Add `schema_version` to memory state.
- Existing `work_memory.json` fields remain valid.
- New fields are optional during migration and normalized on first write.
- If project-local memory artifacts are created, ensure `.gitignore` covers them by default.
- If migration finds malformed memory, preserve the raw file as a backup and start from minimal memory mode.
- Do not store trigger telemetry or diff baselines in `work_memory.json`; memory remains handoff truth, while telemetry remains local-only measurement data.
- `trigger_baseline.json` is a derived snapshot from local audit events. It may contain coarse counters such as `ignored_prompt_rate_7d`, `baseline_window_days`, and `diff_lines_since_intent`, but never raw file paths, raw diffs, memory text, logs, usernames, or secret-like values.

Forward compatibility — VibeLign newer than the file: additive migration as above.

Backward compatibility — VibeLign **older** than the file (downgrade): not silently supported. When an older VibeLign opens a `work_memory.json` with `schema_version` greater than its known max, behavior is:

1. Read in safe mode (no schema mutation, no field assumption).
2. Surface only the fields the older VibeLign understands.
3. Print a one-line warning: `memory schema_version=N is newer than this VibeLign supports — upgrade or run with --legacy-readonly`.
4. Refuse to write `decisions[]`, `active_intent`, `next_action`, or `relevant_files[]` until the user upgrades or explicitly opts into legacy read-only mode.

This avoids silent field stripping that would damage memory written by a newer install.

Interaction with §16 unknown_fields preservation: §16 covers *truly unknown* fields the older VibeLign has never heard of — those are bagged into `unknown_fields` and round-tripped on next write. The §6 downgrade refusal above covers *known fields with newer semantics* (e.g., a future `from_previous_intent` flag attached to an existing field). Known-but-newer-semantics fields are not bagged; they trigger the read-only downgrade refusal because writing them with old semantics would corrupt project truth. The two rules do not overlap: schema-version dictates which path applies.

Forward migration ownership:

- Forward migration functions live in `vibelign/core/memory/store.py` under sub-anchors named `MEMORY_STORE__MIGRATE_V<N>_START` / `MEMORY_STORE__MIGRATE_V<N>_END`, one anchor per source schema version.
- Each migration function takes the raw dict at version N and returns a normalized dict at version N+1; chained calls cover larger jumps.
- `load_memory_state` reads `schema_version`, applies migrations sequentially up to the current binary's max version, then validates.
- New schema versions MUST add a migration function in this anchor pattern; in-place mutation of `load_memory_state` for ad-hoc upgrades is rejected by code review.
- Migration functions are pure (no I/O, no audit writes); audit/observability for migration is the caller's responsibility.

## 7. Security and Privacy Contracts

All surfaces that produce memory or recovery text use the same redaction contract:

1. Summarize raw terminal output by default.
2. Run existing secret scanner.
3. Run privacy filter for local paths, usernames, internal hosts, private IPs, and large logs.
4. Mark fields as `redacted`, `summarized`, or `omitted_fields`.
5. Write local-only audit counts, never raw sensitive values.

MCP permission defaults:

| Capability | Phase | Default | Notes |
|---|---:|---:|---|
| `memory_summary_read` | 3 | Allowed | Redacted summary only. |
| `recovery_preview` | 3 | Allowed | Read-only. |
| `checkpoint_create` | 3 | Allowed | Safe-write, project-root scoped. |
| `memory_full_read` | Later | Denied | Requires explicit grant and confirmation. |
| `memory_write` | Later | Denied | Intent-shaping fields require confirmation. |
| `recovery_apply` | 5 | Denied | Requires checkpoint sandwich and project lock. |
| `handoff_export` | Later | Denied | Requires export confirmation and filtering. |

## 8. Phase 1: Read-Only Recovery Advisor

**Purpose:** give users immediate value when AI breaks or drifts, without modifying files.

**Commands:**

```bash
vib recover --explain
```

**Files:**

- Add: `vibelign/core/recovery/models.py`
- Add: `vibelign/core/recovery/signals.py`
- Add: `vibelign/core/recovery/intent_zone.py`
- Add: `vibelign/core/recovery/planner.py`
- Add: `vibelign/core/recovery/render.py`
- Add: `vibelign/commands/vib_recover_cmd.py`
- Modify CLI registration only where commands are wired.
- Add focused tests near existing CLI/recovery/checkpoint tests.

**Tasks:**

- [x] Define `RecoverySignalSet`, `IntentZone`, `DriftCandidate`, `RecoveryOption`, and `RecoveryPlan` dataclasses.
- [x] Collect current git diff and untracked file list.
- [x] Read latest checkpoint metadata and backup DB rows when available.
- [x] Read project map categories and anchor metadata when available.
- [x] Read latest guard/explain report summaries when available.
- [x] Infer intent zone using explicit memory first, recent patch targets second, project-map category third, anchor co-occurrence later, and diff-aware fallback last.
- [x] Label files outside the inferred zone as `drift_candidate`, never `unrelated`.
- [x] Recommend one of: no-op, explain-only, targeted repair, partial restore preview, or full rollback preview.
- [x] Render 2–3 recovery options in plain language.
- [x] Never modify files in this phase.
- [ ] Expose an optional `patch_suggester` seam for Recovery Level 2 ("targeted repair"). When the suggester is available, Level 2 options MAY include a fix proposal derived from guard/explain output (consistent with the project rule that `subject` quality drives AI patch accuracy). Phase 1 renders the label only and leaves the seam unwired; Phase 4+ may wire the suggester behind a feature flag. Without the seam, Level 2 today degenerates into "read the guard output yourself", which under-delivers the design promise.

**Verification:**

```bash
python -m pytest tests/test_vib_cli_surface.py tests/test_project_root_resolution.py -q
```

Add new targeted tests for:

- Empty project memory falls back to diff-aware recovery.
- File outside explicit relevant files is labeled drift candidate.
- No checkpoint exists → no full rollback recommendation.
- Generated/cache/build files are excluded from recovery targets.
- Windows-style paths and parent traversal are rejected or normalized safely.

**Exit criteria:**

- `vib recover --explain` exits 0 in a normal git project.
- Output is read-only and states that no files were modified.
- Empty memory still produces useful diff-aware recommendations.
- Drift candidates require user review and are not auto-reverted.

## 9. Phase 2: Memory Core + Handoff Review

**Purpose:** create a structured memory service and use it to improve `vib transfer --handoff`.

**Commands:**

```bash
vib memory show
vib memory review
vib memory decide "..."
vib memory relevant path/to/file.py "why it matters"
vib transfer --handoff
```

**Files:**

- Add: `vibelign/core/memory/models.py`
- Add: `vibelign/core/memory/store.py`
- Add: `vibelign/core/memory/review.py`
- Add: `vibelign/core/memory/freshness.py`
- Add: `vibelign/commands/vib_memory_cmd.py`
- Modify existing transfer command only as wiring to the memory service.
- Add tests near existing transfer and handoff tests.

**Tasks:**

- [x] Implement additive migration for `work_memory.json` to `schema_version = 1`.
- [x] Preserve current decisions, verification, relevant files, and recent events.
- [x] Add freshness metadata: `last_updated`, `updated_by`, `from_previous_intent`, and `stale`.
- [x] Implement explicit write APIs for `decisions[]`, `active_intent`, `relevant_files[]`, and `next_action`.
- [x] Implement observed-context append APIs for commits, checkpoints, reports, touched files, and verification results.
- [x] Implement memory compaction caps and `archived_decisions[]`.
- [x] Make `vib transfer --handoff` read from `MemoryState` and show stale verification warnings.
- [x] Keep user confirmation required before writing intent-shaping fields.

**Verification:**

```bash
python -m pytest tests/test_transfer_cli_docs.py tests/test_transfer_git_context.py tests/test_handoff_auto_capture.py tests/test_work_memory.py tests/test_work_memory_record_commit.py tests/test_work_memory_relevant_api.py tests/test_work_memory_migration.py tests/test_work_memory_freshness.py -q
```

The last two test files are new in this phase (per §17 Test File Mapping). Phase 2 cannot exit until both run green. The first three legacy tests must continue to pass — additive migration must not regress existing handoff behavior.

Add new targeted tests for:

- Existing `work_memory.json` migrates without data loss.
- `decisions[]` cannot be silently overwritten by automatic capture.
- Stale verification appears as stale in handoff output.
- Memory caps archive old decisions without changing active intent.
- Newer `schema_version` opened by current binary triggers read-only downgrade behavior (§6).

**Exit criteria:**

- Existing `vib transfer --handoff` behavior remains compatible.
- New memory fields are additive and bounded.
- Handoff output is clearer but not noisier.

## 10. Phase 3: MCP Read-Only Surface

**Purpose:** let external AI tools ask VibeLign for redacted context and recovery options.

**MCP capabilities:**

- `memory_summary_read`
- `recovery_preview`
- `checkpoint_create`

**Files:**

- Add: `vibelign/core/memory/redaction.py`
- Add: `vibelign/core/memory/audit.py`
- Add: `vibelign/mcp/mcp_memory_handlers.py`
- Add: `vibelign/mcp/mcp_recovery_handlers.py`
- Modify: `vibelign/mcp/mcp_tool_specs.py` — additively append memory and recovery tool specs.
- Modify: `vibelign/mcp/mcp_handler_registry.py` and `vibelign/mcp/mcp_dispatch.py` only for registration of new handlers.
- Add focused MCP handler tests.

**Tasks:**

- [x] Wrap existing secret scanner in a memory redaction interface.
- [x] Add privacy filter v1: local absolute paths, usernames/home fragments, internal hosts, private IPs, and oversized terminal output.
- [x] Implement local-only audit event writer.
- [x] Implement `memory_summary_read` with redacted summaries and provenance tags.
- [x] Implement `recovery_preview` using the Phase 1 planner.
- [x] Implement `checkpoint_create` as safe-write, project-root scoped.
- [x] Ensure all MCP tools are non-interactive and parameterized.
- [x] Deny `memory_full_read`, `memory_write`, and `handoff_export`; keep `recovery_apply` denied by default and live only behind explicit grant plus enabled feature flag.
- [ ] Implement `vibelign/core/memory/aggregator.py` — reads `memory_audit.jsonl` plus derived recovery/trigger baselines and emits a count-only release-window summary for each P0 SLO. Required summary fields: `slo_id`, `window_start`, `window_end`, `occurrences`, `sample_count`, `result`. Per-SLO sample definitions: sandwich enforcement = all `recovery_apply` invocations; memory-as-instruction = all memory→action validation calls; redaction = all MCP memory responses; drift label = all drift labels confirmed by user feedback; stale-intent = all handoff/recovery rendering calls.
- [ ] Implement `vibelign/core/memory/retention.py` — rolls `memory_audit.jsonl` at 90 days or 10 MB, whichever first, into count-only summaries under `.vibelign/recovery/`. Active P0 aggregation windows are protected from compaction. A hard `max_active_window_days = 180` safeguards against unbounded retention if a release cycle never closes.
- [ ] Add monotonic `sequence_number` to every audit row; expose a verification helper that detects gaps/duplicates so the aggregator can refuse tampered windows (Design §7 P0 audit log integrity).

**Verification:**

```bash
python -m pytest tests/test_mcp_runtime.py tests/test_mcp_tool_loader.py tests/test_mcp_checkpoint_handlers.py tests/test_secret_scan.py tests/test_mcp_memory_handlers.py tests/test_mcp_recovery_handlers.py tests/test_memory_redaction.py -q
```

The last three test files are new in this phase (per §17). Phase 3 cannot exit until all run green, including the Layer 4 negative test inside `test_mcp_memory_handlers.py` proving memory text cannot reach a command parser (§15 infrastructure gate, §19 traceability).

Add new targeted tests for:

- MCP memory response passes redaction before return.
- Full local paths are shortened or redacted by default.
- Audit events contain counts, not raw memory or full paths.
- Denied capabilities return a clear permission error.
- Layer 4 negative test: memory text containing shell-style strings cannot reach any command parser, file operation, or MCP action invocation.

**Exit criteria:**

- External AI tools can read redacted memory summary and recovery preview.
- No MCP endpoint returns raw terminal output by default.
- Safe-write `checkpoint_create` cannot escape the project root.

## 11. Phase 4: Memory Hygiene + Triggers

**Purpose:** make memory proactive without becoming noisy.

**Files:**

- Modify: `vibelign/core/memory/freshness.py`
- Modify: `vibelign/core/memory/review.py`
- Add focused trigger tests.

**Tasks:**

- [x] Implement stale intent detection: older than 24h or unchanged across 5+ commits.
- [x] Implement stale verification detection when related files change after validation.
- [x] Implement conflict detection for same-field writes within `memory.conflict_window_seconds` default 60 seconds.
- [x] Implement dismiss/snooze logging per session. Surface: inline within `vib memory review` (interactive prompt offers Accept / Dismiss / Snooze choices); no separate `vib memory snooze` command. Snoozed triggers persist for the session only — they reset on next CLI invocation. The dismiss/snooze action is the only place where a trigger ID becomes user-visible.
- [x] Implement trigger thresholds (inlined from design §3 *Trigger Conditions*):
  - `decisions[]` empty AND `patch_apply` invoked ≥3 times in current session.
  - `active_intent` age >6 hours AND diff growth >40 lines since last update.
  - `verification[]` stale (newest result older than newest patch).
  - A patch touches a file outside both explicit `relevant_files[]` AND the inferred intent zone (§5 fallback).
  - `transfer --handoff` invoked without a confirmed `next_action`.
- [x] Render prompts as suggestions, never blocking modals.
- [x] Track ignored-prompt rate per project; if >30% over a 7-day window, log a tuning recommendation (do not auto-disable triggers — operator decides).

**Trigger telemetry and baseline rules:**

- Emit local-only trigger events to `.vibelign/memory_audit.jsonl`; do not mutate `work_memory.json` when a prompt is shown, accepted, dismissed, snoozed, or ignored.
- Keep session suppression in memory only. Persisted trigger events measure UX noise; they must not suppress future prompts by themselves.
- Build any ignored-rate or diff-growth decision from a derived `.vibelign/recovery/trigger_baseline.json` snapshot, not from committed test baselines or handoff memory.
- The first implementation slice is schema-only: audit events can carry sanitized `trigger.id`, `trigger.action`, and `trigger.source`. Later slices may wire prompt-shown/action emission and baseline computation after tests define the event lifecycle.

**Verification:**

```bash
python -m pytest tests/test_handoff_auto_capture.py tests/test_transfer_git_context.py -q
```

Add new targeted tests for:

- Same trigger does not repeat in one session after dismissal.
- Conflicting active intent writes require merge.
- Intent change marks verification stale.

**Exit criteria:**

- Memory review suggestions are useful and dismissible.
- No automatic write changes future AI behavior without confirmation.

## 12. Phase 5: Assisted Partial Recovery

**Purpose:** add selected-file recovery apply only after preview quality is established.

**Entry gate (mandatory — cite from design §6 *Phase 2 Security Gate*):**

Phase 5 baseline implementation exists, but Phase 5 cannot be treated as release-certified or enabled-by-default until **all four** security layers from design §6 are live and verified:

- **Layer 1**: existing secret scanner integrated as the redaction gate for any memory text bound for storage or MCP response.
- **Layer 2 v1**: privacy filter covering local absolute paths, internal hostnames/private-IP ranges, and usernames/home-directory fragments. (Customer-identifier and oversized-log handling can defer to Layer 2 v2.)
- **Layer 3**: per-project + per-tool capability grants persisted with default-deny posture. CLI: `vib mcp grant`. GUI permissions panel can defer to Phase 6.
- **Layer 4**: untrusted-memory boundary verified by negative tests proving memory text cannot reach a command parser. No free-text instruction execution is possible by code construction, not by convention.

In addition, Phase 1 P0 hard SLOs (§15) must show clean instrumentation runs across at least one full release cycle of Phase 1–4. Until these gates are met, Phase 5 remains a default-off baseline implementation rather than an operationally certified release capability.

**Commands / MCP:**

```bash
vib recover --preview
vib recover --file path/to/file.py
vib recover --file path/to/file.py --apply --checkpoint-id ckpt --sandwich-checkpoint-id safety --confirmation 'APPLY ckpt'
```

MCP:

- `recovery_apply` remains denied by default.
- It requires explicit grant, per-operation confirmation, project lock, typed parameters, and checkpoint sandwich.

**Files:**

- Add: `vibelign/core/recovery/apply.py`
- Add: `vibelign/core/recovery/locks.py`
- Modify checkpoint bridge only through existing public APIs.
- Add focused recovery apply tests.

**Tasks:**

- [x] Implement project-level recovery lock.
- [x] Implement checkpoint sandwich precondition.
- [x] Validate `checkpoint_id`, `sandwich_checkpoint_id`, `paths`, and `apply`.
- [x] Canonicalize paths after symlink resolution and constrain to project root.
- [x] Reject parent traversal and generated/cache/build restore targets.
- [x] Require re-confirmation if apply paths differ from preview paths.
- [x] Return restore summary, changed files count, safety checkpoint ID, and verification recommendations.
- [ ] Document `RecoveryApplyRequest.feature_enabled` as audit/traceability metadata only — never a gate. The active gate is the env-backed `is_enabled("RECOVERY_APPLY")` check; any code that switches on `request.feature_enabled` is a security regression. If the field becomes a confusion source in MCP, rename it (`feature_flag_observed`) or remove it; do not let two gate paths coexist.

**Completion note (2026-05-03):** Phase 5 apply is implemented as an explicit, gated selected-file restore path. `recovery_apply` remains denied by default, becomes live only with an explicit per-tool grant and enabled feature flag, requires typed parameters plus `APPLY <checkpoint_id>` confirmation, acquires/releases the project recovery lock, uses the existing checkpoint engine `restore_files` public API, and writes count-only audit events without raw paths.

**Verification:**

```bash
python -m pytest tests/test_checkpoint_cmd_wrapper.py tests/test_mcp_checkpoint_handlers.py tests/test_cross_platform_paths.py tests/test_recovery_path_safety.py tests/test_recovery_planner.py tests/test_recovery_intent_zone.py -q
```

The last three test files (per §17) cover the new apply path: `test_recovery_path_safety.py` enforces the §18 path canonicalization contract, while the planner/intent-zone tests guard against drift-labeling regression now that apply is live.

Add new targeted tests for:

- `recovery_apply` aborts when checkpoint sandwich fails.
- Concurrent apply returns `busy`.
- Apply cannot restore out-of-root paths.
- WSL and Windows-style paths resolve safely.

**Exit criteria:**

- P0 hard SLO tests exist for checkpoint sandwich and memory-as-instruction boundary.
- Recovery apply cannot run from free-text memory instructions.
- User can return to pre-recovery state.

## 13. Phase 6: GUI Agent Cards

**Purpose:** expose memory and recovery state in beginner-friendly GUI cards after service contracts stabilize.

**Files:**

- Add: `vibelign-gui/src/components/agent-memory/SessionMemoryCard.tsx`
- Add: `vibelign-gui/src/components/agent-memory/RecoveryOptionsCard.tsx`
- Modify GUI page routing only as wiring.
- Add GUI integration tests where existing GUI CLI contracts are tested.

**Tasks:**

- [x] Show current goal, decisions, verification freshness, and next action.
- [x] Show current risk summary, changed files count, safe checkpoint candidate, and recovery options.
- [x] Keep editable fields routed through CLI/service commands, not local GUI-only state.
- [x] Display redacted/summarized labels clearly.
- [ ] Maintain a shared JSON schema (e.g. `recovery_plan.schema.json`, `memory_state.schema.json`) generated from the Python dataclasses. GUI integration tests validate the CLI JSON output against this schema so a Python-side rename surfaces as a test failure rather than a runtime error. The schema lives next to the Python models and is regenerated on memory/recovery model changes; the GUI's TypeScript types are derived from the same schema (manual or via a generator) so contracts cannot drift silently.

**Completion note (2026-05-03):** Phase 6 GUI scope is intentionally preview/read-only for beginners. `SessionMemoryCard` reads `vib memory show` through the Tauri CLI bridge, and `RecoveryOptionsCard` reads `vib recover --preview`. Destructive recovery apply remains available only through explicit CLI/MCP surfaces with grants, feature flag, typed parameters, confirmation, lock, sandwich checkpoint, and audit gates; the GUI card does not introduce a second apply model.

**Verification:**

```bash
python -m pytest tests/test_gui_cli_contracts.py -q
npm --prefix vibelign-gui run build
```

**Exit criteria:**

- GUI does not introduce a second memory model.
- Beginner copy avoids internal terms unless needed.
- CLI/MCP/GUI show consistent recovery recommendations.

## 14. Testing Matrix

Required coverage before Phase 5:

| Area | Required cases |
|---|---|
| Memory migration | existing file, malformed file, missing file, cap/compact, downgrade refusal (newer schema_version on older VibeLign) |
| Explicit memory | decisions not auto-written, relevant files separated by explicit/observed |
| Freshness | stale intent, stale verification, intent change cascade |
| Recovery planning | no checkpoint, empty memory, drift candidate, generated-file exclusion |
| Path safety | parent traversal, symlink escape, Windows reserved names, WSL translation |
| Redaction | API key, local path, internal host, long terminal output |
| MCP permission | denied defaults, grant required, audit event written |
| Apply safety | checkpoint sandwich, project lock, path mismatch reconfirmation |
| Memory cap eviction | per-field cap enforcement (decisions 50, recent_events 200, verification 30/scope, relevant_files 100); decisions >90 days move to `archived_decisions[]`; archived decisions never feed `active_intent` |
| Drift accuracy circuit breaker | accuracy <80% over rolling 20-incident window auto-disables drift labeling; recovery falls back to diff-aware mode; user-facing message rendered; recovery still functional in degraded mode |
| Trigger noise | dismissals do not repeat in same session; ignored-prompt rate >30% over 7 days produces a tuning log entry; triggers are non-blocking suggestions |
| Concurrent MCP recovery | second `recovery_apply` during inflight returns `busy` with operation ID and ETA; lock auto-releases on completion or 60s timeout; `recovery_preview`, `memory_summary_read`, `checkpoint_create` are not blocked by the lock |

## 15. P0 Release Gates

No release may enable MCP write/apply or destructive recovery if any gate lacks tests. These gates correspond directly to design §8 *P0 Hard SLOs* and design §7 *P0: Must Not Happen* mitigations.

### Hard behavioral gates (test-enforced)

- `recovery_apply` cannot run without a successful safety checkpoint.
- Memory text cannot become executable instruction.
- MCP memory response cannot bypass secret/privacy filtering.
- Explicitly relevant files cannot be labeled drift candidates.
- Stale `active_intent` cannot be presented as fresh.

### Verification infrastructure gates (rev. 4 design additions)

These are not behaviors — they are mechanisms that must exist for the behavioral gates above to be *measurable*. Without them, P0 SLOs become declarations rather than enforcement.

- **MCP redaction audit log live**: every MCP memory response writes a count-only audit event recording secret_hits, privacy_hits, summarized_fields, and circuit-breaker state. Local-only by default. Random 1% of MCP responses are asynchronously re-scanned to verify the gate fired correctly. Without this, "MCP cannot bypass redaction" is unobservable until external report. (Design §7 P0: MCP exposes raw sensitive context.)
- **P0 occurrence aggregator live**: a local aggregator reads `memory_audit.jsonl` plus derived recovery/trigger baselines and emits a count-only release-window summary for every P0 SLO. Phase gates may cite "0 occurrences" only from this summary, not from one-off tests. Required fields: `slo_id`, `window_start`, `window_end`, `occurrences`, `sample_count`, and `result`.
- **Audit retention live**: `memory_audit.jsonl` rolls over before it becomes operational debt. Default retention is 90 days or 10 MB, preserving any active P0 aggregation window and compacting older rows into count-only summaries under `.vibelign/recovery/`.
- **Drift accuracy circuit breaker functional**: the planner exposes a measurable accuracy state (drift labels confirmed correct vs incorrect by user feedback). When rolling 20-incident accuracy drops below 80%, drift labeling is automatically disabled at the planner layer; recovery continues in diff-aware mode with a user-visible degraded marker. (Design §7 P0: User work incorrectly classified as drift.)
- **Layer 4 boundary verified by negative test**: a test must demonstrate that memory text containing shell-style commands or path-like strings cannot reach any command parser, destructive file operation, or MCP action invocation. The test must fail by construction, not by convention — i.e., the call graph from memory read to command execution or file mutation must be physically absent in the binary. Destructive file operations include delete/restore/overwrite flows and direct calls such as `Path.unlink`, `shutil.rmtree`, and arbitrary-path `write_text` unless the path has passed the recovery path contract. (Design §7 P0: Memory text becomes executable instruction; design §3 Security Model Layer 4.)

## 16. Appendix A: `work_memory.json` Migration Map

Existing memory behavior is anchored in `vibelign/core/work_memory.py` and covered by `tests/test_work_memory.py`, `tests/test_work_memory_record_commit.py`, and `tests/test_work_memory_relevant_api.py`. Phase 2 must migrate additively rather than replacing the existing file shape in one jump.

| Existing field / source | New `MemoryState` field | Migration rule |
|---|---|---|
| `decisions[]` | `decisions[]` | Preserve order. Add `last_updated`, `updated_by`, and `source` metadata if missing. Do not derive new decisions automatically. |
| `verification[]` | `verification[]` | Preserve command/result text. If related file scope is missing, keep the entry but mark it `stale: true` and `scope_unknown: true`. New writers must pass `source` and `related_files` when known; legacy migration may leave them unknown. |
| `relevant_files[]` | `relevant_files[]` | Preserve user-authored entries as explicit. Watch-derived or auto-captured entries become observed entries until user-confirmed. |
| `recent_events[]` | `observed_context[]` | Preserve as supporting context with event kind, timestamp, and source tool. Do not promote recent events into decisions. |
| checkpoint events | `observed_context[]` | Preserve checkpoint ID/message/timestamp when available. Redact or omit full paths. |
| guard/explain summaries | `verification[]` or `risks[]` | Successful guard/test output becomes verification. Warnings, skipped checks, and assumptions become risks. |
| missing `active_intent` | `active_intent` | May propose from latest explicit decision, but store as `proposed: true` until the user confirms. |
| missing `next_action` | `next_action` | Leave `null` and prompt during `vib memory review` or `vib transfer --handoff`. |
| unknown future fields | preserved raw extension bag | Preserve under `unknown_fields` during migration so downgrade/upgrade cycles do not strip data. |

Migration test fixtures:

- legacy file with decisions only.
- legacy file with verification and no file scope.
- new verification write with explicit related file scope.
- automatic guard/explain capture with observed source and inferred related file scope.
- malformed file preserved as backup with minimal memory mode initialized.
- newer `schema_version` opened by older VibeLign in read-only downgrade mode.

## 17. Appendix B: Test File Mapping

Use existing naming conventions: memory tests use `test_work_memory*`, MCP tests use `test_mcp_*`, and CLI surface tests use `test_vib_*`.

| Area | Existing references | New/expanded tests |
|---|---|---|
| Memory core | `tests/test_work_memory.py` | `tests/test_work_memory_migration.py`, `tests/test_work_memory_freshness.py` |
| Memory commit/events | `tests/test_work_memory_record_commit.py` | Add cases for observed context and audit-safe event summaries. |
| Relevant files API | `tests/test_work_memory_relevant_api.py` | Add explicit vs observed relevant-file separation. |
| Transfer/handoff | `tests/test_transfer_cli_docs.py`, `tests/test_transfer_git_context.py`, `tests/test_handoff_auto_capture.py` | Add guided review and stale verification cases. |
| Recovery planner | none yet | `tests/test_recovery_planner.py`, `tests/test_recovery_intent_zone.py` |
| Recovery path safety | `tests/test_cross_platform_paths.py`, `tests/test_project_root_resolution.py` | Add `tests/test_recovery_path_safety.py`. |
| MCP memory | `tests/test_mcp_runtime.py`, `tests/test_mcp_tool_loader.py` | `tests/test_mcp_memory_handlers.py` |
| MCP recovery | `tests/test_mcp_checkpoint_handlers.py`, `tests/test_mcp_transfer_handlers.py` | `tests/test_mcp_recovery_handlers.py` |
| Secret/privacy redaction | `tests/test_secret_scan.py` | `tests/test_memory_redaction.py` |
| Audit aggregator/retention/integrity | none yet | `tests/test_memory_aggregator.py` (per-SLO occurrence counting), `tests/test_memory_retention.py` (rollover preserves active P0 window, `max_active_window_days` cap), `tests/test_memory_audit_integrity.py` (sequence_number gap/duplicate detection) |
| Platform edge-case (Windows / macOS / WSL) | `tests/test_cross_platform_paths.py`, `tests/test_recovery_path_safety.py`, `tests/test_recovery_locks.py`, `tests/test_memory_audit.py` | Add cases enumerated in §3 *Windows/macOS implementation edge-case checklist*: lock TTL cooperative cancel, WSL execution-context canonicalization (cmd / PowerShell / Ubuntu / GUI), Windows ADS / reserved names / trailing-dot-space, macOS APFS case-insensitive + Unicode NFC/NFD + case-sensitive APFS detection, audit JSONL CRLF/LF writer policy, UTF-8 BOM rejection in stored files, `patch_suggester` output normalization. Each case is co-located with its existing test family rather than getting its own file. |
| GUI contracts | `tests/test_gui_cli_contracts.py` | Add Session Memory and Recovery Options command-contract cases in Phase 6. |

Phase verification commands may reference broad existing files, but each phase must also add focused tests for its new service layer. Do not hide new memory/recovery behavior only inside generic CLI tests.

## 18. Appendix C: Path Canonicalization Contract

Recovery paths are high-risk because they can overwrite files. All recovery preview/apply paths must flow through one contract before use.

```python
normalize_recovery_path(project_root: Path, user_path: str, *, trusted_local_cli: bool = False) -> NormalizedPath
```

Rules:

- MCP accepts only project-relative paths.
- CLI may accept absolute paths only in trusted-local mode; absolute paths are converted to project-relative paths after root containment checks.
- Normalize `\` to `/` for stored relative paths.
- Resolve symlinks before project-root containment checks.
- Reject `..` traversal before and after normalization.
- Reject generated/cache/build directories and known output folders.
- Reject out-of-root paths after canonicalization.
- Reject Windows reserved names such as `CON`, `PRN`, `AUX`, and `NUL` in path segments.
- Detect WSL `/mnt/c/...` and Windows `C:\...` equivalence only after canonical project-root resolution.
- Return both canonical absolute path and stored project-relative path.
- Error messages should name the safety rule violated without echoing full sensitive local paths.

Minimum return shape:

```json
{
  "absolute_path": "<internal only>",
  "relative_path": "src/pages/Login.tsx",
  "display_path": "src/pages/Login.tsx",
  "was_absolute_input": false
}
```

`absolute_path` is for internal logic only. It must never appear in:

- MCP responses (any tool, any phase).
- `AuditEvent` records or any local audit/log file.
- User-facing error messages, recovery output, or handoff documents.
- GUI surfaces.

Use `display_path` (project-relative) wherever a path is exposed externally. Privacy filter (Layer 2) must reject any output containing `absolute_path` content as a fail-closed check.

## 19. Appendix D: Critical-Gate Traceability Matrix

Every release-blocking gate must map to a test and an observable artifact. This matrix covers the P0 hard gates from §15 plus high-priority operational gates (concurrency, path safety) that block Phase 5 even if they are not strictly P0 in design §7. Rows are tagged so the gate class is unambiguous.

| Gate | Class | Required test | Required artifact |
|---|---|---|---|
| Checkpoint sandwich required | P0 (§15 hard) | `test_recovery_apply_requires_sandwich` | `AuditEvent` includes `sandwich_checkpoint_id` for successful `recovery_apply`. |
| Memory text not executable | P0 (§15 hard) | `test_memory_text_never_reaches_command_executor` | Negative call-graph/API test showing memory text is data only. |
| MCP redaction required | P0 (§15 hard) | `test_mcp_memory_summary_redacts_secret` | `AuditEvent.redaction.secret_hits` and filtered response markers. |
| Explicit relevant file not drift | P0 (§15 hard) | `test_explicit_relevant_file_not_drift` | `RecoveryPlan.drift_candidates[]` excludes explicit relevant files. |
| Stale active intent labeled stale | P0 (§15 hard) | `test_stale_intent_not_presented_fresh` | `MemoryState.active_intent.stale = true` and handoff/recovery output says stale. |
| MCP redaction audit log live | P0 (§15 infra) | `test_mcp_audit_event_written_for_each_response` | `memory_audit.jsonl` row exists for every MCP memory response, count fields populated, no raw content. |
| P0 occurrence aggregator live | P0 (§15 infra) | `test_p0_occurrence_aggregator_reports_zero_window` | Count-only summary exists for each P0 SLO and gates on nonzero occurrence counts. |
| Audit retention preserves gates | P0/P1 infra | `test_memory_audit_retention_preserves_active_p0_window` | Old audit rows compact into summaries without deleting the active P0 aggregation window. |
| Layer 4 boundary by construction | P0 (§15 infra) | `test_no_execution_or_file_mutation_path_from_memory_call_graph` | Static call-graph assertion that `memory.*` modules do not import or invoke `subprocess`, `os.system`, command-dispatch entry points, or destructive file operations without typed path validation. |
| Drift circuit breaker works | P0 (§15 infra) | `test_drift_accuracy_circuit_breaker_degrades` | `AuditEvent.circuit_breaker_state = degraded` and planner falls back to diff-aware mode. |
| Concurrent apply locked | P1 (operational) | `test_recovery_apply_busy_when_lock_exists` | Result is `busy` with operation ID and ETA. |
| Path escape rejected | P1 (operational) | `test_recovery_path_out_of_root_rejected` | User-facing error without full sensitive local path. |
| Post-sandwich manual edit detected | P1 (trust) | `test_recovery_apply_blocks_paths_changed_after_sandwich` | Apply result reports changed-after-sandwich count and requires second confirmation. |

## 20. Appendix E: Anchor Plan for New Modules

Existing Python anchor style is demonstrated by `vibelign/core/work_memory.py`: `# === ANCHOR: NAME_START ===` and `# === ANCHOR: NAME_END ===`, using upper snake case. New Python modules should follow that style so future patches can target small, stable regions.

Language conventions:

- Python: `# === ANCHOR: NAME_START ===` / `# === ANCHOR: NAME_END ===`.
- Rust: `// === ANCHOR: NAME_START ===` / `// === ANCHOR: NAME_END ===`; place anchors around cohesive modules or high-risk helpers such as path guards, recovery apply, and backup DB mutation boundaries.
- TS/TSX: `// === ANCHOR: NAME_START ===` / `// === ANCHOR: NAME_END ===` at the component/module boundary. For JSX-only regions where line comments are invalid, use `{/* === ANCHOR: NAME_START === */}` / `{/* === ANCHOR: NAME_END === */}` inside JSX.
- Use upper snake case for all anchor names. Sub-anchors use the existing double-underscore convention (`MODULE__SECTION_START`).

| File | Required anchors |
|---|---|
| `vibelign/core/memory/models.py` | `MEMORY_MODELS_START` / `MEMORY_MODELS_END` |
| `vibelign/core/memory/store.py` | `MEMORY_STORE_START` / `MEMORY_STORE_END` |
| `vibelign/core/memory/review.py` | `MEMORY_REVIEW_START` / `MEMORY_REVIEW_END` |
| `vibelign/core/memory/redaction.py` | `MEMORY_REDACTION_START` / `MEMORY_REDACTION_END` |
| `vibelign/core/memory/freshness.py` | `MEMORY_FRESHNESS_START` / `MEMORY_FRESHNESS_END` |
| `vibelign/core/memory/audit.py` | `MEMORY_AUDIT_START` / `MEMORY_AUDIT_END` |
| `vibelign/core/recovery/models.py` | `RECOVERY_MODELS_START` / `RECOVERY_MODELS_END` |
| `vibelign/core/recovery/signals.py` | `RECOVERY_SIGNALS_START` / `RECOVERY_SIGNALS_END` |
| `vibelign/core/recovery/intent_zone.py` | `RECOVERY_INTENT_ZONE_START` / `RECOVERY_INTENT_ZONE_END` |
| `vibelign/core/recovery/planner.py` | `RECOVERY_PLANNER_START` / `RECOVERY_PLANNER_END` |
| `vibelign/core/recovery/render.py` | `RECOVERY_RENDER_START` / `RECOVERY_RENDER_END` |
| `vibelign/core/recovery/locks.py` | `RECOVERY_LOCKS_START` / `RECOVERY_LOCKS_END` |
| `vibelign/core/recovery/apply.py` | `RECOVERY_APPLY_START` / `RECOVERY_APPLY_END` |
| `vibelign/commands/vib_memory_cmd.py` | `VIB_MEMORY_CMD_START` / `VIB_MEMORY_CMD_END` |
| `vibelign/commands/vib_recover_cmd.py` | `VIB_RECOVER_CMD_START` / `VIB_RECOVER_CMD_END` |
| `vibelign/mcp/mcp_memory_handlers.py` | `MCP_MEMORY_HANDLERS_START` / `MCP_MEMORY_HANDLERS_END` |
| `vibelign/mcp/mcp_recovery_handlers.py` | `MCP_RECOVERY_HANDLERS_START` / `MCP_RECOVERY_HANDLERS_END` |

Anchor rules:

- Add one top-level anchor in every new Python source file.
- Add sub-anchors only when a file starts accumulating a second responsibility.
- **Sub-anchor naming convention**: use double-underscore separator, matching the established convention in `vibelign/core/work_memory.py` (`WORK_MEMORY__TRUNCATE_TEXT_START`, `WORK_MEMORY__SAFE_RELATIVE_PATH_START`, `WORK_MEMORY__NORMALIZE_EVENT_START`). Top-level anchors stay single-underscore (`MEMORY_MODELS_START`); sub-anchors use double-underscore (`MEMORY_MODELS__RECOVERY_OPTION_START`). Single-underscore sub-anchors are rejected — they break parsing of the existing patch tooling that relies on the `MODULE__FUNCTION` split.
- Do not place feature logic outside anchors.
- Keep entry/wiring files thin; anchors in command and MCP handler files should wrap delegation/wiring only.

### Modifying existing anchored files

Phase 3 touches existing files: `vibelign/mcp/mcp_tool_specs.py`, `vibelign/mcp/mcp_handler_registry.py`, `vibelign/mcp/mcp_dispatch.py`. These already contain anchors. CLAUDE.md rule 4 (앵커 경계를 지키세요) requires changes to stay inside existing anchor boundaries.

Rules for modifying existing anchored files:

- Locate the existing anchor that owns the area being changed before editing. Use `mcp__vibelign__anchor_list` or `vib anchor list` to enumerate.
- Add new content **inside** the relevant existing anchor — never as a new top-level anchor in an existing file.
- If no fitting anchor exists for the new content, propose a new sub-anchor (double-underscore form) and confirm with the file owner before editing. Do not silently create top-level anchors in existing files.
- Tool spec entries added to `mcp_tool_specs.py` must go inside the existing tool-specs anchor. Handler registration in `mcp_handler_registry.py` and `mcp_dispatch.py` must go inside the existing registry/dispatch anchors.
- Run `vib guard --strict` after editing to confirm no anchor boundary was crossed.

## 21. Resolved Decisions

- Memory audit events remain local JSONL for this phase; SQLite migration is a future backup-engine concern, not part of Memory/Recovery completion.
- `vib recover --explain` and `vib recover --preview` are read-only and do not run guard/explain automatically.
- Memory compaction is deferred until memory growth is observed; current caps and archive fields prevent unbounded active memory growth.
- GUI cards ship as normal Home cards in Phase 6, not behind a separate experimental flag.
- `intent_zone` results are recomputed per preview so recovery reflects the current working tree.
- Memory caps apply only to `work_memory.json`; backup DB retention remains engine-level and independent.
- Phase 5 recovery apply is serialized by the project recovery lock around selected-file restore. The sandwich checkpoint ID is a required precondition supplied to the apply call.
- Implementers follow existing repository conventions in `AGENTS.md` / `AI_DEV_SYSTEM_SINGLE_FILE.md`; this spec does not add a separate workflow.

## 22. Implementation Order Summary

1. Build recovery read-only planner first.
2. Build memory service second.
3. Wire handoff through memory service.
4. Add MCP read-only/safe-write endpoints with redaction, audit log, and Layer 4 boundary verified by negative test (§15 infra gates must pass before this step exits).
5. Add proactive hygiene triggers.
6. Add apply only after preview quality and safety tests exist.
7. Add GUI last as presentation over stable service APIs.
