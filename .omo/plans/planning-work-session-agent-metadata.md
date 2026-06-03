# Planning Work Session Agent Metadata

## Goal

Update planning `session.json` after agent orchestration so PR5 stores persona status metadata and compact run summaries without saving raw model output by default.

## TODOs

- [x] Write agent metadata and compact run records into `.vibelign/planning/{session_id}/session.json`.

## Acceptance Criteria

- `session.json` includes `agents_requested`, `agents_used`, and `agent_statuses` after agent orchestration.
- `session.json` includes one `runs[]` entry per requested persona with `run_id`, `turn_id`, `persona_id`, `cli_id`, `status`, and `summary`.
- Run summaries are compact and do not store the full raw CLI response.
- Existing template-only storage, all-ok, all-fail fallback, transcript opt-in, and JSON output contracts remain unchanged.
- Session metadata writing lives in its own module and does not bloat `orchestrator.py`.

## Evidence

- Baseline test pins existing orchestrator and storage behavior before metadata changes.
- RED test proves agent metadata is missing from `session.json` before implementation.
- Focused Python tests and touched-file lint pass after implementation.
- Manual QA captures a real temp-project `session.json` artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture temp-project artifact, and close Boulder work.
