# Learnings (vibelign_FINAL_COMPLETE_PRD)

Append-only.

- Created `VibeLign_dev_plan/vibelign_FINAL_COMPLETE_PRD/03_development/00_VibeLign_Planning_Checklist.md` as the single execution tracker for the PRD set.
- Checklist convention: every block cites its source document inline, mirrors the PRD folder structure, and separates per-document checks from cross-document alignment, open decisions, and cleanup follow-up.
- Audit result: current code already covered patch preview, CodeSpeak, anchor validation, guard/explain reporting, and checkpoint rollback better than the docs suggested, but `vib init` wiring and `doctor` state updates were lagging the PRD and became the first alignment slice.
- Project Map alignment slice: `run_vib_init` now emits PRD-required `service_modules` and `generated_at`, uses a 300-line threshold for `large_files`, and keeps service classification separate from core modules.
- Consumer alignment slice: `doctor`, `anchor`, `patch`, `explain`, and `guard` now all consume Project Map data in at least one user-visible way, while full-workspace `pyright` still fails because of pre-existing `meta_paths` and `build/lib` issues unrelated to this slice.
- Hygiene slice: added fallback tests for missing/invalid Project Map behavior, removed the duplicate `vibelign_dir` property in `MetaPaths`, and limited pyright scope by excluding generated `build/` artifacts and `.venv/` so workspace type checks reflect project code instead of tool-managed files.
- Anchor recommendation slice: `vib anchor --suggest` now ranks files with explicit reasons using Project Map roles, file size, and symbol structure, so large entry files and UI/service-heavy files surface before generic files.
- CodeSpeak contract slice: `vib patch` now emits a small contract v0 (`status`, `intent`, `scope.allowed_files`, anchor/file statuses, allowed operations, preconditions, verification commands, actionable`) so low-confidence or missing-anchor requests surface as `NEEDS_CLARIFICATION` instead of looking execution-ready.
