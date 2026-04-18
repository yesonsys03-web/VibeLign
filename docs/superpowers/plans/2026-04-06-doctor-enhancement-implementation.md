# Doctor Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `vib doctor` return a structured recovery-oriented issue contract that both CLI and GUI can render consistently.

**Architecture:** Keep `doctor_v2` as the single source of truth for doctor results, but move issue production closer to the source so category, severity, and recovery metadata stop depending on string parsing. Update CLI and GUI to consume the structured issue fields directly, then preserve existing plan/apply behavior with a minimal compatibility update in the action planner.

**Tech Stack:** Python, TypeScript, React, unittest, Vite

---

## Execution progress

- [x] Task 1 complete — Structured doctor issue contract in Python backend
- [x] Task 2 complete — Legacy doctor/guard compatibility and planner plumbing
- [x] Task 3 complete — GUI Doctor page uses backend contract directly
- [x] Task 4 complete — Final regression verification

## File map

- `vibelign/core/risk_analyzer.py` — emit structured issue dictionaries instead of plain strings
- `vibelign/core/doctor_v2.py` — enrich issues with recovery metadata and render richer doctor output
- `vibelign/core/analysis_cache.py` — invalidate old cached doctor reports after the schema change
- `vibelign/commands/doctor_cmd.py` — keep the legacy plain `doctor` command working with structured issues (not `vib_doctor_cmd.py`)
- `vibelign/commands/guard_cmd.py` — keep the legacy plain `guard` command working with structured issues
- `vibelign/action_engine/action_planner.py` — prefer `recommended_command` over parsing `next_step`
- `vibelign-gui/src/pages/Doctor.tsx` — render severity/category/recovery fields directly from backend data
- `tests/test_vib_doctor_v2.py` — contract tests for doctor envelope, cache schema, and markdown rendering
- `tests/test_plain_doctor_guard_render.py` — regression test for legacy doctor text output
- `tests/test_action_planner.py` — new planner compatibility tests for `recommended_command`

---

### Task 1: Introduce structured doctor issues in the Python backend

**Files:**
- Modify: `tests/test_vib_doctor_v2.py`
- Modify: `vibelign/core/risk_analyzer.py`
- Modify: `vibelign/core/doctor_v2.py`
- Modify: `vibelign/core/analysis_cache.py`

- [ ] **Step 1: Add failing contract tests in `tests/test_vib_doctor_v2.py`**

Add these tests near the existing MCP / prepared-tool tests:

```python
    def test_doctor_issue_contains_structured_recovery_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n" * 300, encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)
            issue = envelope["data"]["issues"][0]

            self.assertIn("severity", issue)
            self.assertIn("category", issue)
            self.assertIn("recommended_command", issue)
            self.assertIn("can_auto_fix", issue)
            self.assertIn("auto_fix_label", issue)

    def test_missing_cursor_mcp_issue_uses_mcp_category_and_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / ".cursorrules").write_text("rules\n", encoding="utf-8")

            envelope = build_doctor_envelope(root, strict=False)
            issues = envelope["data"]["issues"]
            mcp_issue = next(i for i in issues if i["category"] == "mcp")

            self.assertEqual("high", mcp_issue["severity"])
            self.assertEqual("vib start --tools cursor", mcp_issue["recommended_command"])
            self.assertFalse(mcp_issue["can_auto_fix"])

    def test_analysis_cache_schema_bumped_to_2(self):
        from vibelign.core.analysis_cache import ANALYSIS_CACHE_SCHEMA

        self.assertEqual(2, ANALYSIS_CACHE_SCHEMA)
```

- [ ] **Step 2: Run the targeted backend tests and confirm they fail**

Run:

```bash
python -m unittest \
  tests.test_vib_doctor_v2.VibDoctorV2Test.test_doctor_issue_contains_structured_recovery_fields \
  tests.test_vib_doctor_v2.VibDoctorV2Test.test_missing_cursor_mcp_issue_uses_mcp_category_and_command \
  tests.test_vib_doctor_v2.VibDoctorV2Test.test_analysis_cache_schema_bumped_to_2
```

Expected: FAIL because the current issue dicts do not include the new fields and `ANALYSIS_CACHE_SCHEMA` is still `1`.

- [ ] **Step 3: Change `vibelign/core/risk_analyzer.py` to emit structured issue dictionaries**

Replace the string-only issue model with a dict-based issue model while keeping `suggestions` for compatibility with old callers.

Use this shape near the top of the file:

```python
IssueDict = dict[str, object]


@dataclass
class RiskReport:
    level: str = "GOOD"
    score: int = 0
    issues: list[IssueDict] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)


def add_issue(
    report: RiskReport,
    *,
    found: str,
    suggestion: str,
    score: int,
    path: str | None,
    category: str,
    severity: str,
    check_type: str,
) -> None:
    report.issues.append(
        {
            "found": found,
            "next_step": suggestion,
            "path": path,
            "category": category,
            "severity": severity,
            "check_type": check_type,
        }
    )
    report.suggestions.append(suggestion)
    report.score += score
```

Then update the existing calls. For example:

```python
        if name in ENTRY_FILES and lines > entry_limit:
            oversized_entry_files += 1
            add_issue(
                report,
                found=f"{rel} 파일이 너무 깁니다 ({lines}줄) — AI가 어디를 고쳐야 할지 헷갈릴 수 있어요",
                suggestion=f"{name}은 시작 코드만 두고 나머지는 다른 파일로 옮기는 게 좋아요",
                score=3,
                path=rel,
                category="structure",
                severity="low" if lines < 500 else "medium",
                check_type="oversized_entry",
            )
```

And for anchors:

```python
        if lines > anchor_limit and "=== ANCHOR:" not in text:
            missing_anchor_files += 1
            add_issue(
                report,
                found=f"{rel}에 안전 구역 표시(앵커)가 없어요",
                suggestion=f"{name}에 앵커를 추가하면 AI가 딱 그 부분만 안전하게 고칠 수 있어요",
                score=2,
                path=rel,
                category="anchor",
                severity="medium",
                check_type="missing_anchor",
            )
```

Update `_check_dependency_risks()` to return dicts too:

```python
def _check_dependency_risks(root: Path) -> list[IssueDict]:
    issues: list[IssueDict] = []
    ...
    issues.append(
        {
            "found": f"{rel}이 '{mod}' 파일을 불러오려 하는데 그 파일이 없어요",
            "next_step": f"'{mod}' 파일이 프로젝트 안에 있는지 확인해보세요",
            "path": rel,
            "category": "metadata",
            "severity": "medium",
            "check_type": "missing_import_target",
        }
    )
```

**CRITICAL:** Replace the existing dedupe logic `report.issues = list(dict.fromkeys(report.issues))` (line ~192). `dict.fromkeys()` requires hashable items — `list[dict]` will raise `TypeError: unhashable type: 'dict'`. Use tuple-key dedupe instead:

```python
report.issues = list({(item["found"], item.get("path")): item for item in report.issues}.values())
```

- [ ] **Step 4: Update `vibelign/core/doctor_v2.py` and `analysis_cache.py` to consume the new issue contract**

First, bump the cache schema:

```python
# vibelign/core/analysis_cache.py
ANALYSIS_CACHE_SCHEMA = 2
```

Then change the doctor issue enrichment flow. Replace the old `_issue_details(issues: list[str], suggestions: list[str])` with a dict-based version:

```python
def _issue_details(issues: list[dict[str, object]]) -> list[dict[str, object]]:
    details: list[dict[str, object]] = []
    for issue in issues:
        found = str(issue.get("found", ""))
        next_step = str(issue.get("next_step", "관련 파일을 직접 열어서 확인해보세요."))
        category = str(issue.get("category", "metadata"))
        severity = str(issue.get("severity", "low"))
        recommended_command = issue.get("recommended_command")
        can_auto_fix = bool(issue.get("can_auto_fix", False))
        auto_fix_label = issue.get("auto_fix_label")
        path = issue.get("path")

        if category == "anchor" and recommended_command is None:
            recommended_command = "vib doctor --fix"
            can_auto_fix = True
            auto_fix_label = "앵커 자동 추가"

        details.append(
            {
                "found": found,
                "why_it_matters": issue.get(
                    "why_it_matters",
                    f"{found} 때문에 AI가 엉뚱한 곳까지 건드리거나 코드를 더 꼬이게 만들 수 있어요.",
                ),
                "next_step": next_step,
                "path": path,
                "severity": severity,
                "category": category,
                "recommended_command": recommended_command,
                "can_auto_fix": can_auto_fix,
                "auto_fix_label": auto_fix_label,
            }
        )
    return details
```

Update the MCP / prepared-tool appenders to append dicts instead of parallel strings. Example:

```python
def _append_mcp_issues(
    issues: list[dict[str, object]], mcp_status: dict[str, dict[str, object]]
) -> None:
    for tool_name, status in mcp_status.items():
        if not status["enabled"] or status["registered"]:
            continue
        config_path = str(status["config_path"])
        label = str(status["label"])
        if status["state"] == "invalid_json":
            issues.append(
                {
                    "found": f"{config_path} 파일을 읽을 수 없어요",
                    "next_step": f"{label} MCP 설정 파일을 다시 만들어야 해요.",
                    "path": config_path,
                    "category": "mcp",
                    "severity": "high",
                    "recommended_command": f"vib start --tools {tool_name}",
                    "can_auto_fix": False,
                    "auto_fix_label": None,
                }
            )
            continue
```

In `analyze_project_v2()`, stop building a separate `suggestions` list and instead use the dicts directly:

```python
    issues = list(legacy.issues)
    ...
    _append_mcp_issues(issues, mcp_status)
    _append_prepared_tool_issues(issues, prepared_tool_status)
    detailed_issues = _issue_details(issues)
    report = DoctorV2Report(
        ...
        issues=detailed_issues,
        recommended_actions=_recommended_actions(detailed_issues),
    )
```

And update `_recommended_actions()` to prefer `recommended_command`:

```python
def _recommended_actions(issues: list[dict[str, object]]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        command = issue.get("recommended_command")
        next_step = issue.get("next_step")
        action = str(command or next_step or "")
        if action and action not in seen:
            seen.add(action)
            actions.append(action)
    return actions[:6]
```

- [ ] **Step 5: Run the backend tests again and make sure they pass**

Run:

```bash
python -m unittest tests.test_vib_doctor_v2 -v
```

Expected: PASS. The doctor envelope should now include the new issue fields, and the cache schema assertion should pass.

- [ ] **Step 6: Commit the backend contract change**

```bash
git add tests/test_vib_doctor_v2.py vibelign/core/risk_analyzer.py vibelign/core/doctor_v2.py vibelign/core/analysis_cache.py
git commit -m "feat: add structured recovery metadata to doctor issues"
```

---

### Task 2: Keep legacy doctor/guard output and plan/apply plumbing compatible

**Files:**
- Modify: `vibelign/commands/doctor_cmd.py` (legacy plain doctor command, not `vib_doctor_cmd.py`)
- Modify: `vibelign/commands/guard_cmd.py` (legacy plain guard command — uses `isinstance(raw_item, str)` filter that drops all dict issues)
- Modify: `vibelign/core/doctor_v2.py`
- Modify: `vibelign/action_engine/action_planner.py`
- Modify: `tests/test_plain_doctor_guard_render.py`
- Create: `tests/test_action_planner.py`

- [ ] **Step 1: Add failing compatibility tests**

Extend `tests/test_plain_doctor_guard_render.py` with a structured-issue assertion:

```python
    def test_run_doctor_renders_structured_issue_found_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n" * 300, encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.doctor_cmd.print_ai_response") as mocked:
                    run_doctor(SimpleNamespace(json=False, strict=False))
                    rendered = mocked.call_args[0][0]
                    self.assertIn("## 3. 먼저 보면 좋은 문제", rendered)
                    self.assertIn("main.py", rendered)
            finally:
                os.chdir(previous)
```

Create `tests/test_action_planner.py` with planner command preservation tests:

```python
import unittest

from vibelign.action_engine.action_planner import generate_plan


class ActionPlannerTest(unittest.TestCase):
    def test_generate_plan_prefers_recommended_command(self):
        report = {
            "project_score": 60,
            "issues": [
                {
                    "found": "앵커가 없어요",
                    "next_step": "앵커를 자동으로 추가한 뒤 다시 doctor를 실행해요",
                    "recommended_command": "vib doctor --fix",
                    "path": "foo.py",
                }
            ],
        }

        plan = generate_plan(report)

        self.assertEqual("vib doctor --fix", plan.actions[0].command)
```

- [ ] **Step 2: Run the compatibility tests and confirm they fail**

Run:

```bash
python -m unittest \
  tests.test_plain_doctor_guard_render.PlainDoctorGuardRenderTest.test_run_doctor_renders_structured_issue_found_lines \
  tests.test_action_planner.ActionPlannerTest.test_generate_plan_prefers_recommended_command
```

Expected: FAIL because `doctor_cmd.py` still assumes string issues and `action_planner.py` still extracts commands from `next_step`.

- [ ] **Step 3: Update `doctor_cmd.py`, `guard_cmd.py`, doctor markdown rendering, and planner command extraction**

In `vibelign/commands/doctor_cmd.py`, render structured issues safely:

```python
    for i, issue in enumerate(report.issues, 1):
        if isinstance(issue, dict):
            lines.append(f"{i}. {issue.get('found', '')}")
        else:
            lines.append(f"{i}. {issue}")
```

In `vibelign/commands/guard_cmd.py`, fix the `isinstance(raw_item, str)` filter in `_render_markdown()` (~line 72-76) so dict issues are not silently dropped:

```python
    raw_issues = doctor_data.get("issues", [])
    issues: list[str] = []
    for raw_item in raw_issues:
        if isinstance(raw_item, dict):
            issues.append(str(raw_item.get("found", "")))
        elif isinstance(raw_item, str):
            issues.append(raw_item)
```

In `vibelign/core/doctor_v2.py`, expand markdown rendering so detailed output shows the new contract:

```python
    if detailed and report.issues:
        lines.extend(["", "자세히 보면:"])
        for item in report.issues:
            sev = str(item.get("severity", "low")).upper()
            cat = str(item.get("category", "metadata"))
            lines.append(f"- [{sev}][{cat}] {item['found']}")
            lines.append(f"  왜 중요하냐면: {item['why_it_matters']}")
            lines.append(f"  다음에 하면 좋은 일: {item['next_step']}")
            if item.get("recommended_command"):
                lines.append(f"  추천 명령: {item['recommended_command']}")
            lines.append(
                "  자동 수정: 가능"
                if item.get("can_auto_fix")
                else "  자동 수정: 불가"
            )
```

In `vibelign/action_engine/action_planner.py`, prefer `recommended_command` first and keep the old fallback:

```python
def _issue_to_action(issue: Dict[str, Any]) -> Action:
    action_type = _classify_issue(issue)
    target_path = issue.get("path")

    command: str | None = None
    recommended_command = issue.get("recommended_command")
    if isinstance(recommended_command, str) and recommended_command.strip():
        command = recommended_command.strip()
    else:
        next_step: str = issue.get("next_step", "")
        if "`" in next_step:
            start = next_step.find("`") + 1
            end = next_step.find("`", start)
            if end > start:
                command = next_step[start:end]
        elif next_step.startswith("vib "):
            command = next_step.strip()
```

- [ ] **Step 4: Run the compatibility tests again**

Run:

```bash
python -m unittest tests.test_plain_doctor_guard_render tests.test_action_planner -v
```

Expected: PASS. The plain doctor command should render `issue["found"]`, and generated plan actions should preserve explicit `recommended_command` values.

- [ ] **Step 5: Commit the compatibility layer**

```bash
git add vibelign/commands/doctor_cmd.py vibelign/commands/guard_cmd.py vibelign/core/doctor_v2.py vibelign/action_engine/action_planner.py tests/test_plain_doctor_guard_render.py tests/test_action_planner.py
git commit -m "fix: preserve legacy doctor/guard cli and plan compatibility with structured issues"
```

---

### Task 3: Update the GUI Doctor page to trust backend issue data

**Files:**
- Modify: `vibelign-gui/src/pages/Doctor.tsx`

- [ ] **Step 1: Update the TypeScript issue/report types**

Replace the local interfaces at the top of `Doctor.tsx` with the structured fields used by the backend:

```tsx
interface Issue {
  severity: "high" | "medium" | "low";
  category?: string;
  found: string;
  why_it_matters?: string;
  next_step?: string;
  path?: string | null;
  recommended_command?: string | null;
  can_auto_fix?: boolean;
  auto_fix_label?: string | null;
}

interface DoctorReport {
  project_score: number;
  status: "Safe" | "Good" | "Caution" | "Risky" | "High Risk";
  anchor_coverage: number;
  issues: Issue[];
  recommended_actions: string[];
}
```

- [ ] **Step 2: Remove `inferSeverity()` and render issue metadata directly**

Delete `inferSeverity()` entirely, then add an explicit status-color helper:

```tsx
function statusBadgeStyle(status: DoctorReport["status"]) {
  if (status === "Safe" || status === "Good") {
    return { background: "#4DFF91", color: "#1A1A1A" };
  }
  if (status === "Caution" || status === "Risky") {
    return { background: "#FFD166", color: "#1A1A1A" };
  }
  return { background: "#FF4D4D", color: "#fff" };
}
```

Use it in the header instead of the current `Healthy` comparison, and expand the issue card UI:

```tsx
                <div className="issue-item" key={i}>
                  <span className={`issue-severity ${sevClass(issue.severity)}`}>
                    {issue.severity.toUpperCase()}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                      <div style={{ fontWeight: 700, fontSize: 12 }}>{issue.found}</div>
                      {issue.category && <code style={{ fontSize: 10 }}>{issue.category}</code>}
                    </div>
                    {issue.path && <code style={{ fontSize: 10, color: "#888" }}>{issue.path}</code>}
                    {issue.why_it_matters && (
                      <div style={{ fontSize: 11, marginTop: 3, color: "#666" }}>{issue.why_it_matters}</div>
                    )}
                    {issue.next_step && (
                      <div style={{ fontSize: 11, marginTop: 3, color: "#666" }}>다음 단계: {issue.next_step}</div>
                    )}
                    {issue.recommended_command && (
                      <code style={{ display: "block", fontSize: 10, color: "#888", marginTop: 4 }}>
                        {issue.recommended_command}
                      </code>
                    )}
                    <div style={{ fontSize: 10, marginTop: 4, color: issue.can_auto_fix ? "#0a7" : "#888" }}>
                      {issue.can_auto_fix
                        ? `자동 수정 가능${issue.auto_fix_label ? ` · ${issue.auto_fix_label}` : ""}`
                        : "자동 수정 불가"}
                    </div>
                  </div>
                </div>
```

- [ ] **Step 3: Type-check and lint the GUI**

Run:

```bash
cd vibelign-gui
npm run build
npm run lint
```

Expected: PASS. `Doctor.tsx` should compile without the old `Healthy` status mismatch or severity inference fallback.

- [ ] **Step 4: Manual QA the Doctor page**

Run:

```bash
cd vibelign-gui
npm run dev
```

Manual checks:

1. Open the Doctor page.
2. Confirm the status badge uses `Safe / Good / Caution / Risky / High Risk` colors correctly.
3. Confirm issue cards show category, next step, recommended command, and auto-fix text.
4. Confirm APPLY still refreshes the report after success.

- [ ] **Step 5: Commit the GUI contract adoption**

```bash
git add vibelign-gui/src/pages/Doctor.tsx
git commit -m "feat: render structured doctor recovery data in gui"
```

---

### Task 4: Final regression verification

**Files:**
- Modify: none
- Test: `tests/test_vib_doctor_v2.py`
- Test: `tests/test_plain_doctor_guard_render.py`
- Test: `tests/test_action_planner.py`

- [ ] **Step 1: Run the Python regression suite for doctor-related behavior**

Run:

```bash
python -m unittest \
  tests.test_vib_doctor_v2 \
  tests.test_plain_doctor_guard_render \
  tests.test_action_planner -v
```

Expected: PASS.

- [ ] **Step 2: Re-run the GUI build as a final contract check**

Run:

```bash
cd vibelign-gui
npm run build
```

Expected: PASS.

- [ ] **Step 3: Smoke-test the CLI output manually**

Run from repo root:

```bash
vib doctor --detailed
vib doctor --json
vib doctor --plan --json
```

Expected:

- `--detailed` shows severity/category/recommended command lines without crashing
- `--json` returns issue objects with `severity`, `category`, `recommended_command`, `can_auto_fix`, `auto_fix_label`
- `--plan --json` still returns actions with command hints when available

---

## Self-review checklist

- Spec coverage:
  - structured issue contract → Task 1
  - cache schema migration → Task 1
  - risk_analyzer dedupe crash fix (dict.fromkeys → tuple-key) → Task 1
  - CLI recovery rendering → Task 2
  - legacy guard_cmd dict compatibility → Task 2
  - GUI severity/status contract → Task 3
  - planner compatibility without full category rewrite → Task 2
  - final regression verification → Task 4
- Placeholder scan:
  - no TBD / TODO markers remain
  - all commands and target files are explicit
- Type consistency:
  - issue keys are consistently `found`, `why_it_matters`, `next_step`, `path`, `severity`, `category`, `recommended_command`, `can_auto_fix`, `auto_fix_label`
  - planner reads `recommended_command` first and falls back to legacy parsing

---

Plan complete and saved to `docs/superpowers/plans/2026-04-06-doctor-enhancement-implementation.md`.

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
