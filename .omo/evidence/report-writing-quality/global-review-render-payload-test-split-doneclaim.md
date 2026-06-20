# Render Payload Test Split Done Claim

Date: 2026-06-20

## Changed Files

- `tests/cli/test_vib_report_render_payload.py`
  - Removed the env render-payload key-binding regressions from the oversized module.
  - Kept the existing render payload, schema, theme, font, and author tests in place.
- `tests/cli/test_vib_report_render_payload_key.py`
  - Added a focused test file for env render-payload `--polish-key` binding behavior.
  - Preserves coverage for matching key success and missing/mismatched key rejection.

## Behavior Scenarios

- Scenario: existing render payload tests still pass.
  - Invocation: `uv run python -m pytest tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_render_payload_key.py -v`
  - Binary observable: exit code 0, 19 tests passed.
  - Captured artifact: this file.
- Scenario: matching `--polish-key` accepts env render payload and writes draft content.
  - Invocation: same pytest command.
  - Binary observable: `tests/cli/test_vib_report_render_payload_key.py::test_render_decisions_payload_file_matching_key_writes_draft_content PASSED`.
  - Captured artifact: this file.
- Scenario: missing or wrong `--polish-key` rejects stale env render payload.
  - Invocation: same pytest command.
  - Binary observable: parameterized cases `[None]` and `[stale-polish-key]` both PASSED.
  - Captured artifact: this file.
- Scenario: touched Python test files satisfy the pure LOC ceiling.
  - Invocation: `awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(\\/\\/|#|--)/ {count[FILENAME]++} END {for (file in count) print count[file], file}' tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_render_payload_key.py`
  - Binary observable: both files report <=250 pure LOC.
  - Captured artifact: this file.

## Command Output

### Pytest

Command:

```bash
uv run python -m pytest tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_render_payload_key.py -v
```

Output:

```text
============================= test session starts ==============================
platform darwin -- Python 3.11.15, pytest-9.0.3, pluggy-1.6.0 -- /Users/topsphinx/Documents/coding/VibeLign/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/topsphinx/Documents/coding/VibeLign
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 19 items

tests/cli/test_vib_report_render_payload.py::test_report_polish_off_by_default_no_provider_call PASSED [  5%]
tests/cli/test_vib_report_render_payload.py::test_report_polish_on_calls_polish PASSED [ 10%]
tests/cli/test_vib_report_render_payload.py::test_report_polish_uses_cache_on_second_run PASSED [ 15%]
tests/cli/test_vib_report_render_payload.py::test_emit_model_prints_base_polished_and_key PASSED [ 21%]
tests/cli/test_vib_report_render_payload.py::test_render_decisions_writes_file PASSED [ 26%]
tests/cli/test_vib_report_render_payload.py::test_render_decisions_payload_file_malformed_schema_reports_json_error PASSED [ 31%]
tests/cli/test_vib_report_render_payload.py::test_render_decisions_payload_file_non_string_block_text_reports_json_error_without_traceback PASSED [ 36%]
tests/cli/test_vib_report_render_payload.py::test_render_decisions_cache_miss_errors PASSED [ 42%]
tests/cli/test_vib_report_render_payload.py::test_theme_threads_to_html PASSED [ 47%]
tests/cli/test_vib_report_render_payload.py::test_generated_theme_threads_to_html PASSED [ 52%]
tests/cli/test_vib_report_render_payload.py::test_font_sizes_thread_to_html PASSED [ 57%]
tests/cli/test_vib_report_render_payload.py::test_invalid_font_size_reports_error_json PASSED [ 63%]
tests/cli/test_vib_report_render_payload.py::test_fonts_thread_to_html PASSED [ 68%]
tests/cli/test_vib_report_render_payload.py::test_invalid_font_reports_error_json PASSED [ 73%]
tests/cli/test_vib_report_render_payload.py::test_unknown_theme_reports_short_error_json PASSED [ 78%]
tests/cli/test_vib_report_render_payload.py::test_author_threads_to_html PASSED [ 84%]
tests/cli/test_vib_report_render_payload_key.py::test_render_decisions_payload_file_matching_key_writes_draft_content PASSED [ 89%]
tests/cli/test_vib_report_render_payload_key.py::test_render_decisions_payload_file_rejects_missing_or_mismatched_key[None] PASSED [ 94%]
tests/cli/test_vib_report_render_payload_key.py::test_render_decisions_payload_file_rejects_missing_or_mismatched_key[stale-polish-key] PASSED [100%]

============================== 19 passed in 0.24s ==============================
```

### Ruff

Command:

```bash
uv run ruff check tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_render_payload_key.py
```

Output:

```text
All checks passed!
```

### Pure LOC

Command:

```bash
awk '!/^[[:space:]]*$/ && !/^[[:space:]]*(\\/\\/|#|--)/ {count[FILENAME]++} END {for (file in count) print count[file], file}' tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_render_payload_key.py
```

Output:

```text
84 tests/cli/test_vib_report_render_payload_key.py
211 tests/cli/test_vib_report_render_payload.py
```

### Whitespace Checks

Command:

```bash
git diff --check -- tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_render_payload_key.py
```

Output:

```text
```

Command:

```bash
for file in tests/cli/test_vib_report_render_payload.py tests/cli/test_vib_report_render_payload_key.py; do tmp=$(mktemp); git diff --no-index --check /dev/null "$file" >"$tmp" 2>&1; rc=$?; if [ "$rc" -gt 1 ] || [ -s "$tmp" ]; then cat "$tmp"; rm -f "$tmp"; exit 1; fi; rm -f "$tmp"; echo "$file: no whitespace errors (no-index status $rc)"; done
```

Output:

```text
tests/cli/test_vib_report_render_payload.py: no whitespace errors (no-index status 1)
tests/cli/test_vib_report_render_payload_key.py: no whitespace errors (no-index status 1)
```

## VibeLign Checks

Command:

```bash
vib doctor --strict
```

Output summary:

```text
exit code 1
project score: 0 / 100
current status: High Risk
residual examples: existing long files, missing anchors, circular imports, .mcp.json vibelign MCP registration
```

Command:

```bash
vib scan
```

Output summary:

```text
exit code 0
code map regenerated: 584 files
anchor integrity residuals:
- vibelign/commands/__init__.py: file contents cannot be read
- vibelign/mcp/__init__.py: file contents cannot be read
```

Command:

```bash
vib explain --write-report
```

Output summary:

```text
exit code 0
risk level: high
reported broad dirty worktree, including files outside this task
```

Command:

```bash
vib guard --strict --write-report
```

Output summary:

```text
exit code 1
overall status: stop
residuals: planning_required for broad worktree changes and missing anchor on vibelign/core/reporting_cli/report_visual_cards.py
accepted per user context; not caused by this test split
```

## Residuals

- The worktree already had many unrelated modified and untracked files. I only edited `tests/cli/test_vib_report_render_payload.py`, created `tests/cli/test_vib_report_render_payload_key.py`, and wrote this evidence file.
- `vib guard --strict --write-report` still fails on accepted broad worktree/anchor residuals. The user explicitly said not to block on those.
- The review-work skill could not launch its five subagents because `multi_agent_v1` tools are not exposed in this session; `tool_search` returned no matching tools.
