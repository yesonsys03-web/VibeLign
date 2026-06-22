# 카드뉴스 생성 진행바 + 갸리 자동차 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** "카드뉴스 초안 만들기" 생성 중, 백엔드 단계 이벤트에 따라 진행바 위 갸리 자동차(`.gyari-loader`)가 이동해 "진행 중"임을 보여준다.

**Architecture:** 백엔드(`vib report --visual-cards`)가 단계 진입 시 `[progress] step=report-cards stage=...` 를 stderr에 flush → GUI가 `runVibWithProgress`로 수신 → 컴포넌트가 stage→{위치·라벨} 매핑으로 자동차를 트랙 위에서 이동. 최종 stdout JSON 파싱은 기존 그대로. 생성 중에만 표시, 확정 등엔 미적용.

**Tech Stack:** Python(pytest) / React+TS(vitest). 진행 형식은 기존 `[progress]` 파서 재사용(`vib_bridge.rs:parse_progress_line`).

## Global Constraints

- 진행 이벤트는 **stderr**에만, 매번 `flush()`. stdout은 최종 JSON 전용(섞이면 파싱 깨짐).
- 형식: `[progress] step=report-cards stage=<draft|assets|poster>\n` — 공백 포함 msg 금지(파서가 공백 분리). 한국어 라벨은 GUI가 소유.
- 앵커 경계 준수, 파일 전체 재작성 금지, import 구조 임의 변경 금지.
- `.gyari-loader` 클래스(`brutalism.css:542`) 재사용 — 자동차 바퀴 스프라이트는 항상 회전(위치 정지해도 "살아있음" 신호).
- 적용 범위: `requestCards`(생성)만. finalize/확정엔 미적용.

## File Structure

- Modify: `vibelign/commands/vib_report_runtime.py` — `_emit_card_progress` 헬퍼 + `_visual_cards`/`_card_news_poster`에서 단계 emit.
- Modify: `vibelign-gui/src/lib/vib/reportVisualCards.ts` — `requestReportVisualCards`에 `onProgress?` 추가, `runVibWithProgress` 사용.
- Modify: `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx` — 진행바 트랙 + 자동차 + stage 라벨, 생성 중 표시.
- Modify: `vibelign-gui/src/styles/brutalism.css` — 진행 트랙 스타일(필요 시) — 또는 인라인 스타일로.
- Tests: `tests/cli/test_vib_report_card_news_mode.py`(progress emit), `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`(onProgress), `.../__tests__/ReportVisualCardsCompanion.test.tsx`(자동차 렌더/이동).

---

### Task 1: 백엔드 단계 progress 이벤트 emit

**Files:**
- Modify: `vibelign/commands/vib_report_runtime.py` (`_visual_cards` ~213-222, `_card_news_poster`)
- Test: `tests/cli/test_vib_report_card_news_mode.py`

**Interfaces:**
- Produces: stderr에 `[progress] step=report-cards stage=draft`(초안 재작성 전), `stage=assets`(materialize 전), `stage=poster`(포스터 generate 전). 신규 `_emit_card_progress(stage: str) -> None`.

- [ ] **Step 1: 실패 테스트** — capsys로 stderr 캡처. CLI provider + poster 모드로 `run_report_command` 실행 시 stderr에 `stage=draft`, `stage=assets`, `stage=poster`가 순서대로 나오는지. (기존 test 파일의 fake-runner/args 패턴 재사용 — 먼저 읽을 것.)

```python
# 핵심 단언 (헬퍼는 test_vib_report_card_news_mode.py 재사용)
err = capsys.readouterr().err
assert "[progress] step=report-cards stage=draft" in err
assert "[progress] step=report-cards stage=assets" in err
assert "[progress] step=report-cards stage=poster" in err  # poster 모드일 때
```

- [ ] **Step 2: 실패 확인** — `pytest tests/cli/test_vib_report_card_news_mode.py -k progress -v` → FAIL.

- [ ] **Step 3: 구현** — 헬퍼 + emit. `import sys`는 파일 상단에 이미 있음.

```python
def _emit_card_progress(stage: str) -> None:
    _ = sys.stderr.write(f"[progress] step=report-cards stage={stage}\n")
    sys.stderr.flush()
```

`_visual_cards`에 삽입:
```python
def _visual_cards(raw: ReportArgs, ctx: ReportCommandContext, model: ReportModel) -> VisualCardsDict:
    provider_name = getattr(raw, "visual_card_cli", "local") or "local"
    _emit_card_progress("draft")
    base = build_report_visual_cards(model, source_text=ctx.text)
    if provider_name in {"", "local"}:
        return base
    provider = CliVisualCardsProvider(provider_name, root=ctx.root)
    draft = provider.draft(base, ctx.text)
    slug = _report_slug(ctx.slug_source)
    _emit_card_progress("assets")
    cards = materialize_card_news_assets(ctx.root, slug, draft["cards"])
    return {**draft, "cards": cards, "assets": [card["image"] for card in cards]}
```

`_card_news_poster`에 삽입(generate 직전, gating 통과 후):
```python
    _emit_card_progress("poster")
    try:
        result = generate_card_news_poster(cards_payload, cards_payload["cards"], ctx.root, provider_name)
```

- [ ] **Step 4: 통과 + 회귀** — `pytest tests/cli/test_vib_report_card_news_mode.py tests/cli/test_vib_report_cmd.py -v`, `ruff check`, basedpyright(0 errors).

- [ ] **Step 5: 커밋** — `feat(report): 카드뉴스 생성 단계 progress 이벤트(stderr) emit`

---

### Task 2: GUI lib — onProgress + runVibWithProgress

**Files:**
- Modify: `vibelign-gui/src/lib/vib/reportVisualCards.ts` (`requestReportVisualCards`)
- Test: `vibelign-gui/src/lib/vib/__tests__/reportVisualCards.test.ts`

**Interfaces:**
- Consumes: `runVibWithProgress(args, cwd, env, onProgress)` (core.ts), `VibProgressEvent`(types.ts).
- Produces: `requestReportVisualCards(cwd, planPath, reportType, provider, mode, onProgress?)` — `onProgress?: (stage: string) => void`. onProgress 있으면 `runVibWithProgress` 사용, 이벤트의 `e.stage`가 비어있지 않을 때 `onProgress(e.stage)` 호출. 없으면 기존 `runVib`. 최종 stdout JSON/poster 파싱 동일.

- [ ] **Step 1: 실패 테스트** — `runVibWithProgress`를 모킹(이벤트 2개 emit + VibResult 반환). `requestReportVisualCards(..., onProgress)` 호출 시 onProgress가 "draft","assets"로 불리고 결과 payload 파싱되는지. (기존 mock 패턴 읽고 재사용.)

- [ ] **Step 2: 실패 확인** — `npx vitest run src/lib/vib/__tests__/reportVisualCards.test.ts` → FAIL.

- [ ] **Step 3: 구현** — 시그니처에 `onProgress?: (stage: string) => void` 추가. 본문:
```ts
const res = onProgress
  ? await runVibWithProgress(
      ["report", planPath, "--type", reportType, "--visual-cards", "--visual-card-cli", provider, "--card-news-mode", mode, "--json"],
      cwd, undefined,
      (e) => { if (e.stage) onProgress(e.stage); },
    )
  : await runVib(
      ["report", planPath, "--type", reportType, "--visual-cards", "--visual-card-cli", provider, "--card-news-mode", mode, "--json"],
      cwd,
    );
```
(이후 `res.stdout` 파싱은 기존 그대로.) `runVibWithProgress` import 추가(같은 `./core` 모듈).

- [ ] **Step 4: 통과 + tsc** — `npx vitest run ...`, `npx tsc --noEmit`.

- [ ] **Step 5: 커밋** — `feat(report-gui): 카드뉴스 요청에 progress 콜백 추가`

---

### Task 3: GUI 컴포넌트 — 진행바 + 갸리 자동차

**Files:**
- Modify: `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx`
- Test: `vibelign-gui/src/components/plan-doc/__tests__/ReportVisualCardsCompanion.test.tsx`

**Interfaces:**
- Consumes: `requestReportVisualCards(..., onProgress)` (Task 2), `.gyari-loader` CSS(brutalism.css).
- Produces: `loading` 동안 진행바 트랙 + 자동차 렌더. `const [stage, setStage] = useState<string | null>(null)`. `requestCards`에서 `setStage(null)` 시작 → `onProgress=(s)=>setStage(s)` 전달 → 완료/에러 시 정리. stage→{percent,label} 매핑.

- [ ] **Step 1: 실패 테스트** — `requestReportVisualCards`를 모킹해 onProgress로 "assets" 호출하도록 → "카드뉴스 초안 만들기" 클릭 후 진행바 컨테이너(예: `aria-label="카드뉴스 생성 진행"`)와 `.gyari-loader` 자동차가 렌더되고, 라벨에 "카드 이미지"가 보이는지. 생성 완료 후 진행바가 사라지는지.

- [ ] **Step 2: 실패 확인** — `npx vitest run src/components/plan-doc/__tests__/ReportVisualCardsCompanion.test.tsx` → FAIL.

- [ ] **Step 3: 구현** —
  - state: `const [stage, setStage] = useState<string | null>(null);`
  - `requestCards`: 시작 시 `setStage(null)`; 호출을 `requestReportVisualCards(cwd, planPath, reportType, provider, mode, (s) => setStage(s))` 로; finally/완료/에러 분기에서 `setStage(null)`.
  - stage 매핑 헬퍼:
```tsx
const STAGE_UI: Record<string, { pct: number; label: string }> = {
  draft: { pct: 30, label: "초안 만드는 중" },
  assets: { pct: 60, label: "카드 이미지 그리는 중" },
  poster: { pct: 88, label: "포스터 디자인 중 (조금 걸려요)" },
};
const stageUi = stage ? STAGE_UI[stage] ?? { pct: 8, label: "준비 중" } : { pct: 8, label: "준비 중" };
```
  - 렌더(생성 중 `loading`일 때, 버튼 아래):
```tsx
{loading && (
  <div aria-label="카드뉴스 생성 진행" style={progressWrap}>
    <div style={progressTrack}>
      <span className="gyari-loader" style={{ position: "absolute", left: `calc(${stageUi.pct}% - 26px)`, transition: "left .5s ease" }} aria-hidden />
    </div>
    <p style={progressLabel}>{stageUi.label}...</p>
  </div>
)}
```
  - styles: `progressWrap`(margin), `progressTrack`(position:relative; height:56; border:2px solid #1A1A1A; background:#FEFBF0; overflow:hidden), `progressLabel`(fontSize:12; fontWeight:800). 기존 인라인 스타일 톤 따름.
  - 기존 "요청 중..." 버튼 텍스트는 "카드뉴스 만드는 중..."으로 유지/조정.

- [ ] **Step 4: 통과 + tsc + 전체 GUI** — `npx vitest run src/components/plan-doc/__tests__`, `npx tsc --noEmit`, `npm test`.

- [ ] **Step 5: 커밋** — `feat(report-gui): 카드뉴스 생성 진행바 + 갸리 자동차`

---

### Task 4: 검증

- [ ] **Step 1**: `pytest tests/cli tests/core/reporting_cli -q`(회귀), `ruff check`, basedpyright(변경 모듈 0 errors).
- [ ] **Step 2**: GUI `npm test` + `npx tsc --noEmit`.
- [ ] **Step 3**: dev 모드 육안 — Antigravity + 전체 디자인 통째 → 자동차가 draft→assets→poster 위치로 이동, poster에서 바퀴 계속 회전, 완료 시 사라짐.

## 비목표 (YAGNI)
- 포스터 단계 내부 실시간 %(불가 — Claude 호출 블랙박스).
- 확정/다른 명령 진행바.
- 시간기반 가짜 진행(이번엔 단계기반만).
