# Planning Work: Legacy Surface Cleanup

## TODOs

- [x] Add regression tests for CLI, docs, and GUI legacy command visibility.
- [x] Move `patch` and `plan-structure` out of beginner CLI help and into legacy wording.
- [x] Emit legacy notices for interactive `vib patch` and `vib plan-structure` execution while preserving JSON output.
- [x] Mark GUI command metadata with `visibility` and keep legacy commands out of beginner lists.
- [x] Structure the GUI legacy badge as a home component instead of inline Home rendering.
- [x] Remove `vib patch`, `CodeSpeak`, and `plan-structure` from README first flows.
- [x] Mark `vib patch` and `vib plan-structure` manual sections as legacy and document `vib plan`.

## Final Verification Wave

- [x] Python focused regression and command-surface suites pass.
- [x] GUI focused regression tests and lint pass.
- [x] Manual QA confirms CLI help legacy grouping and live GUI dev server response.
- [x] QA server cleanup confirmed.
