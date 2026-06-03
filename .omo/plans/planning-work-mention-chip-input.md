# Planning Work Mention Chip Input

## Goal

Make PlanningRoom persona chips write their mention into the composer input, matching the PR5 GUI contract for mention-based persona routing.

## TODOs

- [x] Add mention insertion when persona chips are clicked.

## Acceptance Criteria

- Existing persona selection and sequential follow-up behavior remain intact.
- Clicking `클로이 설계` inserts `@클로이` into the composer input.
- Clicking `모두` inserts `@모두` into the composer input.
- Repeated clicks do not duplicate the same mention token.
- The change stays inside the PlanningRoom composer component boundary and does not introduce raw CLI/model terminology.

## Evidence

- Baseline test pins existing follow-up submit behavior before changes.
- RED test proves mention insertion is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
