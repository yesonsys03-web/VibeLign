# Planning Work Mode Selector

## Goal

Add an `Instant` planning mode selector that maps mode choices to persona selections, matching the PR5 GUI contract without exposing raw CLI/model terminology.

## TODOs

- [x] Add PlanningRoom mode selection with persona mapping.

## Acceptance Criteria

- The composer shows an `Instant` mode selector before the persona chips.
- The default `Instant` mode keeps the existing quick-review target (`gio`) selected.
- Changing the mode updates selected persona chips through persona IDs only.
- Manual persona chip selection still works after mode changes.
- The UI uses persona names and roles, not CLI/model names.
- The mode selector lives in its own component instead of bloating the composer.

## Evidence

- Baseline test pins the current default selected persona before changes.
- RED test proves the mode selector is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
