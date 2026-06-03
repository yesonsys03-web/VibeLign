# Planning Work Persona Response Summary

## Goal

Add a PlanningRoom persona response/failure summary so users can scan which persona answered or failed while the final plan preview remains available.

## TODOs

- [x] Add persona response and failure summary to PlanningRoom.

## Acceptance Criteria

- The summary appears only when there is at least one assistant persona message.
- The summary lists persona outcomes using persona names and statuses, not CLI/model names.
- Failed persona messages are summarized without exposing raw stderr/details.
- A failed persona does not disable the final Markdown preview when `markdown` exists.
- The summary lives in its own component and does not bloat `PlanningRoom` or `PlanningMessages`.

## Evidence

- Baseline test pins final preview availability when one persona failed.
- RED test proves persona response summary is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
