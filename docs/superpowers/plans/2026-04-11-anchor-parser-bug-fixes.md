# Anchor Parser Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 parser-layer bugs in `vibelign/core/anchor_tools.py` so that `extract_anchors` / `extract_anchor_spans` produce a clean baseline for the upcoming eval skill.

**Architecture:** The root cause for 3 of 4 bugs is `ANCHOR_RE = re.compile(r"ANCHOR:\s*([A-Z0-9_]+)")` being too loose — it matches mentions inside docstrings and markdown, and the post-strip `.rstrip("_")` drops legitimate dunder suffixes. Fix = tighten the regex to the full `=== ANCHOR: NAME_START ===` form, stop stripping trailing `_` after `_START`/`_END` removal, and emit a warning + drop span when `_END` is missing (instead of leaving `end=None`). Duplicate-name detection is handled with a warning + stable suffix in `collect_anchor_index`.

**Tech Stack:** Python 3.11+, pytest, regex (stdlib `re`).

**Context for the engineer:**
- `vibelign/core/anchor_tools.py` is the single source of truth for anchor marker parsing.
- Real anchor markers always have the form `<prefix> === ANCHOR: NAME_START ===` (prefix = `#` for py, `//` for js/ts/etc). See `build_anchor_block` at line 115.
- Tests live in `tests/`. There is already `tests/test_anchor_tools_v2.py` and `tests/test_edge_anchor_tools.py`; do **not** modify existing passing tests. Create a new file `tests/test_anchor_parser_bugs.py` for these fixes.
- Run tests with: `python -m pytest tests/test_anchor_parser_bugs.py -v` (working dir = repo root).
- Full anchor-related regression check: `python -m pytest tests/test_anchor_tools_v2.py tests/test_edge_anchor_tools.py tests/test_anchor_parser_bugs.py -v`
- Post-fix project check: `python -m vibelign.cli doctor --strict` (may still exit 1 from size warnings — that's unrelated).

**File Structure:**
- Modify: `vibelign/core/anchor_tools.py`
  - Line 75: `ANCHOR_RE` regex — tighten to require `=== ANCHOR: ... ===`
  - Line 440–446: `extract_anchors` — drop the `.rstrip("_")` call
  - Line 452–478: `extract_anchor_spans` — drop the `.rstrip("_")` calls; skip spans with no `_END` match (instead of `end=None`)
- Create: `tests/test_anchor_parser_bugs.py` — one test class per bug, TDD-first.

---

## Task 1: Bug 2 — phantom spans from docstring/markdown literals

**Root cause:** `ANCHOR_RE = re.compile(r"ANCHOR:\s*([A-Z0-9_]+)")` matches inline mentions like `` `ANCHOR: NAME_START` `` inside help text in `export_cmd.py` and the `# format: /abs/path/file.py:ANCHOR: FOO_START` comment in `fast_tools.py`. Real markers always have the triple-equals wrapper: `=== ANCHOR: NAME_START ===`.

**Files:**
- Modify: `vibelign/core/anchor_tools.py:75`
- Test: `tests/test_anchor_parser_bugs.py` (create)

- [ ] **Step 1.1: Write the failing test for phantom-span rejection**

Create `tests/test_anchor_parser_bugs.py` with:

```python
from pathlib import Path

from vibelign.core.anchor_tools import extract_anchors, extract_anchor_spans


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


class TestBug2PhantomSpans:
    def test_inline_mention_in_docstring_is_not_an_anchor(self, tmp_path: Path) -> None:
        text = '''"""
        Respect anchor boundaries (`ANCHOR: NAME_START` / `ANCHOR: NAME_END`)
        """

        # === ANCHOR: REAL_ONE_START ===
        x = 1
        # === ANCHOR: REAL_ONE_END ===
        '''
        p = _write(tmp_path, "mod.py", text)
        assert extract_anchors(p) == ["REAL_ONE"]
        spans = extract_anchor_spans(p)
        assert [s["name"] for s in spans] == ["REAL_ONE"]

    def test_inline_mention_in_line_comment_is_not_an_anchor(self, tmp_path: Path) -> None:
        text = (
            "# format: /abs/path/file.py:ANCHOR: FOO_START\n"
            "# === ANCHOR: REAL_TWO_START ===\n"
            "y = 2\n"
            "# === ANCHOR: REAL_TWO_END ===\n"
        )
        p = _write(tmp_path, "mod2.py", text)
        assert extract_anchors(p) == ["REAL_TWO"]
        spans = extract_anchor_spans(p)
        assert [s["name"] for s in spans] == ["REAL_TWO"]
```

- [ ] **Step 1.2: Run the test and confirm it fails**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug2PhantomSpans -v`
Expected: both tests FAIL. The assertion for `extract_anchors` will return something like `["NAME", "REAL_ONE"]` (or with `FOO` for the second test) instead of the single real anchor.

- [ ] **Step 1.3: Tighten `ANCHOR_RE`**

In `vibelign/core/anchor_tools.py`, replace line 75:

```python
ANCHOR_RE = re.compile(r"ANCHOR:\s*([A-Z0-9_]+)")
```

with:

```python
ANCHOR_RE = re.compile(r"===\s*ANCHOR:\s*([A-Z0-9_]+)\s*===")
```

- [ ] **Step 1.4: Run the test and confirm it passes**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug2PhantomSpans -v`
Expected: both tests PASS.

- [ ] **Step 1.5: Run the full anchor regression**

Run: `python -m pytest tests/test_anchor_tools_v2.py tests/test_edge_anchor_tools.py tests/test_anchor_parser_bugs.py -v`
Expected: all pass. If a pre-existing test that relied on the loose regex fails, stop and report — do NOT rewrite existing tests without confirming first.

- [ ] **Step 1.6: Commit**

```bash
git add vibelign/core/anchor_tools.py tests/test_anchor_parser_bugs.py
git commit -m "fix(anchor): reject inline ANCHOR: mentions outside === markers"
```

---

## Task 2: Bug 4 — dunder name truncation

**Root cause:** `extract_anchors` and `extract_anchor_spans` call `.rstrip("_")` after stripping `_START`/`_END`. For a dunder symbol like `__init__` the built marker is `CLI_BASE___INIT___START`; stripping `_START` leaves `CLI_BASE___INIT__`, then `.rstrip("_")` drops the trailing `__` and yields `CLI_BASE___INIT` — losing the dunder identity. Name lookup via the returned base then fails.

**Files:**
- Modify: `vibelign/core/anchor_tools.py:444` (`extract_anchors`)
- Modify: `vibelign/core/anchor_tools.py:469,473` (`extract_anchor_spans`)
- Test: `tests/test_anchor_parser_bugs.py` (append)

- [ ] **Step 2.1: Write the failing test for dunder preservation**

Append to `tests/test_anchor_parser_bugs.py`:

```python
class TestBug4DunderPreserved:
    def test_extract_anchors_preserves_dunder_suffix(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: CLI_BASE___INIT___START ===\n"
            "pass\n"
            "# === ANCHOR: CLI_BASE___INIT___END ===\n"
        )
        p = _write(tmp_path, "cli_base.py", text)
        assert extract_anchors(p) == ["CLI_BASE___INIT__"]

    def test_extract_anchor_spans_preserves_dunder_suffix(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: CLI_BASE___INIT___START ===\n"
            "pass\n"
            "# === ANCHOR: CLI_BASE___INIT___END ===\n"
        )
        p = _write(tmp_path, "cli_base.py", text)
        spans = extract_anchor_spans(p)
        assert len(spans) == 1
        assert spans[0]["name"] == "CLI_BASE___INIT__"
        assert spans[0]["start"] == 1
        assert spans[0]["end"] == 3
```

- [ ] **Step 2.2: Run the test and confirm it fails**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug4DunderPreserved -v`
Expected: FAIL. Actual name returned is `"CLI_BASE___INIT"` (missing `__`).

- [ ] **Step 2.3: Drop `.rstrip("_")` in `extract_anchors`**

In `vibelign/core/anchor_tools.py`, replace line 444:

```python
        base = re.sub(r"_(START|END)$", "", raw).rstrip("_")
```

with:

```python
        base = re.sub(r"_(START|END)$", "", raw)
```

- [ ] **Step 2.4: Drop `.rstrip("_")` in `extract_anchor_spans`**

In `vibelign/core/anchor_tools.py`, replace line 469:

```python
            base = re.sub(r"_START$", "", raw).rstrip("_")
```

with:

```python
            base = re.sub(r"_START$", "", raw)
```

And replace line 473:

```python
            base = re.sub(r"_END$", "", raw).rstrip("_")
```

with:

```python
            base = re.sub(r"_END$", "", raw)
```

- [ ] **Step 2.5: Run the test and confirm it passes**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug4DunderPreserved -v`
Expected: both tests PASS.

- [ ] **Step 2.6: Run full anchor regression**

Run: `python -m pytest tests/test_anchor_tools_v2.py tests/test_edge_anchor_tools.py tests/test_anchor_parser_bugs.py -v`
Expected: all pass.

- [ ] **Step 2.7: Commit**

```bash
git add vibelign/core/anchor_tools.py tests/test_anchor_parser_bugs.py
git commit -m "fix(anchor): preserve trailing underscores (dunder symbols) after _START/_END strip"
```

---

## Task 3: Bug 3 — dangling `_START` span with `end=None`

**Root cause:** `extract_anchor_spans` appends the span eagerly on `_START` and only fills `end` when a matching `_END` is seen. If the file has an unterminated START, the span is left with `end=None`, which forces every downstream caller to add a `None` guard. Policy: drop dangling spans from the result. They represent a broken file and should be visible as "missing anchor" upstream, not silently stored with a sentinel.

(With Task 1's regex tightening, the existing `end=None` cases reported in the audit — `export_cmd.py` and `fast_tools.py` — disappear on their own because those START markers were inline-mention false positives. This task covers the remaining structural case: a real but unterminated START.)

**Files:**
- Modify: `vibelign/core/anchor_tools.py:452-478` (`extract_anchor_spans`)
- Test: `tests/test_anchor_parser_bugs.py` (append)

- [ ] **Step 3.1: Write the failing test for dangling-START drop**

Append to `tests/test_anchor_parser_bugs.py`:

```python
class TestBug3DanglingStartDropped:
    def test_unterminated_start_is_not_returned(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: GOOD_START ===\n"
            "ok = 1\n"
            "# === ANCHOR: GOOD_END ===\n"
            "\n"
            "# === ANCHOR: DANGLING_START ===\n"
            "oops = 2\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        names = [s["name"] for s in spans]
        assert names == ["GOOD"]
        # no span should ever have end=None
        assert all(s["end"] is not None for s in spans)
```

- [ ] **Step 3.2: Run the test and confirm it fails**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug3DanglingStartDropped -v`
Expected: FAIL. `names` is `["GOOD", "DANGLING"]` and the DANGLING span has `end=None`.

- [ ] **Step 3.3: Filter dangling spans at the end of `extract_anchor_spans`**

In `vibelign/core/anchor_tools.py`, replace the body of `extract_anchor_spans` (lines 460–478) with:

```python
    text = safe_read_text(path)
    if not text:
        return []
    pending: dict[str, list[int]] = {}
    spans: list[dict[str, object]] = []
    for match in ANCHOR_RE.finditer(text):
        raw = match.group(1)
        line_no = text.count("\n", 0, match.start()) + 1
        if raw.endswith("_START"):
            base = re.sub(r"_START$", "", raw)
            pending.setdefault(base, []).append(len(spans))
            spans.append({"name": base, "start": line_no, "end": None})
        elif raw.endswith("_END"):
            base = re.sub(r"_END$", "", raw)
            stack = pending.get(base)
            if stack:
                idx = stack.pop()
                spans[idx]["end"] = line_no
    return [span for span in spans if span["end"] is not None]
```

Note: this also carries Task 2's `.rstrip("_")` removal forward — keep both edits together.

- [ ] **Step 3.4: Run the test and confirm it passes**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug3DanglingStartDropped -v`
Expected: PASS.

- [ ] **Step 3.5: Run full anchor regression**

Run: `python -m pytest tests/test_anchor_tools_v2.py tests/test_edge_anchor_tools.py tests/test_anchor_parser_bugs.py -v`
Expected: all pass.

- [ ] **Step 3.6: Commit**

```bash
git add vibelign/core/anchor_tools.py tests/test_anchor_parser_bugs.py
git commit -m "fix(anchor): drop dangling _START spans instead of emitting end=None"
```

---

## Task 4: Bug 1 — duplicate anchor names

**Root cause:** Two files contain the same anchor name twice:
- `vibelign/patch/patch_builder.py` → `PATCH_BUILDER_BUILD_CONTRACT` at lines 60 and 255
- `vibelign/mcp/mcp_handler_registry.py` → `MCP_HANDLER_REGISTRY___CALL__` at lines 11 and 153

`extract_anchor_spans` already returns all instances in order, but `extract_anchors` dedupes with `dict.fromkeys` (line 446) so the name list loses one. More importantly, the patch pipeline's `anchor_index` set-dedupes per file, so only the first region of a duplicate is reachable by name.

**Decision:** The fix lives in `extract_anchor_spans` as a hard constraint — **it is illegal for a file to contain two anchor spans with the same name**. The parser should log a warning and disambiguate the duplicates by suffixing `_2`, `_3`, … on the 2nd+ occurrence. This keeps both regions addressable and makes the duplication visible in the project map so the user can rename the source markers when they see fit.

(Check after all 4 tasks whether the two real files above need source-level renames. Do NOT rename them as part of this plan — rename is a separate user decision.)

**Files:**
- Modify: `vibelign/core/anchor_tools.py:452-478` (`extract_anchor_spans`)
- Test: `tests/test_anchor_parser_bugs.py` (append)

- [ ] **Step 4.1: Write the failing test for duplicate suffixing**

Append to `tests/test_anchor_parser_bugs.py`:

```python
class TestBug1DuplicateNamesSuffixed:
    def test_duplicate_spans_get_numeric_suffix(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: DUP_START ===\n"
            "first = 1\n"
            "# === ANCHOR: DUP_END ===\n"
            "\n"
            "# === ANCHOR: DUP_START ===\n"
            "second = 2\n"
            "# === ANCHOR: DUP_END ===\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        names = [s["name"] for s in spans]
        assert names == ["DUP", "DUP_2"]
        # lines should be preserved for both occurrences
        assert spans[0]["start"] == 1 and spans[0]["end"] == 3
        assert spans[1]["start"] == 5 and spans[1]["end"] == 7
```

- [ ] **Step 4.2: Run the test and confirm it fails**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug1DuplicateNamesSuffixed -v`
Expected: FAIL. Both spans currently share the name `"DUP"`.

- [ ] **Step 4.3: Add duplicate suffixing in `extract_anchor_spans`**

In `vibelign/core/anchor_tools.py`, replace the body of `extract_anchor_spans` with:

```python
    text = safe_read_text(path)
    if not text:
        return []
    pending: dict[str, list[int]] = {}
    spans: list[dict[str, object]] = []
    seen_counts: dict[str, int] = {}
    for match in ANCHOR_RE.finditer(text):
        raw = match.group(1)
        line_no = text.count("\n", 0, match.start()) + 1
        if raw.endswith("_START"):
            base = re.sub(r"_START$", "", raw)
            seen_counts[base] = seen_counts.get(base, 0) + 1
            occurrence = seen_counts[base]
            name = base if occurrence == 1 else f"{base}_{occurrence}"
            pending.setdefault(base, []).append(len(spans))
            spans.append({"name": name, "start": line_no, "end": None})
        elif raw.endswith("_END"):
            base = re.sub(r"_END$", "", raw)
            stack = pending.get(base)
            if stack:
                idx = stack.pop()
                spans[idx]["end"] = line_no
    return [span for span in spans if span["end"] is not None]
```

Note that matching of `_END` still uses the raw base (`DUP`), not the suffixed display name. Each `_END` pops the most recent pending START for that base, so nested/out-of-order cases still behave like a stack.

- [ ] **Step 4.4: Run the test and confirm it passes**

Run: `python -m pytest tests/test_anchor_parser_bugs.py::TestBug1DuplicateNamesSuffixed -v`
Expected: PASS.

- [ ] **Step 4.5: Run full anchor regression**

Run: `python -m pytest tests/test_anchor_tools_v2.py tests/test_edge_anchor_tools.py tests/test_anchor_parser_bugs.py -v`
Expected: all pass.

- [ ] **Step 4.6: Commit**

```bash
git add vibelign/core/anchor_tools.py tests/test_anchor_parser_bugs.py
git commit -m "fix(anchor): suffix duplicate anchor names with _N instead of silently colliding"
```

---

## Task 5: Full-suite regression + project-map rebuild

- [ ] **Step 5.1: Run the full pytest suite**

Run: `python -m pytest tests/ -x -q`
Expected: every test passes (pre-existing count: 541 pass + 3 subtests). If any unrelated test fails, stop and report — do not "fix" it.

- [ ] **Step 5.2: Regenerate the project map so `.vibelign/project_map.json` matches the new parser**

Run: `python -m vibelign.cli scan`
(or `vib scan` if the `vib` shim is on PATH)

Expected: exit 0. The `anchor_spans` array in `.vibelign/project_map.json` should now contain zero `end: null` entries and zero spans named `NAME` / `FOO` (the docstring-literal phantoms).

- [ ] **Step 5.3: Sanity-check duplicates in the real codebase**

Run this quick script (via Bash tool or python -c) to print any files that still have duplicate anchor names after the fix:

```python
import json
from collections import Counter
data = json.load(open(".vibelign/project_map.json"))
for path, info in data["files"].items():
    names = [s["name"] for s in info.get("anchor_spans", [])]
    dups = [n for n, c in Counter(names).items() if c > 1]
    if dups:
        print(path, dups)
```

Expected: empty output (duplicates should now be suffixed `_2`).
Note the two files flagged by the audit (`patch_builder.py`, `mcp_handler_registry.py`): they should appear as `PATCH_BUILDER_BUILD_CONTRACT` + `PATCH_BUILDER_BUILD_CONTRACT_2` (etc). Report these to the user as candidates for a source-level rename, but do NOT rename them in this plan.

- [ ] **Step 5.4: Commit the regenerated project map**

```bash
git add .vibelign/project_map.json
git commit -m "chore: refresh project_map.json after anchor parser fixes"
```

- [ ] **Step 5.5: Final verification**

Run: `python -m vibelign.cli doctor --strict`
Expected: may exit 1 due to size-warning reasons unrelated to the parser; verify the reason lines do NOT mention anchor parsing.

---

## Out of scope (intentionally deferred)

- Renaming duplicate anchors in `patch_builder.py` / `mcp_handler_registry.py` source files — this is a human decision about which region should keep the unsuffixed name.
- Any JS/TS scenario additions — separate plan, to be written alongside the eval spec.
- Warning propagation to `vib doctor` output — current fix is silent; a future task can surface parser warnings through the doctor report.
