# Planning Work Advanced Details

## Goal

Add a collapsed advanced details surface in PlanningRoom so raw CLI or bridge details stay hidden by default but remain available for deliberate troubleshooting.

## TODOs

- [x] Add a collapsed advanced details component to PlanningRoom.

## Acceptance Criteria

- Raw `details` text is not visible by default in successful or failed PlanningRoom states.
- When `details` exists, users can expand a Korean "고급 상세" disclosure to inspect it.
- The detail copy explains that the surface is for troubleshooting without exposing model/CLI names as the primary UI.
- The component lives in its own file and does not bloat `PlanningRoom`.
- Existing save, preview, persona response summary, and error rendering behavior remains unchanged.

## Evidence

- Baseline test pins existing raw detail hiding before adding the disclosure.
- RED test proves the advanced details disclosure is missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
