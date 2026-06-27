# 카드뉴스 LLM 이미지 생성 모드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 카드뉴스 초안에서 선택한 CLI 모델(claude/codex/agy/opencode)이 풍부한 SVG를 그리고(또는 카드뉴스 HTML 전체를 디자인하고), 모델 실패 시 폴백을 사용자에게 가시화한다.

**Architecture:** 기존 `vib report --visual-cards --visual-card-cli {provider}` 파이프라인을 확장한다. (A) 카드별 SVG 에셋의 실제 출처(`llm`/`fallback`/`template`)를 메타데이터에 기록하고 GUI 배지로 노출. (B) `_svg_prompt`을 풍부한 일러스트 요구로 교체(보안 sanitizer 유지). (C) 신규 `poster` 모드 — CLI가 카드뉴스 HTML 전체를 디자인하고, sanitize 후 in-app sandbox iframe 프리뷰 + finalize 시 결과물로 저장.

**Tech Stack:** Python 3.13 / pytest / pydantic v2 / argparse. GUI: React + TypeScript + Vitest (Tauri `runVib` invoke). 빌드/검증: `pytest`, `ruff check`, GUI `npm test`.

## Global Constraints

- 이미지 생성 API 미사용. 모든 생성은 `cli_adapters.build_cli_command`으로 해석되는 CLI 실행파일(`claude`/`codex`/`agy`/`opencode`)만 사용.
- 앵커 경계(`# === ANCHOR: NAME_START/END ===`) 안에서만 수정. 파일 전체 재작성 금지. 임포트 구조 임의 변경 금지. (VibeLign `CLAUDE.md` 규칙)
- SVG 보안 불변식 유지: 단일 `<svg>`, `<text>`/Korean/Latin 텍스트·`<script>`·`<foreignObject>`·외부 URL/href/이벤트핸들러 금지, `viewBox 0 0 320 150`.
- 카드뉴스 SVG 에셋 출처 표기 마커: 폴백/템플릿 SVG는 항상 `data-sketch-symbols` 속성을 포함(`render_card_sketch_svg`), LLM SVG는 미포함. 이 마커로 출처를 판별한다.
- 경로 containment: 모든 산출물은 `<root>/.vibelign/reports/card-news/` 내부에만 저장.
- 새 코드는 주변 코드 스타일(앵커, 타입힌트, frozen dataclass, koreanglish 메시지)을 따른다.

---

## File Structure

**Phase A — 출처 가시화 (backend + GUI 배지)**
- Modify: `vibelign/core/reporting_cli/report_visual_cards.py` — `VisualImageMetadata`에 `source` 추가, `_draft_image` 갱신.
- Modify: `vibelign/core/reporting_cli/report_visual_cards_cli.py` — `_cards_from_payload` 이미지에 `source` 추가.
- Modify: `vibelign/core/reporting_cli/report_card_news_asset_generator.py` — `_asset_source` 신규, `_card_with_asset`/`_materialize_card_asset`에 source 배선.
- Modify: `vibelign/core/reporting_cli/report_card_news_payload.py` — `_ImageModel`/`_card_from_model`에 `source`.
- Modify: `vibelign-gui/src/lib/vib/reportVisualCards.ts` — `ReportVisualCardImage.source` + `parseImage`.
- Modify: `vibelign-gui/src/components/plan-doc/ReportVisualCardPreview.tsx` — 카드별 출처 배지.
- Test: `tests/core/reporting_cli/test_report_card_news_asset_generator.py`, `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`.

**Phase B — 풍부한 SVG 프롬프트 + 배치 생성(속도)**
- Modify: `vibelign/core/reporting_cli/report_card_news_asset_generator.py` — `_svg_prompt`, `_ASSET_TIMEOUT_SECONDS` (B1); 배치 생성 경로(B2).
- Test: 신규 `tests/core/reporting_cli/test_report_card_news_svg_prompt.py` (B1); `tests/core/reporting_cli/test_report_card_news_asset_generator.py` 배치 케이스(B2).

> **속도 근거:** 현재 6장 모델 생성 = `draft()` 1회 + 카드당 SVG 6회 = **7 CLI cold-start**(3개씩 2웨이브). 병목은 토큰량이 아니라 CLI 에이전트 spawn 횟수다. B2는 SVG 6회를 **1회**로 묶어 7→2로 줄인다(B1의 풍부화로 인한 per-call 비용을 상쇄하고 순감). poster 모드(Phase C)는 본래 1회 호출이라 구조적으로 가장 빠른 경로.

**Phase C — 전체 포스터 HTML 모드**
- Create: `vibelign/core/reporting_cli/report_card_news_poster.py` — CLI 포스터 생성 + HTML sanitizer.
- Modify: `vibelign/cli/cli_report_command_groups.py` — `--card-news-mode` 인자.
- Modify: `vibelign/commands/vib_report_context.py` — `ReportArgs.card_news_mode`.
- Modify: `vibelign/commands/vib_report_runtime.py` — `_card_news_poster` 분기 + 응답 필드.
- Modify: `vibelign/core/reporting_cli/report_card_news_payload.py` — `poster_html` 로드.
- Modify: `vibelign/core/reporting_cli/report_card_news_export.py` — finalize 시 poster 저장.
- Modify: `vibelign-gui/src/lib/vib/reportVisualCards.ts` — mode 인자 + poster 파싱 + 저장 payload.
- Modify: `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx` — 모드 토글 + sandbox iframe 프리뷰.
- Test: 신규 `tests/core/reporting_cli/test_report_card_news_poster.py`, `tests/cli/test_vib_report_card_news_mode.py`, GUI 테스트 확장.

---

# Phase A — 출처 가시화

### Task A1: `VisualImageMetadata.source` 필드 추가 + 드래프트 이미지 갱신

**Files:**
- Modify: `vibelign/core/reporting_cli/report_visual_cards.py:46-52` (`VISUALIMAGEMETADATA` 앵커), `:148-156` (`_DRAFT_IMAGE` 앵커)
- Test: `tests/core/reporting_cli/test_report_visual_cards.py`

**Interfaces:**
- Produces: `VisualImageMetadata` TypedDict with key `source: Literal["llm", "fallback", "template"]`. `_draft_image()` returns `source="template"`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/core/reporting_cli/test_report_visual_cards.py`에 추가

먼저 이 파일을 Read하여 `build_report_visual_cards(...)`를 호출하는 기존 테스트가 `ReportModel`을 어떻게 만드는지 확인하고, **그 모델 생성 방식을 그대로 재사용**한다(새 import를 발명하지 말 것). 그 모델을 `built`로 받았다고 하면:

```python
def test_draft_image_marks_source_template() -> None:
    built = build_report_visual_cards(<기존 테스트와 동일한 ReportModel 생성>)
    assert built["cards"][0]["image"]["source"] == "template"
```

(`build_report_visual_cards`는 provider 없이 호출하면 `_draft_image` 경로를 타므로 `source == "template"`이어야 한다.)

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_report_visual_cards.py::test_draft_image_marks_source_template -v`
Expected: FAIL — `KeyError: 'source'`

- [ ] **Step 3: 구현** — `VisualImageMetadata`에 키 추가

```python
# === ANCHOR: REPORT_VISUAL_CARDS_VISUALIMAGEMETADATA_START ===
class VisualImageMetadata(TypedDict):
    provider: str
    asset_path: str
    prompt: str
    generated: bool
    source: Literal["llm", "fallback", "template"]
# === ANCHOR: REPORT_VISUAL_CARDS_VISUALIMAGEMETADATA_END ===
```

`_draft_image` 갱신:

```python
# === ANCHOR: REPORT_VISUAL_CARDS__DRAFT_IMAGE_START ===
def _draft_image(request: VisualImageRequest) -> VisualImageMetadata:
    return {
        "provider": DRAFT_PROVIDER_NAME,
        "asset_path": "",
        "prompt": request.visual_prompt,
        "generated": False,
        "source": "template",
    }
# === ANCHOR: REPORT_VISUAL_CARDS__DRAFT_IMAGE_END ===
```

`Literal`는 이미 `from typing import ... Literal`로 import됨(파일 상단 확인).

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_report_visual_cards.py::test_draft_image_marks_source_template -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/report_visual_cards.py tests/core/reporting_cli/test_report_visual_cards.py
git commit -m "feat(report): 카드뉴스 이미지 메타데이터에 source 필드 추가"
```

---

### Task A2: CLI 드래프트 카드 이미지에 source 배선

**Files:**
- Modify: `vibelign/core/reporting_cli/report_visual_cards_cli.py:124-129` (`_CARDS_FROM_PAYLOAD` 앵커 내 image dict)

**Interfaces:**
- Consumes: `VisualImageMetadata` with `source` (Task A1).
- Produces: CLI 드래프트 카드의 `image.source == "template"` (에셋 생성 전이므로).

- [ ] **Step 1: 구현** — `_cards_from_payload`의 image 리터럴에 `"source": "template"` 추가

```python
        image: VisualImageMetadata = {
            "provider": provider,
            "asset_path": "",
            "prompt": visual_prompt,
            "generated": False,
            "source": "template",
        }
```

(이 파일은 직접 단위테스트보다 A3의 통합 경로에서 검증됨. 별도 RED 테스트 생략 — basedpyright/ruff가 누락 키를 잡는다.)

- [ ] **Step 2: 타입체크**

Run: `ruff check vibelign/core/reporting_cli/report_visual_cards_cli.py`
Expected: 통과 (오류 없음)

- [ ] **Step 3: 커밋**

```bash
git add vibelign/core/reporting_cli/report_visual_cards_cli.py
git commit -m "feat(report): CLI 드래프트 카드 이미지에 source=template 표기"
```

---

### Task A3: 에셋 생성기에서 실제 출처(llm/fallback/template) 판별

**Files:**
- Modify: `vibelign/core/reporting_cli/report_card_news_asset_generator.py:68-82` (`_materialize_card_asset`), `:213-233` (`_CARD_WITH_ASSET` 앵커)
- Test: `tests/core/reporting_cli/test_report_card_news_asset_generator.py`

**Interfaces:**
- Consumes: `_CLI_ASSET_PROVIDERS` (기존), `render_card_sketch_svg` 출력의 `data-sketch-symbols` 마커.
- Produces: `_asset_source(provider: str, svg_text: str) -> Literal["llm","fallback","template"]`; `_card_with_asset(card, asset_relative, source)` 시그니처에 `source` 추가.

- [ ] **Step 1: 실패 테스트 작성/수정** — 기존 테스트 헬퍼 `_card`/`_card_with_id`의 image dict에 `"source": "template"` 추가(TypedDict 필수키), 그리고 출처 단언을 추가한다.

`_card` 헬퍼 image 리터럴(파일 88-93행) 및 `_card_with_id`(104-110행)에 `"source": "template",` 한 줄씩 추가. 그다음 단언 추가/수정:

```python
# 성공 케이스 (test_model_provider_generates_svg_asset_from_visual_prompt 끝에 추가)
    assert cards[0]["image"]["source"] == "llm"

# 폴백 케이스 (test_model_provider_falls_back_to_local_asset_when_cli_times_out 끝에 추가)
    assert cards[0]["image"]["source"] == "fallback"
```

신규 테스트:

```python
def test_non_cli_provider_marks_source_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner("")
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)

    cards = materialize_card_news_assets(tmp_path, "예약-알림", [_card("provider-neutral-draft")], runner=runner)

    assert cards[0]["image"]["source"] == "template"
    assert runner.commands == []
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_asset_generator.py -v`
Expected: FAIL — `KeyError: 'source'` 또는 시그니처 불일치

- [ ] **Step 3: 구현** — `_asset_source` 추가 + `_materialize_card_asset`/`_card_with_asset` 배선

`_materialize_card_asset` 교체:

```python
def _materialize_card_asset(
    context: _AssetRenderContext,
    asset_dir: Path,
    index: int,
    card: VisualCardDict,
) -> VisualCardDict:
    if card["image"]["asset_path"].strip():
        return card
    asset_relative = _asset_relative_path(context.slug, card, index)
    asset_path = context.root / asset_relative
    if asset_path.exists():
        svg = asset_path.read_text(encoding="utf-8")
        return _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))
    asset_dir.mkdir(parents=True, exist_ok=True)
    svg = _asset_svg(context, card)
    _ = asset_path.write_text(svg, encoding="utf-8")
    return _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))
```

`_asset_source` 신규(앵커 새로 추가, `_card_with_asset` 위):

```python
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_SOURCE_START ===
def _asset_source(provider: str, svg_text: str) -> str:
    if provider not in _CLI_ASSET_PROVIDERS:
        return "template"
    return "fallback" if "data-sketch-symbols" in svg_text else "llm"
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__ASSET_SOURCE_END ===
```

`_card_with_asset` 시그니처/본문에 source 반영:

```python
def _card_with_asset(card: VisualCardDict, asset_relative: Path, source: str) -> VisualCardDict:
    prompt = card["visual_prompt"] or card["image"]["prompt"]
    image: VisualImageMetadata = {
        "provider": card["image"]["provider"],
        "asset_path": asset_relative.as_posix(),
        "prompt": prompt,
        "generated": True,
        "source": source if source in ("llm", "fallback", "template") else "template",
    }
    return {
        "id": card["id"],
        "title": card["title"],
        "body": card["body"],
        "caption": card["caption"],
        "visual_prompt": card["visual_prompt"],
        "negative_prompt": card["negative_prompt"],
        "source_refs": card["source_refs"],
        "image": image,
        "approved": card["approved"],
    }
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_asset_generator.py -v`
Expected: PASS (전부)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/report_card_news_asset_generator.py tests/core/reporting_cli/test_report_card_news_asset_generator.py
git commit -m "feat(report): 카드뉴스 SVG 에셋 출처(llm/fallback/template) 판별"
```

---

### Task A4: payload 모델에 source 로드

**Files:**
- Modify: `vibelign/core/reporting_cli/report_card_news_payload.py:34-42` (`_IMAGEMODEL`), `:90-108` (`_CARD_FROM_MODEL`)
- Test: `tests/core/reporting_cli/test_model_json.py` 또는 신규 케이스

**Interfaces:**
- Produces: 저장 payload 왕복 시 `image.source` 보존(누락 시 기본 `"template"`).

- [ ] **Step 1: 실패 테스트 작성** — `tests/cli/test_vib_report_card_news_finalize_cmd.py`가 쓰는 payload 빌더 방식을 따라, source가 보존되는지 확인하는 단위 테스트를 `tests/core/reporting_cli/test_model_json.py`에 추가(파일 상단 import 패턴 재사용):

```python
def test_image_model_preserves_source(tmp_path) -> None:
    from vibelign.core.reporting_cli.report_card_news_payload import load_visual_cards_payload
    payload = tmp_path / "p.json"
    payload.write_text(
        '{"schema_version":"report-visual-cards-v1","status":"ready","provider":"agy",'
        '"cards":[{"id":"c1","title":"t","body":"b","caption":"","visual_prompt":"",'
        '"negative_prompt":"","source_refs":[],"approved":true,'
        '"image":{"provider":"agy","asset_path":"","prompt":"","generated":true,"source":"llm"}}]}',
        encoding="utf-8",
    )
    loaded = load_visual_cards_payload(payload)
    assert loaded["cards"][0]["image"]["source"] == "llm"
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_model_json.py::test_image_model_preserves_source -v`
Expected: FAIL — `KeyError: 'source'`

- [ ] **Step 3: 구현**

`_ImageModel`에 필드 추가:

```python
class _ImageModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    provider: str = ""
    asset_path: str = ""
    prompt: str = ""
    generated: StrictBool = False
    source: Literal["llm", "fallback", "template"] = "template"
```

`_card_from_model`의 image dict에 `"source": card.image.source` 추가:

```python
        "image": {
            "provider": card.image.provider,
            "asset_path": card.image.asset_path,
            "prompt": card.image.prompt,
            "generated": card.image.generated,
            "source": card.image.source,
        },
```

(`Literal`는 파일 상단 `from typing import ClassVar, Literal`에 이미 있음.)

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_model_json.py -v`
Expected: PASS

- [ ] **Step 5: 전체 회귀 + 커밋**

```bash
pytest tests/core/reporting_cli tests/cli -q
git add vibelign/core/reporting_cli/report_card_news_payload.py tests/core/reporting_cli/test_model_json.py
git commit -m "feat(report): 카드뉴스 payload 왕복에 image.source 보존"
```

Expected: 회귀 그린(기존 실패 3건 제외 — 별도 확인).

---

### Task A5: GUI 타입/파서에 source + 카드 출처 배지

**Files:**
- Modify: `vibelign-gui/src/lib/vib/reportVisualCards.ts:13-18` (`ReportVisualCardImage`), `:96-106` (`parseImage`)
- Modify: `vibelign-gui/src/components/plan-doc/ReportVisualCardPreview.tsx` (카드별 배지)
- Modify: `vibelign-gui/src/components/plan-doc/ReportVisualCardsPanel.tsx` (폴백 집계 알림)
- Test: `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`

**Interfaces:**
- Consumes: 백엔드 JSON `image.source`.
- Produces: `ReportVisualCardImage.source: "llm" | "fallback" | "template"`; 카드 미리보기에 출처 배지.

- [ ] **Step 1: 실패 테스트 작성** — `reportVisualCards.test.ts`에 추가

```ts
it("parses image.source, defaulting to template", () => {
  const payload = parseReportVisualCardsPayload({
    status: "ready",
    provider: "agy",
    cards: [{ id: "c1", image: { provider: "agy", source: "llm" } }],
  });
  expect(payload.cards[0].image.source).toBe("llm");
  const fallback = parseReportVisualCardsPayload({ status: "ready", cards: [{ id: "c2", image: {} }] });
  expect(fallback.cards[0].image.source).toBe("template");
});
```

- [ ] **Step 2: 실패 확인**

Run: `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/reportVisualCards.test.ts`
Expected: FAIL — `source` 없음/타입오류

- [ ] **Step 3: 구현**

타입에 추가:

```ts
export type ReportVisualCardImage = {
  readonly provider: string;
  readonly asset_path: string;
  readonly prompt: string;
  readonly generated: boolean;
  readonly source: "llm" | "fallback" | "template";
};
```

`parseImage`에 source 파싱 헬퍼 추가:

```ts
function parseImage(value: unknown): ReportVisualCardImage {
  const record = isRecord(value) ? value : {};
  const rawSource = stringValue(record.source);
  const source = rawSource === "llm" || rawSource === "fallback" ? rawSource : "template";
  return {
    provider: stringValue(record.provider),
    asset_path: stringValue(record.asset_path),
    prompt: stringValue(record.prompt),
    generated: booleanValue(record.generated),
    source,
  };
}
```

- [ ] **Step 4: 통과 확인**

Run: `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/reportVisualCards.test.ts`
Expected: PASS

- [ ] **Step 5: 카드 배지 구현** — `ReportVisualCardPreview.tsx`에 출처 배지 추가

`ReportVisualCardPreview.tsx`를 Read한 뒤, 카드 헤더/번호 영역 근처(앵커 내)에 배지 한 줄을 추가한다. 라벨 매핑:

```tsx
// card.image.source 기준 라벨/색
const sourceBadge =
  card.image.source === "llm" ? { text: "모델 생성", bg: "#4DFF91" }
  : card.image.source === "fallback" ? { text: "폴백 · 모델 실패", bg: "#FFD84D" }
  : { text: "템플릿", bg: "#EEEEEE" };
```

기존 inline-style 패턴(2px solid #1A1A1A 등)을 따라 `<span>`으로 렌더. (구체 위치는 컴포넌트 구조에 맞춰 앵커 내부에 배치.)

- [ ] **Step 5b: 폴백 집계 알림** — `ReportVisualCardsPanel.tsx` 헤더 영역(`REPORTVISUALCARDSPANEL_REPORTVISUALCARDSPANEL` 앵커 내, providerBadge 근처)에 폴백 개수 요약 추가

```tsx
const fallbackCount = cards.filter((c) => c.image.source === "fallback").length;
// ...header 내부, providerBadge 다음:
{fallbackCount > 0 && (
  <span style={{ ...providerBadge, background: "#FFD84D" }}>
    {`${cards.length}장 중 ${fallbackCount}장 폴백(모델 실패)`}
  </span>
)}
```

- [ ] **Step 6: GUI 테스트 + 커밋**

Run: `cd vibelign-gui && npx vitest run src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx`
Expected: 기존 통과 유지(필요 시 배지 텍스트 단언 추가).

```bash
git add vibelign-gui/src/lib/vib/reportVisualCards.ts vibelign-gui/src/components/plan-doc/ReportVisualCardPreview.tsx vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts
git commit -m "feat(report-gui): 카드뉴스 카드별 이미지 출처 배지"
```

---

# Phase B — 풍부한 SVG 프롬프트

### Task B1: `_svg_prompt` 풍부화 + 타임아웃 상향

**Files:**
- Modify: `vibelign/core/reporting_cli/report_card_news_asset_generator.py:26-27` (`_ASSET_TIMEOUT_SECONDS`), `:158-173` (`_SVG_PROMPT` 앵커)
- Test: `tests/core/reporting_cli/test_report_card_news_svg_prompt.py` (신규)

**Interfaces:**
- Produces: `_svg_prompt(card)` — "simple/under 80 elements/geometric shapes only" 제약 제거, 디테일·면채움·그림자 요구. 보안 규칙 문장 유지.

- [ ] **Step 1: 실패 테스트 작성** (신규 파일)

```python
from __future__ import annotations

from vibelign.core.reporting_cli.report_card_news_asset_generator import _svg_prompt
from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict


def _card() -> VisualCardDict:
    return {
        "id": "c1", "title": "예약 알림",
        "body": "캘린더 예약과 알림 권한 흐름을 한 장으로 설명합니다.",
        "caption": "출처: 개요",
        "visual_prompt": "mobile calendar reminder permission flow, no readable text in image",
        "negative_prompt": "readable text, logo, watermark",
        "source_refs": [],
        "image": {"provider": "agy", "asset_path": "", "prompt": "fallback prompt", "generated": False, "source": "template"},
        "approved": True,
    }


def test_svg_prompt_drops_minimalist_constraints() -> None:
    prompt = _svg_prompt(_card())
    assert "under 80 elements" not in prompt
    assert "geometric shapes only" not in prompt


def test_svg_prompt_requests_rich_illustration_and_keeps_safety_rules() -> None:
    prompt = _svg_prompt(_card())
    assert "detailed" in prompt.lower() or "rich" in prompt.lower()
    # 보안 불변식 문장 유지
    assert "<text>" in prompt
    assert "viewBox 0 0 320 150" in prompt
    # 카드 맥락 포함(기존 통합 테스트 호환)
    assert "calendar reminder permission" in prompt
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_svg_prompt.py -v`
Expected: FAIL

- [ ] **Step 3: 구현** — `_svg_prompt` 교체 + 타임아웃 상향

```python
_MAX_CONCURRENT_ASSET_REQUESTS: Final = 3
_ASSET_TIMEOUT_SECONDS: Final = 120
```

```python
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SVG_PROMPT_START ===
def _svg_prompt(card: VisualCardDict) -> str:
    visual_prompt = (card["visual_prompt"] or card["image"]["prompt"])[:_VISUAL_PROMPT_LIMIT]
    return (
        "Create one rich, detailed standalone SVG illustration for a report card body image slot.\n"
        "Return only one <svg>...</svg> element. No markdown fences, no explanation.\n"
        "Canvas: viewBox 0 0 320 150. Hand-drawn editorial card-news style with bold black outlines.\n"
        "Make it visually rich: layered shapes, filled areas, soft shadows, and a clear focal scene\n"
        "so it reads like an illustrator drew it, not a flat icon.\n"
        "Do not include readable text, Korean text, Latin text, <text>, scripts, external images, URLs, hrefs, or event handlers.\n"
        "Make the illustration specific to this visual prompt, not generic.\n\n"
        f"Card title: {card['title']}\n"
        f"Card body meaning: {card['body'][:260]}\n"
        f"Visual prompt: {visual_prompt}\n"
        f"Negative prompt: {card['negative_prompt'][:260]}"
    )
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SVG_PROMPT_END ===
```

- [ ] **Step 4: 통과 확인 + 회귀**

Run: `pytest tests/core/reporting_cli/test_report_card_news_svg_prompt.py tests/core/reporting_cli/test_report_card_news_asset_generator.py -v`
Expected: PASS (기존 통합 테스트의 `"calendar reminder permission" in runner.commands[0][2]`도 유지)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/report_card_news_asset_generator.py tests/core/reporting_cli/test_report_card_news_svg_prompt.py
git commit -m "feat(report): 카드뉴스 SVG 프롬프트 풍부화 + 타임아웃 120s"
```

---

### Task B2: 배치 SVG 생성 — 카드당 호출 → 단일 CLI 호출 (속도)

**Files:**
- Modify: `vibelign/core/reporting_cli/report_card_news_asset_generator.py` — 상수/`import json`, `materialize_card_news_assets` 라우팅, 신규 `_shared_cli_provider`/`_materialize_via_batch`/`_batch_svg_list`/`_parse_batch_svgs`/`_batch_svg_prompt`
- Test: `tests/core/reporting_cli/test_report_card_news_asset_generator.py`

**Interfaces:**
- Consumes (Phase A·B): `_asset_source`, `_card_with_asset(card, asset_relative, source)`, `_asset_relative_path`, `_fallback_asset_svg`, `_extract_safe_svg`, `_with_svg_schema`, `_CLI_ASSET_PROVIDERS`, `safe_planning_status`, `cli_adapters.build_cli_command`.
- Produces: CLI provider + 카드 2장 이상이면 `materialize_card_news_assets`가 **1회 CLI 호출**로 N장 SVG를 받는다. 응답 형식 `{"svgs": ["<svg>...</svg>", ...]}`(카드 순서). 누락/비안전/타임아웃 SVG는 카드별 `_fallback_asset_svg`로 강등(전체 실패 아님). 단일 카드·비-CLI provider는 기존 경로 유지.

- [ ] **Step 1: 기존 동시성 테스트를 배치 동작으로 교체 + 신규 테스트** — `test_report_card_news_asset_generator.py`

`test_model_provider_generates_multiple_assets_concurrently`를 배치 단언으로 교체(배치는 1회 호출이므로 동시성 단언이 더 이상 유효하지 않음):

```python
def test_model_provider_batches_multiple_assets_in_one_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_json = '{"svgs": ['
    batch_json += ','.join(
        f'"<svg viewBox=\\"0 0 320 150\\" data-card=\\"{i}\\"><rect width=\\"320\\" height=\\"150\\"/></svg>"'
        for i in range(1, 4)
    )
    batch_json += ']}'
    runner = FakeRunner(batch_json)
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    cards = [_card_with_id(f"card-{index}", f"카드 {index}") for index in range(1, 4)]

    generated = materialize_card_news_assets(tmp_path, "예약-알림", cards, runner=runner)

    assert len(generated) == 3
    assert len(runner.commands) == 1  # 단일 배치 호출
    for index, card in enumerate(generated, 1):
        svg = (tmp_path / card["image"]["asset_path"]).read_text(encoding="utf-8")
        assert f'data-card="{index}"' in svg
        assert card["image"]["source"] == "llm"


def test_batch_falls_back_per_card_for_missing_svg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # svgs 배열에 2개만 제공 → 3번째 카드는 폴백 스케치
    runner = FakeRunner('{"svgs": ["<svg viewBox=\\"0 0 320 150\\"><rect/></svg>", "<svg viewBox=\\"0 0 320 150\\"><circle/></svg>"]}')
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    cards = [_card_with_id(f"card-{index}", f"카드 {index}") for index in range(1, 4)]

    generated = materialize_card_news_assets(tmp_path, "예약-알림", cards, runner=runner)

    assert len(runner.commands) == 1
    third = (tmp_path / generated[2]["image"]["asset_path"]).read_text(encoding="utf-8")
    assert "data-sketch-symbols" in third
    assert generated[2]["image"]["source"] == "fallback"


def test_batch_timeout_falls_back_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = FakeRunner("", status="timeout")
    monkeypatch.setattr(cli_adapters, "build_cli_command", _fake_build_command)
    cards = [_card_with_id(f"card-{index}", f"카드 {index}") for index in range(1, 3)]

    generated = materialize_card_news_assets(tmp_path, "예약-알림", cards, runner=runner)

    assert len(runner.commands) == 1
    for card in generated:
        svg = (tmp_path / card["image"]["asset_path"]).read_text(encoding="utf-8")
        assert "data-sketch-symbols" in svg
        assert card["image"]["source"] == "fallback"
```

`CountingRunner`는 더 이상 쓰이지 않으면 남겨두되(다른 테스트 참조 없으면 삭제 가능), import 오류 안 나게만 유지.

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_asset_generator.py -v`
Expected: FAIL — 배치 함수 없음 / 기존 동시성 테스트 제거로 인한 정의 부재

- [ ] **Step 3: 구현** — 상수/import 추가

파일 상단 import에 `import json` 추가(이미 `import re` 있음). 상수 영역에 추가:

```python
_BATCH_TIMEOUT_SECONDS: Final = 180
_JSON_OBJECT_RE: Final[re.Pattern[str]] = re.compile(r"\{[\s\S]*\}")
```

`materialize_card_news_assets` 라우팅 교체:

```python
def materialize_card_news_assets(
    root: Path,
    slug: str,
    cards: list[VisualCardDict],
    runner: cli_adapters.PlanningCliRunner | None = None,
    timeout_seconds: int = _ASSET_TIMEOUT_SECONDS,
) -> list[VisualCardDict]:
    context = _AssetRenderContext(root=root, slug=slug, runner=runner, timeout_seconds=timeout_seconds)
    asset_dir = _safe_asset_dir(root, slug)
    if len(cards) > 1 and _shared_cli_provider(cards) is not None:
        return _materialize_via_batch(context, asset_dir, cards)
    if len(cards) <= 1:
        return [_materialize_card_asset(context, asset_dir, index, card) for index, card in enumerate(cards, 1)]
    worker_count = min(_MAX_CONCURRENT_ASSET_REQUESTS, len(cards))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(_materialize_card_asset, context, asset_dir, index, card)
            for index, card in enumerate(cards, 1)
        ]
        return [future.result() for future in futures]
```

신규 함수(앵커 추가, `_materialize_card_asset` 인근):

```python
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SHARED_CLI_PROVIDER_START ===
def _shared_cli_provider(cards: list[VisualCardDict]) -> str | None:
    providers = {card["image"]["provider"] for card in cards}
    if len(providers) != 1:
        return None
    provider = next(iter(providers))
    return provider if provider in _CLI_ASSET_PROVIDERS else None
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__SHARED_CLI_PROVIDER_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__MATERIALIZE_VIA_BATCH_START ===
def _materialize_via_batch(
    context: _AssetRenderContext,
    asset_dir: Path,
    cards: list[VisualCardDict],
) -> list[VisualCardDict]:
    resolved: dict[int, VisualCardDict] = {}
    pending: list[tuple[int, VisualCardDict, Path]] = []
    for index, card in enumerate(cards, 1):
        if card["image"]["asset_path"].strip():
            resolved[index] = card
            continue
        asset_relative = _asset_relative_path(context.slug, card, index)
        existing = context.root / asset_relative
        if existing.exists():
            svg = existing.read_text(encoding="utf-8")
            resolved[index] = _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))
            continue
        pending.append((index, card, asset_relative))
    if pending:
        asset_dir.mkdir(parents=True, exist_ok=True)
        svgs = _batch_svg_list(context, [card for _, card, _ in pending])
        for offset, (index, card, asset_relative) in enumerate(pending):
            svg = svgs[offset] if offset < len(svgs) and svgs[offset] is not None else _fallback_asset_svg(card)
            _ = (context.root / asset_relative).write_text(svg, encoding="utf-8")
            resolved[index] = _card_with_asset(card, asset_relative, _asset_source(card["image"]["provider"], svg))
    return [resolved[index] for index in range(1, len(cards) + 1)]
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__MATERIALIZE_VIA_BATCH_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_LIST_START ===
def _batch_svg_list(context: _AssetRenderContext, cards: list[VisualCardDict]) -> list[str | None]:
    provider = cards[0]["image"]["provider"]
    command = cli_adapters.build_cli_command(provider, _batch_svg_prompt(cards))
    if command is None:
        raise CardNewsAssetError(f"{provider} CLI를 찾지 못해 카드뉴스 이미지를 만들지 못했어요.")
    runner = context.runner or cli_adapters.SubprocessPlanningCliRunner()
    result = runner.run(command, cwd=context.root, input_text="", timeout_seconds=_BATCH_TIMEOUT_SECONDS)
    status = safe_planning_status(result.status, result.stdout)
    if status == "timeout":
        return [None] * len(cards)
    if status != "ok":
        raise CardNewsAssetError(f"{provider} CLI 카드뉴스 이미지 생성 실패: {result.stderr.strip() or status}")
    return _parse_batch_svgs(result.stdout, len(cards))
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_LIST_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__PARSE_BATCH_SVGS_START ===
def _parse_batch_svgs(stdout: str, count: int) -> list[str | None]:
    match = _JSON_OBJECT_RE.search(stdout.strip())
    if match is None:
        return [None] * count
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [None] * count
    raw = data.get("svgs") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return [None] * count
    out: list[str | None] = []
    for index in range(count):
        item = raw[index] if index < len(raw) and isinstance(raw[index], str) else ""
        try:
            svg = _extract_safe_svg(item)
        except CardNewsAssetError:
            svg = None
        out.append(_with_svg_schema(svg) if svg else None)
    return out
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__PARSE_BATCH_SVGS_END ===


# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_PROMPT_START ===
def _batch_svg_prompt(cards: list[VisualCardDict]) -> str:
    lines: list[str] = []
    for index, card in enumerate(cards, 1):
        visual = (card["visual_prompt"] or card["image"]["prompt"])[:_VISUAL_PROMPT_LIMIT]
        lines.append(f'{index}. title="{card["title"]}" meaning="{card["body"][:160]}" visual="{visual}"')
    listing = "\n".join(lines)
    return (
        f"Create {len(cards)} rich, detailed SVG illustrations for report card body slots.\n"
        'Return ONLY one JSON object: {"svgs": ["<svg>...</svg>", ...]} with exactly one <svg> per card, in order.\n'
        "Each SVG: viewBox 0 0 320 150, hand-drawn editorial card-news style, bold black outlines,\n"
        "layered filled shapes, soft shadows, a clear focal scene (not a flat icon).\n"
        "No readable text, no Korean text, no Latin text, no <text>, no scripts, no external images, no URLs, no hrefs, no event handlers.\n"
        "Make each illustration specific to its card.\n\n"
        f"Cards:\n{listing}"
    )
# === ANCHOR: REPORT_CARD_NEWS_ASSET_GENERATOR__BATCH_SVG_PROMPT_END ===
```

> **참고(배치 vs 단일 차이):** 단일 경로(`_llm_asset_svg`)는 비안전 SVG에 `CardNewsAssetError`를 raise하지만, 배치 경로는 해당 카드만 폴백으로 강등한다(한 장의 위험 SVG가 전체 생성을 막지 않도록). 의도된 차이.
> **argv 가드:** 배치 프롬프트는 카드당 visual 900자로 잘려 N=6이면 ~7K자 → Windows argv ~32K자 한계 내. 카드 수는 `_MAX_CARDS=6` 상한.

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_asset_generator.py -v`
Expected: PASS (단일 카드 기존 테스트 4종 + 배치 3종)

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/report_card_news_asset_generator.py tests/core/reporting_cli/test_report_card_news_asset_generator.py
git commit -m "perf(report): 카드뉴스 SVG를 단일 CLI 배치 호출로 생성(7회→2회)"
```

---

# Phase C — 전체 포스터 HTML 모드

### Task C1: HTML sanitizer

**Files:**
- Create: `vibelign/core/reporting_cli/report_card_news_poster.py`
- Test: `tests/core/reporting_cli/test_report_card_news_poster.py` (신규)

**Interfaces:**
- Produces: `sanitize_card_news_html(raw_html: str) -> str | None` — `<html>...</html>` 추출 + 위험 요소 제거. 추출 불가 시 `None`. `CardNewsPosterError(ValueError)`.

- [ ] **Step 1: 실패 테스트 작성** (신규 파일)

```python
from __future__ import annotations

from vibelign.core.reporting_cli.report_card_news_poster import sanitize_card_news_html


def test_sanitize_strips_script_and_handlers() -> None:
    html = sanitize_card_news_html(
        '<html><body><h1 onclick="x()">A</h1><script>alert(1)</script><p>본문</p></body></html>'
    )
    assert html is not None
    assert "<script" not in html
    assert "onclick" not in html
    assert "본문" in html


def test_sanitize_strips_external_resources() -> None:
    html = sanitize_card_news_html(
        '<html><head><link rel="stylesheet" href="https://cdn/x.css"></head>'
        '<body><img src="https://evil/x.png"><iframe src="//e"></iframe>카드</body></html>'
    )
    assert html is not None
    assert "https://" not in html
    assert "<iframe" not in html
    assert "<link" not in html


def test_sanitize_returns_none_without_html() -> None:
    assert sanitize_card_news_html("그냥 설명 텍스트, HTML 없음") is None


def test_sanitize_keeps_inline_style() -> None:
    html = sanitize_card_news_html("<html><head><style>.c{color:red}</style></head><body>카드</body></html>")
    assert html is not None
    assert "<style>" in html
    assert "color:red" in html
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_poster.py -v`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현** — 신규 모듈(sanitizer 부분)

```python
# === ANCHOR: REPORT_CARD_NEWS_POSTER_START ===
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from vibelign.core.planning_cli import cli_adapters
from vibelign.core.planning_cli.response_policy import safe_planning_status
from vibelign.core.reporting_cli.report_card_news_html import render_card_news_html
from vibelign.core.reporting_cli.report_visual_cards import VisualCardDict, VisualCardsDict

_HTML_RE: Final[re.Pattern[str]] = re.compile(r"<html\b[\s\S]*?</html>", re.IGNORECASE)
_SCRIPT_RE: Final[re.Pattern[str]] = re.compile(r"<script\b[\s\S]*?</script>", re.IGNORECASE)
_DANGEROUS_TAG_RE: Final[re.Pattern[str]] = re.compile(
    r"<\s*/?\s*(iframe|object|embed|link|base|meta)\b[^>]*>", re.IGNORECASE
)
_HANDLER_RE: Final[re.Pattern[str]] = re.compile(r"""\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)
_EXTERNAL_ATTR_RE: Final[re.Pattern[str]] = re.compile(
    r"""\s(?:src|href|xlink:href)\s*=\s*("(?:https?:)?//[^"]*"|'(?:https?:)?//[^']*')""", re.IGNORECASE
)
_POSTER_TIMEOUT_SECONDS: Final = 150
_MAX_SOURCE_CHARS: Final = 7000


class CardNewsPosterError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PosterResult:
    html: str
    source: Literal["llm", "fallback"]


def sanitize_card_news_html(raw_html: str) -> str | None:
    match = _HTML_RE.search(raw_html)
    if match is None:
        return None
    html = match.group(0)
    html = _SCRIPT_RE.sub("", html)
    html = _DANGEROUS_TAG_RE.sub("", html)
    html = _HANDLER_RE.sub("", html)
    html = _EXTERNAL_ATTR_RE.sub("", html)
    if _has_remaining_external_url(html):
        html = re.sub(r"(https?:)?//[^\s\"'>]+", "", html)
    return html


def _has_remaining_external_url(html: str) -> bool:
    return "http://" in html or "https://" in html
# === ANCHOR: REPORT_CARD_NEWS_POSTER_END ===
```

- [ ] **Step 4: 통과 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_poster.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/report_card_news_poster.py tests/core/reporting_cli/test_report_card_news_poster.py
git commit -m "feat(report): 카드뉴스 포스터 HTML sanitizer"
```

---

### Task C2: CLI 포스터 생성 (성공/폴백)

**Files:**
- Modify: `vibelign/core/reporting_cli/report_card_news_poster.py` (`generate_card_news_poster` 추가)
- Test: `tests/core/reporting_cli/test_report_card_news_poster.py`

**Interfaces:**
- Consumes: `cli_adapters.build_cli_command`, `safe_planning_status`, `render_card_news_html` (폴백), `sanitize_card_news_html` (C1).
- Produces: `generate_card_news_poster(payload: VisualCardsDict, cards: list[VisualCardDict], root: Path, provider: str, runner=None, timeout_seconds=150) -> PosterResult`. CLI 미설치/비-ok status → `CardNewsPosterError`. 타임아웃/추출실패 → `render_card_news_html` 폴백 + `source="fallback"`. 성공 → sanitized HTML + `source="llm"`.

- [ ] **Step 1: 실패 테스트 작성** — `test_report_card_news_poster.py`에 FakeRunner(에셋 생성기 테스트와 동일 패턴) 추가 후:

```python
from pathlib import Path
import pytest
from vibelign.core.planning_cli import cli_adapters
from vibelign.core.reporting_cli.report_card_news_poster import (
    CardNewsPosterError, generate_card_news_poster,
)

class FakeRunner:
    def __init__(self, stdout: str, status: cli_adapters.PlanningCliStatus = "ok") -> None:
        self.stdout, self.status, self.commands = stdout, status, []
    def run(self, command, *, cwd, input_text, timeout_seconds):
        self.commands.append(command)
        return cli_adapters.PlanningCliResult(status=self.status, stdout=self.stdout, stderr="", exit_code=0, duration_ms=7)

def _payload() -> dict:
    card = {
        "id": "c1", "title": "목표", "body": "한 줄 목표", "caption": "출처: 개요",
        "visual_prompt": "scene, no readable text in image", "negative_prompt": "text",
        "source_refs": [], "approved": True,
        "image": {"provider": "agy", "asset_path": "", "prompt": "", "generated": False, "source": "template"},
    }
    return {"schema_version": "report-visual-cards-v1", "status": "ready", "provider": "agy", "cards": [card], "assets": []}

def test_poster_success_returns_sanitized_llm_html(tmp_path: Path, monkeypatch) -> None:
    runner = FakeRunner("<html><body><h1>카드뉴스</h1><script>x</script></body></html>")
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda p, prompt: ["fake", p])
    p = _payload()
    result = generate_card_news_poster(p, p["cards"], tmp_path, "agy", runner=runner)
    assert result.source == "llm"
    assert "<script" not in result.html
    assert "카드뉴스" in result.html

def test_poster_timeout_falls_back(tmp_path: Path, monkeypatch) -> None:
    runner = FakeRunner("", status="timeout")
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda p, prompt: ["fake", p])
    p = _payload()
    result = generate_card_news_poster(p, p["cards"], tmp_path, "agy", runner=runner)
    assert result.source == "fallback"
    assert "<html" in result.html.lower()

def test_poster_missing_cli_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cli_adapters, "build_cli_command", lambda p, prompt: None)
    p = _payload()
    with pytest.raises(CardNewsPosterError):
        _ = generate_card_news_poster(p, p["cards"], tmp_path, "agy")
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/core/reporting_cli/test_report_card_news_poster.py -v`
Expected: FAIL — `generate_card_news_poster` 없음

- [ ] **Step 3: 구현** — 모듈에 추가(앵커 `_END` 위)

```python
def generate_card_news_poster(
    payload: VisualCardsDict,
    cards: list[VisualCardDict],
    root: Path,
    provider: str,
    runner: cli_adapters.PlanningCliRunner | None = None,
    timeout_seconds: int = _POSTER_TIMEOUT_SECONDS,
) -> PosterResult:
    command = cli_adapters.build_cli_command(provider, _poster_prompt(cards))
    if command is None:
        raise CardNewsPosterError(f"{provider} CLI를 찾지 못해 카드뉴스 포스터를 만들지 못했어요.")
    active_runner = runner or cli_adapters.SubprocessPlanningCliRunner()
    result = active_runner.run(command, cwd=root, input_text="", timeout_seconds=timeout_seconds)
    status = safe_planning_status(result.status, result.stdout)
    if status == "timeout":
        return PosterResult(html=render_card_news_html(payload, cards, root, root), source="fallback")
    if status != "ok":
        raise CardNewsPosterError(f"{provider} CLI 카드뉴스 포스터 생성 실패: {result.stderr.strip() or status}")
    sanitized = sanitize_card_news_html(result.stdout)
    if sanitized is None:
        return PosterResult(html=render_card_news_html(payload, cards, root, root), source="fallback")
    return PosterResult(html=sanitized, source="llm")


def _poster_prompt(cards: list[VisualCardDict]) -> str:
    import json

    storyboard = json.dumps(
        [{"number": i, "title": c["title"], "body": c["body"], "caption": c["caption"]} for i, c in enumerate(cards, 1)],
        ensure_ascii=False,
    )[:_MAX_SOURCE_CHARS]
    return (
        "아래 스토리보드로 단일 파일 반응형 한국어 카드뉴스 HTML을 만들어줘.\n"
        "조건: 한국어는 DOM 텍스트로(이미지 글자 금지), 각 카드 본문에 CSS/inline-SVG 도식,\n"
        "외부 스크립트/이미지/CDN/iframe/link 금지, 인라인 <style>만 사용, 모바일에서 겹침/잘림 없음.\n"
        "설명 없이 <html>...</html> 하나만 반환해.\n\n"
        f"스토리보드 JSON:\n{storyboard}"
    )
```

- [ ] **Step 4: 통과 확인 + 커밋**

Run: `pytest tests/core/reporting_cli/test_report_card_news_poster.py -v`
Expected: PASS

```bash
git add vibelign/core/reporting_cli/report_card_news_poster.py tests/core/reporting_cli/test_report_card_news_poster.py
git commit -m "feat(report): CLI 카드뉴스 포스터 HTML 생성(성공/폴백)"
```

---

### Task C3: `--card-news-mode` 인자 + ReportArgs

**Files:**
- Modify: `vibelign/cli/cli_report_command_groups.py:87-92` (report parser, `--visual-card-cli` 다음)
- Modify: `vibelign/commands/vib_report_context.py:23-47` (`ReportArgs`)

**Interfaces:**
- Produces: argparse `card_news_mode` (choices `per-card`/`poster`, default `per-card`); `ReportArgs.card_news_mode: str`.

- [ ] **Step 1: 인자 추가** — `--visual-card-cli` 블록 바로 다음에

```python
    _ = r.add_argument(
        "--card-news-mode",
        default="per-card",
        choices=["per-card", "poster"],
        help="카드뉴스 생성 방식 (per-card=카드별 SVG, poster=CLI가 HTML 전체 디자인)",
    )
```

- [ ] **Step 2: ReportArgs에 필드 추가** — `visual_card_cli: str` 다음 줄

```python
    visual_card_cli: str
    card_news_mode: str
```

- [ ] **Step 3: 인자 파싱 스모크 테스트**

Run: `python3 -c "import argparse; from vibelign.cli.cli_command_groups import build_parser" 2>/dev/null; vib report --help | grep -- "--card-news-mode"`
Expected: `--card-news-mode` 라인 출력 (또는 빌드된 CLI에서 확인)

대안 검증: `pytest tests/cli/test_vib_report_cmd.py -q` (기존 report 인자 파싱 테스트 그린 유지).

- [ ] **Step 4: 커밋**

```bash
git add vibelign/cli/cli_report_command_groups.py vibelign/commands/vib_report_context.py
git commit -m "feat(report): --card-news-mode 인자(per-card/poster) 추가"
```

---

### Task C4: 런타임 poster 분기 + JSON 응답 필드

**Files:**
- Modify: `vibelign/commands/vib_report_runtime.py:29-40` (types), `:186-222` (`_print_render_response`, `_visual_cards`)
- Test: `tests/cli/test_vib_report_card_news_mode.py` (신규)

**Interfaces:**
- Consumes: `generate_card_news_poster` (C2), `_visual_cards` 결과 cards.
- Produces: poster 모드일 때 JSON 응답에 `"card_news_poster": {"html": str, "source": "llm"|"fallback"}` 추가.

- [ ] **Step 1: 실패 테스트 작성** (신규 파일) — 기존 `tests/cli/test_vib_report_cmd.py`의 호출 패턴(runner/모델 주입)을 참고해, poster 모드 응답에 `card_news_poster.html`이 포함되는지 검증. (해당 테스트 파일의 헬퍼·fixture를 그대로 재사용하여 작성.)

```python
# 핵심 단언 (헬퍼는 test_vib_report_cmd.py 패턴 재사용)
def test_poster_mode_includes_poster_html(...):
    payload = run_report_json(args_with(visual_cards=True, visual_card_cli="agy", card_news_mode="poster"), fake_runner_returning_html)
    assert "card_news_poster" in payload
    assert payload["card_news_poster"]["source"] in ("llm", "fallback")
    assert "<html" in payload["card_news_poster"]["html"].lower()
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/cli/test_vib_report_card_news_mode.py -v`
Expected: FAIL

- [ ] **Step 3: 구현** — types 확장

```python
class ReportRenderJsonPayload(TypedDict):
    ok: bool
    path: str
    report_type: str
    visual_cards: NotRequired[VisualCardsDict]
    card_news_poster: NotRequired[dict[str, str]]
```

`_print_render_response`에서 poster 분기 추가(visual_cards 계산 직후):

```python
        if getattr(raw, "visual_cards", False):
            try:
                cards_payload = _visual_cards(raw, ctx, model)
                payload["visual_cards"] = cards_payload
                poster = _card_news_poster(raw, ctx, cards_payload)
                if poster is not None:
                    payload["card_news_poster"] = poster
            except (CardNewsAssetError, VisualCardsCliError) as exc:
                _fail(ctx.want_json, str(exc))
```

신규 `_card_news_poster` 함수(`_visual_cards` 아래):

```python
def _card_news_poster(
    raw: ReportArgs, ctx: ReportCommandContext, cards_payload: VisualCardsDict
) -> dict[str, str] | None:
    if getattr(raw, "card_news_mode", "per-card") != "poster":
        return None
    provider_name = getattr(raw, "visual_card_cli", "local") or "local"
    if provider_name in {"", "local"} or cards_payload["status"] != "ready":
        return None
    from vibelign.core.reporting_cli.report_card_news_poster import (
        CardNewsPosterError,
        generate_card_news_poster,
    )

    try:
        result = generate_card_news_poster(cards_payload, cards_payload["cards"], ctx.root, provider_name)
    except CardNewsPosterError as exc:
        _fail(ctx.want_json, str(exc))
    return {"html": result.html, "source": result.source}
```

import 추가(파일 상단 reporting_cli import 블록): 위 함수 내 지연 import로 처리(순환/lazy 일관). `ReportArgs`는 이미 import됨.

- [ ] **Step 4: 통과 확인 + 회귀**

Run: `pytest tests/cli/test_vib_report_card_news_mode.py tests/cli/test_vib_report_cmd.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign/commands/vib_report_runtime.py tests/cli/test_vib_report_card_news_mode.py
git commit -m "feat(report): poster 모드 런타임 분기 + card_news_poster 응답"
```

---

### Task C5: finalize 시 poster HTML 저장

**Files:**
- Modify: `vibelign/core/reporting_cli/report_card_news_payload.py` (`_PayloadModel.poster_html`, 신규 로더)
- Modify: `vibelign/core/reporting_cli/report_card_news_export.py:55-80` (`export_card_news`)
- Test: `tests/cli/test_vib_report_card_news_finalize_cmd.py` (기존 파일에 케이스 추가)

**Interfaces:**
- Consumes: `sanitize_card_news_html` (C1).
- Produces: payload에 `poster_html: str` 있으면 export 시 그 HTML(sanitize 통과분)을 `html_path`에 기록. 없거나 unsafe면 기존 `render_card_news_html` 사용.

- [ ] **Step 1: 실패 테스트 작성** — `test_vib_report_card_news_finalize_cmd.py`의 payload 빌더에 `poster_html` 포함시키고, 결과 HTML 파일이 그 내용을 담는지 단언(파일 기존 헬퍼 재사용):

```python
def test_finalize_writes_poster_html_when_present(tmp_path, ...):
    payload = approved_payload_dict()
    payload["poster_html"] = "<html><body><h1>모델 포스터</h1></body></html>"
    # payload 파일로 저장 후 export_card_news 또는 run_vib_report_card_news 호출
    export = export_card_news(payload_path)
    assert "모델 포스터" in export.html_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 실패 확인**

Run: `pytest tests/cli/test_vib_report_card_news_finalize_cmd.py -k poster -v`
Expected: FAIL

- [ ] **Step 3: 구현** — payload 모델에 필드 + 로더

`_PayloadModel`에 추가:

```python
    cards: list[_CardModel]
    poster_html: str = ""
```

신규 로더(기존 `load_visual_cards_payload` 아래, 앵커 추가):

```python
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_LOAD_POSTER_HTML_START ===
def load_card_news_poster_html(payload_path: Path) -> str:
    try:
        model = _PayloadModel.model_validate_json(payload_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValidationError):
        return ""
    return model.poster_html
# === ANCHOR: REPORT_CARD_NEWS_PAYLOAD_LOAD_POSTER_HTML_END ===
```

`export_card_news`에서 html 작성부 교체(`html_path.write_text(...)` 라인):

```python
    poster_html = load_card_news_poster_html(payload_path)
    safe_poster = sanitize_card_news_html(poster_html) if poster_html else None
    html_body = safe_poster if safe_poster is not None else render_card_news_html(
        payload, approved_with_assets, root, html_path.parent
    )
    _ = html_path.write_text(html_body, encoding="utf-8")
```

import 추가(파일 상단): `from vibelign.core.reporting_cli.report_card_news_payload import load_visual_cards_payload, load_card_news_poster_html` 및 `from vibelign.core.reporting_cli.report_card_news_poster import sanitize_card_news_html`.

- [ ] **Step 4: 통과 확인 + 회귀**

Run: `pytest tests/cli/test_vib_report_card_news_finalize_cmd.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add vibelign/core/reporting_cli/report_card_news_payload.py vibelign/core/reporting_cli/report_card_news_export.py tests/cli/test_vib_report_card_news_finalize_cmd.py
git commit -m "feat(report): finalize 시 모델 포스터 HTML 저장(sanitize 통과분)"
```

---

### Task C6: GUI — mode 인자 + poster 파싱 + 저장 payload

**Files:**
- Modify: `vibelign-gui/src/lib/vib/reportVisualCards.ts:42-44` (`ReportVisualCardsResult`), `:157-177` (`requestReportVisualCards`), `:180-222` (`saveReportVisualCards`)
- Test: `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`

**Interfaces:**
- Produces: `requestReportVisualCards(cwd, planPath, reportType, provider, mode)` — `--card-news-mode {mode}` 전달, 응답의 `card_news_poster` 파싱. `ReportVisualCardsResult` ok 분기에 `poster?: { html: string; source: "llm" | "fallback" }`. `saveReportVisualCards`는 payload에 `poster_html` 포함.

- [ ] **Step 1: 실패 테스트 작성**

```ts
it("passes card-news-mode and parses poster", async () => {
  // runVib 모킹: --card-news-mode 가 인자에 포함되고, card_news_poster 가 결과로 파싱되는지
});
```

(파일 기존 `runVib` 모킹 패턴 재사용. 단언: 호출 args에 `"--card-news-mode"`, `"poster"` 포함, result.poster.html === 기대값.)

- [ ] **Step 2: 실패 확인**

Run: `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/reportVisualCards.test.ts`
Expected: FAIL

- [ ] **Step 3: 구현**

`ReportVisualCardsResult` 확장:

```ts
export type ReportVisualCardsResult =
  | {
      readonly ok: true;
      readonly payload: ReportVisualCardsPayload;
      readonly poster?: { readonly html: string; readonly source: "llm" | "fallback" };
    }
  | { readonly ok: false; readonly error: string };
```

`requestReportVisualCards` 시그니처/본문:

```ts
export async function requestReportVisualCards(
  cwd: string,
  planPath: string,
  reportType: ReportType,
  provider: ReportVisualCardsProviderId,
  mode: "per-card" | "poster" = "per-card",
): Promise<ReportVisualCardsResult> {
  const res = await runVib(
    ["report", planPath, "--type", reportType, "--visual-cards", "--visual-card-cli", provider, "--card-news-mode", mode, "--json"],
    cwd,
  );
  try {
    const raw: unknown = JSON.parse(res.stdout.trim());
    if (!isRecord(raw) || raw.ok !== true) {
      return { ok: false, error: isRecord(raw) ? stringValue(raw.error) || "카드뉴스 생성 실패" : "카드뉴스 생성 실패" };
    }
    return { ok: true, payload: parseReportVisualCardsPayload(raw.visual_cards), poster: parsePoster(raw.card_news_poster) };
  } catch {
    return { ok: false, error: res.stderr.trim() || "카드뉴스 생성 실패" };
  }
}

function parsePoster(value: unknown): { html: string; source: "llm" | "fallback" } | undefined {
  if (!isRecord(value)) return undefined;
  const html = stringValue(value.html);
  if (html.length === 0) return undefined;
  return { html, source: value.source === "fallback" ? "fallback" : "llm" };
}
```

`saveReportVisualCards`는 호출 측에서 `poster_html`을 payload에 넣어 전달하므로(다음 태스크), 여기서는 `writeReportJsonPayload(cwd, payload)`가 그대로 직렬화하면 됨 — `ReportVisualCardsPayload` 타입에 optional `poster_html?: string`를 추가:

```ts
export type ReportVisualCardsPayload = {
  readonly schema_version: "report-visual-cards-v1";
  readonly status: "ready" | "empty";
  readonly provider: string;
  readonly cards: readonly ReportVisualCard[];
  readonly assets: readonly ReportVisualCardImage[];
  readonly poster_html?: string;
};
```

- [ ] **Step 4: 통과 확인 + 커밋**

Run: `cd vibelign-gui && npx vitest run src/lib/vib/__tests__/reportVisualCards.test.ts`
Expected: PASS

```bash
git add vibelign-gui/src/lib/vib/reportVisualCards.ts vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts
git commit -m "feat(report-gui): 카드뉴스 mode 인자 + poster 응답 파싱"
```

---

### Task C7: GUI — 모드 토글 + sandbox iframe 포스터 프리뷰

**Files:**
- Modify: `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx`
- Test: `vibelign-gui/src/components/plan-doc/__tests__/ReportVisualCardsPanel.test.tsx` 또는 신규 companion 테스트

**Interfaces:**
- Consumes: `requestReportVisualCards(..., mode)` (C6), `result.poster`.
- Produces: 모델 드롭다운 옆 모드 토글(`per-card`/`poster`); poster 결과 시 `<iframe sandbox srcDoc={poster.html}>` 프리뷰 + 출처 배지; finalize 시 `poster_html`을 payload에 포함.

- [ ] **Step 1: 상태/토글 추가** — 컴포넌트 상단 state

```tsx
const [mode, setMode] = useState<"per-card" | "poster">("per-card");
const [poster, setPoster] = useState<{ html: string; source: "llm" | "fallback" } | null>(null);
```

`requestCards`에서 mode 전달 및 poster 저장:

```tsx
const result = await requestReportVisualCards(cwd, planPath, reportType, provider, mode);
setLoading(false);
if (!result.ok) { /* 기존 분기 */ return; }
setPayload(result.payload);
setPoster(result.poster ?? null);
setExportResult(null);
```

- [ ] **Step 2: 토글 UI** — 모델 `<select>` 옆에 모드 `<select>` 추가(기존 `select` 스타일 재사용)

```tsx
<select aria-label="카드뉴스 생성 방식" value={mode}
  onChange={(e) => setMode(e.target.value === "poster" ? "poster" : "per-card")}
  disabled={loading} style={select}>
  <option value="per-card">카드별 일러스트</option>
  <option value="poster">전체 디자인 통째</option>
</select>
```

- [ ] **Step 3: 포스터 프리뷰** — payload 렌더 영역 위에

```tsx
{poster !== null && (
  <div style={resultBox}>
    <p style={resultTitle}>모델 포스터 프리뷰 · {poster.source === "llm" ? "모델 생성" : "폴백"}</p>
    <iframe title="카드뉴스 포스터 프리뷰" sandbox="" srcDoc={poster.html}
      style={{ width: "100%", height: 520, border: "2px solid #1A1A1A", background: "#FFFFFF" }} />
  </div>
)}
```

`sandbox=""` (allow-scripts 없음) 필수.

- [ ] **Step 4: finalize에 poster_html 포함** — `finalizeCards`의 save 호출

```tsx
const result = await saveReportVisualCards(cwd, { ...payload, cards, ...(poster ? { poster_html: poster.html } : {}) });
```

- [ ] **Step 5: 테스트** — poster 결과 시 iframe(sandbox 빈 문자열) 렌더 확인

```tsx
it("renders sandboxed poster preview", () => {
  // requestReportVisualCards 모킹이 poster 반환 → iframe[title="카드뉴스 포스터 프리뷰"] 존재 + sandbox === ""
});
```

Run: `cd vibelign-gui && npx vitest run src/components/plan-doc/__tests__`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx vibelign-gui/src/components/plan-doc/__tests__
git commit -m "feat(report-gui): 카드뉴스 모드 토글 + sandbox iframe 포스터 프리뷰"
```

---

### Task C8: 전체 검증 + codemap 재생성

**Files:** (검증 전용)

- [ ] **Step 1: Python 전체 테스트**

Run: `pytest -q`
Expected: 신규/수정 테스트 그린. 사전에 알려진 기존 실패 3건은 별도 확인(이 작업과 무관함을 diff로 확인).

- [ ] **Step 2: lint + 타입체크**

Run: `ruff check vibelign tests`
Expected: 통과

Run: `basedpyright vibelign/core/reporting_cli vibelign/commands` (프로젝트에 basedpyright 설정이 있으면)
Expected: 신규/수정 코드에 새 오류 없음 (특히 `source` 키 누락, `VisualImageMetadata` 리터럴 완전성)

- [ ] **Step 3: GUI 테스트 + 타입체크**

Run: `cd vibelign-gui && npm test && npx tsc --noEmit`
Expected: 통과

- [ ] **Step 4: codemap 재생성** (앵커 변경 반영)

Run: `vib codemap` (또는 프로젝트의 project_map.json 재생성 명령 — `vib --help`로 확인)
Expected: `.vibelign/project_map.json` 갱신, 신규 앵커(`REPORT_CARD_NEWS_POSTER_*`, `_ASSET_SOURCE_*`, `LOAD_POSTER_HTML_*`) 포함

- [ ] **Step 5: 최종 커밋**

```bash
git add .vibelign/project_map.json
git commit -m "chore(report): 카드뉴스 LLM 이미지 모드 codemap 재생성"
```

---

## 검증 메모 (육안 QA — 코드 외)

- Windows/실기기에서 실제 CLI(`agy` 등) 설치 상태로 `poster` 모드 생성 → iframe 프리뷰 한글 정상, 외부 네트워크 요청 0(개발자도구 Network 확인).
- `per-card` 모드로 생성 시 카드별 배지가 `모델 생성`/`폴백`/`템플릿`로 정확히 표기되는지.
- finalize 후 저장된 HTML이 poster(있으면)/결정론적 렌더(없으면)인지.

## No Silent Caps / 비목표

- 포스터 프리뷰는 finalize 전 미저장 프리뷰. finalize 시에만 파일로 기록(C5).
- 이미지 생성 API·래스터·data-URL/외부 이미지 임베딩은 비목표(보안/단순화).
- 폴백 사유의 상세 구분(timeout vs no-svg)은 v1에서 단일 `fallback`로 묶음 — 더 세분화는 후속.
- 배치 SVG(B2)는 CLI provider + 카드 2장 이상에만 적용. 단일 카드/`local`은 기존 경로. 배치 1회 응답이 일부 SVG를 누락/위험하면 그 카드만 폴백(전체 실패 아님).
