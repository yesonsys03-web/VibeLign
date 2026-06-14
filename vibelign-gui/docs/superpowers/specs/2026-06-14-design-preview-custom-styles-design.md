# 디자인 미리보기 — 클로드 스타일 합성(커스텀 디자인) 설계 스펙

- 날짜: 2026-06-14
- 대상: `vibelign-gui` (프론트 `DesignPreview.tsx`·`styles.ts`·`vib/design.ts` / 백엔드 `commands/design_preview.rs`)
- 상태: 설계 확정 대기(사용자 리뷰)

## 1. 배경 / 문제

디자인 미리보기는 현재 **고정 5개 프리셋**(`DESIGN_STYLES`)만 제공한다. 사용자가 더 다양한 디자인을 원해도 선택지가 5개로 묶여 있다.

핵심 관찰:
- 생성 엔진 `generate_design_mockup`은 **임의의 `StyleSpec`(토큰+recipe+motion)을 받아 HTML을 생성**한다. 5개라는 제약은 **프론트 목록**뿐이고 엔진은 무제한이다.
- 확정 시 `onConfirm({ mockupPath, tokens, motion })` 로 **토큰이 코딩 스캐폴드에 바인딩**된다(결정적 일치). → 커스텀 스타일도 **진짜 토큰 객체**가 있어야 바인딩이 성립한다. 단순 자유텍스트로는 부족.
- 초보는 "테크노·네온" 같은 디자인 용어를 모른다 → **일상어를 전문 StyleSpec으로 번역**하는 책임을 클로드가 져야 한다.

## 2. 목표 / 비목표

**목표**
- 사용자가 **일상어 묘사** 또는 **프리셋 변형 한마디**로 새 디자인을 만들 수 있다(용어 몰라도 OK).
- 클로드가 그 의도를 **유효한 `StyleSpec`(팔레트 토큰 + recipe + motion + 이름)으로 합성**하고, 기존 엔진으로 렌더한다.
- 합성 결과를 **"이런 스타일을 만들었어요"(이름·팔레트·설명)** 로 보여준다.
- 만든 커스텀 스타일을 **저장·재사용**(다음에 프리셋과 함께 목록에 표시).
- 빈 입력창 막막함을 **예시 칩**으로 해소.

**비목표**
- 가이드 객관식 선택지(분위기/색감/용도 픽커) — 이번 범위 제외(사용자 결정).
- 토큰 수동 색피커 편집기 — 제외(클로드 합성으로 충분).
- 커스텀 스타일 공유/마켓플레이스 — 제외.
- 기존 HTML 생성·sandbox·확정·바인딩 파이프라인 변경 — **무변경 재사용**.

## 3. 설계

### 3-1. 아키텍처 — 신규는 "스타일 합성" 1단계뿐

```
[일상어 묘사]  또는  [프리셋 + "이렇게 바꿔줘"]
        │
        ▼  ✦ 신규: synthesize_style (Claude)
   StyleSpec JSON (id·name·description·tokens·recipe·motion)  → 검증
        │
        ▼  기존 그대로: generate_design_mockup(StyleSpec)
        HTML 목업 → sandbox iframe 미리보기
        │
        ├─ "이 스타일 저장하기" → ✦ 신규: save_custom_style (영속)
        └─ "이 디자인으로 만들기" → 기존 confirm(토큰 바인딩)
```

생성은 **2-콜**(합성→목업)이 된다. 합성은 짧은 JSON이라 가볍고, 프롬프트 해시 캐시로 중복 제거.

### 3-2. 데이터 모델

- `StyleSpec`(기존, `styles.ts`): `{ id, name, description, tokens: DesignTokens, recipe, motion? }` — **그대로 사용**. 합성 결과도 이 타입.
- 커스텀 스타일 저장소: **프로젝트 로컬** `.vibelign/design_preview/custom-styles.json` = `StyleSpec[]`. (디자인 미리보기는 projectDir 기준이므로 프로젝트별 보관이 자연스럽다.)
- 합성 스타일 id 규약: `custom-<짧은해시>` (클로드가 임의 id를 주더라도 백엔드가 `is_safe_style_id` 통과하도록 정규화/재발급).

### 3-3. 백엔드 (`commands/design_preview.rs` + `lib.rs` 등록)

**신규 `synthesize_style`**
- 입력: `{ project_dir, plan_path, description: String, base_style: Option<StyleSpec> }`
- `build_synthesis_prompt(spec_md, description, base_style)`: 기획안 맥락 + 사용자 일상어 묘사(+있으면 baseStyle의 토큰/recipe를 "이 스타일을 변형" 기준으로) 를 주고, **지정 JSON 스키마(StyleSpec)로만** 응답하도록 지시.
- LLM 호출: 기존 `planning_persona::run_design_generation(dir, &prompt)` 재사용(원시 텍스트 반환) → JSON 파싱.
- 검증 `validate_style_spec(spec)`:
  - `tokens` 각 색상 필드(bg/surface/text/primary/accent)는 허용 CSS 색 패턴(`#hex`, `rgb()/rgba()`, 명명색)만 — 따옴표·`;`·`{}`·`url(`·`expression(`·`</` 등 인젝션 토큰 거부.
  - `radius`/`border`/`shadow`/`fontFamily`도 길이 제한 + 위 금지 토큰 거부(이미 `tokens_to_css_vars`로 CSS 변수에 들어가므로 방어 필수).
  - `recipe`·`description` 길이 상한(예: 각 1–2KB).
  - `id`는 `is_safe_style_id` 통과하도록 `custom-<design_cache_key 앞 8자>`로 재발급.
- 캐시: 합성 프롬프트 → `design_cache_key` → `.vibelign/design_preview/synth-<key>.json`.
- 반환: 검증된 `StyleSpec`.

**신규 `save_custom_style`**
- 입력: `{ project_dir, style: StyleSpec }`
- `validate_style_spec` 재검증 → `custom-styles.json` 로드 → 같은 id면 교체, 아니면 append(상한 예: 50개) → 원자적 쓰기.

**신규 `list_custom_styles`**
- 입력: `{ project_dir }` → `custom-styles.json` 읽어 `StyleSpec[]` 반환(없으면 `[]`). 손상 시 `[]`로 폴백(앱 안 깨지게).

**(선택) `delete_custom_style`** `{ project_dir, style_id }` — 저장 목록 정리용. 이번 범위 포함(작음).

기존 `generate_design_mockup`/`save_design_mockup`/`build_mockup_prompt`/`validate_mockup_html`은 **무변경**.

### 3-4. 프론트 (`vib/design.ts` + `DesignPreview.tsx`)

`vib/design.ts` — invoke 래퍼 추가: `synthesizeStyle`, `saveCustomStyle`, `listCustomStyles`, `deleteCustomStyle`.

`DesignPreview.tsx` UX:
```
[ 프리셋 그리드 ]  = 내장 DESIGN_STYLES + 저장된 커스텀(배지·삭제버튼)   ← 마운트 시 listCustomStyles 로 병합
─────────────────────────────────────────────
✏️ 직접 만들기
   [ 어떤 느낌이면 좋겠어요?  ___________________ ]
   예시 칩(클릭→입력칸 채움): (귀엽고 파스텔) (신뢰감 있는 업무용)
        (게임처럼 화려한) (단아한 여백) (레트로 감성) …
   → [ 클로드에게 그려달라기 ]
─────────────────────────────────────────────
프리셋 선택 시: [ 이 스타일에서 바꾸기: "더 밝게 / 더 미니멀하게" ___ ] → 변형 생성
```
- 흐름: 입력 → `synthesizeStyle` → **합성 결과 카드 표시("이런 스타일을 만들었어요": 이름·설명·팔레트 스와치 5색·모션 한 줄)** → 자동으로 `generateDesignMockup(합성 StyleSpec)` 호출해 목업 렌더.
- 목업 아래 액션: 기존 "다시 그리기"·"이 디자인으로 만들기" + **신규 "이 스타일 저장하기"**(저장 시 그리드에 추가).
- 변형 모드: 프리셋 선택 상태에서 "바꾸기" 입력 → `synthesizeStyle({ base_style: 선택프리셋, description })`.
- 로딩/에러: 기존 `loading`/`error` 패턴 재사용(합성 단계·목업 단계 각각 표시).

### 3-5. 합성 결과 노출("이런 스타일을 만들었어요")
합성 `StyleSpec`에서 `name`·`description`·`tokens`(bg/surface/text/primary/accent 스와치)·`motion?.recipe`를 작은 카드로 렌더. 사용자가 클로드가 무엇을 만들었는지 즉시 이해 → 다시 그리기/저장 판단.

## 4. 검증 / 안전
- 합성 JSON은 **반드시 `validate_style_spec` 통과** 후에만 `tokens_to_css_vars`로 들어간다(CSS 인젝션 차단 — 토큰이 `<style>` 변수로 주입되므로 핵심).
- 최종 HTML은 기존 `validate_mockup_html`(외부 리소스·스크립트 차단)이 계속 방어.
- `custom-styles.json`은 경로 고정(projectDir 하위)·원자적 쓰기·손상 시 `[]` 폴백.
- LLM이 스키마를 안 지키면(파싱 실패) 명확한 에러 + 재시도 안내(빈 화면 금지).

## 5. 캐싱 / 비용
- 합성·목업 둘 다 프롬프트 해시 캐시. 같은 묘사/같은 스타일은 재생성 안 함.
- 합성은 짧은 JSON이라 저비용. 2-콜 지연은 수용 범위(로딩 표시).

## 6. 엣지 케이스
- 클로드가 위험 토큰/잘못된 색 반환 → 검증 거부 → 사용자에게 "다시 시도" 안내.
- 커스텀 스타일 id 충돌 → 해시 기반 재발급으로 회피, 저장 시 같은 id 교체.
- `custom-styles.json` 없음/손상 → `[]`(프리셋만 표시).
- 웹 게이트(`isLikelyWeb=false`) → 기존 경고 배너 유지(비차단).
- 저장 상한(50) 초과 → 가장 오래된 것 제거 또는 저장 거부(스펙: 거부 + 안내).

## 7. 테스트
- **순수/단위(우선, vitest·rust)**:
  - `validate_style_spec`: 정상 통과 / 인젝션 토큰(`;`,`</`,`url(`,`expression(`) 거부 / 색 포맷 위반 거부 / 길이 초과 거부. (rust 단위)
  - `is_safe_style_id` 재발급이 항상 안전 id 생성.
  - 합성 프롬프트 빌더가 base_style 있을 때/없을 때 올바른 텍스트 구성(rust).
  - 프론트: 그리드가 내장+커스텀 병합 렌더, 예시 칩 클릭이 입력칸 채움, 합성 결과 카드가 팔레트 스와치 렌더(testing-library, invoke 목).
- **통합/수동**: 일상어 묘사 → 합성 카드 → 목업 렌더 → 저장 → 재진입 시 그리드에 표시 → 확정 바인딩까지. (실호출 1회 검증)

## 8. 영향 범위 / 파일
- Create: 없음(기존 파일 확장). 단 저장소 파일 `.vibelign/design_preview/custom-styles.json`은 런타임 생성.
- Modify:
  - `src-tauri/src/commands/design_preview.rs` — `synthesize_style`/`save_custom_style`/`list_custom_styles`/`delete_custom_style` + `validate_style_spec` + `build_synthesis_prompt`.
  - `src-tauri/src/lib.rs` — 신규 커맨드 등록.
  - `src/lib/vib/design.ts` — invoke 래퍼 4종.
  - `src/pages/DesignPreview.tsx` — 자유입력·예시칩·변형·합성결과카드·저장·커스텀 병합.
  - (선택) `src/lib/design-preview/styles.ts` — 예시 칩 시드 상수(또는 DesignPreview 내 상수).
- 무변경: `generate_design_mockup`·`save_design_mockup`·`build_mockup_prompt`·`validate_mockup_html`·확정/바인딩.
