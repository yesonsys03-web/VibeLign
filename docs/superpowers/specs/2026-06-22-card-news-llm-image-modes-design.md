# 카드뉴스 초안 — "LLM이 만든 듯한 이미지" 생성 설계

- 날짜: 2026-06-22
- 브랜치: feat/report-export-integrate
- 상태: 설계 승인 대기 → 구현 계획 작성 예정

## 1. 문제 정의

보고서 카드뉴스 기능에서 사용자가 초안 모델(ChatGPT/Gemini/Claude 류)을 선택했을 때,
ChatGPT/Gemini에서 직접 만든 결과물처럼 "LLM이 그린 듯한" 이미지가 나오기를 원한다.

현재 앱 초안은 고정된 12종 아이콘 템플릿(`render_card_sketch_svg`)으로 보이고,
외부 LLM 결과물(풍부한 일러스트/포스터)과 격차가 크다.

### 사용자가 못박은 제약

- **이미지 생성 API를 쓰지 않는다.** 모든 생성은 앱에 이미 연결된 CLI 에이전트(`claude`/`codex`/`agy`/`opencode`)만 사용한다.
- CLI 에이전트는 코드 생성기이므로 **래스터(픽셀) 그림은 불가능**하다. 따라서 목표는
  "회화풍 래스터"가 아니라 **CLI가 디자인한 풍부한 벡터(SVG)/HTML 그래픽**이다. 이 점은 합의됨.

## 2. 현재 구조 (사실 확인)

이미 다음 파이프라인이 존재하고 GUI에 배선되어 있다.

- GUI: `ReportVisualCardsCompanion.tsx:123-133`에 "카드뉴스 초안 모델" 드롭다운 존재
  (`local`/`claude`/`codex`/`agy`/`opencode`).
- `requestReportVisualCards()` (`reportVisualCards.ts:158`) → CLI `report ... --visual-cards --visual-card-cli {provider} --json`.
- 백엔드 `_visual_cards()` (`vib_report_runtime.py:213`):
  - `local` → `build_report_visual_cards()` 템플릿만 반환(asset_path 빈 값 → 고정 스케치 렌더).
  - CLI provider → `CliVisualCardsProvider.draft()`로 카드 텍스트 재작성 →
    `materialize_card_news_assets()`로 카드별 SVG 생성.
- `materialize_card_news_assets()` (`report_card_news_asset_generator.py:47`):
  - `card.image.provider`가 `{claude,codex,agy,opencode}`이면 `_llm_asset_svg()` (CLI 호출),
    아니면 `_fallback_asset_svg()` (고정 스케치).
- 렌더: `render_card_news_html()`가 전체 포스터 HTML을 만들고, 각 패널은 `asset_path` SVG가 있으면 사용,
  없으면 고정 스케치.
- `build_cli_command()` (`cli_adapters.py:207`)는 provider를 실제 실행파일로 매핑(`shutil.which`).

### 왜 여전히 템플릿처럼 보이는가 (근본 원인)

1. **조용한 폴백**: `_llm_asset_svg()`는 타임아웃(`_ASSET_TIMEOUT_SECONDS=90`) 또는 비-SVG 응답 시
   말없이 `_fallback_asset_svg()`(고정 스케치)로 대체한다. `_card_with_asset()`은 출처와 무관하게
   항상 `generated:True`로 기록 → 사용자는 모델이 실패했는지 알 수 없다.
2. **프롬프트가 의도적으로 단순함**: `_svg_prompt()`가 *"simple, under 80 elements, geometric shapes only,
   no text"*를 요구 → 성공해도 밋밋한 기하 아이콘이 나온다.
3. CLI는 이미지 모델이 아니므로 최선이어도 벡터 SVG (제약상 당연).

## 3. 목표

선택한 CLI 모델로 "LLM이 만든 듯한" 카드뉴스를 만든다. 범위 A+B+C 전부:

- **A. 실패 가시화** — 폴백을 숨기지 않고 사용자에게 알린다.
- **B. 풍부한 SVG 프롬프트** — 카드별 일러스트를 디테일/색감 있게.
- **C. 전체 포스터 통째 생성** — CLI가 카드뉴스 HTML 전체를 하나로 디자인하는 신규 모드.

## 4. 설계

### 4.0 두 가지 생성 모드 + 명시적 토글

초안 생성을 두 모드로 나눈다. 모델 드롭다운 옆에 **명시적 토글**을 둔다(자동 추론 아님).

| 모드 | 누가 그림 | 한글 텍스트 | 특성 |
|---|---|---|---|
| `per-card` (기존+A+B) | CLI가 카드별 SVG | 앱이 오버레이(편집 가능) | 안전·편집성 높음, 레이아웃 고정 |
| `poster` (신규 C) | CLI가 카드뉴스 HTML 전체 | CLI가 DOM 텍스트로 | 가장 LLM다움, 편집성 낮음 |

`local` provider는 항상 `per-card` 템플릿(CLI 호출 없음). `poster` 모드는 CLI provider일 때만 활성.

### 4.A 실패 가시화

- `VisualImageMetadata`에 출처 필드 추가: `source: "llm" | "fallback" | "template"`.
  - `_llm_asset_svg()`가 실제 LLM SVG를 받으면 `llm`, 타임아웃/비SVG로 스케치 대체 시 `fallback`.
  - `local`/비CLI 경로는 `template`.
  - 기존 `generated: bool`은 호환 위해 유지하되 의미를 "이미지 파일이 만들어짐"으로 좁히고, 신규 `source`가 진짜 출처를 표현.
- `_llm_asset_svg()`가 폴백할 때 사유(timeout / no-svg / unsafe)를 카드 메타데이터 또는 응답에 누적.
- GUI:
  - `ReportVisualCardPreview`/`ReportVisualCardsPanel`에 카드별 배지("모델 생성" vs "폴백 — 모델 실패").
  - `ReportVisualCardsCompanion` 상단에 집계 알림("N장 중 M장 폴백됨, 사유: …").
  - 현재 비-ok status가 전체 요청을 실패(`_fail`)시키는 동작은 유지하되, 부분 폴백은 요청 성공으로 두고 표시.

### 4.B 풍부한 SVG 프롬프트

- `_svg_prompt()` 교체: "simple / under 80 elements / geometric only" 제약 제거.
  디테일·레이어·면 채움·그라데이션·그림자가 있는 일러스트를 요구.
- **유지(보안 불변식)**: 단일 `<svg>`만, `<text>`/Korean/Latin 텍스트 금지, `<script>`/`<foreignObject>` 금지,
  외부 URL/href/이벤트핸들러 금지, `viewBox 0 0 320 150`. sanitizer(`_extract_safe_svg`/`_sanitize_svg`/`_has_external_url`) 그대로.
- 요소 수 상한은 완화하되 과도한 응답 방지를 위해 상식적 상한(예: 길이 기반) 유지.
- 리치 SVG는 더 오래 걸리므로 `_ASSET_TIMEOUT_SECONDS` 상향(예: 90→120s) 검토. 동시 요청 수(`_MAX_CONCURRENT_ASSET_REQUESTS`)는 유지.

### 4.C 전체 포스터 통째 생성

- 형식: **HTML** (SVG 아님). 카드뉴스는 읽히는 한글이 필수인데 SVG 경로는 `<text>`를 strip하므로 부적합.
  HTML이면 한글이 DOM 텍스트로 안 깨지고, CLI(특히 Claude)가 가장 잘하는 출력.
- 기존에 export만 되던 `claude-html-prompt.md` 로직을 실제 in-app CLI 호출로 승격.
- 신규 모듈 `vibelign/core/reporting_cli/report_card_news_poster.py`:
  - 입력: 스토리보드(payload + cards), provider, root, runner, timeout.
  - CLI 프롬프트: "스토리보드 JSON으로 단일 파일 반응형 한국어 카드뉴스 HTML 생성. 한글은 DOM 텍스트,
    각 카드 본문에 CSS/inline-SVG 도식, 외부 스크립트/이미지/CDN 금지, 모바일에서 겹침/잘림 없음."
  - 응답에서 HTML 추출 + **HTML sanitizer**(신규):
    - 제거: `<script>`, `on*=` 이벤트핸들러, 외부 URL(`http://`/`https://`/`//`), `<iframe>`, `<link>`,
      `<object>`/`<embed>`, `<base>`.
    - 허용: inline `<style>`, inline SVG, data-URL 이미지는 금지(용량/추적 회피, 단순화). 네트워크 0 보장.
    - 추출 실패/위험 → `render_card_news_html()`(기존 결정론적 포스터)로 폴백 + `source:"fallback"` 표시.
  - 저장: 기존 카드뉴스 결과물 폴더(`.vibelign/reports/card-news/...`) 안으로만(경로 containment 재사용).
- 렌더/프리뷰: GUI는 **sandbox iframe**(`sandbox`, allow-scripts 없음)로 표시.
- `vib_report_runtime.py:_visual_cards()`에 모드 분기 추가. 신규 CLI 인자 `--card-news-mode {per-card|poster}`.

## 5. 손대는 파일

### 백엔드 (Python)

- `vibelign/core/reporting_cli/report_card_news_asset_generator.py` — 풍부한 `_svg_prompt`(B), 출처 구분(A), 타임아웃 상향(B).
- `vibelign/core/reporting_cli/report_visual_cards.py` (+ `report_card_news_payload.py`) — `VisualImageMetadata.source` 필드(A).
- `vibelign/core/reporting_cli/report_card_news_poster.py` — **신규**: 전체 HTML 포스터 CLI 생성 + HTML sanitizer(C).
- `vibelign/commands/vib_report_runtime.py` — `_visual_cards()` 모드 분기(C).
- 카드뉴스 CLI 인자 정의(`vib_report_card_news_cmd.py` / 관련 arg) — `--card-news-mode` 추가(C).

### GUI (TypeScript/React)

- `vibelign-gui/src/lib/vib/reportVisualCards.ts` — `requestReportVisualCards`에 mode 인자, 응답에 source/poster 파싱.
- `vibelign-gui/src/components/plan-doc/ReportVisualCardsCompanion.tsx` — 모드 토글(A·C), 폴백 집계 알림(A), 포스터 sandbox iframe 프리뷰(C).
- `vibelign-gui/src/components/plan-doc/ReportVisualCardPreview.tsx` / `ReportVisualCardsPanel.tsx` — 카드별 출처 배지(A).

기존 앵커 경계(`ANCHOR: *_START/_END`)를 지키고, 파일 전체 재작성 금지(프로젝트 규칙 준수).

## 6. 데이터 흐름

```
[GUI] 모델 드롭다운 + 모드 토글
   │  requestReportVisualCards(cwd, planPath, type, provider, mode)
   ▼
vib report ... --visual-cards --visual-card-cli {provider} --card-news-mode {mode} --json
   ▼
_visual_cards():
   ├─ mode=per-card → CliVisualCardsProvider.draft() → materialize_card_news_assets()
   │     └─ 카드별 _llm_asset_svg() (풍부 프롬프트, 출처 기록)  ──► asset_path + source
   └─ mode=poster   → report_card_news_poster.generate() (CLI HTML + sanitize)  ──► poster_html + source
   ▼
[GUI] per-card: 패널 + 출처 배지 + 폴백 알림 / poster: sandbox iframe 프리뷰
   ▼
확정(finalize) → 기존 export 경로
```

## 7. 에러 처리 / 보안 불변식

- CLI 미설치(`build_cli_command`→None): 명확한 에러 메시지(기존 동작).
- 타임아웃/비SVG/비HTML(=형식 불일치): 카드별/포스터 결정론적 폴백 + `source:"fallback"` 가시화(A). 전체 요청 실패시키지 않음(부분 폴백 허용).
- 단, CLI 실행 자체 실패(비-ok status, 프로세스 크래시)는 폴백이 아니라 명확한 에러로 노출(기존 동작 유지).
- SVG: 기존 sanitizer 불변식 유지(텍스트/스크립트/외부URL 금지).
- HTML(C): script/이벤트핸들러/외부 리소스/iframe/link 제거, 네트워크 0, 프로젝트 폴더 내부 저장만, 프리뷰는 sandbox iframe.

## 8. 테스트 전략

### Python (pytest)

- 풍부 프롬프트: `_svg_prompt`가 금지 토큰("under 80", "geometric shapes only")을 더 이상 포함하지 않고
  디테일 요구 문구를 포함하는지.
- 출처 구분: fake `PlanningCliRunner` 주입으로 (a) 정상 SVG→`llm`, (b) 타임아웃→`fallback`,
  (c) 비SVG→`fallback`, (d) local→`template` 검증.
- 포스터(C): fake runner가 (a) 정상 HTML→sanitized 저장, (b) script/외부URL 포함 HTML→제거 확인,
  (c) 추출 실패→결정론적 포스터 폴백.
- 경로 containment: 포스터/asset 저장이 프로젝트 밖을 가리키면 거부.

### GUI (vitest)

- 모드 토글 렌더 및 `requestReportVisualCards`에 mode 전달.
- 카드별 출처 배지(llm/fallback/template) 렌더.
- 폴백 집계 알림 표시.
- 포스터 모드에서 sandbox iframe(no allow-scripts) 렌더.

## 9. 비목표 (YAGNI)

- 이미지 생성 API 연동(사용자 제외).
- 래스터 이미지 생성/저장.
- data-URL/외부 이미지 임베딩(보안·단순화 위해 제외).
- 모드 자동 추론(명시적 토글로 충분).

## 10. 열린 질문 (구현 계획에서 확정)

- `--card-news-mode` 인자명/기본값(기본 `per-card` 제안).
- 포스터 HTML 프리뷰를 finalize 전 임시 렌더로 보여줄지, finalize 후 파일로만 열지.
- 타임아웃 상향 폭(120s? provider별 차등?).
