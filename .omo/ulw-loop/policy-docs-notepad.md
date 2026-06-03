# Policy Docs ULW Notepad

## Success Criteria

- C1 happy: planning CLI tests pass and policy docs pin the official CLI contract: `codex exec`, `claude -p`, `agy -p`.
- C2 adversarial: target docs and adapter code contain no stale Antigravity `--print`, `headless/print`, or grey-area relay language.
- C3 regression: `vib plan` template-only and best-effort persona orchestration remain covered by focused tests.

## Source Baseline

- Antigravity official docs checked on 2026-06-03: install registers `agy`; best-practices document shows `agy -p "..." --cwd $(pwd)`; permissions docs define local allow/deny/ask and sandbox behavior.
- Claude Code CLI reference checked on 2026-06-03: `claude -p "query"` is print/non-interactive mode.
- Codex CLI official/OpenAI sources checked on 2026-06-03: `codex exec` is the non-interactive route already used by this repo.

## TDD

- RED confirmed: `uv run pytest tests/test_policy_docs.py tests/core/planning_cli/test_orchestrator.py::test_orchestrator_runs_requested_personas_in_fixed_order` failed on missing `agy -p`, stale Antigravity grey-area/headless language, and `agy --print` command construction.
- GREEN confirmed: `uv run pytest tests/test_policy_docs.py tests/core/planning_cli/test_orchestrator.py::test_orchestrator_runs_requested_personas_in_fixed_order` passed after updating docs and `agy` command construction.
- Regression confirmed: `uv run pytest tests/core/planning_cli tests/cli/test_vib_plan_cmd.py tests/test_policy_docs.py` passed 30 tests after the README notice wording fix.
- Manual QA: `tmux` was unavailable on this machine, so equivalent shell QA was captured at `.omo/ulw-loop/evidence/policy-docs-shell-qa.txt`; it passed 3 focused tests and printed `NO_STALE_POLICY_STRINGS`.
- Cmux QA: `cmux new-workspace --name ulw-qa-policy-docs-2 ...` captured `.omo/ulw-loop/evidence/policy-docs-cmux-qa.txt`; it passed 3 focused tests and printed `NO_STALE_POLICY_STRINGS`. Cleanup: `cmux close-workspace --workspace workspace:8`; follow-up list confirmed workspace 8 was gone.
- Lint: `uv run ruff check tests/test_policy_docs.py tests/core/planning_cli/test_orchestrator.py vibelign/core/planning_cli/cli_adapters.py` passed.
- Template regression: `uv run vib plan "정책 검증용 예약 앱" --template-only --json` returned `ok: true` with `fallback_reason: template_only`; generated QA file `plans/정책-검증용-예약-앱.md` was removed.
- Review gate: two `codex-ultrawork-reviewer` attempts were launched after QA evidence, but both failed to return a final PASS/finding result and were closed. Local review gates above were completed instead.
