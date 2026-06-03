# Planning Work Persona Avatars

## Goal

Add three static persona avatars for Chloe, Gio, and Mina in the PlanningRoom surface, matching the PR5 GUI contract while keeping persona UI componentized.

## TODOs

- [x] Add reusable static persona avatars to PlanningRoom persona surfaces.

## Acceptance Criteria

- The PlanningRoom progress summary exposes static avatars for `클로이`, `지오`, and `미나`.
- Persona chips and assistant message headers can reuse the same avatar component without changing existing button names.
- Unknown persona IDs degrade to a neutral avatar instead of throwing.
- The UI continues to show persona names and roles, not CLI/model names.
- Avatar logic lives in its own component and does not bloat the composer or message components.

## Evidence

- Baseline test pins existing persona progress labels before changes.
- RED test proves avatar roles are missing before implementation.
- Focused tests and touched-file lint pass after implementation.
- Manual QA captures a live Vite HTTP 200 artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture live HTTP artifact, and close Boulder work.
