# Plan — 폴리시 헛소리(non-answer) 응답 가드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI 다듬기 provider 가 보고 문장 대신 거부·되묻기·메타응답(마크다운/여러 줄/질문)을 돌려줄 때 이를 결정론적으로 감지해 해당 블록을 원문으로 유지하고 `reason="non_answer"` 가드로 기록한다.

**Architecture:** 기존 수치 가드(`polish_guard.py` + `polish_report_model_with_guards`)에 한 단계 더 얹는다. 새 순수 함수 `looks_like_non_answer(original, polished)` 가 강한 구조 신호(마크다운/멀티라인+길이폭증/되묻기 키워드+물음표)로만 **보수적으로** 판정한다(좋은 다듬기를 절대 안 되돌리게). polish 루프에서 수치 가드보다 먼저 검사하고, 걸리면 원문 유지 + guard 기록. 검토 UI(BlockDiff)는 `non_answer` reason 에 맞는 배지·툴팁을 보여준다.

**Tech Stack:** Python 3 / pytest / ruff (백엔드), React + TypeScript + Vitest (GUI 배지).

**근거(실제 E2E):** 짧은 입력 `"동네 미용실 사장님"` 에 provider 가 다음을 반환했고 polish 가 그대로 수락함 —
`"This is an **evaluation/clarification** intent — you've given me… 어떤 문장을 다듬어 드릴까요?…"`. 수치 가드는 숫자가 없어 못 막았다.

---

## File Structure

**수정 (기존 파일 — Edit 는 precheck 면제)**
- `vibelign/core/reporting_cli/polish_guard.py` — `looks_like_non_answer` 추가(POLISH_GUARD 앵커 안)
- `vibelign/core/reporting_cli/polish.py` — `polish_report_model_with_guards` 루프에 non-answer 분기 추가
- `vibelign-gui/src/components/report-review/BlockDiff.tsx` — guard 배지/툴팁을 reason 별로

**테스트**
- `tests/core/reporting_cli/test_polish_guard.py` — `looks_like_non_answer` 케이스
- `tests/core/reporting_cli/test_polish.py` — non-answer 반환 시 원문 유지 + 가드 기록
- `vibelign-gui/src/components/report-review/__tests__/BlockDiff.test.tsx` — non_answer 배지

> **구조화 규율:** 최소 패치·순수 함수·앵커 경계 준수. 신규 파일 없음(전부 기존 파일 확장).

---

## Task 1: `looks_like_non_answer` 감지기

**Files:**
- Modify: `vibelign/core/reporting_cli/polish_guard.py` (POLISH_GUARD 앵커 안, `guard_polished` 위/아래)
- Test: `tests/core/reporting_cli/test_polish_guard.py` (추가)

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_polish_guard.py 에 추가
from vibelign.core.reporting_cli.polish_guard import looks_like_non_answer

_REAL_GARBAGE = (
    "This is an **evaluation/clarification** intent — you've given me the "
    "refinement instructions but I don't see the actual sentence to refine.\n\n"
    "**어떤 문장을 다듬어 드릴까요?**"
)


def test_nonanswer_detects_real_garbage():
    assert looks_like_non_answer("동네 미용실 사장님", _REAL_GARBAGE) is True


def test_nonanswer_detects_markdown_bold():
    assert looks_like_non_answer("짧은 원문", "**다듬은 결과**") is True


def test_nonanswer_detects_length_blowup():
    assert looks_like_non_answer("짧은 문장", "가" * 200) is True


def test_nonanswer_allows_clean_rewrite():
    base = "전화 예약 누락을 줄이려고 MVP 를 빨리 deploy 하는 게 목표임. 신규 회원 50% 증가 기대."
    pol = "전화 예약 누락을 줄이기 위해 MVP를 신속히 deploy하는 것이 목표입니다. 신규 회원 50% 증가가 기대됩니다."
    assert looks_like_non_answer(base, pol) is False


def test_nonanswer_allows_short_clean_rewrite():
    assert looks_like_non_answer("동네 미용실 사장님", "동네 미용실 사장님입니다") is False
```

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_polish_guard.py -k nonanswer -v`
Expected: FAIL — `ImportError: cannot import name 'looks_like_non_answer'`

- [ ] **Step 3: 구현 (`polish_guard.py` 의 `guard_polished` 정의 바로 위에 삽입 — 앵커 END 위)**

```python
# 보고 한 문장 다듬기에는 안 나오는 강한 비-응답 신호들. 보수적으로(강신호만) 판정한다.
_NONANSWER_MARKERS = (
    "다듬어 드릴까요", "어떤 문장", "문장을 알려", "원문을 알려",
    "please provide", "i don't see", "clarification",
)


def looks_like_non_answer(original: str, polished: str) -> bool:
    """provider 가 다듬은 문장 대신 거부·되묻기·메타응답을 돌려줬는지 보수적으로 판정한다.
    True 면 호출자가 원문을 유지해야 한다(좋은 다듬기를 되돌리지 않도록 강신호만 본다)."""
    p = polished.strip()
    # 1) 마크다운 구조: 보고 한 문장엔 ** 나 머리글(#) 이 안 나온다.
    if "**" in p or p.startswith("#") or "\n#" in p:
        return True
    # 2) 멀티라인 + 원문보다 크게 길어짐(한 문장 다듬기가 문단으로 부풀음).
    if "\n" in p and len(p) > len(original) + 40:
        return True
    # 3) 길이 폭증(군더더기만 덜어내라 했으므로 4배+ 는 비정상).
    if len(p) > len(original) * 4 + 40:
        return True
    # 4) 되묻기/거부 키워드 + 물음표(사용자에게 질문을 되던짐).
    low = p.lower()
    if "?" in p and any(m.lower() in low for m in _NONANSWER_MARKERS):
        return True
    return False
```

- [ ] **Step 4: 통과 확인 + 기존 가드 테스트 회귀**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_polish_guard.py -v`
Expected: PASS (신규 5 + 기존 6)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/polish_guard.py tests/core/reporting_cli/test_polish_guard.py
git commit -m "feat(report): 폴리시 비-응답(헛소리) 감지기 추가"
```

---

## Task 2: polish 루프에 non-answer 분기 통합

**Files:**
- Modify: `vibelign/core/reporting_cli/polish.py` (import + `polish_report_model_with_guards` 루프)
- Test: `tests/core/reporting_cli/test_polish.py` (추가)

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/core/reporting_cli/test_polish.py 에 추가
class _NonAnswerRunner:
    """다듬기 대신 헛소리 메타응답을 돌려주는 가짜 provider."""

    def run(self, command, *, cwd, input_text, timeout_seconds):
        from types import SimpleNamespace

        return SimpleNamespace(
            status="ok",
            stdout="**어떤 문장을 다듬어 드릴까요?** 원문을 알려주세요.",
            stderr="", exit_code=0, duration_ms=1,
        )


def test_nonanswer_block_kept_original_and_recorded():
    model = ReportModel(
        title="t", report_type="work", date="d",
        sections=[Section(heading="대상", blocks=[Block(kind="paragraph", text="동네 미용실 사장님")])],
    )
    out, guards = polish_report_model_with_guards(
        model, provider="codex", runner=_NonAnswerRunner(), root=None,
    )
    assert out.sections[0].blocks[0].text == "동네 미용실 사장님"  # 원문 유지
    assert guards == [{"section": 0, "block": 0, "reason": "non_answer", "missing": []}]
```

> `ReportModel`, `Section`, `Block`, `polish_report_model_with_guards` 는 test_polish.py 상단에서 이미 import 됨.

- [ ] **Step 2: 실패 확인**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_polish.py -k nonanswer -v`
Expected: FAIL — 헛소리가 그대로 수락돼 text 가 바뀌고 guards 가 비어 있음

- [ ] **Step 3: import 추가 (`polish.py`)**

```python
from vibelign.core.reporting_cli.polish_guard import guard_polished, looks_like_non_answer
```

(기존 `from vibelign.core.reporting_cli.polish_guard import guard_polished` 한 줄을 위로 교체)

- [ ] **Step 4: 루프의 `if polished:` 블록 교체 (`polish_report_model_with_guards` 안)**

```python
                if polished:
                    if looks_like_non_answer(block.text, polished):
                        new_blocks.append(block)
                        guards.append({"section": si, "block": bi, "reason": "non_answer", "missing": []})
                    else:
                        ok, reason, missing = guard_polished(block.text, polished)
                        if ok:
                            new_blocks.append(replace(block, text=polished))
                        else:
                            new_blocks.append(block)
                            guards.append({"section": si, "block": bi, "reason": reason, "missing": missing})
                else:
                    new_blocks.append(block)
```

- [ ] **Step 5: 통과 확인 + 기존 polish 테스트 회귀**

Run: `.venv/bin/python -m pytest tests/core/reporting_cli/test_polish.py tests/core/reporting_cli/test_emit.py -v`
Expected: PASS (신규 1 + 기존 polish/emit 전부 — 수치 가드·graceful·불변 케이스 유지)

- [ ] **Step 6: 커밋**

```bash
git add vibelign/core/reporting_cli/polish.py tests/core/reporting_cli/test_polish.py
git commit -m "feat(report): polish 루프에 비-응답 가드 통합(원문 유지 + non_answer 기록)"
```

---

## Task 3: 검토 UI 배지/툴팁에 non_answer 반영

**Files:**
- Modify: `vibelign-gui/src/components/report-review/BlockDiff.tsx` (`guardTitle` + 배지 라벨)
- Test: `vibelign-gui/src/components/report-review/__tests__/BlockDiff.test.tsx` (추가)

> guard 가 걸린 블록은 base==polished(원문 유지)라 diff 는 "= same" 으로 보이고, 배지로 "왜 원문인지" 를 알린다. `useReviewState` 의 기본 거부 동작은 그대로(이미 guard 블록 기본 reject).

- [ ] **Step 1: 실패 테스트 작성 (BlockDiff 가 non_answer 배지를 보여주는지)**

```tsx
// __tests__/BlockDiff.test.tsx 에 추가
test("non_answer 가드는 'AI 응답 보류' 배지를 보여준다", () => {
  render(
    <BlockDiff
      heading="대상"
      base={{ kind: "paragraph", text: "동네 미용실 사장님", items: [] }}
      polished={{ kind: "paragraph", text: "동네 미용실 사장님", items: [] }}
      decision="reject"
      guard={{ section: 0, block: 0, reason: "non_answer", missing: [] }}
      onAccept={() => {}}
      onReject={() => {}}
    />,
  );
  expect(screen.getByText("AI 응답 보류")).toBeInTheDocument();
});
```

> 파일 상단 import(`render, screen, cleanup`, `BlockDiff`)와 `afterEach(cleanup)` 는 이미 있음.

- [ ] **Step 2: 실패 확인**

Run(`cd vibelign-gui`): `npx vitest run src/components/report-review/__tests__/BlockDiff.test.tsx`
Expected: FAIL — 배지 텍스트가 항상 "숫자 보존됨" 이라 "AI 응답 보류" 없음

- [ ] **Step 3: `BlockDiff.tsx` — reason 별 배지 라벨 + 툴팁**

`guardTitle` 을 교체하고 `guardLabel` 헬퍼를 추가한다:

```tsx
function guardLabel(g: GuardRecord): string {
  return g.reason === "non_answer" ? "AI 응답 보류" : "숫자 보존됨";
}

function guardTitle(g: GuardRecord): string {
  if (g.reason === "non_answer") return "AI 응답이 보고 문장 같지 않아 원문을 유지했어요";
  if (g.reason === "number_added") return "다듬기가 원문에 없던 숫자를 넣으려 해서 원문을 유지했어요";
  return `보존된 수치: ${g.missing.join(", ")}`;
}
```

그리고 배지 JSX 를 라벨 헬퍼로 바꾼다:

```tsx
        {guard && <span style={badge} title={guardTitle(guard)}>{guardLabel(guard)}</span>}
```

- [ ] **Step 4: 통과 확인 + report-review 회귀**

Run(`cd vibelign-gui`): `npx vitest run src/components/report-review/ && npx tsc --noEmit`
Expected: PASS (BlockDiff 신규 + 기존 모호어/리뷰 테스트), tsc 0

- [ ] **Step 5: 커밋**

```bash
git add vibelign-gui/src/components/report-review/BlockDiff.tsx vibelign-gui/src/components/report-review/__tests__/BlockDiff.test.tsx
git commit -m "feat(gui-report): 검토 배지를 가드 reason 별로(비-응답=AI 응답 보류)"
```

---

## Task 4: 실제 바이너리 E2E 재확인

- [ ] **Step 1: 실제 provider 로 헛소리 블록이 이제 원문 유지 + 가드되는지**

임시 프로젝트에 짧은 블록을 포함한 기획안을 만들고:
```bash
vib report plans/<plan>.md --type proposal --emit-model --polish --json > /tmp/emit.json
```
`/tmp/emit.json` 에서 확인: 헛소리가 나왔던 블록의 `polished` 텍스트 == `base` 텍스트(원문), 그리고 `guards` 에 `{"reason":"non_answer",...}` 1건 존재.
(provider 비결정성으로 헛소리가 안 나오면 이 단계는 "재현 안 됨"으로 기록 — 단위 테스트가 로직을 이미 커버)

- [ ] **Step 2: 좋은 다듬기는 그대로 통과(거짓양성 없음)** — 같은 emit 출력에서 숫자/문장이 멀쩡히 다듬어진 블록은 `polished != base` 이고 guard 없음을 확인.

---

## 완료 기준 (Definition of Done)
- `pytest tests/core/reporting_cli` 전부 통과(non-answer 감지·통합·기존 회귀).
- `cd vibelign-gui && npx vitest run src/components/report-review && npx tsc --noEmit && npx eslint src/components/report-review` 무오류.
- 헛소리 응답이 온 블록은 원문 유지 + "AI 응답 보류" 배지, 좋은 다듬기는 영향 없음.

## YAGNI / 보수성 메모
- 감지는 **강신호(마크다운/멀티라인+길이폭증/되묻기+물음표)** 만. 임계값을 더 조이면 거짓양성으로 좋은 다듬기를 되돌릴 위험 → 검토 UI 가 최종 안전망이므로 굳이 공격적으로 가지 않는다.
- LLM 기반 2차 판정·정교한 NLP 는 범위 밖(결정론·무비용 원칙 유지).
