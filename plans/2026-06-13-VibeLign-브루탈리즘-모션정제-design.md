# VibeLign 자체 UI — 브루탈리즘 모션 정제 — 설계

> 작성 2026-06-13 · 사용자와 단계별 합의
> 출처: [[vibelign_design_skill_directions]] 트랙 3(VibeLign 자체 UI 리스타일) · animations.dev 모션 어휘 적용
> 선행: 디자인 프리뷰 PR A·모션 차원·PR B(완료). 본 트랙은 디자인 프리뷰가 아니라 **VibeLign 자체 GUI**를 다듬는다.

## 0. 한 줄 정의

**brutalism.css에 흩어진 모션 타이밍을 모션 토큰으로 통일하고, `.btn`에만 있던 "하드그림자 눌림" 인터랙션을 인터랙티브 공유 클래스(nav·클릭형 카드·입력 focus)에 일관 적용하며, `prefers-reduced-motion`을 전면화한다 — brutalism.css 단일 파일 수정으로 앱 전체에 전파, 컴포넌트 파일은 건드리지 않는다.**

## 1. 확정 결정 (세션 합의 이력)

| 결정 | 선택 | 기각 대안 · 이유 |
|---|---|---|
| 리스타일 방향 | **현 브루탈리즘 정제·폴리시** | 새 미감 피봇(구조 재작업↑) · 자체 독푸딩(전체 CSS를 StyleSpec서 파생, 큰 리팩터) — 둘 다 과함. 정제가 안전·점진·기존 구조 재사용 |
| 첫 슬라이스 영역 | **모션 체계화 + reduced-motion** | 스페이싱 스케일·컴포넌트 마감 — 각각 더 넓은 sweep. 모션이 가장 눈에 띄고 공유 클래스 수준에서 바운드됨 + 실제 접근성 갭(reduced-motion 1곳) 메움 |
| 적용 레벨 | **brutalism.css 공유 클래스만** | 컴포넌트 파일 개별 수정 — 100+ 파일 sweep, 위험·비효율. 공유 클래스 정제가 앱 전파 |

## 2. 현황 (코드 기준, 2026-06-13)

- `brutalism.css` 536줄, `:root` CSS 변수 기반(색·border·shadow 토큰 존재). **스페이싱·모션 토큰은 없음.**
- 모션 18곳 중 대부분 마스코트/가이드 레이어(6 keyframes: spin·popbubble·suckbubble·mascot-rollin·guide-pulsering·guide-nudge).
- `prefers-reduced-motion`: **1곳**(접근성 갭).
- `.btn`(82-101)은 이미 브루탈리즘 시그니처: `transition: transform 0.05s, box-shadow 0.05s` + `:hover translate(2px,2px)+--shadow-sm` + `:active translate(4px,4px)+shadow none`. **단 하드코딩 0.05s**(토큰 아님).
- 공유 클래스: `.btn`·`.card`·`.feature-card`·`.nav-tab`·`.input-field`·`.badge` 등.

## 3. 설계

### 3.1 모션 토큰 (`:root`에 추가)
```css
--dur: 60ms;                      /* 현 .btn 0.05s 근접, 딱딱·즉각 */
--dur-pop: 140ms;                 /* 등장/펄스용 */
--ease: cubic-bezier(.2, 0, 0, 1);/* 각진 즉각 — 모션트랙 네오브루탈리즘과 동일 성격 */
```

### 3.2 기존 타이밍 토큰화
하드코딩된 `0.05s` 류 전환을 `var(--dur) var(--ease)`로 교체(`.btn`, `.btn-sm` 등). **동작 동일**, 일관성·향후 조정 한 곳에서.

### 3.3 시그니처 모션 확장 (인터랙티브 표면만)
`.btn`의 눌림 패턴을 인터랙티브 공유 클래스에 일관 적용:
- `.nav-tab`: hover 시 1~2px 이동 + 그림자 축소, active 눌림. 선택 탭은 눌린 상태 유지 가능.
- 클릭형 `.card`/`.feature-card`(인터랙티브한 것만): hover 시 1~2px 이동 + 그림자 축소.
- `.input-field`: `:focus-visible`에 굵은 하드 아웃라인(브루탈리즘답게, 색=`--primary` 또는 `--black`).
- **비인터랙티브 정보 카드는 제외** — "맞는 것만"(과한 움직임 방지).

### 3.4 prefers-reduced-motion 전면
```css
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
  }
}
```
기존 마스코트/가이드 keyframe도 이 전역 가드로 자동 완화.

## 4. 범위 / 안전

- **brutalism.css 단일 파일** 수정. 컴포넌트 `.tsx` 0개 수정.
- `.btn` 기존 동작 보존(토큰화는 시각·동작 동일 — 0.05s≈60ms 미세차만).
- 마스코트/가이드 keyframe·동작 유지(reduced-motion 가드만 추가 적용).
- 비인터랙티브 카드 미변경(과한 모션 방지).

## 5. 검증

- **빌드**: `npm run build`(vite) 또는 `tsc` + 앱 실행(`npm run tauri dev`).
- **육안(앱 실행)**:
  - 버튼·nav·클릭형 카드 hover/press가 일관된 브루탈리즘 눌림
  - 입력 focus-visible 하드 아웃라인
  - OS "동작 줄이기" 켜면 모든 모션·마스코트 애니메이션 정지/즉각
  - 기존 `.btn` 인터랙션 회귀 없음(눌림 그대로)
- CSS는 단위테스트 부적합 → 육안 + (가능하면) 스냅샷/시각 회귀.

## 6. 미결 (구현 중 확정)
| 항목 | 메모 |
|---|---|
| `--dur` 정확값 | 60ms vs 80ms — 육안 후. 현 .btn 0.05s 보존 우선이면 50~60 |
| focus-visible 아웃라인 스펙 | 굵기(2~3px)·색(--primary vs --black)·offset — 육안 |
| 인터랙티브 카드 식별 | `.card`/`.feature-card` 중 클릭 가능한 것만. 마크업 확인 필요(클래스 추가 vs 셀렉터 한정) |

## 7. 후속 (범위 밖)
- 스페이싱 스케일 토큰(`--space-*`) 도입 + 적용
- 컴포넌트 마감 일관성(상태·정렬·포커스 통일, component.gallery 참조)
- 등장 모션 확대(패널 mount pop 등)
