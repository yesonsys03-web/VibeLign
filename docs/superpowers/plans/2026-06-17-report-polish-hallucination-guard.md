# Plan B — 다듬기 환각·과장 방어 (수치 가드 + 모호어 린트) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI 다듬기가 숫자·사실을 바꾸거나 과장을 끼워넣지 못하게 결정론적으로 막고, 모호어를 비차단 경고로 표면화한다.

**Architecture:** ① 다듬기 프롬프트에 "숫자·사실 변경 금지, 과장 신규 생성 금지" 명시. ② polish 후 원본 블록의 수치가 다듬은 문장에 보존됐는지 정규식으로 검증 — 누락/신규 숫자가 있으면 그 블록은 원문 유지 + guard 기록(`polish_guard.py`). ③ 모호어를 규칙 기반으로 스캔(`vague_lint.py`). guard·경고는 Plan A 의 emit payload·블록 diff 화면에 배지/하이라이트로 흐른다.

**Tech Stack:** Python 3 / pytest / ruff (백엔드), React 19 + TypeScript + Vitest (GUI 표시).

**의존성:** Task 1~4 는 Plan A 와 독립(가드는 UI 없이도 조용히 동작). **Task 5 는 Plan A Task 5(`emit.py`)**, **Task 6 은 Plan A Task 9(`BlockDiff.tsx`)** 가 선행돼야 한다. 권장 순서: 본 Plan Task 1~4 먼저 머지 → Plan A → 본 Plan Task 5~6.

---

## File Structure

**신규 (단일 책임)**
- `vibelign/core/reporting_cli/polish_guard.py` — 수치 추출 + 보존 검증(순수 함수)
- `vibelign/core/reporting_cli/vague_lint.py` — 모호어 스캔(순수 함수)

**수정**
- `vibelign/core/reporting_cli/polish.py` — 프롬프트 강화 + `polish_report_model_with_guards` 추가(가드 통합)
- `vibelign/core/reporting_cli/emit.py` *(Plan A 생성)* — guards/vague_warnings 채우기
- `vibelign-gui/src/components/report-review/BlockDiff.tsx` *(Plan A 생성)* — 모호어 하이라이트

**테스트**
- `tests/core/reporting_cli/test_polish_guard.py`, `test_vague_lint.py`
- `tests/core/reporting_cli/test_polish.py` (가드 통합 케이스 추가)
- `tests/core/reporting_cli/test_emit.py` (guards/vague 채움 케이스 추가)
- `vibelign-gui/src/components/report-review/__tests__/BlockDiff.test.tsx`

> **구조화 규율:** 가드·린트는 순수 함수(I/O 없음)로 두어 단위 테스트 용이. `polish_report_model` 시그니처는 유지(기존 호출자 불변). 신규 파일은 위 2개만.

---

## Task 1: 다듬기 프롬프트 강화

**Files:**
- Modify: `vibelign/core/reporting_cli/polish.py:34-38`
- Test: `tests/core/reporting_cli/test_polish.py` (추가)

- [ ] **Step 1: 실패 테스트 작성 (프롬프트가 핵심 제약 문구를 포함하는지)**

```python
# tests/core/reporting_cli/test_polish.py 에 추가
from vibelign.core.reporting_cli import polish as polish_mod


def test_polish_prompt_forbids_changing_numbers(monkeypatch):
    captured = {}

    def fake_build(adapter, prompt):
        captured["prompt"] = prompt
        return None  # 미설치로 처리 → 호출만 캡처

    monkeypatch.setattr(polish_mod.cli_adapters, "build_cli_command", fake_build)
    polish_mod.polish_block_text(
        "신규 회원 50% 증가", provider="codex",
        runner=polish_mod.cli_adapters.SubprocessPlanningCliRunner(), root=None, timeout_seconds=1,
    )
    assert "숫자" in captured["prompt"]
    assert "과장" in captured["prompt"]
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_polish.py -k forbids_changing_numbers -v`
Expected: FAIL — 프롬프트에 해당 문구 없음

- [ ] **Step 3: 프롬프트 교체 (`polish.py:34-38`)**

```python
    prompt = (
        "다음 보고서 문장을 비즈니스 보고 어조로 자연스럽게 다듬어줘. "
        "단, 숫자·비율·금액·날짜·고유명사는 절대 바꾸지 말고, 원문에 없는 사실이나 "
        "'대폭·획기적' 같은 과장 표현을 새로 만들지 마. 군더더기만 덜어내고 의미는 그대로 유지해. "
        "설명·따옴표 없이 다듬은 문장만 출력해.\n\n"
        f"{text}"
    )
```

- [ ] **Step 4: 통과 확인 + 기존 polish 테스트 회귀**

Run: `pytest tests/core/reporting_cli/test_polish.py -v`
Expected: PASS (신규 1 + 기존 전부)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/polish.py tests/core/reporting_cli/test_polish.py
git commit -m "feat(report): 다듬기 프롬프트에 수치·사실 변경/과장 금지 명시"
```

---

## Task 2: 수치 보존 가드 `polish_guard.py`

**Files:**
- Create: `vibelign/core/reporting_cli/polish_guard.py`
- Test: `tests/core/reporting_cli/test_polish_guard.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_polish_guard.py
from __future__ import annotations

from vibelign.core.reporting_cli.polish_guard import extract_numbers, guard_polished


def test_extract_normalizes_thousands_separator():
    assert extract_numbers("회원 1,000명, 매출 50% 증가") == {"1000", "50"}


def test_guard_ok_when_numbers_preserved():
    ok, reason, missing = guard_polished("신규 회원 50% 증가", "신규 회원이 50% 늘었습니다")
    assert ok is True
    assert reason == ""
    assert missing == []


def test_guard_fails_when_number_dropped():
    ok, reason, missing = guard_polished("신규 회원 50% 증가", "신규 회원이 대폭 늘었습니다")
    assert ok is False
    assert reason == "number_dropped"
    assert missing == ["50"]


def test_guard_fails_when_new_number_added():
    ok, reason, missing = guard_polished("회원이 늘었다", "회원이 200% 늘었다")
    assert ok is False
    assert reason == "number_added"


def test_guard_ok_when_no_numbers_either_side():
    ok, reason, missing = guard_polished("회원이 늘었다", "회원이 증가했습니다")
    assert ok is True


def test_guard_ok_when_date_reformatted():
    # '06'(원본) 과 '6'(다듬) 을 같게 보아 멀쩡한 날짜 재포맷을 되돌리지 않는다.
    ok, reason, missing = guard_polished("기한 2026-06-17 까지", "기한 2026년 6월 17일까지")
    assert ok is True
    assert missing == []
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_polish_guard.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# vibelign/core/reporting_cli/polish_guard.py
from __future__ import annotations

import re
from collections import Counter

# 천단위 콤마를 포함한 숫자 런. 단위(%, 만, 원 등)는 무시하고 숫자 자체만 본다.
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _norm(token: str) -> str:
    """천단위 콤마 제거 + 정수 토큰의 선행 0 제거('06'→'6').
    날짜 재포맷('2026-06-17'→'2026년 6월 17일')이 가드를 헛발동시키지 않게 한다."""
    t = token.replace(",", "")
    return str(int(t)) if t.isdigit() else t


def extract_numbers(text: str) -> set[str]:
    """문자열의 숫자 토큰을 정규화한 집합으로 반환한다."""
    return {_norm(m) for m in _NUM.findall(text)}


def _counts(text: str) -> Counter[str]:
    return Counter(_norm(m) for m in _NUM.findall(text))


def guard_polished(original: str, polished: str) -> tuple[bool, str, list[str]]:
    """다듬은 문장이 원문의 숫자를 그대로 보존하고 새 숫자를 안 만들었는지 검증한다.
    반환: (ok, reason, missing). ok=False 면 호출자가 원문을 유지해야 한다.
    reason: '' | 'number_dropped' | 'number_added' | 'number_changed'."""
    orig = _counts(original)
    pol = _counts(polished)
    missing = sorted((orig - pol).keys())
    added = sorted((pol - orig).keys())
    if not missing and not added:
        return True, "", []
    if missing and added:
        return False, "number_changed", missing
    if missing:
        return False, "number_dropped", missing
    return False, "number_added", missing
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_polish_guard.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/polish_guard.py tests/core/reporting_cli/test_polish_guard.py
git commit -m "feat(report): 다듬기 수치 보존 결정론적 가드 추가"
```

---

## Task 3: 가드를 polish 모델 루프에 통합

**Files:**
- Modify: `vibelign/core/reporting_cli/polish.py:53-81`
- Test: `tests/core/reporting_cli/test_polish.py` (추가)

- [ ] **Step 1: 실패 테스트 작성 (숫자 바꾸는 가짜 다듬기 → 원문 유지 + guard 기록)**

```python
# tests/core/reporting_cli/test_polish.py 에 추가
from dataclasses import replace as _replace

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.polish import polish_report_model_with_guards


class _Runner:
    """summary 블록의 50% 를 '대폭' 으로 바꾸는(=숫자 누락) 가짜 다듬기."""
    def run(self, command, *, cwd, input_text, timeout_seconds):
        from types import SimpleNamespace
        return SimpleNamespace(status="ok", stdout="신규 회원 대폭 증가", stderr="", exit_code=0, duration_ms=1)


def test_guard_reverts_block_and_records(monkeypatch):
    from vibelign.core.reporting_cli import polish as pm
    monkeypatch.setattr(pm.cli_adapters, "build_cli_command", lambda a, p: ["echo"])
    model = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="개요", blocks=[Block(kind="summary", text="신규 회원 50% 증가")])],
    )
    out, guards = polish_report_model_with_guards(model, provider="codex", runner=_Runner(), root=None)
    assert out.sections[0].blocks[0].text == "신규 회원 50% 증가"  # 원문 유지
    assert guards == [{"section": 0, "block": 0, "reason": "number_dropped", "missing": ["50"]}]
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_polish.py -k guard_reverts -v`
Expected: FAIL — `polish_report_model_with_guards` 없음

- [ ] **Step 3: `polish.py` 에 가드 버전 추가 + 기존 함수는 얇은 래퍼로**

`polish_report_model`(`polish.py:53-81`)를 다음으로 교체:

```python
from vibelign.core.reporting_cli.polish_guard import guard_polished


def polish_report_model_with_guards(
    model: ReportModel,
    *,
    provider: str = "auto",
    runner=None,
    root: Path | None = None,
    timeout_seconds: int = 60,
) -> tuple[ReportModel, list[dict]]:
    """paragraph/summary 블록을 다듬되, 수치 가드를 통과한 블록만 교체한다.
    가드 실패 블록은 원문 유지 + guards 에 기록. 입력 model 은 변경하지 않는다."""
    if runner is None:
        runner = cli_adapters.SubprocessPlanningCliRunner()
    if root is None:
        root = Path.cwd()

    guards: list[dict] = []
    new_sections: list[Section] = []
    for si, section in enumerate(model.sections):
        new_blocks: list[Block] = []
        for bi, block in enumerate(section.blocks):
            if block.kind in _POLISH_BLOCK_KINDS and block.text:
                polished = polish_block_text(
                    block.text, provider=provider, runner=runner, root=root,
                    timeout_seconds=timeout_seconds,
                )
                if polished:
                    ok, reason, missing = guard_polished(block.text, polished)
                    if ok:
                        new_blocks.append(replace(block, text=polished))
                    else:
                        new_blocks.append(block)
                        guards.append({"section": si, "block": bi, "reason": reason, "missing": missing})
                else:
                    new_blocks.append(block)
            else:
                new_blocks.append(block)
        new_sections.append(replace(section, blocks=new_blocks))
    return replace(model, sections=new_sections), guards


def polish_report_model(model: ReportModel, **kwargs) -> ReportModel:
    """하위호환 래퍼: 가드를 적용하되 guards 기록은 버리고 모델만 반환한다."""
    new_model, _ = polish_report_model_with_guards(model, **kwargs)
    return new_model
```

> `replace`, `Path`, `cli_adapters`, `Block`, `Section`, `_POLISH_BLOCK_KINDS` 는 기존 import 유지. `guard_polished` import 만 추가.

- [ ] **Step 4: 통과 확인 + 기존 polish 테스트 회귀(시그니처 불변)**

Run: `pytest tests/core/reporting_cli/test_polish.py -v`
Expected: PASS — 신규 + 기존 전부(특히 입력 불변·graceful fallback 케이스)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/polish.py tests/core/reporting_cli/test_polish.py
git commit -m "feat(report): polish 루프에 수치 가드 통합(원문 폴백 + 기록)"
```

---

## Task 4: 모호어 린트 `vague_lint.py`

**Files:**
- Create: `vibelign/core/reporting_cli/vague_lint.py`
- Test: `tests/core/reporting_cli/test_vague_lint.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_vague_lint.py
from __future__ import annotations

from vibelign.core.reporting_cli.models import Block, ReportModel, Section
from vibelign.core.reporting_cli.vague_lint import lint_model


def _model(text: str) -> ReportModel:
    return ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="개요", blocks=[Block(kind="summary", text=text)])],
    )


def test_detects_vague_term_with_offset():
    out = lint_model(_model("성과가 대폭 좋아졌다"))
    assert out == [{"section": 0, "block": 0, "term": "대폭", "offset": 4}]


def test_clean_text_returns_empty():
    assert lint_model(_model("매출이 50% 늘었다")) == []


def test_ignores_bullets():
    model = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="개요", blocks=[Block(kind="bullets", items=["대폭 증가"])])],
    )
    assert lint_model(model) == []
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_vague_lint.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 구현**

```python
# vibelign/core/reporting_cli/vague_lint.py
from __future__ import annotations

from vibelign.core.reporting_cli.models import ReportModel

# 정량 표현으로 대체돼야 할 주관·과장어. 단어장 확장이 아니라 고정 규칙 셋.
_VAGUE_TERMS: tuple[str, ...] = (
    "대폭", "대거", "많이", "크게", "상당히", "매우", "엄청", "획기적",
    "혁신적", "압도적", "급격히", "현저히", "월등히",
)
_LINT_KINDS = {"paragraph", "summary"}


def lint_model(model: ReportModel) -> list[dict]:
    """paragraph/summary 블록에서 모호·과장어 출현을 (section, block, term, offset) 으로 모은다.
    비차단 경고용 — 렌더를 막지 않는다."""
    out: list[dict] = []
    for si, section in enumerate(model.sections):
        for bi, block in enumerate(section.blocks):
            if block.kind not in _LINT_KINDS or not block.text:
                continue
            for term in _VAGUE_TERMS:
                start = block.text.find(term)
                while start != -1:
                    out.append({"section": si, "block": bi, "term": term, "offset": start})
                    start = block.text.find(term, start + 1)
    return out
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_vague_lint.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/vague_lint.py tests/core/reporting_cli/test_vague_lint.py
git commit -m "feat(report): 모호·과장어 규칙 기반 린트 추가"
```

---

## Task 5: emit 에 guards / vague_warnings 채우기 *(Plan A Task 5 선행)*

**Files:**
- Modify: `vibelign/core/reporting_cli/emit.py`
- Test: `tests/core/reporting_cli/test_emit.py` (추가)

- [ ] **Step 1: 실패 테스트 작성 (모호어 다듬기 결과가 vague_warnings 에, 가드 발동이 guards 에)**

```python
# tests/core/reporting_cli/test_emit.py 에 추가
def test_emit_fills_vague_warnings(tmp_path, monkeypatch):
    plan = tmp_path / "p.md"
    plan.write_text("# 제목\n\n## 한 줄 목표\n성과가 대폭 좋아졌다\n", encoding="utf-8")
    payload = emit_report_payload(
        str(plan), "work", date="2026-06-17", polish=False, provider="auto", root=tmp_path
    )
    # base(=polished, polish=False) 의 summary 에 '대폭' → 경고 1건
    assert any(w["term"] == "대폭" for w in payload["vague_warnings"])


def test_emit_fills_guards_when_polish_drops_number(tmp_path, monkeypatch):
    plan = tmp_path / "p.md"
    plan.write_text("# 제목\n\n## 한 줄 목표\n신규 회원 50% 증가\n", encoding="utf-8")

    def fake_with_guards(model, **kwargs):
        # summary 의 50% 가 사라진 다듬기를 가정 → 원문 유지 + guard 기록
        return model, [{"section": 0, "block": 0, "reason": "number_dropped", "missing": ["50"]}]

    monkeypatch.setattr(
        "vibelign.core.reporting_cli.emit.polish_report_model_with_guards", fake_with_guards
    )
    payload = emit_report_payload(
        str(plan), "work", date="2026-06-17", polish=True, provider="auto", root=tmp_path
    )
    assert payload["guards"] == [{"section": 0, "block": 0, "reason": "number_dropped", "missing": ["50"]}]
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_emit.py -k "vague or guards" -v`
Expected: FAIL — emit 이 빈 배열 반환

- [ ] **Step 3: `emit.py` 수정 — 가드 버전 호출 + 린트 실행**

import 와 polish 블록을 교체:

import 교체 (emit.py 상단): `polish_report_model` → `polish_report_model_with_guards`, 그리고 `lint_model` 추가.

```python
from vibelign.core.reporting_cli.polish import polish_report_model_with_guards
from vibelign.core.reporting_cli.vague_lint import lint_model
```

`emit_report_payload` 의 polish/return 사이 블록을 교체한다(Plan A 가 `key` 를 위에서 이미 계산해 둠 — 여기서 다시 계산하지 않는다):

```python
    key = polish_cache_key(base, provider=provider)  # (Plan A 에서 추가됨 — 그대로 유지)
    guards: list[dict] = []
    if polish:
        polished, guards = polish_report_model_with_guards(base, provider=provider, root=root)
        save_polish_cache(root, slug, key=key, model=polished)
    else:
        polished = base

    vague_warnings = lint_model(polished)  # Plan A 의 `vague_warnings: list[dict] = []` 를 대체
```

> `vague_warnings` 지역변수는 기존 반환 dict 에서 이미 참조(Plan A). polish=False 면 polished=base 라 base 의 모호어를 잡는다.

- [ ] **Step 4: 통과 확인 + 기존 emit 테스트 회귀**

Run: `pytest tests/core/reporting_cli/test_emit.py -v`
Expected: PASS — 신규 2 + 기존(단 base==polished 케이스의 vague_warnings 는 `대폭` 없는 PLAN 이므로 `[]` 유지)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/emit.py tests/core/reporting_cli/test_emit.py
git commit -m "feat(report): emit payload 에 수치 가드·모호어 경고 채움"
```

---

## Task 6: BlockDiff 모호어 하이라이트 *(Plan A Task 9 선행)*

**Files:**
- Modify: `vibelign-gui/src/components/report-review/BlockDiff.tsx`
- Modify: `vibelign-gui/src/components/report-review/ReportDiffReview.tsx` (vague 전달)
- Test: `vibelign-gui/src/components/report-review/__tests__/BlockDiff.test.tsx`

> guard 배지와 "가드 블록 기본 거부" 는 Plan A 의 `BlockDiff`/`useReviewState` 에 이미 구현됨. 본 Task 는 **모호어 하이라이트만** 추가한다.

- [ ] **Step 1: 실패 테스트 작성**

```tsx
// __tests__/BlockDiff.test.tsx
import { test, expect, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { BlockDiff } from "../BlockDiff";

afterEach(cleanup);

test("모호어가 하이라이트(mark)로 표시된다", () => {
  render(
    <BlockDiff
      heading="개요"
      base={{ kind: "summary", text: "성과가 대폭 좋아졌다", items: [] }}
      polished={{ kind: "summary", text: "성과가 대폭 좋아졌다", items: [] }}
      decision="accept"
      vague={[{ section: 0, block: 0, term: "대폭", offset: 4 }]}
      onAccept={() => {}}
      onReject={() => {}}
    />,
  );
  const mark = screen.getByText("대폭");
  expect(mark.tagName.toLowerCase()).toBe("mark");
});
```

- [ ] **Step 2: 실패 확인**

Run: `npx vitest run src/components/report-review/__tests__/BlockDiff.test.tsx`
Expected: FAIL — `vague` prop 미지원, mark 없음

- [ ] **Step 3: `BlockDiff` 에 `vague` prop + 하이라이트 렌더 추가**

Props 인터페이스에 `vague?: VagueWarning[]` 추가(import `VagueWarning`), 다듬 텍스트를 offset 기준으로 잘라 `<mark>` 삽입하는 헬퍼를 추가:

```tsx
import type { Decision, GuardRecord, RModelBlock, VagueWarning } from "../../lib/vib/reportModel";

// Props 에 추가: vague?: VagueWarning[];

// lint 의 offset(파이썬 코드포인트 기준)을 신뢰하지 않고, GUI 에서 term 을 직접 재탐색한다.
// → 이모지 등 non-BMP 문자가 있어도 JS 문자열 내부에서 offset 이 일관(정렬 안전).
function highlight(text: string, vague: VagueWarning[]) {
  const terms = [...new Set(vague.map((w) => w.term))];
  if (!terms.length) return text;
  const hits: { start: number; len: number }[] = [];
  for (const term of terms) {
    let i = text.indexOf(term);
    while (i !== -1) { hits.push({ start: i, len: term.length }); i = text.indexOf(term, i + 1); }
  }
  hits.sort((a, b) => a.start - b.start);
  const out: (string | JSX.Element)[] = [];
  let cur = 0;
  hits.forEach((h, idx) => {
    if (h.start < cur) return; // 겹치는 매치는 건너뛴다
    out.push(text.slice(cur, h.start));
    out.push(<mark key={idx} style={{ background: "#ffe08a" }}>{text.slice(h.start, h.start + h.len)}</mark>);
    cur = h.start + h.len;
  });
  out.push(text.slice(cur));
  return out;
}
```

다듬 컬럼 렌더를 교체: `<div style={{ color: changed ? "#1A1A1A" : "#999" }}>{highlight(polished.text, vague ?? [])}</div>`

- [ ] **Step 4: `ReportDiffReview` 가 블록별 vague 를 넘기도록 한 줄 추가**

`guardByKey` 옆에 `vagueByKey` 를 만들고 `BlockDiff` 에 전달:

```tsx
const vagueByKey = new Map<string, VagueWarning[]>();
payload.vague_warnings.forEach((w) => {
  const k = blockKey(w.section, w.block);
  vagueByKey.set(k, [...(vagueByKey.get(k) ?? []), w]);
});
// <BlockDiff ... vague={vagueByKey.get(blockKey(si, bi))} />
```

(`VagueWarning` import 추가)

- [ ] **Step 5: 통과 확인 + Plan A 리뷰 테스트 회귀**

Run: `npx vitest run src/components/report-review/`
Expected: PASS — BlockDiff 신규 + ReportDiffReview(Plan A) 그대로

- [ ] **Step 6: 커밋**

```bash
git add vibelign-gui/src/components/report-review/
git commit -m "feat(gui-report): 다듬기 리뷰에 모호어 하이라이트 표시"
```

---

## Task 7: 검증 + Windows 무관성 확인

- [ ] **Step 1: 백엔드 전체 회귀**

Run: `pytest tests/core/reporting_cli -v`
Expected: PASS (guard/lint/polish/emit 전부)

- [ ] **Step 2: 플랫폼 무관성 확인(코드 점검)** — `polish_guard.py`/`vague_lint.py` 는 순수 정규식·문자열만 사용(파일·subprocess·플랫폼 API 없음) → Windows 동일 동작. 정규식은 ASCII 숫자만 매칭하므로 OS 로캘 영향 없음.
- [ ] **Step 3: 한글·유니코드 처리 확인** — 파이썬 `str.find` 의 offset 은 코드포인트 기준이고 JS `String` 은 UTF-16 기준이라, 이모지 등 non-BMP 문자가 섞이면 둘이 어긋난다. 그래서 GUI `highlight` 는 lint 의 offset 을 쓰지 않고 **term 을 JS 문자열에서 직접 재탐색**한다(Task 6) → 정렬 불일치 원천 회피. lint 의 offset 은 서버측 디버그·집계용으로만 남는다.
- [ ] **Step 4: GUI 타입체크/린트**

Run: `cd vibelign-gui && npx tsc --noEmit && npx eslint src/components/report-review src/lib/vib/reportModel.ts`
Expected: 0 errors

---

## 완료 기준 (Definition of Done)
- `pytest tests/core/reporting_cli` 전부 통과(가드 reverts·새 숫자 차단·린트 탐지·emit 채움).
- 다듬기가 숫자를 바꾸면 그 블록이 원문으로 복원되고, 리뷰 화면에 "숫자 보존됨" 배지 + 기본 거부.
- 모호어가 다듬 텍스트에 `<mark>` 로 하이라이트.
- mac/Windows 동일 동작(순수 함수, 플랫폼 의존 없음).

## 의존성 요약
- Task 1~4: Plan A 무관, 선 머지 가능(가드는 UI 없이도 조용히 원문 폴백 — 즉시 안전성 향상).
- Task 5: Plan A Task 5(`emit.py`) 필요.
- Task 6: Plan A Task 9(`BlockDiff.tsx`/`ReportDiffReview.tsx`) 필요.
