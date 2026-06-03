# Planning Work Transcript Turn Files

## Goal

Store opt-in planning CLI transcripts under PR5 turn-file paths so saved raw responses are structured by turn order and adapter.

## TODOs

- [x] Save opt-in persona transcripts under `.vibelign/planning/{session_id}/turns/turn_###_{adapter}.md`.

## Acceptance Criteria

- `save_transcript=True` writes one Markdown file per attempted persona run under `turns/`.
- File names include stable 1-based turn order and adapter id, such as `turn_001_claude.md`.
- Transcript saving remains opt-in and does not create transcript files when disabled.
- Existing all-ok, all-fail fallback, and append-to-plan behavior remains unchanged.
- Transcript path logic lives in its own module instead of growing orchestration logic.

## Evidence

- Baseline test pins existing orchestrator behavior before transcript path changes.
- RED test proves PR5 turn-file transcript paths are missing before implementation.
- Focused Python tests and touched-file lint pass after implementation.
- Manual QA captures a real temp-project transcript artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture temp-project artifact, and close Boulder work.
