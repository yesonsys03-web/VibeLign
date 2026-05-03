# VibeLign Memory + Recovery Agent Implementation Spec

Date: 2026-05-02
Status: Implementation spec draft (rev. 3 — adds double-underscore sub-anchor convention, rules for modifying existing anchored files, audit-log + Layer-4 rows in traceability matrix, new tests included in each phase's verification command, ID generation rule, dismiss/snooze CLI surface, schema-conflict clarification, internal-only absolute path rule, Layer 4 in implementation order)
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
└─ audit.py

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
- `verification[]` records command, result, timestamp, related file scope, and stale status.
- `risks[]` stores unresolved warnings, skipped tests, assumptions, and redaction notes.
- `observed_context[]` stores supporting evidence such as touched files, commits, checkpoints, guard/explain summaries, and watch events.
- Caps: `decisions[]` last 50, `recent_events[]` last 200, `verification[]` last 30 per scope, `relevant_files[]` last 100.

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
  "result": "success"
}
```

`paths_count` separates in-zone vs drift to enable post-hoc accuracy measurement (§14, §15) without storing raw paths. `circuit_breaker_state` is `active` (drift labeling enabled) or `degraded` (drift labeling auto-disabled per design §7 P0 mitigation); recording the state per event lets audits prove the breaker fired at the right moment.

## 6. Storage and Migration

Phase 1 can read existing files without schema migration. Phase 2 introduces memory schema ownership.

Recommended storage:

```text
.vibelign/
├─ work_memory.json          # existing user/project memory, migrated additively
├─ memory_audit.jsonl        # local-only audit events, gitignored
└─ recovery/
   ├─ last_preview.json      # local-only, redacted/summarized
   └─ locks/                 # Phase 5 recovery lock files
```

Migration rules:

- Add `schema_version` to memory state.
- Existing `work_memory.json` fields remain valid.
- New fields are optional during migration and normalized on first write.
- If project-local memory artifacts are created, ensure `.gitignore` covers them by default.
- If migration finds malformed memory, preserve the raw file as a backup and start from minimal memory mode.

Forward compatibility — VibeLign newer than the file: additive migration as above.

Backward compatibility — VibeLign **older** than the file (downgrade): not silently supported. When an older VibeLign opens a `work_memory.json` with `schema_version` greater than its known max, behavior is:

1. Read in safe mode (no schema mutation, no field assumption).
2. Surface only the fields the older VibeLign understands.
3. Print a one-line warning: `memory schema_version=N is newer than this VibeLign supports — upgrade or run with --legacy-readonly`.
4. Refuse to write `decisions[]`, `active_intent`, `next_action`, or `relevant_files[]` until the user upgrades or explicitly opts into legacy read-only mode.

This avoids silent field stripping that would damage memory written by a newer install.

Interaction with §16 unknown_fields preservation: §16 covers *truly unknown* fields the older VibeLign has never heard of — those are bagged into `unknown_fields` and round-tripped on next write. The §6 downgrade refusal above covers *known fields with newer semantics* (e.g., a future `from_previous_intent` flag attached to an existing field). Known-but-newer-semantics fields are not bagged; they trigger the read-only downgrade refusal because writing them with old semantics would corrupt project truth. The two rules do not overlap: schema-version dictates which path applies.

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

- [ ] Define `RecoverySignalSet`, `IntentZone`, `DriftCandidate`, `RecoveryOption`, and `RecoveryPlan` dataclasses.
- [ ] Collect current git diff and untracked file list.
- [ ] Read latest checkpoint metadata and backup DB rows when available.
- [ ] Read project map categories and anchor metadata when available.
- [ ] Read latest guard/explain report summaries when available.
- [ ] Infer intent zone using explicit memory first, recent patch targets second, project-map category third, anchor co-occurrence later, and diff-aware fallback last.
- [ ] Label files outside the inferred zone as `drift_candidate`, never `unrelated`.
- [ ] Recommend one of: no-op, explain-only, targeted repair, partial restore preview, or full rollback preview.
- [ ] Render 2–3 recovery options in plain language.
- [ ] Never modify files in this phase.

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

- [ ] Implement additive migration for `work_memory.json` to `schema_version = 1`.
- [ ] Preserve current decisions, verification, relevant files, and recent events.
- [ ] Add freshness metadata: `last_updated`, `updated_by`, `from_previous_intent`, and `stale`.
- [ ] Implement explicit write APIs for `decisions[]`, `active_intent`, `relevant_files[]`, and `next_action`.
- [ ] Implement observed-context append APIs for commits, checkpoints, reports, touched files, and verification results.
- [ ] Implement memory compaction caps and `archived_decisions[]`.
- [ ] Make `vib transfer --handoff` read from `MemoryState` and show stale verification warnings.
- [ ] Keep user confirmation required before writing intent-shaping fields.

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

- [ ] Wrap existing secret scanner in a memory redaction interface.
- [ ] Add privacy filter v1: local absolute paths, usernames/home fragments, internal hosts, private IPs, and oversized terminal output.
- [ ] Implement local-only audit event writer.
- [ ] Implement `memory_summary_read` with redacted summaries and provenance tags.
- [ ] Implement `recovery_preview` using the Phase 1 planner.
- [ ] Implement `checkpoint_create` as safe-write, project-root scoped.
- [ ] Ensure all MCP tools are non-interactive and parameterized.
- [ ] Deny `memory_full_read`, `memory_write`, `recovery_apply`, and `handoff_export` until later phases explicitly enable them.

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

- [ ] Implement stale intent detection: older than 24h or unchanged across 5+ commits.
- [ ] Implement stale verification detection when related files change after validation.
- [ ] Implement conflict detection for same-field writes within `memory.conflict_window_seconds` default 60 seconds.
- [ ] Implement dismiss/snooze logging per session. Surface: inline within `vib memory review` (interactive prompt offers Accept / Dismiss / Snooze choices); no separate `vib memory snooze` command. Snoozed triggers persist for the session only — they reset on next CLI invocation. The dismiss/snooze action is the only place where a trigger ID becomes user-visible.
- [ ] Implement trigger thresholds (inlined from design §3 *Trigger Conditions*):
  - `decisions[]` empty AND `patch_apply` invoked ≥3 times in current session.
  - `active_intent` age >6 hours AND diff growth >40 lines since last update.
  - `verification[]` stale (newest result older than newest patch).
  - A patch touches a file outside both explicit `relevant_files[]` AND the inferred intent zone (§5 fallback).
  - `transfer --handoff` invoked without a confirmed `next_action`.
- [ ] Render prompts as suggestions, never blocking modals.
- [ ] Track ignored-prompt rate per project; if >30% over a 7-day window, log a tuning recommendation (do not auto-disable triggers — operator decides).

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

Phase 5 cannot start until **all four** security layers from design §6 are live and verified:

- **Layer 1**: existing secret scanner integrated as the redaction gate for any memory text bound for storage or MCP response.
- **Layer 2 v1**: privacy filter covering local absolute paths, internal hostnames/private-IP ranges, and usernames/home-directory fragments. (Customer-identifier and oversized-log handling can defer to Layer 2 v2.)
- **Layer 3**: per-project + per-tool capability grants persisted with default-deny posture. CLI: `vib mcp grant`. GUI permissions panel can defer to Phase 6.
- **Layer 4**: untrusted-memory boundary verified by negative tests proving memory text cannot reach a command parser. No free-text instruction execution is possible by code construction, not by convention.

In addition, Phase 1 P0 hard SLOs (§15) must show clean instrumentation runs across at least one full release cycle of Phase 1–4. Phase 5 ships behind a default-off feature flag until these gates are met.

**Commands / MCP:**

```bash
vib recover --preview
vib recover --file path/to/file.py
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

- [ ] Implement project-level recovery lock.
- [ ] Implement checkpoint sandwich precondition.
- [ ] Validate `checkpoint_id`, `sandwich_checkpoint_id`, `paths`, and `apply`.
- [ ] Canonicalize paths after symlink resolution and constrain to project root.
- [ ] Reject parent traversal and generated/cache/build restore targets.
- [ ] Require re-confirmation if apply paths differ from preview paths.
- [ ] Return restore summary, changed files count, safety checkpoint ID, and verification recommendations.

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

- [ ] Show current goal, decisions, verification freshness, and next action.
- [ ] Show current risk summary, changed files count, safe checkpoint candidate, and recovery options.
- [ ] Keep editable fields routed through CLI/service commands, not local GUI-only state.
- [ ] Display redacted/summarized labels clearly.

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
- **Drift accuracy circuit breaker functional**: the planner exposes a measurable accuracy state (drift labels confirmed correct vs incorrect by user feedback). When rolling 20-incident accuracy drops below 80%, drift labeling is automatically disabled at the planner layer; recovery continues in diff-aware mode with a user-visible degraded marker. (Design §7 P0: User work incorrectly classified as drift.)
- **Layer 4 boundary verified by negative test**: a test must demonstrate that memory text containing shell-style commands or path-like strings cannot reach any command parser, file operation, or MCP action invocation. The test must fail by construction, not by convention — i.e., the call graph from memory read to command execution must be physically absent in the binary. (Design §7 P0: Memory text becomes executable instruction; design §3 Security Model Layer 4.)

## 16. Appendix A: `work_memory.json` Migration Map

Existing memory behavior is anchored in `vibelign/core/work_memory.py` and covered by `tests/test_work_memory.py`, `tests/test_work_memory_record_commit.py`, and `tests/test_work_memory_relevant_api.py`. Phase 2 must migrate additively rather than replacing the existing file shape in one jump.

| Existing field / source | New `MemoryState` field | Migration rule |
|---|---|---|
| `decisions[]` | `decisions[]` | Preserve order. Add `last_updated`, `updated_by`, and `source` metadata if missing. Do not derive new decisions automatically. |
| `verification[]` | `verification[]` | Preserve command/result text. If related file scope is missing, keep the entry but mark it `stale: true` and `scope_unknown: true`. |
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
| Layer 4 boundary by construction | P0 (§15 infra) | `test_no_command_path_from_memory_call_graph` | Static call-graph assertion that `memory.*` modules do not import or invoke `subprocess`, `os.system`, or command-dispatch entry points. |
| Drift circuit breaker works | P0 (§15 infra) | `test_drift_accuracy_circuit_breaker_degrades` | `AuditEvent.circuit_breaker_state = degraded` and planner falls back to diff-aware mode. |
| Concurrent apply locked | P1 (operational) | `test_recovery_apply_busy_when_lock_exists` | Result is `busy` with operation ID and ETA. |
| Path escape rejected | P1 (operational) | `test_recovery_path_out_of_root_rejected` | User-facing error without full sensitive local path. |

## 20. Appendix E: Anchor Plan for New Modules

Existing Python anchor style is demonstrated by `vibelign/core/work_memory.py`: `# === ANCHOR: NAME_START ===` and `# === ANCHOR: NAME_END ===`, using upper snake case. New Python modules should follow that style so future patches can target small, stable regions.

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

## 21. Open Questions

- Should memory audit events live in JSONL or SQLite once backup DB history becomes the dominant local data store?
- Should `vib recover --explain` read latest guard/explain reports only, or optionally run them when stale?
- Should Phase 2 include `vib memory compact`, or defer compaction until memory growth is observed?
- Should GUI cards ship behind an experimental flag before Phase 6?
- Should `intent_zone` results be cached per-session or recomputed each preview? Caching cuts repeated planner cost; recomputing reflects fresh git state. Default likely "cache with 60s TTL keyed on git HEAD + uncommitted file set hash".
- How do memory caps (decisions 50, recent_events 200, etc.) interact with the existing backup DB retention policy? Caps are advisory for `work_memory.json`; backup DB retention is engine-level. They should not contradict — confirm before Phase 2.
- Does the Phase 5 project-level recovery lock include the safety-checkpoint creation step, or are the two operations separately serializable? Choosing "lock includes sandwich" simplifies failure modes but extends lock duration.
- Implementer workflow: should this spec require contributors to follow VibeLign's standard `vib doctor → vib anchor → vib checkpoint → work → vib guard → vib checkpoint` cycle per CLAUDE.md, or is that left to existing repo conventions?

## 22. Implementation Order Summary

1. Build recovery read-only planner first.
2. Build memory service second.
3. Wire handoff through memory service.
4. Add MCP read-only/safe-write endpoints with redaction, audit log, and Layer 4 boundary verified by negative test (§15 infra gates must pass before this step exits).
5. Add proactive hygiene triggers.
6. Add apply only after preview quality and safety tests exist.
7. Add GUI last as presentation over stable service APIs.
