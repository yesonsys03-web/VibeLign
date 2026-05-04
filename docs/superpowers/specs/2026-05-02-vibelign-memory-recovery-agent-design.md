# VibeLign Memory + Recovery Agent Design

Date: 2026-05-02
Status: Completed product design (rev. 6 — Memory/Recovery direction finalized through Phase 6; implementation baseline and remaining hardening backlog are tracked in `docs/superpowers/specs/2026-05-02-vibelign-memory-recovery-agent-implementation-spec.md` and `docs/superpowers/plans/2026-05-03-memory-recovery-agent-completion-trace.md`)

## 1. Why This Direction Comes First

Among the broader VibeLign agent ideas, the strongest near-term direction is to focus on:

1. Project Memory / Handoff Agent
2. Recovery Agent

These two directions fit VibeLign's current strengths better than a fully autonomous coding supervisor.

VibeLign already has the core ingredients:

- `PROJECT_CONTEXT.md` for session transfer.
- `work_memory.json` for decisions, verification, relevant files, and recent events.
- `vib transfer --handoff` for AI-to-AI continuity.
- `vib checkpoint`, `vib undo`, and `vib history` for recovery.
- Rust backup DB and restore previews for deeper backup inspection.
- `vib explain` and `vib guard` for post-change understanding and safety checks.
- Project map and anchor metadata for understanding file roles and safe edit zones.

The product opportunity is not to compete with coding agents. Claude, Cursor, Codex, and OpenCode can write code. VibeLign can become the agent that remembers what those tools were trying to do and helps recover safely when they go wrong.

## 2. Product Concept

Positioning:

> VibeLign is the AI work memory and recovery agent for vibe coding.

The Memory Agent preserves the user's intent, decisions, relevant files, verification state, and next action.

The Recovery Agent uses that memory, plus checkpoints and backups, to recommend the safest path when the project breaks or the user loses confidence.

Together, they answer two high-value questions:

1. “What were we doing, and what should the next AI do?”
2. “Something broke. What is the safest way back?”

### Foundational Product Rule

Recovery must not look like an automatic rollback product in early versions. The trusted shape — applicable across all phases, MCP and CLI alike — is:

1. **Explain** what changed.
2. **Preview** recovery options.
3. **Create a safety checkpoint** (sandwich) before any destructive step.
4. **Apply** only after explicit confirmation.

Every feature in §3–§7 should be readable as an instance of this 4-step shape. If a proposed feature breaks the shape, the feature is wrong, not the rule.

### Guided + Assisted Recovery Agent Contract

The next product direction is **not** a fully autonomous recovery bot. It is a guided safety agent that helps the user understand, choose, and approve recovery.

User-facing promise:

> VibeLign explains the situation, recommends the safest next step, previews what would change, saves the current state, and only applies a limited recovery after the user approves it.

Behavior contract:

| Stage | Agent may do | User approval | File changes |
|---|---|---:|---:|
| Explain | Summarize what looks wrong in middle-school-level language. | No | No |
| Recommend | Suggest the safest option and alternatives. | No | No |
| Preview | Show affected files, risk, and checkpoint candidate. | No | No |
| Prepare | Create or request a safety checkpoint before recovery. | Yes, when surfaced as part of an apply flow | Checkpoint only |
| Apply | Restore only the user-selected files or module. | Yes, explicit confirmation required | Yes, limited scope |
| Result | Explain what changed and what to verify next. | No | No |

Hard boundaries:

- No code-changing recovery runs from memory text, handoff text, or AI free-form advice.
- No full rollback as the default recommendation when a smaller selected-file recovery is plausible.
- No GUI destructive action unless it follows the same service-layer preview, checkpoint sandwich, confirmation, lock, path validation, and audit gates as CLI/MCP.
- No hidden apply. The user must see what will change before anything destructive happens.
- No beginner-facing technical dump. Recovery explanations must translate logs, JSON, and tool output into plain-language next steps while preserving exact details for local audit/debug surfaces.

This contract combines the useful parts of a Guided Agent and an Assisted Apply Agent: the product should do enough to remove user anxiety, but not so much that it becomes an untrusted automatic rollback system.

## 3. Memory Agent

### Goal

The Memory Agent keeps the project understandable across AI sessions and tools. It should produce a handoff that a new AI can read in under one minute and use immediately.

### Memory Model

The memory should be small and structured, not a raw transcript dump.

Recommended fields:

- **Active intent**: the current goal or guiding decision.
- **Decisions**: important product or architecture choices, with a short reason.
- **Relevant files**: files that matter now, plus why they matter.
- **Verification**: commands run, results, and whether the result is stale.
- **Risks**: unresolved warnings, risky edits, skipped tests, or assumptions.
- **Next action**: the single best next step.

Definitions:

- **Explicit memory**: user-confirmed memory such as `decisions[]`, explicitly marked relevant files, and confirmed next actions.
- **Observed context**: automatically captured supporting evidence such as touched files, commits, checkpoints, guard/explain summaries, and watch events.
- **Intent zone**: the set of files and anchors that appear relevant to the current work, derived first from explicit memory and then from fallback signals in §5.
- **Drift candidate**: a changed file outside the intent zone. It is not automatically wrong; it is a candidate the user should review.
- **Safe checkpoint candidate**: a checkpoint that predates the risky change, is inside the current project root, and has enough metadata for preview before restore.
- **First meaningful patch**: the first post-handoff patch or edit that touches a project source file, excluding generated/cache/build files.

### Automatic Capture

VibeLign can safely capture these without asking the user every time:

- Checkpoint creation events.
- Git commit events.
- Guard and explain report summaries.
- Files touched by patch, restore, or backup flows.
- Verification command results.
- Release/tag events.
- Stale verification warnings when files change after a test/build.

Automatic capture must preserve the existing trust split:

- `decisions[]` remain explicit only. The agent may propose an active intent, but it must not silently write a decision because `decisions[-1]` becomes project truth for handoff.
- Explicit relevant files and watch-derived files stay separate. Explicit entries can appear as handoff-relevant files; watch-derived entries remain supporting context until confirmed.
- Stale watch or work-memory data is a secondary signal. Git status, recent commits, explicit verification, and user-confirmed handoff fields have higher priority.

Verification capture has an additional trust split:

- `verification[].source` must distinguish user-confirmed verification (`explicit`) from tool-observed verification (`observed`).
- `verification[].related_files` should be filled whenever the command or tool scope is known. If scope cannot be inferred, store `scope_unknown: true` and treat that entry as lower-confidence in handoff and recovery output.
- Scope inference responsibility belongs to the tool that records the verification first. Patch/guard/MCP flows should pass known touched files; transfer/handoff flows may fall back to recent changed files; manual text entry may remain scope-unknown but must be labeled as such.

### Explicit User Confirmation

These should require explicit confirmation because they shape future AI behavior:

- Active intent changes.
- Product decisions.
- Architecture decisions.
- “This file is relevant because...” notes.
- “The next action is...” handoff statements.

This distinction prevents noisy memory. Routine progress logs should not become project truth.

### Trigger Conditions

Memory becomes an *agent* only when it knows when to interrupt the user. Without triggers, `vib memory review` is just another command nobody runs. The agent should proactively suggest a review when any of these conditions hold:

- `decisions[]` is empty but `patch_apply` has run 3 or more times in the current session.
- `active_intent` is older than 6 hours and the diff has grown by more than 40 lines since.
- `verification[]` is stale (newest guard/test result is older than the newest patch).
- A patch touches a file outside both explicit relevant files and the current inferred intent zone (see §5 fallback).
- `transfer --handoff` is invoked without a confirmed `next_action`.

Triggers must be **suggestions, not blocking modals**. The agent surfaces a one-line prompt; the user accepts, dismisses, or snoozes. Each dismissal is logged so the same trigger does not repeat in the same session.

### Memory Hygiene

Memory rots. The agent must manage that, not assume freshness.

- **Stale intent**: every field carries a `last_updated` timestamp and `updated_by` tool tag. `active_intent` older than 24h or unchanged across 5+ commits triggers a "still your goal?" prompt.
- **Tool-of-record**: when two AI tools (e.g. Claude Code and Cursor) write the same field within a short window, the agent surfaces both versions and asks the user to merge — never silent overwrite.
- **Intent change cascade**: when `active_intent` changes, `verification[]` is auto-marked stale and `relevant_files[]` is preserved but tagged `from_previous_intent` until reconfirmed in the next review.

Schema note:

Per-field freshness metadata such as `last_updated`, `updated_by`, and `from_previous_intent` is a schema migration from the current `work_memory.json` model. It should be introduced deliberately rather than assumed to exist.

### Security Model

Memory and handoff files can accidentally capture API keys, tokens, private paths, internal URLs, customer identifiers, or terminal output. The Memory + Recovery Agent therefore needs a stronger security model than “save useful context.”

Security principle:

> Memory is local-first, redacted-by-default, and permission-gated before leaving VibeLign.

The model has four layers.

#### Layer 1: Existing Secret Scanner Reuse

VibeLign should not build a separate secret system for API keys and tokens. It should reuse the existing `vib secrets` / secret scan engine as the first redaction gate before memory is persisted or exposed through MCP.

Policy:

- Run the existing secret scanner on any text blob that would be stored in memory, written to `PROJECT_CONTEXT.md`, or returned through MCP.
- Store structured summaries by default, not raw terminal output.
- If secret scan finds API keys, tokens, private keys, `.env`-like content, or high-confidence secret patterns, redact the value and mark the memory field as redacted.
- Keep the existing `vibelign: allow-secret` style exception concept for rare false positives, but require explicit user confirmation when memory/handoff export is involved.

#### Layer 2: Privacy Filter for Non-Secret Sensitive Data

The existing secret scanner is necessary but not sufficient. Some sensitive data is not technically a secret: local usernames, full file paths, internal hostnames, customer names, and long terminal logs may still be inappropriate for MCP or public handoff export.

Memory should therefore add a lightweight privacy filter on top of secret scanning.

Privacy filter candidates:

- Local absolute paths such as `/Users/name/...` or `C:\Users\name\...`.
- Internal URLs and hosts such as `localhost`, private IP ranges, and non-public company domains.
- Usernames, home directory fragments, and machine names.
- Customer/project identifiers when they appear in terminal output or generated summaries.
- Oversized raw command output, especially logs containing many paths, environment details, or stack traces.

Default behavior:

- Keep local paths in internal-only memory when needed for recovery.
- Redact or shorten paths in handoff/MCP output unless the user explicitly requests full paths.
- Store terminal output as summarized findings, not raw logs, unless the user opts in.
- Mark filtered fields as `redacted` or `summarized` so a future AI knows information was intentionally withheld.

#### Layer 3: MCP Permission Gate

MCP is the main exfiltration boundary. Once memory is available to external AI tools, VibeLign must assume the receiving tool may send content to a remote model provider.

Default MCP posture:

- Read-only by default.
- Redacted summaries by default.
- Project-root scoped.
- No raw terminal output by default.
- No destructive recovery through MCP unless explicitly enabled.

Suggested MCP capabilities (underscore form, consistent with existing `mcp__vibelign__*` tools):

- `memory_summary_read`: read redacted handoff summary.
- `memory_full_read`: read fuller local memory after explicit user approval.
- `memory_write`: propose memory updates; user confirmation required before committing decisions.
- `recovery_preview`: inspect recovery options without modifying files.
- `recovery_apply`: execute a selected recovery operation; disabled by default and requires checkpoint sandwich.
- `checkpoint_create`: create a checkpoint for the current project.
- `handoff_export`: generate an external handoff document after secret/privacy filtering.

Permission rules:

- Capabilities are granted per project and per tool.
- `memory_full_read`, `recovery_apply`, and `handoff_export` require explicit opt-in.
- Any MCP response that includes memory text must pass the secret scanner and privacy filter.
- Any MCP action derived from memory text must be treated as untrusted and require user confirmation (see Layer 4).

MCP permissions matrix:

| Capability | Default | Requires grant | Requires per-operation confirmation | Notes |
|---|---:|---:|---:|---|
| `memory_summary_read` | Allowed | No | No | Redacted summary only. |
| `recovery_preview` | Allowed | No | No | Read-only preview; never modifies files. |
| `checkpoint_create` | Allowed | No | No | Safe-write capability; project-root scoped. |
| `memory_full_read` | Denied | Yes | Yes | Full local memory; secret/privacy filtered before exposure. |
| `memory_write` | Denied | Yes | Yes for intent-shaping fields | Cannot silently write `decisions[]`, `active_intent`, or `next_action`. |
| `recovery_apply` | Denied | Yes | Yes | Requires checkpoint sandwich and explicit typed parameters. |
| `handoff_export` | Denied | Yes | Yes | External handoff output after secret/privacy filtering. |

Capability stability:

- MCP capability names published in any GA release are frozen.
- Renames or breaking schema changes ship a one-release deprecation window where both the old and new names are accepted; the old name returns a `deprecated_in` field pointing at its successor.
- Versioned alternates (e.g. `memory_summary_read_v2`) are the rename path, not in-place renames.
- External tools (Claude Code, Cursor, OpenCode, Codex) may rely on capability names persisting across patch releases; deprecation must therefore be a deliberate spec change with audit trail.

#### Layer 4: Untrusted-Memory Execution Boundary

Memory text is potentially adversarial input. Another AI tool, a teammate, or a leaked memory file from a different project could have written it. Once a future AI reads memory and acts on it, the contents become an attack surface.

Boundary rules:

- VibeLign must never directly execute commands extracted from memory text.
- All memory-derived actions (`recovery_apply`, file restore targets, handoff export paths) accept explicit parameters only — never free-text command strings parsed from memory.
- Memory rendered to the user or to MCP must be presented as data, not as agent instructions. The receiving AI tool may still treat it as instructions; VibeLign's job is to label it clearly so the user understands.
- When MCP exposes memory, the response must include a provenance tag (`source: memory`, `updated_by: <tool>`, `last_updated: <timestamp>`) so downstream agents can decide whether to trust it.

This layer is conceptually distinct from secret scanning (Layer 1) and privacy filtering (Layer 2): those gate *what data leaves*. Layer 4 gates *what actions data can trigger*.

#### Storage Defaults

Memory should be local-first.

- Store internal memory in VibeLign-controlled project metadata or user-private storage with restrictive permissions.
- Do not commit memory, handoff drafts, or recovery reports unless the user explicitly exports them.
- Generated handoff files must pass secret/privacy filtering before being written.
- Support a “minimal memory mode” that stores only active intent, next action, and verification freshness.

### CLI Experience

Possible commands:

```bash
vib memory show
vib memory review
vib memory decide "Use backup DB as the source of truth for GUI history because it matches restore behavior."
vib memory relevant vibelign-gui/src/pages/BackupDashboard.tsx "Owns backup dashboard state and selected backup ID."
vib transfer --handoff
```

`vib memory review` should be the central guided flow. It can show the current active intent, recent decisions, stale verification, changed files, and proposed next action, then let the user confirm or edit them.

### GUI Experience

Add a “Session Memory” card with four editable sections:

1. Current goal
2. Important decisions
3. Verification status
4. Next action

The card should not feel like a log viewer. It should feel like a short briefing for the next AI.

### MVP

Start by upgrading `vib transfer --handoff` into a guided memory review:

1. Read current `work_memory.json` and git status.
2. Propose active intent and next action.
3. Show stale verification warnings.
4. Ask the user to confirm or edit the handoff summary.
5. Write `PROJECT_CONTEXT.md`.

This creates visible value without requiring a new autonomous runtime.

## 4. Recovery Agent

### Goal

The Recovery Agent helps users recover when AI edits break the project, make confusing changes, or drift away from the requested scope.

It should not default to full rollback. The best recovery is often partial: keep useful work, remove risky work, and preserve the current state before trying anything destructive.

### Recovery Levels

0. **No-op recovery**: confirm nothing is actually broken. The user's "AI 망가뜨렸어" is sometimes a misread of a stale build, an unrelated test, or an editor that needs reload. The agent should be allowed to conclude "no recovery needed — try X first".
1. **Explain-only recovery**: describe what changed and which files look risky.
2. **Targeted repair**: keep the work and suggest fixes for guard/test/build failures.
3. **Partial restore**: restore selected files or modules from a checkpoint.
4. **Full rollback**: return to a previous checkpoint.

Cross-cutting safety action:

- **Checkpoint sandwich**: before any destructive recovery action, save the current broken state so the user can return to it. This is not a recovery level; it is a mandatory pre-apply safety step.

### Diagnostic Inputs

The Recovery Agent should combine multiple signals:

- Current git diff and untracked files.
- Latest checkpoint and backup DB rows.
- Restore preview output.
- Guard report.
- Explain report.
- Project map file categories.
- Anchor metadata.
- Memory Agent active intent and relevant files.
- Recent verification status.

### Recovery Flow

```text
User: "망가졌어" / "undo 해줘" / "AI가 이상하게 바꿨어"

Recovery Agent:
  1. Create a checkpoint of the current state.
  2. Inspect changed files and recent events.
  3. Compare current state to the latest safe checkpoint.
  4. Run or read guard/explain signals.
  5. Present 2-3 recovery options.
  6. Execute only after user confirmation.
```

Example recovery options:

- “Restore only `src/pages/Login.tsx` from the last checkpoint.”
- “Keep the UI changes, but revert unrelated service files.”
- “Run targeted repair because only the build is failing.”
- “Full rollback to checkpoint `before-login-feature`.”

### CLI Experience

Possible commands:

```bash
vib recover --explain
vib recover --preview
vib recover --file src/pages/Login.tsx
vib recover --checkpoint <id>
```

The first MVP should be read-only:

```bash
vib recover --explain
```

It should inspect the current state and print recommended recovery options without changing files. Execution commands can come after the recommendation quality is reliable.

### Apply Safety

Recovery can overwrite files, resurrect old code, or discard useful work. The default recovery path must be preview-first.

Apply rules:

- `recover --explain` and `recovery_preview` never modify files.
- Destructive recovery requires an affected-file list and a diff preview.
- Destructive recovery always creates a checkpoint sandwich (§4 Recovery Levels cross-cutting safety action) first.
- File restore targets must be canonicalized and constrained to the project root after symlink resolution.
- Recovery execution must be non-interactive when exposed through MCP. Interactive confirmation is acceptable in the CLI, but MCP tools must use explicit parameters such as `checkpoint_id`, `paths` (array of project-relative file paths), `preview_only`, and `apply` rather than `input()` prompts.
- If secret/privacy filtering (§3 Security Model Layers 1–2) changes the recovery explanation, VibeLign must say that details were redacted rather than silently hiding context.
- All memory-derived recovery parameters (e.g., file paths inferred from `relevant_files[]`) must follow the Layer 4 rule — the agent never executes free-text instructions extracted from memory; only explicit, validated parameters.

#### MCP Recovery Apply Flow

1. Client calls `recovery_preview`.
2. VibeLign returns recommended options, affected `paths`, and whether a safety checkpoint is required.
3. User explicitly selects one option.
4. Client calls `checkpoint_create` for the current project root.
5. VibeLign returns `sandwich_checkpoint_id`.
6. Client calls `recovery_apply` with explicit parameters:
   - `checkpoint_id`
   - `sandwich_checkpoint_id`
   - `paths`
   - `apply: true`
6.5. If `recovery_apply` returns `busy` (an inflight operation holds the project lock), the client MUST surface the `operation_id` and ETA to the user and MUST NOT auto-retry. The user decides whether to wait, cancel, or take other action. Auto-retry from clients is a P1 trust violation because two human decisions can stack the same restore.
7. VibeLign validates project-root scope, parent traversal, generated/cache/build exclusions, safety checkpoint existence, and whether selected `paths` match the preview. If paths differ from the preview, the operation requires re-confirmation.
8. Apply runs only after validation passes.
9. Result includes restore summary, safety checkpoint ID, changed files, redaction notices, and recommended verification commands.

### GUI Experience

Add a “Recovery Options” panel near the Backups or Guard flow.

The panel should show:

- Current risk summary.
- Files changed since last checkpoint.
- Latest safe checkpoint candidate.
- Recommended recovery path.
- Alternative recovery paths.
- “Create safety checkpoint first” as the default pre-action.

The user should never need to understand git internals to recover.

### MVP

MVP scope:

1. Read current git status and recent checkpoint metadata.
2. Create a plain-language explanation of what changed.
3. Identify files that are likely risky based on project-map category, anchor rules, and guard output.
4. Recommend one of: no-op, explain-only, targeted repair, partial restore, or full rollback.
5. Do not execute destructive recovery yet.

## 5. How Memory and Recovery Work Together

Memory and recovery should share context.

The Memory Agent knows:

- What the user was trying to do.
- Which files were intentionally relevant.
- Which verification was already run.
- Which risks were already known.

The Recovery Agent uses that to distinguish intentional work from accidental drift.

### Intent Inference Fallback

In practice, most users will not have populated `active_intent` or `relevant_files[]` when recovery is first needed. The recovery agent must still produce a useful "intent zone". The fallback algorithm, in priority order:

1. **Explicit memory** (highest priority): `relevant_files[]` and `active_intent` from `work_memory.json`.
2. **Recent patch targets**: files touched by the last N (default 5) `patch_apply` calls in the current session form an implicit relevant set.
3. **Project map category**: files in the same current project-map category (`entry`, `ui`, `core`, or `other`) as recent patches expand the zone. If finer categories such as `gui/backup` are needed, that requires a future project-map schema extension.
3.5. **`ui_label_index` co-occurrence** (Phase 3+ optimization): when recent patches touch GUI components, expand the zone to include components sharing the same `ui_label_index` group. This honors the project rule that intent inference must use real code signals (anchor / `ui_label_index` / filename / import graph) rather than translation dictionaries; it is not a Phase 1 requirement and degrades cleanly when `ui_label_index` is absent.
4. **Anchor co-occurrence**: anchors changed together in recent git history can extend the zone. A cached `.vibelign/anchor_graph.json` would be a later optimization, not a Phase 1 requirement.
5. **Default**: if all above are empty, the agent falls back to **diff-aware** recovery and explicitly says so to the user — "no intent context found; recommendations based on raw diff only".

Files outside the inferred zone are flagged as **drift candidates**, not declared "unrelated". The user remains the final judge — the agent shows reasoning ("this file is outside the intent zone because…") and lets the user override.

All inferred file paths must pass the same path hygiene rules used by current memory capture: no absolute paths, no parent traversal, no generated/cache/build directories, and no out-of-root paths after canonicalization.

This fallback is the mechanism that makes "intent-aware" a real claim instead of a marketing line. Without it, the spec depends on user discipline that will not exist.

Example:

```text
Active intent: Improve BACKUPS file history UX.
Relevant files (intent zone):
  - FileHistoryTable.tsx: owns backup list rendering
  - DateGraph.tsx: owns timeline interaction

Changed files:
  - FileHistoryTable.tsx        (in intent zone)
  - DateGraph.tsx               (in intent zone)
  - src/services/auth.ts        (drift candidate — outside intent zone)

Recovery recommendation:
  Keep intent-zone files.
  Drift candidate src/services/auth.ts is outside the active intent.
  Suggested action: review and revert if unintentional. User confirms before any restore.
```

This is the core value: recovery becomes intent-aware, not just diff-aware. Drift candidates are surfaced for review, never auto-reverted.

## 6. Suggested Product Roadmap

The phases are reordered so that **immediate user value comes first** and **strategic moat (MCP) comes early**. The original ordering led with memory, but memory requires user input before paying off — that is a bad first-impression curve. Recovery pays off on first use without any prior setup.

### Phase 1: Read-Only Recovery Advisor

- Add `vib recover --explain`.
- Combine git diff, checkpoint metadata, project map, anchor metadata, and guard/explain signals.
- Use the **Intent Inference Fallback** (§5) so recovery works even when memory is empty.
- Print recovery options (Levels 0–4) without modifying files.

This phase delivers the "AI 망가뜨렸을 때 살려줌" promise on day one, with zero user setup required. It also generates the trigger surface that makes Phase 3 useful.

### Phase 2: MCP Integration

- Expose recovery and (initially read-only) memory tools through MCP.
- MCP tools must be non-interactive, parameterized, project-root scoped, and safe by default.
- MCP memory responses must pass the secret/privacy redaction gate before leaving VibeLign.
- Let Claude Code, Cursor, OpenCode, and Codex ask VibeLign:
  - "What is the current intent?"
  - "Which files are safe to edit?"
  - "What recovery options exist?"
- This is the strategic moat: VibeLign becomes infrastructure other AI tools depend on, not just another CLI a single user runs.

Moved up from Phase 5 because the positioning ("agent for other AI agents") only materializes once MCP is live.

#### Phase 2 Security Gate (mandatory before any MCP write/apply capability)

Phase 2 cannot ship `memory_full_read`, `memory_write`, `recovery_apply`, or `handoff_export` until **all** of the following are live:

- **Layer 1**: existing secret scanner integrated as the redaction gate for any memory text bound for storage or MCP response.
- **Layer 2 v1**: privacy filter covering local absolute paths, internal hostnames/private-IP ranges, and usernames/home-directory fragments. Customer/project-identifier detection and oversized terminal-log summarization can defer to Layer 2 v2.
- **Layer 3**: per-project + per-tool capability grants persisted somewhere visible (CLI: `vib mcp grant`, GUI: a permissions panel in the MCP/Settings card). Default-deny posture.
- **Layer 4**: Untrusted-Memory Execution Boundary enforced — all MCP-exposed actions take typed parameters only; no free-text command parsing from memory.

Until this gate is satisfied, Phase 2 ships only the read-only redacted endpoints (`memory_summary_read`, `recovery_preview`) plus the safe-write `checkpoint_create` capability, scoped to the current project root, and the existing `mcp__vibelign__*` surface. Write/apply capabilities are gated behind the security checklist above, not behind a calendar date.

### Phase 3: Memory Review with Triggers

- Add `vib memory show` and `vib memory review`.
- Implement **Trigger Conditions** (§3) so review surfaces proactively, not on user initiative.
- Improve `transfer --handoff` with guided confirmation.
- Apply **Memory Hygiene** policies (timestamps, tool-of-record, intent-change cascade).

Now memory pays off immediately because Phase 1 recovery already exists — populating memory makes recovery smarter on the *next* incident, which is a real and visible reward.

### Phase 4: Assisted Partial Recovery

- Add restore preview for selected files.
- Let users recover one file or module (Recovery Level 3).
- Always create a checkpoint sandwich before any destructive restore.
- Preserve existing checkpoint-engine semantics: safe-restore backups that exist to protect recovery should not be mixed into normal `vib history` / default `vib undo` choices unless a dedicated restore UI intentionally exposes them.

Execution comes only after Phase 1 has proven recommendation quality.

### Phase 5: GUI Agent Cards

- Add Session Memory card.
- Add Recovery Options card.
- Show current risk, active intent, and next action in beginner-friendly form.

GUI is intentionally last: by Phase 5 the underlying logic is stable, so the GUI is a presentation layer over a known-good engine, not a UX patching over half-built behavior.

## 7. Edge Cases and Failure Modes

This direction is valuable only if VibeLign stays conservative under uncertainty. The product should treat the following cases as design constraints, not afterthoughts.

### P0: Must Not Happen

These are safety failures. They should block apply/write capabilities until mitigated.

#### Stale memory treated as current truth

Failure mode: `active_intent`, `next_action`, or `relevant_files[]` may describe yesterday's work while a new AI treats them as the current goal.

Risk: wrong edits, wrong handoff, or recovery recommendations based on outdated intent.

Mitigation: *(spec source: §3 Memory Hygiene, §3 Explicit User Confirmation)*

- Require `last_updated` and `updated_by` metadata for intent-shaping fields.
- Mark `active_intent` stale when it is older than 24 hours or unchanged across 5+ commits.
- Show stale fields as stale in `PROJECT_CONTEXT.md`, `memory_summary_read`, and recovery output.
- Never silently refresh `decisions[]`, `active_intent`, or `next_action`; propose changes and ask the user to confirm.

#### User work incorrectly classified as drift

Failure mode: a file outside the inferred intent zone may be legitimate work, not accidental AI drift.

Risk: VibeLign recommends reverting useful work.

Mitigation: *(spec source: §5 Intent Inference Fallback)*

- Use the label **drift candidate**, never "unrelated" or "wrong".
- Show the reason: which signal put the file outside the intent zone.
- Require user confirmation before any restore involving a drift candidate.
- Capture user feedback on drift labels so intent-zone accuracy can be measured (§8 Intent zone accuracy metric).
- **Auto-degrade circuit breaker**: if measured intent-zone accuracy drops below 80% over a rolling 20-incident window, drift labeling is automatically disabled and recovery falls back to diff-aware mode until the inference fallback is retuned. The user-facing message: "drift labeling temporarily disabled — accuracy below threshold". Without this circuit, the §8 accuracy metric is a vanity number.

#### Destructive recovery without a checkpoint sandwich

Failure mode: partial restore or full rollback runs before saving the current broken state.

Risk: the user loses the ability to return to useful work that existed before recovery.

Mitigation: *(spec source: §4 Recovery Levels cross-cutting safety, §4 Apply Safety)*

- Treat checkpoint sandwich as a hard precondition for `recovery_apply`.
- Abort destructive recovery if the safety checkpoint cannot be created.
- Include the safety checkpoint ID in the recovery result.
- Offer "return to pre-recovery state" after a failed or unsatisfactory restore.

#### Memory text becomes executable instruction

Failure mode: memory or handoff text contains commands, malicious instructions, or old recovery advice, and an AI tool treats that text as something to execute.

Risk: prompt injection, wrong file operations, or command execution sourced from untrusted memory.

Mitigation: *(spec source: §3 Security Model Layer 4)*

- Keep Layer 4 mandatory: memory is data, not instruction.
- MCP actions accept typed parameters only, such as `checkpoint_id`, `paths`, `preview_only`, and `apply`.
- Never parse free-text commands from memory.
- Treat file operations as execution too: memory-derived text must not flow into destructive calls such as delete, restore, overwrite, `unlink`, `rmtree`, or arbitrary `write_text` paths without passing the same typed parameter validation as recovery apply.
- Include provenance tags in MCP memory responses: `source`, `updated_by`, and `last_updated`.

#### User manual edits clobbered by recovery apply

Failure mode: after the safety checkpoint is created, the user manually edits one of the same files selected for recovery, then `recovery_apply` overwrites that newer manual work.

Risk: the user loses work even though the checkpoint sandwich technically allows recovery. This breaks trust because the danger is not obvious at the confirmation step.

Mitigation: *(spec source: §4 Apply Safety, §7 P1 Trust and Correctness)*

- Record the preview timestamp, selected paths, and sandwich checkpoint timestamp for every apply-ready option.
- Before apply, compare current file mtimes/hashes against the preview/sandwich baseline for selected paths.
- If any selected path changed after the sandwich checkpoint, block the default apply and show: "This file changed after the safety save. Review before restoring."
- Require a second explicit confirmation for paths changed after the sandwich checkpoint.
- Include post-sandwich manual-edit detection in the recovery result and audit event as counts only, never raw paths in audit.

#### MCP exposes raw sensitive context

Failure mode: `memory_full_read`, `handoff_export`, or `recovery_preview` returns API keys, local paths, internal URLs, customer identifiers, or raw terminal output.

Risk: private project context leaves VibeLign through another AI tool.

Mitigation: *(spec source: §3 Security Model Layers 1–3, §6 Phase 2 Security Gate)*

- Run the existing secret scanner and the privacy filter immediately before any MCP response containing memory text.
- Keep `memory_summary_read` and `recovery_preview` redacted by default.
- Gate `memory_full_read`, `memory_write`, `recovery_apply`, and `handoff_export` per project and per tool.
- Label redacted or summarized fields so downstream tools know details were intentionally withheld.
- **Audit log**: every MCP memory response records redaction-gate output as counts (not content) — number of secrets redacted, fields filtered by privacy layer, fields summarized. The audit log itself is local-first and subject to the privacy filter. A random 1% sample is asynchronously re-scanned to verify the gate fired correctly. Without the audit log, P0 leakage is detectable only after external report.
- **Audit log integrity**: every audit row carries a monotonic `sequence_number`. The P0 occurrence aggregator rejects any window containing a sequence gap or duplicate. This is not cryptographic tamper-proofing; it detects accidental truncation, naive file rewrite, and concurrent-writer races so a tampered or partial log cannot silently certify "0 occurrences".

### P1: Trust and Correctness

These failures may not destroy data, but they can make users stop trusting the agent.

#### Multiple AI tools overwrite the same memory field

Failure mode: Claude Code, Cursor, OpenCode, Codex, or the CLI writes conflicting versions of `active_intent`, `next_action`, or relevant-file notes.

Risk: handoff context becomes a blend of incompatible goals.

Mitigation: *(spec source: §3 Memory Hygiene — Tool-of-record)*

- Preserve tool-of-record metadata.
- Detect conflicting writes within a configurable short time window. Default: 60 seconds. Configurable via `vib config memory.conflict_window_seconds`.
- Surface both versions and ask the user to merge; never silently choose one.
- Retune the default after the first release cycle using observed same-field conflict data. If more than 10% of conflicts arrive outside the current window but within 10 minutes, widen the default or prompt the user to configure it.

#### Verification looks fresh after related files changed

Failure mode: tests or guard passed, then relevant files changed, but the handoff still reads like verification is current.

Risk: the next AI over-trusts stale validation.

Mitigation: *(spec source: §3 Memory Model — Verification field, §3 Memory Hygiene — Intent change cascade)*

- Store verification command, result, timestamp, and related file scope.
- Mark verification stale when files in that scope change.
- Distinguish `passed`, `failed`, `skipped`, and `stale` in memory and handoff output.

#### Secret scanning misses unusual tokens

Failure mode: a token, internal credential, or customer-specific identifier does not match the existing scanner's high-confidence patterns.

Risk: sensitive data persists in memory or leaves through MCP/export.

Mitigation: *(spec source: §3 Security Model Layers 1–2)*

- Layer secret scanning with privacy filtering and raw-output minimization.
- Store summaries rather than raw terminal output by default.
- Provide export preview for handoff documents.
- Keep explicit allow-secret exceptions rare and user-confirmed.

#### Partial restore breaks dependent files

Failure mode: restoring one file from a checkpoint leaves related files at incompatible versions.

Risk: build or runtime failures after an apparently successful recovery.

Mitigation: *(spec source: §4 Recovery Levels — Partial restore, §6 Phase 4)*

- Preview dependent files using project map categories, anchor metadata, and git history when available.
- Prefer module/anchor-aware restore groups over isolated file restore when dependency risk is high.
- Recommend guard/test commands after recovery and mark verification stale until they pass.

#### No safe checkpoint exists

Failure mode: the project has no checkpoint, the latest checkpoint predates too much work, or checkpoint metadata is incomplete.

Risk: recovery recommendations become speculative.

Mitigation: *(spec source: §3 Memory Model — Safe checkpoint candidate, §4 Recovery Flow)*

- Say explicitly when no safe checkpoint candidate exists.
- Avoid recommending full rollback without a previewable checkpoint.
- Fall back to explain-only or targeted repair using raw diff and guard/explain signals.
- Cross-reference with the P0 sandwich rule: if no checkpoint exists *and* destructive recovery is requested, abort destructive recovery (P0 enforcement) — never apply Level 3/4 without a sandwich.

#### Concurrent MCP recovery operations

Failure mode: two AI tools (Claude Code, Cursor, OpenCode, Codex) — or one tool plus the CLI — invoke `recovery_apply` on the same project simultaneously, or stack `recovery_apply` calls before the previous one completes.

Risk: half-applied restore, corrupted checkpoint sandwich, files at inconsistent versions, or two safety checkpoints fighting for the same name.

Mitigation: *(spec source: §3 Security Model Layer 3, §4 Apply Safety)*

- Project-level recovery lock: a single inflight `recovery_apply` per project root.
- New apply attempts during an active operation return `busy` with the in-progress operation ID and ETA, never queue silently.
- Lock auto-releases on completion or hard timeout (default 60 seconds, configurable via `vib config recovery.lock_timeout_seconds`).
- Lock acquisition happens *before* permission grant evaluation — a busy lock cannot be bypassed by re-grant.
- `recovery_preview`, `memory_summary_read`, `checkpoint_create` are read-safe and not subject to the lock.
- **Lock TTL vs long restore**: if `restore_files` runs longer than `recovery.lock_timeout_seconds`, the apply must abort and surface a "restore exceeded lock window" error rather than letting the lock expire mid-restore. Lock release MUST verify the holder's `lock_id` before deletion so a stale apply cannot remove a freshly acquired lock. For projects where 60 seconds is regularly insufficient, the user raises the timeout explicitly; the system never silently extends the lock mid-restore.

### P2: UX and Operations

These cases affect adoption, debugging, and long-term maintainability.

#### Memory review prompts become noisy

Failure mode: proactive triggers fire too often and users learn to dismiss them.

Risk: memory quality declines because users stop engaging.

Mitigation: *(spec source: §3 Trigger Conditions, §8 Trigger usefulness metric)*

- Keep triggers as one-line suggestions, not blocking modals.
- Support accept, dismiss, and snooze.
- Log dismissals so the same trigger does not repeat in the same session.
- Measure ignored prompt rate and retune thresholds when it exceeds 30%.

#### Redaction makes explanations unclear

Failure mode: recovery output hides paths, URLs, or logs so aggressively that the user cannot tell what happened.

Risk: users distrust the recommendation or choose the wrong recovery option.

Mitigation: *(spec source: §3 Security Model Layer 2 — Privacy filter)*

- State when details were redacted or summarized.
- Use shortened project-relative paths by default.
- Allow full local detail in trusted CLI/GUI contexts after explicit user action.

#### Cross-platform path handling differs

Failure mode: Windows paths, WSL `/mnt/c/...` ↔ `C:\...` translation, symlinks, reserved names, path separators, case-sensitivity differences, or path-length limits cause restore target validation to behave differently across macOS, Linux, Windows, and WSL.

Risk: failed recovery, out-of-root restore attempts, or confusing previews.

Mitigation: *(spec source: §4 Apply Safety, §5 Intent Inference Fallback path hygiene)*

- Canonicalize and resolve symlinks before root-scope checks.
- Reject parent traversal and generated/cache/build targets.
- Add Windows-specific checks for reserved names (CON, PRN, NUL, etc.), drive prefixes, and long paths (>260 chars unless long-path mode is enabled).
- Detect WSL contexts: a project at `/mnt/c/...` may be referenced by a Windows tool as `C:\...`. Resolve both forms to the same canonical project root before scope checks.
- Treat case-sensitivity per-platform: macOS/Windows are case-insensitive by default; Linux/WSL are case-sensitive. Path equality checks must use platform-appropriate comparison.
- Keep all MCP recovery paths explicit and project-root scoped.
- Implementation-side platform edge-case enumeration (Windows ADS/reserved names, WSL execution-context canonicalization, APFS case/Unicode handling, audit JSONL line-ending policy, etc.) lives in the implementation spec's Windows/macOS checklist (impl-spec §3 *Completion interpretation and open hardening backlog*); design mitigations and impl checklist items must remain in sync.

#### Telemetry captures sensitive context

Failure mode: metrics for triggers, MCP calls, recovery outcomes, or patch timing include file paths, customer names, or memory text.

Risk: telemetry becomes a second exfiltration surface.

Mitigation: *(spec source: §3 Security Model Layer 2, §8 Instrumentation note)*

- Default telemetry to local-only.
- Require opt-in for aggregated product metrics.
- Log event types and coarse counts, not raw memory, diff, logs, or full paths.
- Keep trigger telemetry and diff-growth baselines out of `work_memory.json`; memory stores handoff truth, while telemetry stores local-only measurement data.
- Persist trigger prompt/action events as sanitized IDs and coarse counts only. Do not store prompt copy, user-entered reasons, raw file paths, raw diffs, terminal output, usernames, or secrets.
- Apply the privacy filter to any exported telemetry bundle.

#### Summary and full memory diverge

Failure mode: `memory_summary_read` omits details that `memory_full_read` contains, causing different AI tools to make different recommendations.

Risk: inconsistent behavior across tools.

Mitigation: *(spec source: §3 Security Model Layer 3, §3 Storage Defaults)*

- Include `redacted`, `summarized`, or `omitted_fields` indicators in summaries.
- Let tools request `memory_full_read` only after explicit permission.
- If the summary is insufficient for a recommendation, say so rather than guessing.

#### Memory file grows unbounded

Failure mode: `decisions[]`, `relevant_files[]`, `verification[]`, and `recent_events[]` accumulate over months without retention policy. After heavy use, `work_memory.json` becomes large, noisy, and slow to load.

Risk: handoff summaries dilute, MCP responses grow large, summary quality degrades, and old decisions resurface as "active intent" through `decisions[-1]`.

Mitigation: *(spec source: §3 Memory Model, §3 Storage Defaults — minimal memory mode)*

- Cap each list at a sensible size by default: `decisions[]` last 50, `recent_events[]` last 200, `verification[]` last 30 entries per scope, `relevant_files[]` last 100.
- Decisions older than 90 days move to an `archived_decisions[]` list; the archive is *not* used for `active_intent` derivation.
- Caps are configurable via `vib config memory.<field>.cap`.
- Compaction runs lazily on memory write and explicitly via `vib memory compact`.
- "Minimal memory mode" (already in §3 Storage Defaults) is the floor: only `active_intent`, `next_action`, and verification freshness — guaranteed bounded size.

### Product Rule

See §2 Foundational Product Rule. Every P0/P1/P2 mitigation in this section must respect the four-step trusted shape (explain → preview → safety checkpoint → confirmed apply). A mitigation that breaks the shape is not a valid mitigation.

## 8. Success Criteria

### Qualitative (user-facing)

The Memory + Recovery Agent direction is working if users can say:

- "I can switch AI tools without explaining everything again."
- "When AI breaks something, VibeLign tells me the safest recovery path."
- "I know what changed, what was verified, and what to do next."
- "I can recover without understanding git deeply."

### Quantitative (measurable)

Each phase must hit these targets before the next phase ships.

#### P0 Hard SLOs (binary — any breach is a release-blocking incident)

These correspond directly to §7 P0 cases. Unlike the percentage-based metrics below, P0 SLOs are 0/100 — any nonzero value triggers an incident review and gates the next phase.

- **Sandwich enforcement**: `recovery_apply` runs without a successful pre-apply checkpoint sandwich = **0 occurrences**. (P0: Destructive recovery without a checkpoint sandwich.)
- **Memory-as-instruction execution**: any agent-executed action whose parameters were free-text-parsed from memory text = **0 occurrences**. (P0: Memory text becomes executable instruction.)
- **Unredacted MCP leak**: MCP response containing memory text that bypassed the secret scanner or privacy filter = **0 occurrences**, verified by the audit log and 1% async re-scan sample. (P0: MCP exposes raw sensitive context.)
- **Drift label on confirmed user intent**: file is labeled drift candidate after the user has explicitly added it to `relevant_files[]` = **0 occurrences**. (P0: User work incorrectly classified as drift.)
- **Stale active_intent silently treated as current**: `active_intent` past the staleness threshold is presented as fresh in any handoff or recovery output = **0 occurrences**. (P0: Stale memory treated as current truth.)

#### P0 Audit Event Schema

Each P0-relevant operation writes a local-only audit event. Audit events are for proving safety gates fired; they must not contain raw memory text, raw diff, full paths, terminal output, or secret values.

Example:

```json
{
  "event": "recovery_apply",
  "project_root_hash": "...",
  "tool": "claude-code",
  "timestamp": "2026-05-02T12:34:56Z",
  "sandwich_checkpoint_id": "ckpt_...",
  "paths_count": {
    "in_zone": 2,
    "drift": 0,
    "total": 2
  },
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

Minimum required event fields:

- `event`: one of `memory_summary_read`, `memory_full_read`, `memory_write`, `recovery_preview`, `checkpoint_create`, `recovery_apply`, or `handoff_export`.
- `project_root_hash`: stable hash of the project root, never the raw path.
- `tool`: calling tool or CLI surface.
- `timestamp`: ISO-8601 timestamp.
- `capability_grant_id`: grant record used for denied-by-default capabilities, when applicable.
- `sandwich_checkpoint_id`: required for `recovery_apply`.
- `paths_count`: coarse affected-path counts, split into `in_zone`, `drift`, and `total`; never raw paths.
- `redaction`: counts for secret hits, privacy hits, and summarized fields.
- `trigger`: optional Phase 4 trigger metadata with sanitized `id`, `action`, and `source`; no prompt text or user reason.
- `result`: `success`, `denied`, `aborted`, `failed`, or `busy`.

P0 occurrence aggregation:

- A local aggregator must scan `memory_audit.jsonl` plus derived trigger/recovery baselines and produce a release-cycle summary for each P0 SLO.
- The summary stores counts only: `slo_id`, `window_start`, `window_end`, `occurrences`, `sample_count`, and `result` (`pass`/`fail`).
- Phase gates may cite "0 occurrences" only when the aggregator has run over the required window. A test passing once is not enough evidence for a release-cycle SLO.
- If local-only telemetry is used, aggregation remains per-project unless the user opts into product telemetry.

Audit retention:

- `memory_audit.jsonl` is local-only but still needs lifecycle control.
- Default retention: keep 90 days or 10 MB, whichever is smaller, then roll older rows into a count-only summary snapshot under `.vibelign/recovery/`.
- Summary snapshots must preserve P0/P1 counters and circuit-breaker state but must not contain raw paths, raw memory, raw terminal output, or user-entered text.
- Retention must never delete rows needed for an active release-cycle P0 aggregation window.

#### Percentage Metrics (quality bars — retune if missed)

- **Recovery quality**: 50% or more of recovery sessions resolve via Level 0–2 (no-op, explain-only, or targeted repair) — i.e., not full rollback. Full-rollback rate is a regression signal.
- **Handoff speed**: median time from `vib transfer --handoff` to the next AI's first meaningful patch is under 5 minutes (measured via patch_apply timestamps in the new session).
- **Trigger usefulness**: 70% or more of agent-suggested triggers are explicitly accepted or dismissed within the same session — *not* ignored. An ignore rate above 30% means triggers are noise and must be retuned. The retune recommendation only fires when the rolling 7-day window contains at least 15 trigger events; below that threshold the rate is logged but acted on by neither the agent nor the operator (small-sample noise).
- **Intent zone accuracy**: when the user labels a recovery's drift candidates as correct/incorrect, 80%+ of "drift" flags should be confirmed correct. Below 80% triggers the §7 P0 auto-degrade circuit breaker (drift labeling disabled until retuned).
- **MCP adoption** (Phase 2+): at least 2 external AI tools (Claude Code, Cursor, OpenCode, or Codex) call `memory_summary_read` or `recovery_preview` MCP endpoints in the wild within 30 days of release.

Instrumentation note:

These metrics require explicit event logging for memory review prompts, trigger accept/dismiss/snooze actions, recovery recommendation outcomes, drift-candidate user feedback, MCP tool calls, and patch timing. If telemetry is local-only, VibeLign can still compute per-project metrics, but project-wide product metrics require opt-in aggregation.

Operationally, ignored-prompt rate and diff-growth thresholds are computed from local-only audit events plus a derived baseline snapshot under `.vibelign/recovery/`. The baseline stores coarse counters such as 7-day trigger counts and diff line totals since the last confirmed intent update. It is not committed, not exported by default, and not treated as handoff truth.

## 9. Non-Goals

This design does not require VibeLign to become a coding model.

It also should not start with full autonomy. The first versions should recommend, explain, and preview. Execution should remain user-confirmed until the recommendation quality is proven.

## 10. Positioning Statement

> VibeLign remembers AI coding work and helps recover it safely.

Longer version:

> VibeLign is the memory and recovery agent for AI coding. It preserves intent across tools, tracks what changed, explains risk, and guides users back to a safe state when AI edits go wrong.
