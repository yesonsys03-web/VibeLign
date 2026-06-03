# Planning Work Status Labels

## Goal

Normalize PlanningRoom persona status labels so CLI failure states are shown as user-facing persona states instead of raw backend status codes.

## TODOs

- [x] Add shared persona status label mapping and wire it into PlanningRoom persona surfaces.

## Acceptance Criteria

- `not_installed`, `not_logged_in`, and `tty_required` show as `연결 필요`.
- `timeout`, `rate_limited`, `bad_output`, `process_error`, and `terms_blocked` show as `건너뜀`.
- Existing `ready`, `pending`, `ok`, and `failed` labels remain stable.
- Progress summary, response summary, and message badges use the same label mapping.
- The mapping lives in its own module and does not expand page-level logic.

## Evidence

- Baseline test pins existing pending/ok/failed labels before adding new mappings.
- RED test proves raw backend status codes are currently exposed.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
