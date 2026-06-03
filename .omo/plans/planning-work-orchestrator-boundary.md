# Planning Work Orchestrator Boundary

## Goal

Refactor planning CLI orchestration so `orchestrator.py` stays below the project file-size risk threshold before the next backend feature is added.

## TODOs

- [x] Split prompt building and response policy responsibilities out of `orchestrator.py`.

## Acceptance Criteria

- Existing planning CLI behavior remains unchanged.
- `orchestrator.py` pure LOC is no more than 220.
- Persona prompt text lives in its own module.
- LLM response safety/status policy lives in its own module.
- New modules stay below the 250 pure LOC limit and have focused tests or are covered by existing orchestrator tests.

## Evidence

- Baseline test pins existing orchestrator behavior before refactor.
- RED structure test proves `orchestrator.py` is too close to the 250 pure LOC limit.
- Focused Python tests and touched-file lint pass after refactor.
- Manual QA captures a real temp-project planning output artifact.

## Final Verification Wave

- [x] Run focused tests, lint touched files, capture temp-project artifact, and close Boulder work.
