# Planning Work Mention Persona Boundary

## TODOs

- [x] Derive planning CLI mention aliases from persona metadata.

### Acceptance Criteria

- Korean mention aliases are derived from `PlanningPersona.name`.
- English mention aliases remain the persona ids.
- `mentions.py` no longer hardcodes the Chloe/Gio/Mina alias table separately.
- Existing Korean, English, `@모두`, and default mention behavior stays unchanged.
- Every touched Python file stays below 180 pure LOC.

## Final Verification Wave

- [x] Run focused pytest, ruff on touched files, capture CLI-level artifact, and close Boulder work.

### Verification Commands

- `python3 -m pytest tests/core/planning_cli/test_mentions.py`
- `python3 -m ruff check vibelign/core/planning_cli/mentions.py tests/core/planning_cli/test_mentions.py`
