# Planning Work Engine Prompt Boundary

## TODOs

- [x] Route single-persona planning engine prompt and section formatting through persona prompt helpers.

### Acceptance Criteria

- `engine.py` uses `build_persona_prompt` with `PlanningPersona.prompt_role`.
- `engine.py` uses `append_persona_section` with `PlanningPersona.section_title`.
- `engine.py` no longer hardcodes Gio-specific prompt/section strings.
- Existing Codex/Gio success, missing CLI fallback, and forbidden-term rejection stay unchanged.
- Every touched Python file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused pytest, ruff on touched files, capture CLI-level artifact, and close Boulder work.

### Verification Commands

- `.venv/bin/python3.11 -m pytest tests/core/planning_cli/test_plan_engine_pr4.py`
- `.venv/bin/python3.11 -m ruff check vibelign/core/planning_cli/engine.py tests/core/planning_cli/test_plan_engine_pr4.py`
