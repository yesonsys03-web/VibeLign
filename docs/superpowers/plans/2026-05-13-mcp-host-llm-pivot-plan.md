# MCP Host-LLM Pivot — Slim PoC Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** host LLM(Claude Code 등)이 anchor + project_map MCP primitive로 사용자 자유 자연어 요청에서 **정확한 file:anchor 지점을 직접 지적**할 수 있는지 검증. 현재 rule-based `patch_suggester` 정확도를 baseline으로 잡고, host-LLM-driven 경로가 동등 이상인지 측정한다.

> **Current status note (2026-05-14):** 이 문서는 PoC 실행 계획이자 구현 기록으로 보존한다. 신규 MCP 도구 2개(`anchor_read_content`, `project_map_get`)와 baseline lock, `user_requests.json` 데이터셋은 이미 mainlined 되었고, `CHANGELOG.md` v2.2.10 에 사용자 실요청 측정 결과(rule-based baseline `0/6`, host-LLM flow `6/6`)가 기록되어 있다. 따라서 남은 판단은 “도구를 만들 것인가”가 아니라 **Gemini/`vib patch --ai` 경로 deprecation 또는 host-LLM 중심 full migration을 어떤 순서로 진행할 것인가**이다.

**Architecture:**
- 진짜 책임 영역은 `vibelign/core/patch_suggester.py` + `vibelign/core/project_map.py` (file/anchor 매핑). codespeak action 라벨, Gemini는 PoC 범위 밖.
- 기존 `vibelign/mcp/` 인프라(19개 핸들러)는 그대로. 신규 2개 도구만 추가 — host LLM이 전역 구조와 앵커 내용을 직접 탐색하도록.
- 평가는 (a) `sample_project` 20개 자동 회귀 락 + (b) 사용자 실제 프로젝트의 자연어 요청 N개 수동 평가.
- Gemini(`ai_codespeak.py`), `use_ai` 인자 명시화, `vib patch --ai` 전부 무변경 — full migration은 PoC 결과 이후.

**Tech Stack:** Python 3.11+, pytest, 기존 `vibelign.core.anchor_tools.extract_anchor_blocks`, `vibelign.core.project_map.load_project_map`, MCP (`vibelign/mcp/`).

---

## File Structure

**Modified:**
- `vibelign/mcp/mcp_anchor_handlers.py` — `handle_anchor_read_content` 추가
- `vibelign/mcp/mcp_misc_handlers.py` 또는 신규 — `handle_project_map_get` 추가 (project_map이 anchor 도메인과 분리되므로 misc 또는 신규 module 적합)
- `vibelign/mcp/mcp_handler_registry.py` — 두 핸들러 등록 + Protocol 확장
- `vibelign/mcp/mcp_tool_specs.py` — 두 tool spec 추가

**Created:**
- `tests/test_mcp_anchor_read_content.py`
- `tests/test_mcp_project_map_get.py`
- `tests/benchmark/test_patch_suggester_baseline.py` — file/anchor 정확도 baseline 락
- `docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md`

**Untouched:**
- `vibelign/core/ai_codespeak.py`, `vibelign/core/codespeak.py`
- `vibelign/commands/vib_patch_cmd.py`
- `vibelign/mcp/mcp_patch_handlers.py` (use_ai 노출은 후속)
- patch_targeting / patch_builder / patch_suggester (측정만, 변경 없음)

---

## Task 0: 실제 실패 사례 수집 (사용자 협업, 비동기 가능)

**목적:** 평가 데이터셋의 자연 분포 확보. 인공 sample_project만으로는 실제 사용자 한국어 자유 요청에서의 정확도를 측정할 수 없음.

**Files:**
- Create: `tests/benchmark/user_requests.json` (수집되면)

- [ ] **Step 1: 사용자에게 요청**

사용자에게 다음 부탁:
> 최근에 본인 프로젝트에서 vib에게 "이거 수정해줘" 식으로 요청했거나 요청하고 싶었던 자연어 문장 **3~10개**를 모아주세요. 각 문장마다 정답 file 경로와 anchor 이름(있다면)을 메모.

- [ ] **Step 2: 받은 자료를 JSON 형태로 정리**

```json
[
  {
    "id": "user-001",
    "request": "<사용자 자연어 요청>",
    "correct_files": ["<상대 경로>"],
    "correct_anchor": "<ANCHOR_NAME 또는 null>",
    "source": "user-project",
    "notes": "<선택: 왜 이 위치가 정답인지>"
  }
]
```

`tests/benchmark/user_requests.json`으로 저장. 사용자 자료 미수집 시 빈 배열 `[]`로 두고 진행.

- [ ] **Step 3: Commit (수집된 경우만)**

```bash
git add tests/benchmark/user_requests.json
git commit -m "test(bench): 사용자 자연어 요청 실패 사례 수집"
```

---

## Task 1: `handle_anchor_read_content` 추가 (TDD)

**목적:** host LLM이 패치 작성 전 정확한 앵커 경계 안 내용을 한 번에 read. Claude Code의 `Read`보다 토큰 효율 + 경계 명확.

**Files:**
- Create: `tests/test_mcp_anchor_read_content.py`
- Modify: `vibelign/mcp/mcp_anchor_handlers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp_anchor_read_content.py
from __future__ import annotations

import json
from pathlib import Path

from vibelign.mcp.mcp_anchor_handlers import handle_anchor_read_content


def _factory(*, type: str, text: str) -> dict[str, str]:
    return {"type": type, "text": text}


def _write_sample(root: Path) -> None:
    (root / "sample.py").write_text(
        "# === ANCHOR: FOO_START ===\n"
        "def foo() -> int:\n"
        "    return 42\n"
        "# === ANCHOR: FOO_END ===\n"
        "\n"
        "# === ANCHOR: BAR_START ===\n"
        "def bar() -> str:\n"
        "    return \"hi\"\n"
        "# === ANCHOR: BAR_END ===\n",
        encoding="utf-8",
    )


def test_read_content_returns_anchor_body(tmp_path: Path) -> None:
    _write_sample(tmp_path)
    result = handle_anchor_read_content(
        tmp_path,
        {"file": "sample.py", "anchor_name": "FOO"},
        _factory,
    )
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is True
    body = payload["data"]["content"]
    assert "def foo()" in body
    assert "def bar()" not in body
    assert payload["data"]["anchor_name"] == "FOO"


def test_read_content_unknown_anchor(tmp_path: Path) -> None:
    _write_sample(tmp_path)
    result = handle_anchor_read_content(
        tmp_path,
        {"file": "sample.py", "anchor_name": "DOES_NOT_EXIST"},
        _factory,
    )
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "DOES_NOT_EXIST" in payload["error"]


def test_read_content_missing_file(tmp_path: Path) -> None:
    result = handle_anchor_read_content(
        tmp_path,
        {"file": "nope.py", "anchor_name": "X"},
        _factory,
    )
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "nope.py" in payload["error"]


def test_read_content_requires_args(tmp_path: Path) -> None:
    r1 = handle_anchor_read_content(tmp_path, {"anchor_name": "X"}, _factory)
    assert json.loads(r1[0]["text"])["ok"] is False
    r2 = handle_anchor_read_content(tmp_path, {"file": "x.py"}, _factory)
    assert json.loads(r2[0]["text"])["ok"] is False
```

- [ ] **Step 2: Run test, observe failure**

Run: `pytest tests/test_mcp_anchor_read_content.py -v`
Expected: ImportError — `handle_anchor_read_content`가 아직 없음

- [ ] **Step 3: Implement handler**

`vibelign/mcp/mcp_anchor_handlers.py`의 `# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_GET_META_END ===` 다음, `# === ANCHOR: MCP_ANCHOR_HANDLERS_END ===` 직전에 추가:

```python
# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_READ_CONTENT_START ===
def handle_anchor_read_content(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.anchor_tools import extract_anchor_blocks

    file_raw = arguments.get("file")
    anchor_raw = arguments.get("anchor_name")
    if not isinstance(file_raw, str) or not file_raw.strip():
        err = {"ok": False, "error": "file is required", "data": None}
        return _text(text_content, json.dumps(err, ensure_ascii=False))
    if not isinstance(anchor_raw, str) or not anchor_raw.strip():
        err = {"ok": False, "error": "anchor_name is required", "data": None}
        return _text(text_content, json.dumps(err, ensure_ascii=False))
    file_rel = file_raw.strip()
    anchor_name = anchor_raw.strip()
    fp = (root / file_rel).resolve()
    if not fp.is_file():
        err = {
            "ok": False,
            "error": f"file not found: {file_rel}",
            "data": None,
        }
        return _text(text_content, json.dumps(err, ensure_ascii=False))
    blocks = extract_anchor_blocks(fp)
    body = blocks.get(anchor_name)
    if body is None:
        err = {
            "ok": False,
            "error": f"anchor not found: {anchor_name}",
            "data": None,
        }
        return _text(text_content, json.dumps(err, ensure_ascii=False))
    payload = {
        "ok": True,
        "error": None,
        "data": {
            "file": file_rel,
            "anchor_name": anchor_name,
            "content": body,
        },
    }
    return _text(text_content, json.dumps(payload, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_READ_CONTENT_END ===
```

- [ ] **Step 4: Run test, observe pass**

Run: `pytest tests/test_mcp_anchor_read_content.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add vibelign/mcp/mcp_anchor_handlers.py tests/test_mcp_anchor_read_content.py
git commit -m "feat(mcp): handle_anchor_read_content — 앵커 경계 안 텍스트 정확히 read"
```

---

## Task 2: `handle_project_map_get` 추가 (TDD)

**목적:** host LLM이 프로젝트 전역 구조(카테고리/파일/앵커 인덱스)를 한 번에 파악. 매번 Read/Grep으로 헤매지 않고 한 도구 호출로 "어디에 무엇이 있는지" 확보.

**Files:**
- Create: `tests/test_mcp_project_map_get.py`
- Modify: `vibelign/mcp/mcp_misc_handlers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp_project_map_get.py
from __future__ import annotations

import json
from pathlib import Path

from vibelign.mcp.mcp_misc_handlers import handle_project_map_get


def _factory(*, type: str, text: str) -> dict[str, str]:
    return {"type": type, "text": text}


def test_project_map_get_returns_map(tmp_path: Path) -> None:
    # set up a tiny .vibelign/project_map.json
    vib = tmp_path / ".vibelign"
    vib.mkdir()
    (vib / "project_map.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "project_name": "demo",
                "tree": ["a.py"],
            }
        ),
        encoding="utf-8",
    )
    result = handle_project_map_get(tmp_path, {}, _factory)
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is True
    assert payload["data"]["project_name"] == "demo"
    assert "tree" in payload["data"]


def test_project_map_get_no_map(tmp_path: Path) -> None:
    result = handle_project_map_get(tmp_path, {}, _factory)
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "project_map" in payload["error"].lower()
```

- [ ] **Step 2: Run test, observe failure**

Run: `pytest tests/test_mcp_project_map_get.py -v`
Expected: ImportError

- [ ] **Step 3: Implement handler**

`load_project_map`은 `frozen=True` dataclass를 반환하며 직렬화 메서드가 없다. host LLM에 그대로 전달할 데이터는 디스크의 `.vibelign/project_map.json` 그 자체이므로, raw JSON read가 단일 올바른 구현이다.

`vibelign/mcp/mcp_misc_handlers.py` 파일 끝 `END` 앵커 직전에 추가:

```python
# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_PROJECT_MAP_GET_START ===
def handle_project_map_get(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.meta_paths import MetaPaths

    map_path = MetaPaths(root).project_map_path
    if not map_path.is_file():
        payload = {
            "ok": False,
            "error": "project_map.json not found — run `vib doctor` to generate it",
            "data": None,
        }
        return _text(text_content, json.dumps(payload, ensure_ascii=False))
    try:
        data = json.loads(map_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        payload = {
            "ok": False,
            "error": f"project_map.json read failed: {exc}",
            "data": None,
        }
        return _text(text_content, json.dumps(payload, ensure_ascii=False))
    payload = {"ok": True, "error": None, "data": data}
    return _text(text_content, json.dumps(payload, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_MISC_HANDLERS_HANDLE_PROJECT_MAP_GET_END ===
```

> **Note:** `MetaPaths(root).project_map_path`는 `.vibelign/project_map.json` 절대 경로를 반환 (이미 `vibelign/core/meta_paths.py`에 존재). 테스트의 `tmp_path / ".vibelign" / "project_map.json"`도 같은 위치를 가리킴.

- [ ] **Step 4: Run test, observe pass**

Run: `pytest tests/test_mcp_project_map_get.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add vibelign/mcp/mcp_misc_handlers.py tests/test_mcp_project_map_get.py
git commit -m "feat(mcp): handle_project_map_get — host LLM이 전역 구조 일괄 확보"
```

---

## Task 3: Registry + tool_specs 등재

**Files:**
- Modify: `vibelign/mcp/mcp_handler_registry.py`
- Modify: `vibelign/mcp/mcp_tool_specs.py`

- [ ] **Step 1: Extend AnchorHandlersModule Protocol**

`mcp_handler_registry.py`의 `AnchorHandlersModule` Protocol 내부, `handle_anchor_get_meta` 다음에 추가:

```python
    def handle_anchor_read_content(
        self,
        root: Path,
        arguments: dict[str, object],
        text_content: TextContentFactory,
    ) -> list[object]: ...
```

- [ ] **Step 2: Extend MiscHandlersModule Protocol**

같은 파일에서 `MiscHandlersModule` (또는 해당 misc 도구를 노출하는 Protocol)을 찾는다:

Run: `grep -n "MiscHandlersModule\|misc_handlers" vibelign/mcp/mcp_handler_registry.py | head -10`

해당 Protocol에 추가:

```python
    def handle_project_map_get(
        self,
        root: Path,
        arguments: dict[str, object],
        text_content: TextContentFactory,
    ) -> list[object]: ...
```

- [ ] **Step 3: Wire dispatch branches**

`mcp_handler_registry.py`에서 anchor 도구 디스패치 인접 분기를 찾고 추가:

```python
        if name == "anchor_read_content":
            return anchor_handlers.handle_anchor_read_content(
                root, arguments, text_content
            )
```

misc 디스패치 분기 (또는 적절한 위치)에 추가:

```python
        if name == "project_map_get":
            return misc_handlers.handle_project_map_get(
                root, arguments, text_content
            )
```

- [ ] **Step 4: Add tool specs**

`vibelign/mcp/mcp_tool_specs.py`의 `anchor_get_meta` entry 다음에 추가:

```python
{
    "name": "anchor_read_content",
    "description": (
        "지정된 파일의 앵커 내부 텍스트를 정확한 경계로 읽습니다. "
        "host LLM이 패치 작성 전에 정확한 컨텍스트만 빠르게 확인할 때 사용."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "file": {
                "type": "string",
                "description": "프로젝트 루트 기준 상대 경로",
            },
            "anchor_name": {
                "type": "string",
                "description": "ANCHOR: <NAME>_START / _END 의 NAME",
            },
        },
        "required": ["file", "anchor_name"],
    },
},
```

`patch_get` 또는 적절한 위치 다음에 `project_map_get` 추가:

```python
{
    "name": "project_map_get",
    "description": (
        "프로젝트의 카테고리/파일/앵커 인덱스를 한 번에 반환합니다. "
        "host LLM이 사용자 자연어 요청을 정확한 파일에 매핑하기 위한 전역 컨텍스트."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
    },
},
```

- [ ] **Step 5: Run dispatch + snapshot tests**

Run: `pytest tests/test_mcp_dispatch_capture.py tests/test_mcp_tool_snapshot.py tests/test_mcp_anchor_read_content.py tests/test_mcp_project_map_get.py -v`
Expected: 모두 PASS (snapshot은 갱신 필요시 갱신).

- [ ] **Step 6: Commit**

```bash
git add vibelign/mcp/mcp_handler_registry.py vibelign/mcp/mcp_tool_specs.py
git add tests/test_mcp_tool_snapshot.py
git commit -m "feat(mcp): anchor_read_content + project_map_get registry/spec 등재"
```

---

## Task 4: `patch_suggester` 정확도 baseline (numeric lock)

**목적:** 현재 rule-based `patch_suggester`의 file/anchor 정확도를 수치로 고정. 이후 host-LLM-driven 결과와 동일 메트릭으로 비교.

**Files:**
- Create: `tests/benchmark/test_patch_suggester_baseline.py`

- [ ] **Step 1: Write baseline test**

```python
# tests/benchmark/test_patch_suggester_baseline.py
"""
patch_suggester baseline lock — file 매칭 정확도를 수치로 고정.
MCP host-LLM pivot PoC는 이 수치를 동등 이상으로 재현해야 한다.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibelign.core.patch_suggester import suggest_patch

ROOT = Path(__file__).parent.parent.parent
SCENARIOS = json.loads(
    (ROOT / "tests" / "benchmark" / "scenarios.json").read_text(encoding="utf-8")
)
SAMPLE = ROOT / "tests" / "benchmark" / "sample_project"


def _normalize(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def _file_matches(actual: str, correct_files: list[str]) -> bool:
    a = _normalize(actual)
    return any(a.endswith(_normalize(c)) or _normalize(c).endswith(a) for c in correct_files)


def _anchor_matches(actual: str, correct_anchor: str | None) -> bool:
    if correct_anchor is None:
        return True  # scenario doesn't pin a specific anchor
    return actual == correct_anchor


@pytest.fixture(scope="module")
def results() -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for s in SCENARIOS:
        suggestion = suggest_patch(SAMPLE, str(s["request"]), use_ai=False)
        out.append(
            {
                "id": s["id"],
                "request": s["request"],
                "correct_files": s["correct_files"],
                "correct_anchor": s.get("correct_anchor"),
                "got_file": suggestion.target_file,
                "got_anchor": suggestion.target_anchor,
                "file_ok": _file_matches(
                    suggestion.target_file, [str(p) for p in s["correct_files"]]
                ),
                "anchor_ok": _anchor_matches(
                    suggestion.target_anchor, s.get("correct_anchor")
                ),
            }
        )
    return out


def test_file_accuracy_baseline(results: list[dict[str, object]]) -> None:
    """Lock current file-level matching count. Update value if intentional change."""
    passing = sum(1 for r in results if r["file_ok"])
    # Pin current value as N. Run once, record N, then set the assertion.
    # Initial pin: replace BASELINE_FILE_PASSING with actual count after first run.
    BASELINE_FILE_PASSING = 0  # ← 첫 실행 후 실제 값으로 갱신
    assert passing == BASELINE_FILE_PASSING, (
        f"file accuracy regression — passing={passing}, baseline={BASELINE_FILE_PASSING}.\n"
        f"failed scenarios: {[r['id'] for r in results if not r['file_ok']]}"
    )


def test_anchor_accuracy_baseline(results: list[dict[str, object]]) -> None:
    """Lock current anchor-level matching count among scenarios with a pinned anchor."""
    anchor_scenarios = [r for r in results if r["correct_anchor"] is not None]
    passing = sum(1 for r in anchor_scenarios if r["anchor_ok"])
    BASELINE_ANCHOR_PASSING = 0  # ← 첫 실행 후 실제 값으로 갱신
    assert passing == BASELINE_ANCHOR_PASSING, (
        f"anchor accuracy regression — passing={passing}, "
        f"baseline={BASELINE_ANCHOR_PASSING}.\n"
        f"failed: {[r['id'] for r in anchor_scenarios if not r['anchor_ok']]}"
    )
```

- [ ] **Step 2: First run to discover actual baseline numbers**

Run: `pytest tests/benchmark/test_patch_suggester_baseline.py -v -s`
Expected: 두 테스트 모두 FAIL (BASELINE_*_PASSING이 0). 실패 메시지에서 실제 passing 값을 읽고 메모.

- [ ] **Step 3: Pin actual numbers**

Step 2에서 본 값으로 `BASELINE_FILE_PASSING`과 `BASELINE_ANCHOR_PASSING`을 갱신.

- [ ] **Step 4: Run test, observe pass**

Run: `pytest tests/benchmark/test_patch_suggester_baseline.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add tests/benchmark/test_patch_suggester_baseline.py
git commit -m "test(bench): patch_suggester file/anchor 정확도 baseline 락 (PoC 비교 기준)"
```

---

## Task 5: Host LLM 수동 평가 runbook

**목적:** 사람이 Claude Code MCP 세션에서 실제로 신규 도구를 써서 file:anchor를 지목하는 능력을 측정.

**Files:**
- Create: `docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md`

- [ ] **Step 1: Write the runbook**

```markdown
# MCP Host-LLM Pivot — 수동 평가 Runbook

## 평가 목표

host LLM(Claude Code)이 신규 MCP 도구 `project_map_get` + `anchor_read_content` 만으로 사용자 자연어 요청을 정확한 file:anchor로 매핑하는가.

baseline = `patch_suggester.suggest_patch(request, use_ai=False)` (Task 4에서 락된 수치).

## 데이터셋

1. `tests/benchmark/scenarios.json` — 인공 시나리오 20개 (sample_project)
2. `tests/benchmark/user_requests.json` — 사용자 실제 자연어 요청 N개 (Task 0 산출물, 비어 있을 수 있음)

## 평가 절차

1. Claude Code (또는 Cursor) 에 VibeLign MCP 서버 등록
2. 평가용 worktree에서 `sample_project` (or 사용자 프로젝트 사본) 열기
3. 각 시나리오마다 새 대화로:
   - `request` 텍스트를 그대로 Claude에게 입력
   - Claude에게 명시적 지시: "정답 파일과 앵커 이름만 알려줘. 코드 수정은 하지 마. VibeLign MCP 도구를 활용해도 좋아."
   - Claude의 답을 기록 (file:anchor)
4. 정답(`correct_files`, `correct_anchor`)과 대조

## 메트릭

- File-level pass: Claude가 답한 파일이 `correct_files` 중 하나에 포함
- Anchor-level pass: file이 맞고 + anchor도 일치 (`correct_anchor=null`인 시나리오는 anchor 평가 제외)
- 도구 호출 분포: 평균 도구 호출 수, 어떤 도구가 가장 많이 쓰였는가

## 성공 기준

- File-level pass ≥ baseline + 0 (= 동등 이상)
- 사용자 실제 요청에서 File-level pass ≥ 60% (인공 시나리오보다 어렵다는 가정)
- 도구 호출이 5번 이하로 수렴 (LLM이 헤매지 않음)

## 결과 기록

`.vibelign/eval/2026-05-13-mcp-pivot/results.md` 에 표 형태:

| id | request | correct | got (host LLM) | got (baseline) | tool calls |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

## 의사결정

- 성공 → full migration plan (use_ai 인자 노출, Gemini deprecation, ACTION_MAP 단순화, marketing 메시지 갱신)
- 미달 → 실패 패턴 분석 → 추가 MCP 도구(예: `anchor_search`, `anchor_list_by_file`) 도입 검토 → plan v3
```

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md
git commit -m "docs(plan): MCP host-LLM pivot 수동 평가 runbook"
```

---

## Task 6: PoC 종결 + memory 갱신

**목적:** 도구 추가가 끝났음을 표시하고, 평가 단계(수동)로 핸드오프.

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update CHANGELOG**

`CHANGELOG.md`의 `## [Unreleased]` (없으면 생성)에 추가:

```markdown
### Added
- MCP `anchor_read_content`: 앵커 내부 텍스트를 정확한 경계로 read (host LLM 친화)
- MCP `project_map_get`: 프로젝트 전역 구조(카테고리/파일/앵커) 일괄 read

### Notes
- 위 도구는 MCP host-LLM pivot PoC의 일부. 사용 평가는 `docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md` 참조.
- Gemini 경로(`vib patch --ai`, `ai_codespeak.py`)는 PoC 단계에서 변경 없음. 평가 결과에 따라 full migration 결정.
```

- [ ] **Step 2: Update pivot memory note**

수동: `/Users/topsphinx/.claude/projects/-Users-topsphinx-Documents-coding-VibeLign/memory/vibelign_mcp_pivot.md` 의 "관련 작업 시작점" 섹션에 추가:

```markdown
**PoC v2 구현 완료 (2026-05-13):**
- 신규 MCP 도구 2개: `anchor_read_content`, `project_map_get`
- baseline 락: `tests/benchmark/test_patch_suggester_baseline.py`
- 평가 runbook: `docs/superpowers/specs/2026-05-13-mcp-host-llm-pivot-eval-runbook.md`
- 다음 단계: runbook 수동 실행 → 결과 분석 → full migration 또는 plan v3
```

- [ ] **Step 3: Commit CHANGELOG**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): MCP host-LLM pivot PoC 도구 추가 기록"
```

---

## Self-Review Checklist

- **Spec coverage**: pivot 가설 재정의(file/anchor 매핑이 진짜 책임 영역)에 맞춰 신규 도구 2개(`anchor_read_content`, `project_map_get`) + baseline + 평가 runbook 매핑됨. Gemini 관련 모든 작업은 의도적으로 제외.
- **Placeholder scan**: 각 task에 구체 코드/명령 포함. Task 2 Step 4-5는 `ProjectMapSnapshot` 실제 직렬화 방식 미확인이므로 두 대안(dataclass 분기 vs raw JSON 재read) 모두 제공.
- **Type consistency**: 모든 새 핸들러 시그니처 `(root: Path, arguments: dict[str, object], text_content: TextContentFactory) -> list[object]` 일관. 반환 payload 형식 `{"ok": bool, "error": str|None, "data": object|None}` 일관.

## 알려진 가정 (실행자 확인)

1. `extract_anchor_blocks(path) -> dict[str, str]` — anchor 이름 → 본문. 이미 `vibelign/core/anchor_tools.py`에 존재 확인됨.
2. `load_project_map(root) -> tuple[Snapshot|None, str|None]` — 이미 `vibelign/core/project_map.py`에 존재 확인됨. Snapshot 직렬화 방식은 Task 2 Step 3에서 확정.
3. `MiscHandlersModule` Protocol 명칭은 `mcp_handler_registry.py`에서 실제 명칭 확인 후 사용 (Task 3 Step 2).
4. Task 4 baseline 수치는 첫 실행 후 발견(0이 아님). 인공 시나리오 20개 중 sample_project가 실제로 갖춘 파일/앵커에 한해서만 적용.
5. Task 5 평가는 사람 작업 — plan 본 task는 도구/runbook 준비까지. 실제 측정은 plan 종료 후.

## 실행 옵션

Plan saved to `docs/superpowers/plans/2026-05-13-mcp-host-llm-pivot-plan.md`. 두 가지 선택:

**1. Subagent-Driven (권장)** — task마다 fresh subagent dispatch, 사이에 검토. 빠른 반복.

**2. Inline Execution** — 이 세션에서 executing-plans skill로 batch 실행, 체크포인트마다 검토.

어느 쪽으로 진행할까요?
