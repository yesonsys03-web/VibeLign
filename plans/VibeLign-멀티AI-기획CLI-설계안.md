# VibeLign 멀티 AI 기획 CLI 설계안

작성일: 2026-05-31
목표: 코알못이 Markdown을 몰라도 바이브코딩 전에 AI가 이해할 수 있는 기획안을 만들게 한다.

---

## 1. 핵심 결정

새 명령은 `vib plan`으로 만든다.

```bash
vib plan "동네 카페 예약 앱을 만들고 싶어"
```

기존 `vib plan-structure`는 새 `vib plan`/기획방의 사용자 흐름에서 제외한다.
UI에서는 완전히 숨겨도 된다. 기존 내부 구현은 이번 범위에서 삭제하거나 완성하지 않는다.

| 명령 | 역할 | 결과물 |
|---|---|---|
| `vib plan` | 제품/기능 기획안 생성 | `plans/{slug}.md` |
| `vib plan-structure` | 레거시 내부 구조 계획 보조 기능. 새 기획방/초보 UI에 노출하지 않음 | `.vibelign/plans/{id}.json` |

이 기능은 CodeSpeak, patch 지시문, 코드 수정 명령을 만들지 않는다. 목적은 "AI에게 줄 기획안"을 만드는 것이다.

`vib plan` CLI는 **사용자가 처음 만나는 면이 아니다**. 1차 사용자 표면은 **GUI 기획방의 ChatGPT 스타일 입력 바**다 (통합기획안 §4-1, §9-0-1 참조). 같은 백엔드 엔진을 GUI가 호출하고, CLI는 그 엔진을 터미널에서도 부를 수 있게 하는 부산물로 둔다.

이 문서가 정의하는 것은 (a) 멀티 페르소나 기획 엔진 자체와 (b) 엔진의 두 진입점 — GUI 입력 바·CLI 명령 — 이다. 구현 순서는 통합기획안 §11 우선순위와 §12 PR 1~9을 따른다. 진실 기준은 온보딩 화면 수정 → plan 기능 → Home 정리 → 기존 기능 제거 준비 순서다:

```text
PR 1: 온보딩 ChatGPT 입력 바 (기존 카드 전부 제거)
PR 2: 자동 start + 5단계 진행 + Claude Code 체크박스
PR 3: 기획 엔진 + 입력 바 → 기획방 정적 전환 (CLI 진입점은 `vib plan --template-only`로 검증)
PR 4: 첫 CLI 페르소나 스파이크 + 실제 응답 — 본인 v1 dogfood 시작
PR 5: 나머지 adapter 추가 + 3 페르소나 순차 best-effort + mention 라우팅
PR 6: 기존 Home 화면 정리
PR 7: patch/CodeSpeak/plan-structure legacy 숨김과 제거 준비
PR 8: 자동 watch/anchor/guard 정밀화 + 에러 인간화
PR 9: 페르소나 캐릭터 커스터마이즈 + 점진적 공개
```

> 진실 기준은 통합기획안 §12의 PR 1~9다. 이 문서의 PR 목록은 그 요약이며, 충돌 시 통합기획안 §12를 따른다.

CLI 진입점 검증은 PR 3에서 `vib plan --template-only`로 수행하고, 사용자에게 노출하는 면은 항상 GUI다.

---

## 2. 사용자 경험

### 기본 흐름 (GUI 우선)

```text
사용자: 온보딩 첫 화면의 입력 바에 "예약 앱 만들고 싶어" 입력 후 ● 전송

VibeLign:
1. 입력 바가 기획방 화면으로 자연 전환된다.
2. 쉬운 질문 3~5개를 채팅으로 던진다.
3. 답변을 바탕으로 기획안 초안을 만든다.
4. 설계자 클로이, 검토자 지오, 탐색자 미나가 채팅에 등장해 서로 다른 관점으로 검토한다.
5. 검토 결과를 합쳐 최종 Markdown 기획안을 만든다.
6. plans/{slug}.md 에 저장한다.
```

CLI 진입점 (엔진 검증/터미널 사용자용, 사용자에게 마케팅 안 함):

```text
사용자: vib plan "예약 앱 만들고 싶어"
       (GUI와 동일한 백엔드 엔진을 호출, 결과 동일)
```

### 초보자에게 보여줄 말

```text
기획안을 만들었어요.
이 파일을 AI에게 보여주면 더 정확하게 작업을 시작할 수 있어요.

저장 위치: plans/cafe-reservation-plan.md
```

사용자는 Markdown 문법을 직접 입력하지 않는다.

### GUI 채팅방

`vib plan`의 CLI 기능은 먼저 만들지만, 제품의 실제 락인은 채팅 UI에서 생긴다. GUI에서는 모델 선택 화면이 아니라 "기획방"을 보여준다.

화면 구조:

```text
기획방

나
카페 예약 앱을 만들고 싶어

설계자 클로이 · Claude Code
예약 앱의 목적과 사용자 흐름을 먼저 정리할게요.

검토자 지오 · Codex
예약 취소 정책과 관리자 권한이 아직 정해지지 않았어요.

탐색자 미나 · Antigravity
처음에는 예약 신청과 승인만 MVP로 두는 게 좋아요.

VibeLign 정리
기획안을 만들었어요.
[기획안 보기] [AI 작업 시작]
```

호출 입력:

```text
@클로이 초안 만들어줘
@지오 빠진 점 검토해줘
@미나 더 쉬운 MVP로 줄여줘
@모두 이 기획안 검토해줘
```

UI 원칙:

- 모델명보다 페르소나 이름을 먼저 표시한다.
- 연결 CLI 상태는 보조 정보로 작게 표시한다.
- CLI raw log는 기본 숨김이고, 실패 시 "자세히 보기"에서만 보여준다.
- 최종 Markdown 원문은 기본 편집 화면이 아니라 "기획안 보기" 뒤에 둔다.
- 메시지는 말풍선보다 업무용 타임라인에 가깝게, 조밀하고 읽기 쉽게 구성한다.

기획방 시각 스타일:

- 레퍼런스 repo: <https://github.com/unclejobs-ai/satgat> (이 repo 안에 없는 외부 자산이므로, 구현 착수 시 색·간격·타이포 토큰과 채팅 화면 스크린샷을 `vibelign-gui` 안에 박제하거나 링크를 코드 주석에 남긴다.)
- `satgat`의 한국형 문서 톤을 채팅방 레퍼런스로 삼는다: 백자지 계열 배경, 먹색 본문, 단청색 포인트, 명조/돋움 대비.
- `satgat` 화면을 그대로 복제하지 않는다. 문서 출력 화면이 아니라 입력·응답·저장 상태가 빠르게 읽히는 작업실 UI로 변형한다.
- 배경은 따뜻한 종이색으로 두되, 채팅 영역은 카드처럼 과하게 떠 보이지 않게 하고 문서 위에 기록이 쌓이는 느낌을 준다.
- 단청색 포인트는 전송 버튼, 중요한 상태, 최종 `[기획안 보기]`/`[AI 작업 시작]` 버튼에만 제한적으로 쓴다.
- 메시지별 장식보다 읽기 밀도와 스캔성을 우선한다. 큰 여백, 한자 장식, 인쇄물 샘플 같은 장식은 초보 기획 흐름을 방해하면 쓰지 않는다.

OpenDesign 판단:

- OpenDesign는 Claude Design의 유료 대안으로 참고할 수 있는 오픈 디자인 자산으로 사용한다.
- 1차 구현에서 OpenDesign을 런타임 UI 라이브러리 의존성으로 추가하지 않는다.
- `satgat` 스타일을 1차 채팅방 레퍼런스로 삼고, `DESIGN.md`, 토큰, 채팅 화면 레퍼런스, anti-pattern 체크리스트는 보조 기준으로 사용한다.
- 현재 GUI는 React/Vite/Tauri 기반이므로 실제 구현은 VibeLign 내부 React 컴포넌트로 만든다.
- 유료 Claude Design이 없어도 동일한 UX 기준을 유지할 수 있어야 한다.

### 페르소나 캐릭터 커스터마이즈

기본 캐릭터를 제공하되, 사용자가 자기만의 페르소나 캐릭터를 쉽게 만들 수 있게 한다. 이 기능은 단순 장식이 아니라 "내 AI 팀"을 만드는 락인 장치다.

1차 초보 UX:

```text
내 AI 팀 꾸미기

이름: 클로이
역할: 설계자
색상: 민트
분위기: 차분함
상징: 노트

[캐릭터 만들기]
```

초보 모드에서는 sprite-gen을 바로 실행하지 않고, 준비된 base sprite set을 조합한다.

- 이름 변경
- 색상 preset 변경
- 역할 배지 변경
- 상태별 frame 선택
- idle/thinking/writing/done 애니메이션 선택

고급 모드에서는 sprite-gen을 사용한다.

- sprite request 생성
- image-gen으로 state row 생성
- sprite-gen frame extraction 실행
- curation webview에서 frame 검수
- 승인된 atlas와 manifest만 VibeLign persona asset으로 등록

저장 계약:

```text
.vibelign/personas/{persona_id}/persona.json
.vibelign/personas/{persona_id}/sprite-sheet-alpha.png
.vibelign/personas/{persona_id}/manifest.json
```

기본 캐릭터 asset:

```text
vibelign-gui/src/assets/personas/default/chloe/
vibelign-gui/src/assets/personas/default/gio/
vibelign-gui/src/assets/personas/default/mina/
```

원칙:

- 앱 실행 때마다 sprite-gen을 실행하지 않는다.
- 사용자가 명시적으로 "캐릭터 만들기"를 눌렀을 때만 생성한다.
- 실패해도 기획 기능은 계속 동작한다.
- 기본 캐릭터가 항상 fallback으로 존재한다.
- 캐릭터는 32~48px 상태 아바타로 사용하고, 메시지 내용보다 튀지 않게 한다.

---

## 3. CLI 계약

> **읽는 순서 주의**: §3~§9 본문은 이 기능을 CLI-first로 처음 설계했을 때의 상세 계약이 그대로 남아 있다(historical). 현재 진실 기준은 §1·통합기획안 §4-1/§9-0-1 — **1차 사용자 표면은 GUI 기획방 입력 바이고 `vib plan` CLI는 같은 엔진을 부르는 부산물**이다. 따라서 아래 CLI 계약(옵션·대화형 흐름)은 엔진 검증 진입점(PR 3 `--template-only`)과 터미널 사용자용으로 구현하되, **사용자에게 마케팅하는 1차 흐름으로 만들지 않는다.** 구현 착수 시 §1 → 통합기획안 §12 PR 순서부터 읽고, §3~§9는 엔진/계약 참조로 본다.

### 명령

```bash
vib plan [idea...]
```

### 옵션

| 옵션 | 기본값 | 의미 |
|---|---:|---|
| `--agents chloe,gio,mina` | 준비된 agent 자동 선택 | 부를 페르소나 순서 |
| `--cli claude,codex,antigravity` | 자동 탐지 | 사용할 공식 CLI 순서 |
| `--rounds 1` | `1` | draft/review/synthesis 반복 횟수 |
| `--output plans/name.md` | 자동 slug | 최종 기획안 저장 경로 |
| `--language auto` | `auto` | 출력 언어. `auto`, `ko`, `en` 지원 |
| `--template-only` | false | AI CLI 호출 없이 로컬 템플릿만 생성 |
| `--review-only path.md` | 없음 | 기존 기획안을 페르소나들이 검토하고 개선 |
| `--save-transcript` | false | 페르소나별 채팅 내용을 별도 파일로 저장 |
| `--force` | false | 기존 출력 파일 덮어쓰기 |
| `--yes` | false | round 2 이상에서 추가 CLI 호출 확인 생략 |
| `--json` | false | 결과를 JSON으로 출력 |

### 입력이 없을 때

```bash
vib plan
```

입력이 없으면 대화형으로 시작한다.

```text
무엇을 만들고 싶나요?
```

---

## 4. 생성 파일 계약

### 최종 기획안

경로:

```text
plans/{slug}.md
```

필수 섹션:

```markdown
# {프로젝트 또는 기능 이름}

## 한 줄 목표

## 만들고 싶은 이유

## 대상 사용자

## 핵심 기능

## 화면 또는 사용 흐름

## 제외할 것

## 아직 결정이 필요한 질문

## 구현 전에 AI가 알아야 할 맥락

## 다음 단계
```

### 메타데이터

요약 메타데이터 경로:

```text
.vibelign/planning/{session_id}.json
```

세션 상세 경로:

```text
.vibelign/planning/{session_id}/session.json
```

필드:

| 필드 | 의미 |
|---|---|
| `id` | planning session id |
| `idea` | 최초 사용자 입력 |
| `answers` | CLI 질문 답변 |
| `agents_requested` | 사용자가 요청한 페르소나 |
| `agents_used` | 실제 응답한 페르소나 |
| `cli_used` | 실제 실행된 공식 CLI |
| `fallback_reason` | fallback이 발생한 이유 |
| `output_path` | 최종 Markdown 경로 |
| `language` | 출력 언어 |
| `review_summary` | 페르소나별 검토 요약 |
| `created_at` | 생성 시각 |

메타데이터는 항상 저장한다. 단, 페르소나 원문 응답 전문은 기본 저장하지 않고 요약과 상태만 저장한다.

### 세션/턴/실행 ID 계약

각 LLM이 자체적으로 응답 ID를 붙일 수는 있지만, VibeLign은 그 ID에 의존하지 않는다. 안정적인 구분 기준은 VibeLign이 CLI 호출 전에 직접 발급하는 ID다.

ID 계층:

| ID | 예시 | 의미 |
|---|---|---|
| `session_id` | `plan_20260531_abc123` | 하나의 기획 세션 |
| `turn_id` | `turn_001` | 채팅방의 한 응답 단위 |
| `run_id` | `run_claude_001` | 실제 CLI subprocess 실행 단위 |
| `persona_id` | `chloe` | 페르소나 |
| `cli_id` | `claude` | 호출한 공식 CLI |

저장 구조:

```text
.vibelign/planning/{session_id}/session.json
.vibelign/planning/{session_id}/turns/turn_001_claude.md
.vibelign/planning/{session_id}/turns/turn_002_codex.md
.vibelign/planning/{session_id}/turns/turn_003_antigravity.md
.vibelign/planning/{session_id}/final.md
```

`session.json` 예시:

```json
{
  "session_id": "plan_20260531_abc123",
  "idea": "카페 예약 앱을 만들고 싶어",
  "turns": [
    {
      "turn_id": "turn_001",
      "run_id": "run_claude_001",
      "persona_id": "chloe",
      "persona_name": "설계자 클로이",
      "cli_id": "claude",
      "status": "ok",
      "output_file": "turns/turn_001_claude.md"
    }
  ],
  "final_output": "final.md"
}
```

프롬프트에는 보조 marker를 넣는다.

```text
[VIBELIGN_SESSION_ID: plan_20260531_abc123]
[VIBELIGN_TURN_ID: turn_001]
[VIBELIGN_PERSONA_ID: chloe]
```

이 marker는 응답 검증과 디버깅에만 사용한다. 모델이 marker를 빼먹어도 VibeLign의 metadata가 진짜 기준이다.

### 검토 로그

`--save-transcript`를 켰을 때만 생성한다.

```text
plans/{slug}.reviews.md
```

기본값은 생성하지 않는다. 초보자에게 중간 채팅 로그를 먼저 보여주면 복잡해지기 때문이다.

### 파일 충돌 정책

- `--output`이 없고 같은 slug 파일이 있으면 `plans/{slug}-2.md`, `plans/{slug}-3.md`처럼 새 이름을 만든다.
- `--output`이 있고 파일이 이미 있으면 실패한다.
- `--force`가 있으면 지정한 `--output` 파일을 덮어쓴다.

---

## 5. 페르소나와 CLI 역할

> **아키텍처 한 줄 요약 (2 레이어)**
> - **표면 (GUI 채팅창):** 각 모델이 페르소나로 보인다 — 설계자 클로이(Claude) · 검토자 지오(Codex/GPT) · 탐색자 미나(Antigravity/Gemini). 모델명보다 페르소나 이름이 먼저, `@클로이`·`@지오`·`@미나`·`@모두`로 호출.
> - **백그라운드 (relay):** 페르소나 호출 → 매핑된 **공식 CLI를 subprocess로 실행해 stdin/stdout만 채팅창에 중계.** VibeLign은 인증·토큰을 수행·보관·열람하지 않는다(auth-agnostic relay — §13). 인증은 사용자가 터미널에서 이미 해둔 공식 CLI 설정 그대로.
> - **한 줄로:** "사용자가 터미널에서 이미 쓰는 구독 CLI들을 채팅창으로 끌어와 페르소나 팀처럼 부른다."

기본 페르소나:

| 페르소나 | 연결 CLI | 기본 역할 |
|---|---|---|
| 설계자 클로이 | Claude Code CLI | 사용자의 말을 제품 기획안 초안으로 구조화 |
| 검토자 지오 | Codex CLI | 빠진 요구사항, 모순, 구현 가능성, 테스트 기준 검토 |
| 탐색자 미나 | Antigravity CLI | 대안 흐름, MVP 축소안, 범위 조절, 리스크 검토 |
| VibeLign | 내부 정리기 | 세 응답을 합쳐 최종 Markdown 기획안 생성 |

fallback 규칙:

1. 세 CLI가 모두 준비되어 있으면 세 페르소나를 모두 부른다.
2. CLI가 두 개면 준비된 두 페르소나가 초안/검토 역할을 나눠 맡는다.
3. CLI가 하나면 해당 페르소나가 draft/review/synthesis 역할 프롬프트를 순서대로 수행한다.
4. 준비된 CLI가 없거나 `--template-only`면 로컬 템플릿 기획안을 만든다.

초보자 UX에서는 CLI 부족을 실패로 보지 않는다.

탐색자 미나는 품질을 높이는 best-effort reviewer다. Antigravity CLI가 없거나 실패해도 `vib plan`은 실패하지 않는다.

```text
아직 준비된 AI CLI가 없어 기본 템플릿으로 기획안을 만들었어요.
나중에 Claude Code, Codex, Antigravity에 로그인하면 더 꼼꼼하게 검토할 수 있어요.
```

### 채팅창 호출 UX

사용자는 모델명을 고르지 않고 페르소나를 부른다.

```text
@클로이 초안 만들어줘
@지오 빠진 점 검토해줘
@미나 더 쉬운 MVP로 줄여줘
@모두 이 기획안 검토해줘
```

기본 채팅 출력:

```text
나:
카페 예약 앱을 만들고 싶어

설계자 클로이:
예약 앱의 목적과 사용 흐름을 먼저 정리할게요.

검토자 지오:
현재 기획에는 예약 취소 정책과 관리자 권한이 빠져 있어요.

탐색자 미나:
처음에는 예약 신청과 관리자 승인만 MVP로 두는 게 좋아요.
```

### Synthesis owner

최종 synthesis는 다음 순서로 고른다.

1. 설계자 클로이가 있으면 클로이 응답을 기본 초안으로 사용
2. 없으면 검토자 지오 응답을 기본 구조로 사용
3. 없으면 탐색자 미나 응답을 기본 구조로 사용
4. 준비된 CLI가 없으면 local synthesis

단, 최종 파일 쓰기는 항상 `markdown_writer.py`가 수행한다. CLI가 Markdown 파일을 직접 덮어쓰지 않는다.

### 호출 수와 비용

기본 `--rounds 1`에서는 최대 4회 CLI 호출한다.

```text
draft 1회 + review 최대 2회 + synthesis 1회
```

`--rounds 2` 이상은 사용량을 더 소모하므로 실행 전에 한 번 확인한다. `--yes`가 있으면 확인을 생략한다.

### 로그인과 보안 경계

사용자는 GUI에서 자신이 쓰는 AI를 선택만 한다 (통합기획안 §4-1-2). VibeLign이 그 선택을 공식 CLI로 매핑해 설치·로그인 흐름을 대신 띄운다.

```text
Claude 선택   → claude CLI 감지/설치/로그인 흐름
ChatGPT 선택  → codex CLI 감지/설치/로그인 흐름
Gemini 선택   → agy(Antigravity) CLI 감지/설치/로그인 흐름
```

**VibeLign은 인증에 무관(auth-agnostic)하다.** OAuth든 API 키든, 인증은 사용자가 터미널에서 공식 CLI에 이미 해둔 설정이고 VibeLign은 그것을 수행·보관·열람·선택하지 않는다. VibeLign은 공식 CLI를 subprocess로 실행해 stdin/stdout만 relay한다. 미인증이면 사용자가 공식 CLI에서 직접 로그인하도록 안내만 한다(토큰은 공식 CLI가 보관). 로그인 자체는 브라우저 OAuth 등 공식 CLI의 대화형 단계를 거칠 수 있고, 이 자동화 안정성은 §10의 최대 리스크에 포함된다.

### 락인 효과

이 기능은 모델 API가 아니라 VibeLign의 기획 경험에 락인 효과를 만든다.

락인 요소:

- 사용자가 만든 기획안이 `plans/*.md`에 쌓인다.
- 클로이/지오/미나의 역할 분담이 사용자의 사고 방식이 된다.
- 각 AI CLI를 오가며 복사/붙여넣기 하던 검토 루프가 VibeLign 명령 하나로 줄어든다.
- 기획안이 이후 GUI 안전장치와 AI 작업실로 바로 이어진다.
- VibeLign은 특정 모델보다 "여러 구독 CLI를 한 팀처럼 부르는 작업실"이 된다.

핵심:

```text
모델 락인이 아니라 워크플로우 락인이다.
```

---

## 6. 구현 위치

**구현 순서**: 통합기획안 §11 우선순위에 따라 (1) GUI 기획방 컴포넌트 → (2) Python core 엔진 → (3) CLI 진입점 등록 순으로 만든다. 아래 하위 섹션의 등장 순서는 historical하며, 실제 PR 작업 순서가 아니다. 새 작업은 다음과 같이 매핑한다:

| 하위 섹션 | 매핑되는 PR |
|---|---|
| GUI 채팅 컴포넌트 | 통합기획안 PR 1 (입력 바) + PR 3 (기획방 정적 전환) + PR 5 (3 페르소나 mention) |
| 새 core 모듈 | 통합기획안 PR 3 (엔진 골격, template-only) + PR 4 (첫 adapter) + PR 5 (3 adapter + orchestration) |
| 새 command (`vib plan`) | 통합기획안 PR 3 (엔진 검증용 진입점) |
| CLI 등록 | 통합기획안 PR 3 (parser 추가 한 번) |

### CLI 등록

수정 파일:

- `vibelign/cli/cli_command_groups.py`

추가:

- `plan` subcommand
- `lazy_command("vibelign.commands.vib_plan_cmd", "run_vib_plan")`

주의:

- `plan` help 문구는 "기획안 만들기"로 쓴다.
- `vib plan`/기획방 UI와 초보 도움말에서는 `plan-structure`를 비교 대상이나 다음 단계로 노출하지 않는다.
- 기존 `plan-structure` CLI 구현은 이번 범위에서 삭제/개선하지 않는다.

### 새 command

새 파일:

- `vibelign/commands/vib_plan_cmd.py`

책임:

- argparse args 해석
- 프로젝트 루트 확인
- `.vibelign/`와 `plans/` 디렉터리 준비
- 대화형 질문 실행
- orchestrator 호출
- 결과 출력
- `--json` 출력
- `--language`, `--force`, `--yes` 옵션 처리

### 새 core 모듈

새 디렉터리:

- `vibelign/core/planning_cli/`

파일:

| 파일 | 책임 |
|---|---|
| `models.py` | `PlanningInput`, `PlanningDraft`, `PersonaReview`, `PlanningResult` dataclass |
| `ids.py` | `session_id`, `turn_id`, `run_id` 발급과 파일명 매핑 |
| `questions.py` | 초보자 질문 3~5개 생성과 답변 정규화 |
| `prompts.py` | draft/review/synthesis prompt |
| `cli_adapters.py` | Claude Code/Codex/Antigravity CLI adapter |
| `orchestrator.py` | draft → review → synthesis 흐름 |
| `markdown_writer.py` | 최종 Markdown 생성 |
| `storage.py` | `plans/`, `.vibelign/planning/{session_id}/session.json`, `turns/*.md`, `final.md` 저장 |
| `redaction.py` | prompt에 포함될 수 있는 secrets/env/path 민감정보 제거 |

기존 코드 재사용:

- `vibelign/core/project_root.py`
- `vibelign/core/meta_paths.py`
- CLI 실행은 `subprocess.run` 또는 PTY가 필요한 CLI용 wrapper로 분리한다.
- 토큰/세션 파일은 직접 읽지 않는다.

### GUI 채팅 컴포넌트

새 파일 후보:

- `vibelign-gui/src/components/planning/PlanningRoom.tsx`
- `vibelign-gui/src/components/planning/PersonaMessage.tsx`
- `vibelign-gui/src/components/planning/PersonaMentionInput.tsx`
- `vibelign-gui/src/components/planning/PlanningSummaryPanel.tsx`
- `vibelign-gui/src/components/planning/PersonaAvatar.tsx`
- `vibelign-gui/src/lib/planning/personas.ts`
- `vibelign-gui/src/lib/planning/personaAssets.ts`

책임:

- 페르소나별 메시지 렌더링
- `@클로이`, `@지오`, `@미나`, `@모두` mention 입력
- CLI 준비/로그인 상태 표시
- 최종 `plans/*.md` 저장 결과 표시
- CLI raw log는 접힌 고급 정보로 분리
- 페르소나 캐릭터 상태 아바타 렌더링

OpenDesign 적용 방식:

- `satgat` 스타일을 1차 채팅방 레퍼런스로 삼고, `DESIGN.md` 또는 OpenDesign 산출물은 보조 레퍼런스로 참고한다.
- 색, 간격, 타이포그래피는 백자지 배경·먹색 본문·단청 포인트·명조/돋움 대비를 기준으로 정한다.
- 단, satgat 문서 화면을 복제하지 않고 VibeLign의 기획방 작업 흐름에 맞게 조밀한 타임라인형 채팅 UI로 변형한다.
- 의존성 추가보다 내부 컴포넌트 구현을 우선한다.
- 기존 GUI의 React/Vite/Tauri 구조와 테스트 방식을 유지한다.

---

## 7. 프롬프트 계약

### Draft prompt

목표:

- 사용자의 짧은 아이디어와 질문 답변을 구조화한다.
- 모르는 것은 만들지 말고 "결정 필요"로 남긴다.

출력:

- Markdown이 아니라 JSON 형태의 중간 구조.

필수 필드:

- `title`
- `goal`
- `target_users`
- `features`
- `user_flow`
- `out_of_scope`
- `open_questions`
- `implementation_context`
- `next_steps`

### Review prompt

목표:

- 빠진 요구사항
- 모호한 표현
- 초보자가 나중에 막힐 지점
- 범위가 너무 큰 부분
- 구현 전에 결정해야 하는 질문

출력:

- JSON list of review items
- 각 item은 `severity`, `point`, `recommendation` 포함

### Synthesis prompt

목표:

- 초안과 리뷰를 합쳐 최종 기획안으로 만든다.
- `--language` 값에 맞춰 출력한다. `auto`면 사용자 입력 언어를 따른다.
- AI 작업자에게 필요한 구체성은 유지한다.

출력:

- `markdown_sections` JSON
- `open_questions`가 있으면 숨기지 않는다.

---

## 8. 작업 계획

**작업 단위 매핑**: 아래 Task 1~9는 historical로, 통합기획안 §12 PR 1~9에 다음과 같이 분산된다. 한 PR에 한 Task만 들어가지는 않고, 각 PR은 여러 Task의 일부분만 가져간다.

| Task | 통합기획안 PR | 비고 |
|---|---|---|
| Task 1 (CLI 표면 추가 `vib plan`) | PR 3 | 사용자 표면이 아니라 엔진 검증 진입점 |
| Task 2 (Markdown writer + 저장소) | PR 3 | 엔진 골격 |
| Task 3 (CLI adapter) | PR 4 (probe로 확정한 첫 adapter 1개) + PR 5 (나머지 adapter) | 분할 |
| Task 4 (멀티 AI orchestration) | PR 5 | 3 페르소나 순차 best-effort |
| Task 5 (초보자 질문 흐름) | PR 3 | 엔진 입력 |
| Task 6 (CLI 통합 테스트) | 각 PR마다 분산 | 단일 Task로 끝나지 않음 |
| Task 7 (문서와 manual 갱신) | PR 7 | patch/CodeSpeak/plan-structure legacy 숨김과 함께 |
| Task 8 (기획방 채팅 UI) | PR 1 + PR 3 + PR 5 | 입력 바·기획방·mention 라우팅으로 분할 |
| Task 9 (페르소나 캐릭터 커스터마이즈) | PR 9 | 마지막 |

**1차 우선 작업은 온보딩 입력 바(Task 8 일부) → 기획방/엔진 골격(Task 2/5/1) → CLI adapter와 orchestration(Task 3/4) → 기존 Home 정리 → patch/CodeSpeak/plan-structure legacy 숨김** 순이다. Task 1을 가장 먼저 만들지 않는다.

각 Task의 상세 정의는 그대로 둔다. 완료 기준과 QA는 해당 PR에서 그대로 활용한다.

### Task 1: CLI 표면 추가

파일:

- `vibelign/cli/cli_command_groups.py`
- `vibelign/commands/vib_plan_cmd.py`

작업:

- `vib plan` parser 추가
- 옵션 계약 구현
- 입력이 없으면 대화형 시작
- 아직 core가 없을 때는 local template stub을 호출

완료 기준:

- `vib plan "예약 앱"`이 command dispatch까지 도달한다.
- `vib plan --help`는 기획안 생성 목적만 설명하고 `plan-structure`를 사용자 선택지로 홍보하지 않는다.
- `vib plan --language ko "예약 앱"`이 한국어 기획안을 만든다.

QA:

```bash
python -m vibelign.cli.vib_cli plan --help
python -m vibelign.cli.vib_cli plan "예약 앱" --template-only
```

### Task 2: Markdown writer와 저장소 구현

파일:

- `vibelign/core/planning_cli/models.py`
- `vibelign/core/planning_cli/markdown_writer.py`
- `vibelign/core/planning_cli/storage.py`

작업:

- 최종 Markdown 필수 섹션 생성
- slug 생성
- `plans/` 디렉터리 생성
- `.vibelign/planning/{session_id}.json` 요약 저장
- `.vibelign/planning/{session_id}/session.json` 상세 저장

완료 기준:

- 준비된 CLI 없이도 `plans/{slug}.md`가 생성된다.
- 생성 파일에는 필수 섹션 9개가 모두 있다.

QA:

```bash
python -m pytest tests/core/planning_cli/test_markdown_writer.py
python -m pytest tests/core/planning_cli/test_storage.py
```

### Task 3: CLI adapter 구현

세부 스펙: `plans/spec-pr4-first-cli-persona-spike.md`, `plans/spec-pr5-multi-persona-routing.md`

파일:

- `vibelign/core/planning_cli/cli_adapters.py`
- `vibelign/core/planning_cli/prompts.py`
- `vibelign/core/planning_cli/redaction.py`

작업:

- Claude Code CLI adapter 작성
- Codex CLI adapter 작성
- Antigravity CLI adapter 작성
- 설치 여부는 `shutil.which`로 확인
- 로그인 필요/권한 오류/명령 실패 메시지를 친절한 fallback reason으로 변환
- 테스트에서는 fake CLI runner를 주입할 수 있게 Protocol 정의
- CLI 호출 전 민감정보 redaction 적용
- API key와 provider SDK 의존성은 추가하지 않음
- 각 CLI 호출 전에 `run_id`, `turn_id`, `persona_id`, `cli_id` metadata를 확정

완료 기준:

- 실제 CLI 설치 없이 fake runner로 orchestration 테스트가 가능하다.
- 설치되지 않은 CLI는 건너뛴다.
- 로그인되지 않은 CLI는 전체 실패가 아니라 fallback reason으로 기록된다.
- VibeLign은 CLI 토큰/세션 파일을 읽지 않는다.
- CLI 응답에 자체 ID가 있어도 VibeLign metadata가 우선한다.

QA:

```bash
python -m pytest tests/core/planning_cli/test_cli_adapters.py
python -m pytest tests/core/planning_cli/test_redaction.py
```

### Task 4: 멀티 AI orchestration 구현

세부 스펙: `plans/spec-pr5-multi-persona-routing.md`

파일:

- `vibelign/core/planning_cli/orchestrator.py`
- `vibelign/core/planning_cli/ids.py`

작업:

- draft → review → synthesis 순서 구현
- session/turn/run ID 발급
- 준비된 CLI 수에 따른 fallback 규칙 구현
- `--rounds`는 1차에서는 1 또는 2만 허용
- review item을 synthesis에 반영
- `--save-transcript`일 때만 채팅 로그 Markdown 생성
- 각 turn output을 `.vibelign/planning/{session_id}/turns/`에 저장

완료 기준:

- 3 CLI fake 입력에서 클로이 draft, 지오 review, 미나 risk review, synthesis가 순서대로 실행된다.
- 1 CLI fake 입력에서도 세 역할이 순서대로 실행된다.
- 0 CLI 입력에서는 local template로 완료된다.
- Antigravity fake failure는 fallback reason으로 기록되고 최종 Markdown은 생성된다.
- `session.json`의 turn metadata와 `turns/*.md` 파일명이 일치한다.

QA:

```bash
python -m pytest tests/core/planning_cli/test_orchestrator.py
python -m pytest tests/core/planning_cli/test_ids.py
```

### Task 5: 초보자 질문 흐름 구현

파일:

- `vibelign/core/planning_cli/questions.py`
- `vibelign/commands/vib_plan_cmd.py`

질문 기본값:

1. 누가 사용할 건가요?
2. 사용자가 가장 먼저 하고 싶은 일은 무엇인가요?
3. 꼭 들어가야 하는 기능은 무엇인가요?
4. 이번에는 빼도 되는 것은 무엇인가요?
5. 어떤 화면이나 결과를 기대하나요?

작업:

- 아이디어가 짧으면 질문 5개
- 아이디어가 충분하면 질문 3개
- 빈 답변은 허용하되 Markdown의 "아직 결정이 필요한 질문"으로 남긴다.

완료 기준:

- 사용자가 Markdown 문법을 입력하지 않아도 된다.
- 빈 답변이 있어도 명령이 실패하지 않는다.

QA:

```bash
python -m pytest tests/core/planning_cli/test_questions.py
```

### Task 6: CLI 통합 테스트

파일:

- `tests/cli/test_vib_plan_cmd.py`

시나리오:

- `vib plan "예약 앱" --template-only`가 `plans/*.md`를 만든다.
- `vib plan --review-only plans/existing.md --template-only`가 기존 문서를 개선 경로로 처리한다.
- `vib plan "예약 앱" --json --template-only`가 `ok`, `output_path`, `fallback_reason`을 출력한다.
- `vib plan "예약 앱" --output plans/existing.md`는 파일이 있으면 실패한다.
- `vib plan "예약 앱" --output plans/existing.md --force`는 파일을 덮어쓴다.
- 생성 문서에 `CodeSpeak`, `patch`, `target_anchor`가 들어가지 않는다.

완료 기준:

- 테스트가 실제 CLI 로그인 없이 통과한다.

QA:

```bash
python -m pytest tests/cli/test_vib_plan_cmd.py
```

### Task 7: 문서와 manual 갱신

파일:

- `vibelign/commands/vib_manual_cmd.py`
- `README.md`
- `README.ko.md` 또는 존재하는 getting-started 문서

작업:

- `vib plan`을 "바이브코딩 시작 전 기획안 만들기"로 소개
- 초보 UI/help/manual에서는 `plan-structure`를 숨기거나 레거시/고급 내부 기능으로 낮춘다.
- patch/CodeSpeak를 초보 흐름에서 연결하지 않는다.

완료 기준:

- 초보 문서 첫 흐름이 `vib plan` → 기획안 → AI 작업 또는 GUI 안전장치로 이어진다.
- `vib patch`가 추천 첫 경로로 나오지 않는다.
- `plan-structure`가 기획방, 초보 온보딩, 주요 도움말의 추천 경로로 나오지 않는다.

QA:

```bash
rg -n "vib patch|CodeSpeak|plan-structure|vib plan" README.md README.ko.md vibelign/commands/vib_manual_cmd.py
```

### Task 8: 기획방 채팅 UI 설계/구현

파일:

- `vibelign-gui/src/components/planning/PlanningRoom.tsx`
- `vibelign-gui/src/components/planning/PersonaMessage.tsx`
- `vibelign-gui/src/components/planning/PersonaMentionInput.tsx`
- `vibelign-gui/src/components/planning/PlanningSummaryPanel.tsx`
- `vibelign-gui/src/lib/planning/personas.ts`

작업:

- 클로이/지오/미나/VibeLign 정리 메시지 타입 정의
- mention 입력에서 `@클로이`, `@지오`, `@미나`, `@모두` 지원
- CLI 상태를 보조 배지로 표시
- raw CLI log는 접힌 고급 정보로 분리
- 최종 `plans/*.md` 생성 후 `[기획안 보기] [AI 작업 시작]` 액션 표시
- `satgat` 스타일을 1차 채팅방 레퍼런스로 쓰고 OpenDesign은 디자인 토큰/anti-pattern 보조 참고로만 사용
- 백자지 배경, 먹색 본문, 단청 포인트, 명조/돋움 대비를 적용하되 문서 갤러리처럼 보이지 않는 조밀한 작업실 UI로 구현
- 디자인 런타임 의존성은 추가하지 않음

완료 기준:

- 첫 화면에서 모델 선택 드롭다운이 보이지 않는다.
- 사용자는 페르소나 이름으로 AI를 부른다.
- CLI 실패 로그가 기본 화면을 오염시키지 않는다.
- Markdown 원문은 기본 입력 화면에 노출되지 않는다.

QA:

```bash
cd vibelign-gui
npm test -- --run src/components/planning
npm run build
```

### Task 9: 페르소나 캐릭터 커스터마이즈

파일:

- `vibelign-gui/src/components/planning/PersonaAvatar.tsx`
- `vibelign-gui/src/components/planning/PersonaCustomizer.tsx`
- `vibelign-gui/src/lib/planning/personaAssets.ts`
- `vibelign-gui/src/lib/planning/personaStorage.ts`
- `vibelign/core/planning_cli/persona_assets.py`

작업:

- 기본 클로이/지오/미나 sprite asset 로드
- `persona.json` schema 정의
- 이름/색상/역할 배지/상태 애니메이션 preset 커스터마이즈
- `.vibelign/personas/{persona_id}/` 저장
- sprite-gen 기반 생성은 고급 모드 feature flag 뒤에 둠
- 캐릭터 생성 실패 시 기본 asset fallback

완료 기준:

- 사용자가 AI 팀 캐릭터를 바꿔도 기획 기능은 영향받지 않는다.
- 기본 asset만으로 오프라인 커스터마이즈가 가능하다.
- sprite-gen이 없어도 앱이 정상 동작한다.
- 캐릭터는 메시지 보조 신호로만 보이고 채팅 내용을 가리지 않는다.

QA:

```bash
cd vibelign-gui
npm test -- --run src/components/planning src/lib/planning
npm run build
```

---

## 9. 최종 검증

전체 테스트:

```bash
python -m pytest tests/core/planning_cli tests/cli/test_vib_plan_cmd.py
```

수동 QA:

```bash
tmpdir=$(mktemp -d)
cd "$tmpdir"
git init
vib plan "동네 카페 예약 앱을 만들고 싶어" --template-only
ls plans
sed -n '1,160p' plans/*.md
```

통과 기준:

- 터미널에서 Markdown 문법을 요구하지 않는다.
- `plans/*.md`가 생성된다.
- 필수 섹션이 모두 있다.
- 준비된 CLI가 없어도 실패하지 않는다.
- `patch`, `CodeSpeak`, `target_anchor`가 최종 기획안에 나오지 않는다.
- `vib plan`은 `.vibelign/plans/*.json`이나 active planning state에 의존하지 않는다.
- 기획방 UI에서 `plan-structure`는 노출되지 않는다.

---

## 10. 보수적 현실성 평가

### 현재 VibeLign에서 바로 가능한 것

현 코드베이스 기준으로 다음은 비교적 현실적이다.

- `vib plan --template-only`로 `plans/*.md` 생성
- 쉬운 질문 3~5개를 받아 Markdown 기획안으로 정리
- `claude`, `codex`, `antigravity` 설치 여부 확인
- CLI 미설치/미로그인 상태를 친절한 fallback reason으로 표시
- React/Vite/Tauri 기반 GUI에 `PlanningRoom` 페이지 또는 컴포넌트 추가
- 기본 클로이/지오/미나 아바타 preset 제공
- sprite-gen으로 기본 캐릭터를 빌드/디자인 단계에서 만들어 repo asset으로 포함

이유:

- 기존 command 등록 패턴은 참고할 수 있지만 `plan-structure` 자체를 사용자 흐름에 연결하지 않는다.
- GUI는 Tauri invoke와 React 컴포넌트 구조가 있다.
- Tauri/Rust 쪽에는 subprocess 실행과 Claude 설치/검증 관련 선례가 있다.
- docs/markdown viewer, `react-markdown`, project file 접근 구조가 이미 있다.

### 아직 보수적으로 봐야 할 것

다음은 바로 안정화된 기능으로 보기 어렵다.

- 구독 CLI 3개를 안정적으로 non-interactive 호출
- 각 CLI의 stdout/stderr를 같은 형식으로 파싱
- 로그인 만료, TTY 요구, 사용량 제한, CLI 업데이트에 대응
- Antigravity CLI의 자동화 가능한 non-interactive 계약 확정
- 앱 안에서 sprite-gen을 직접 실행해 사용자가 새 캐릭터를 만드는 흐름
- 채팅 UI, CLI orchestration, persona asset system을 한 PR에서 동시에 구현

### 가장 큰 문제

가장 큰 기술 리스크는 sprite-gen이 아니라 **구독 CLI 자동화 안정성**이다. 그리고 안정성과 별개로 **약관/계약 차원의 리스크**가 벤더별로 다르게 존재한다 — 상세는 §13 참조. 특히 Anthropic은 제3자 자격증명 라우팅을 능동 단속 중이고, Google Antigravity(`agy`)는 **토큰 추출형 접근**에 밴 사례가 있으나 **공식 바이너리 relay(VibeLign식, 토큰 미열람)는 선례 없는 회색지대**다(§13-7).

API 방식은 JSON schema, timeout, retry, structured output을 우리가 통제할 수 있다. 반면 구독 CLI 방식은 각 도구의 CLI UX에 종속된다. 다음 문제가 실제로 발생할 수 있다.

- 로그인 만료
- 첫 실행 interactive prompt
- TTY가 없으면 실패하는 명령
- stdout 형식 변경
- 긴 응답 중단
- 사용량 제한 메시지
- CLI 업데이트로 옵션 변경
- 에러와 정상 응답이 같은 stdout에 섞임

따라서 `vib plan`의 핵심 안정성은 캐릭터나 UI보다 먼저 `CLI adapter contract`에서 결정된다.

필수 계약:

- 각 CLI 호출은 timeout을 가진다.
- 실패한 CLI는 전체 작업을 실패시키지 않는다.
- stdout/stderr 원문은 transcript로만 저장하고, UI 기본 화면에는 요약만 표시한다.
- 로그인 필요/미설치/사용량 제한/TTY 필요를 구분해 fallback reason으로 기록한다.
- CLI 응답이 깨져도 최종 `plans/*.md`는 local template로 생성된다.

### 스코프 폭발 리스크

현재 기획은 기능 하나처럼 보이지만 실제로는 세 개의 제품 축이다.

```text
1. 기획안 생성 CLI
2. 멀티 AI 페르소나 채팅방
3. 페르소나 캐릭터/asset 커스터마이즈
```

이를 한 번에 구현하면 실패할 가능성이 높다. 보수적 구현 순서는 통합기획안 §11 우선순위와 §12 PR 1~9에 정렬한다:

1. 온보딩 첫 화면 ChatGPT 입력 바, 기존 카드 전부 제거 (통합기획안 PR 1)
2. 폴더 선택 → 자동 start + 5단계 진행 + Claude Code 체크박스 동작 (PR 2)
3. 기획 엔진 + 입력 바 → 기획방 정적 전환, CLI 진입점은 `vib plan --template-only`로 검증 (PR 3)
4. 첫 CLI 페르소나 스파이크 + 실제 응답 — 본인 v1 dogfood 시작 (PR 4)
5. 나머지 adapter 추가 + 3 페르소나 순차 best-effort + mention 라우팅 + 정적 아바타 (PR 5)
6. 기존 Home 화면 정리 — 안전 상태, 지금 할 일, 되돌리기 3개 중심 (PR 6)
7. patch/CodeSpeak/plan-structure 초보 표면 제거 + legacy/deprecated 처리 (PR 7)
8. 자동 watch/anchor/guard 정밀화 + 에러 인간화 (PR 8)
9. 페르소나 preset 커스터마이즈 (PR 9)
10. sprite-gen 고급 생성/큐레이션 (별도 PR 보류)

### 보수적 MVP

첫 MVP는 다음 범위로 제한한다.

```text
vib plan "예약 앱 만들고 싶어"
→ 질문 3~5개
→ template Markdown 생성
→ 준비된 CLI가 있으면 best-effort review
→ 실패한 CLI는 건너뜀
→ 최종 plans/*.md 저장
```

GUI MVP:

```text
기획방
→ 클로이/지오/미나 기본 아바타
→ CLI 준비 상태
→ 채팅 로그
→ 기획안 보기
```

제외:

- 앱 내 sprite-gen 실시간 생성
- 캐릭터 curation webview 내장
- 모든 CLI 동시 안정화
- 자동 코드 수정 연결

---

## 11. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| `vib plan-structure`가 새 기획방/초보 UI에 새어 나와 사용자를 헷갈리게 함 | 기획방, 온보딩, 주요 도움말에서 숨기고 `vib plan`만 노출 |
| 구독 CLI 자동화 불안정 | CLI adapter contract를 먼저 만들고 timeout/fallback/status 분류를 테스트 |
| 구독 CLI 약관 위반 리스크(벤더별 상이) | §13 가드레일 준수: 공식 바이너리 subprocess relay만·토큰 추출 금지·재판매/풀링 금지. agy 토큰 추출은 밴 사례, 공식 바이너리 relay는 회색지대(§13-7) → VibeLign은 인증 무관 relay(OAuth/토큰 미취급), 잔존은 Antigravity ToS 6조 문구뿐(§13-8). Claude Agent SDK 크레딧(6-15~) 고지 |
| CLI 사용량/실패 | 기본 rounds 1, CLI 오류는 fallback으로 처리 |
| 중간 채팅 로그가 초보자에게 복잡함 | `--save-transcript`를 켠 경우에만 별도 저장 |
| AI가 근거 없는 요구사항을 추가함 | prompt에 모르는 것은 "결정 필요"로 남기도록 고정 |
| 민감정보 전송 | source code 전체를 보내지 않고 사용자 입력/답변/프로젝트 요약만 전송 |
| 구현자가 patch 흐름과 연결함 | acceptance criteria에 CodeSpeak/patch 금지를 명시 |
| 캐릭터 기능이 제품을 장난감처럼 보이게 함 | 32~48px 상태 아바타로 제한하고 기획 내용이 주인공이 되게 함 |
| sprite-gen 생성 실패 | 기본 asset fallback으로 기획 기능은 계속 동작 |

---

## 12. 완료 정의

이 계획은 다음이 모두 만족되면 완료다.

1. **온보딩 첫 화면이 ChatGPT 입력 바 하나로 정리되었다** — 기존 카드(코드맵 생성·AI 폭주 방지·원클릭 복구·AI 이동 자유·도움말·깃허브·바이브라인 첫걸음)와 터미널 시뮬레이터 전부 제거.
2. **GUI 기획방**에서 입력 바로 자연어를 던지면 3 페르소나(클로이·지오·미나) 채팅이 실행되고 최종 `plans/*.md`가 저장된다.
3. 같은 동작이 `vib plan "..."` CLI 진입점으로도 가능하다 (엔진 동일, API 키 없이도 동작).
4. `claude`/`codex`/`agy` CLI가 준비되어 있으면 해당 페르소나들이 역할별로 참여한다. 일부만 있어도 작동한다 (best-effort).
5. 생성 기획안은 초보자가 읽을 수 있고 AI 작업자가 실행할 수 있을 만큼 구체적이다.
6. `vib plan-structure`는 기획방/초보 UI에 노출되지 않고, `vib plan`은 기존 구조 계획 state와 독립적으로 동작한다.
7. CodeSpeak/patch 지시문이 생성되지 않는다.
8. 자동 테스트와 수동 QA가 모두 통과한다.

---

## 13. 구독 CLI 약관 준수 분석 (2026-06-02 리서치)

> 1차 출처(공식 약관/정책 페이지) 기반 다출처 적대적 검증 결과. 약관은 자주 바뀌므로 구현 착수·배포 전 재확인 필요. **법률 자문이 아니다.**

### 13-0. 한 줄 결론

벤더별로 답이 다르다. 단일 yes/no가 아니다.

- **OpenAI(Codex) — 가장 안전.** 구독으로 CLI 사용 + 비대화형 `codex exec` 공식 지원. 소비자 약관에 프로그래매틱 추출 금지 조항 없음(반대 주장은 검증에서 0-3 반증).
- **Anthropic(Claude) — 회색지대(미해결).** `claude -p` 비대화형은 구독에서 명시적으로 허용. 그러나 "제3자가 Pro/Max 자격증명을 사용자 대신 라우팅"하는 것은 금지(2026-01-09부터 서버측 능동 단속, OpenCode 등 차단). **공식 `claude` 바이너리를 사용자 본인 로그인으로 로컬 subprocess 실행하는 것**이 "native app의 통상 사용"인지 "금지된 제3자 라우팅"인지는 어떤 1차 출처도 결론 내리지 않음.
- **Google(Antigravity, `agy`) — 접근 패턴에 따라 갈림(후속 리서치 §13-7).** Antigravity CLI(2026-05-19 GA, 구 Gemini CLI 후신)는 Google AI 구독으로 쓸 수 있다. 🔴 **토큰 추출/리버스-프록시**(OAuth 토큰을 읽어 비공식 클라이언트로 백엔드 접근, OpenClaw식)는 유료 AI Pro/Ultra 구독자($250/월 포함)도 밴된 확정 위반이다. 🟡 **공식 `agy` 바이너리를 subprocess로 relay**(토큰 미열람, stdin/stdout만 중계 — VibeLign의 실제 설계)는 요청을 진짜 공식 바이너리가 보내므로 사용자가 직접 친 것과 구분되지 않고, OpenClaw를 잡은 시그니처 탐지의 근거가 약하다 → 밴 선례 없는 회색지대다. **VibeLign은 agy의 OAuth/토큰을 다루지 않고 공식 바이너리를 relay할 뿐이므로 OpenClaw식 토큰 추출 우려는 적용되지 않는다.** 남는 건 Antigravity ToS 6조("Service를 우리가 제공하지 않은 제품과 연결해 사용하지 말 것")의 넓은 문구뿐인데, 이는 인증 방식과 무관하게 "제3자 제품이 루프에 끼어있음"을 겨냥한 회색지대다(§13-8).

### 13-1. 벤더별 상세

| 벤더 / CLI | 구독으로 CLI 사용 | 비대화형/프로그래매틱 | 제3자 로컬 subprocess 래핑 |
|---|---|---|---|
| OpenAI Codex | ✅ Free/Go/Plus/Pro/Business/Edu/Enterprise 포함 | ✅ `codex exec` 공식 문서화, 구독 계정 인증 지원(단 CI/CD엔 API 키 권장) | 🟢 가장 방어 가능 — 금지 조항 미발견 |
| Anthropic Claude Code | ✅ Pro/Max(소비자 약관 적용) | ✅ `claude -p` 명시 허용. 단 2026-06-15부터 구독의 `claude -p`/Agent SDK는 별도 월 Agent SDK 크레딧에서 차감 | 🟡 미해결 회색지대 — `claude -p` 허용 vs "자격증명 대신 라우팅/OAuth 토큰 추출" 금지의 경계 미확정 |
| Google Antigravity CLI (`agy`) | 구독으로 사용 가능(AI Pro/Ultra/무료) | 헤드리스 플래그 존재하나 약관 지위 미확인 | 🔴 토큰 추출/프록시 = 밴 확정(2026-02). 🟡 공식 바이너리 subprocess relay(VibeLign식, 토큰 미열람) = 선례 없는 회색지대(ToS 6조 넓음). §13-7 |

출처(1차/공식 우선):

- Anthropic: [Use the Claude Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan), [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview), [Anthropic legal terms](https://www.anthropic.com/legal)
- OpenAI: [Codex CLI and Sign in with ChatGPT](https://help.openai.com/en/articles/11381614-api-codex-cli-and-sign-in-with-chatgpt), [OpenAI Codex CLI - Getting Started](https://help.openai.com/en/articles/11096431), [OpenAI Terms of Use](https://openai.com/policies/row-terms-of-use)
- Google: [Transitioning Gemini CLI to Antigravity CLI](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/), [Gemini API Terms](https://ai.google.dev/gemini-api/terms), [Gemini CLI ToS/privacy resource](https://github.com/google-gemini/gemini-cli/blob/main/docs/resources/tos-privacy.md)

README/README.ko 공개 고지는 PR 4/5에서 실제 CLI adapter를 넣기 직전에 추가한다. PR 3까지는 공식 CLI 호출이 없으므로 README에 약관 고지를 먼저 노출하지 않는다.

### 13-2. 시한부 데드라인 (오늘 2026-06-02 기준)

- **2026-06-15 — Anthropic Agent SDK 크레딧 분리.** Anthropic Help Center에 따르면 구독의 `claude -p`/Agent SDK 사용은 대화형 한도와 분리된 월 Agent SDK 크레딧을 사용한다. → VibeLign이 Claude를 자동 호출하면 사용자의 이 크레딧을 소모할 수 있다는 점을 UX에 투명 고지.
- **2026-06-18 — 구 Gemini CLI 구독 종료(= Antigravity CLI로 전환 완료).** Google Developers Blog는 Gemini CLI/Gemini Code Assist IDE extensions가 개인/free/Google AI Pro·Ultra 요청 제공을 중단하고 Antigravity CLI로 전환한다고 공지했다. VibeLign은 후신인 `agy`(Antigravity CLI)를 쓰는 방향이므로 남는 리스크는 종료가 아니라 **Antigravity CLI의 구독·제3자 래핑 약관 미확인**(§13-5)이다.

### 13-3. VibeLign 설계가 이미 방어선에 있는 부분

배포 래퍼가 추가로 위반할 수 있는 조항(재판매, rate limit 우회, 모델 출력으로 경쟁 모델 학습)은 세 벤더 공통이지만, VibeLign의 **재판매 없음 · 계정 풀링 없음 · 사용자 본인 구독 한도 내 · 로컬 실행 · 자격증명 미열람** 설계는 표면적으로 이들을 건드리지 않는다(특히 무료 OSS라 재판매·경쟁 모델 조항은 거의 무관 — §13-8). 단 "제3자 앱이 BYO 로그인으로 구독을 쓰는 것이 공식 인정된 사용처"라는 주장은 검증에서 0-3 반증됨 — **어떤 벤더도 VibeLign의 정확한 패턴을 명시적으로 축복하지 않았다.** "위반 아님"이 아니라 "정면으로 다뤄지지 않음"이 정확한 상태다.

### 13-4. 설계 가드레일 (이 분석에서 도출)

- VibeLign은 **공식 CLI 바이너리를 subprocess로 실행**할 뿐, OAuth 토큰/세션 파일을 읽거나 비공식 API 클라이언트로 추출하지 않는다(§5 경계 = Anthropic 회색지대에서 방어 가능한 쪽).
- 계정 풀링·중앙 자격증명 보관·재판매·모델 학습 금지를 acceptance criteria에 명시한다.
- VibeLign은 **인증 무관 relay**다 — CLI의 인증(OAuth/API 키)은 사용자 터미널 설정이고 VibeLign이 고르거나 다루지 않는다. (구독-tier 집행이 걱정되는 사용자는 자기 CLI를 API 키로 구성할 수 있으나, 그건 VibeLign 밖 사용자 설정이다.)
- Claude 자동 호출이 사용자의 Agent SDK 크레딧(2026-06-15~)을 소모할 수 있음을 고지한다.

### 13-5. 미해결 질문 (구현·배포 전 확정 필요)

1. Anthropic: 사용자 본인 OAuth 로그인으로 공식 `claude` 바이너리를 로컬 subprocess 실행하는 것이 "통상 사용"인가 "금지된 제3자 라우팅"인가? — 1차 출처 미결, VibeLign의 Claude 적법성을 좌우.
2. Google/Antigravity: **§13-7에서 부분 확인됨** — 토큰 추출형 접근(OAuth 토큰을 비공식 클라이언트로 라우팅)은 실제 밴 집행 대상으로 확인(유료 구독자 포함). 단 **공식 바이너리 subprocess relay**(VibeLign식)는 밴 선례가 없고, 렌더 가능한 Antigravity 전용 1차 약관 클로즈(antigravity.google/terms)도 공백이라 명시 허용/금지 미확정. 유료 API 키 경로가 제3자 앱에 공식 허용인지도 Google 미확인.
3. OpenAI: `codex exec` + ChatGPT 계정 인증은 지원되나 공개/오픈소스 repo CI에는 권고하지 않음 — 공개 OSS로 배포되는 로컬 래퍼가 "신뢰된 사설 자동화"인가, 공개 배포 자체가 태세를 바꾸는가?
4. 공통: 자격증명 미접촉 로컬 오케스트레이터를 "판매"하는 행위 자체가 분석을 바꾸는가? 검토한 약관은 자격증명 라우팅·재판매를 겨냥할 뿐 이 케이스를 정면으로 다루지 않음.

### 13-6. 권고 — 패턴 구분이 핵심 (§13-7 반영)

핵심은 "agy를 쓰느냐"가 아니라 "**어떻게 접근하느냐**"다.

- **(절대 금지) OAuth 토큰 추출 / 리버스-프록시** — 토큰을 읽어 비공식 클라이언트로 백엔드 접근. OpenClaw식, 유료 구독자도 밴된 확정 위반. **VibeLign은 이걸 하지 않는다(§5 경계).**
- **(VibeLign의 설계 = 허용 가능한 회색지대) 공식 CLI 바이너리 subprocess relay** — 사용자가 터미널에서 이미 쓰는 공식 CLI를 그대로 실행하고 stdin/stdout만 채팅창에 relay. 토큰 미열람. 밴 선례 없음. 다만 Antigravity ToS 6조 문구가 넓어 회색이고, 공개 OSS여도 벤더 재량 리스크는 남는다.

벤더별 (relay 패턴 기준):

- **OpenAI Codex 🟢** — `codex exec` 비대화형 공식 문서화. relay 가장 안전.
- **Anthropic Claude 🟡(안전 쪽)** — `claude -p` 구독에서 명시 허용. 금지되는 건 토큰 라우팅/추출이지 공식 바이너리 relay가 아니다.
- **Google Antigravity 🟡** — 공식 `agy` relay는 밴 선례 없음·기술 탐지 근거 약함. 단 ToS 6조 가장 넓음·축복 없음.

따라서 **PR 4 `agy` dogfood는 토큰 추출 없이 공식 바이너리 relay로만 한다면 진행 가능**하다(작성자 본인 1인 로컬). 단:

- 각 CLI의 **비대화형/헤드리스 모드**(`claude -p`, `codex exec`, agy 헤드리스)로 relay한다. TUI 자동 제어는 깨지기 쉬워 피한다.
- 공개 OSS 배포라도(§13-8) Antigravity ToS 6조·축복 부재는 남는다(인증 방식과 무관). 단 VibeLign은 인증 무관 relay라 OAuth 토큰 추출 우려는 없고, 남는 §6 리스크는 "제3자 제품이 루프에 끼어있음" 자체다.
- "최대한 확인된 footing"을 원하면 Codex(지오) 우선 시작이 가장 안전하지만, agy 우선도 relay 패턴이면 방어 가능하다.

### 13-7. Antigravity CLI 약관 후속 리서치 (2026-06-02)

agy(Antigravity CLI) 전용으로 1차 출처 검증을 다시 돌린 결과, 앞선 "미확인 → 아마 괜찮음" 톤을 **하향 조정한다.** VibeLign의 정확한 시나리오(로컬 앱이 사용자 본인 구독 로그인 agy를 subprocess로 호출)는 **깨끗한 허용이 아니라 상당한 약관 리스크**다.

확정된 사실(high confidence):

- **실제 밴 집행.** Google은 2026년 2월 제3자 도구/프록시로 구독 OAuth를 통해 Antigravity 백엔드에 접근한 계정을 밴했고, **유료 AI Pro/Ultra 구독자($250/월 포함)**도 포함됐다. (Google 공식 메인테이너 jackwotherspoon, GitHub Discussion #20632 "Addressing Antigravity Bans"; Techzine·The Register 등 다수 보도 교차 확인)
- **인용 클로즈.** 메인테이너: "제3자 소프트웨어·도구·서비스로 Gemini CLI/Antigravity OAuth 인증을 harvest/piggyback해 백엔드에 접근하는 것은 직접적 위반." Antigravity ToS 6조: "You must not ... use the Service in connection with products not provided by us."
- **탐지 방식 — 패턴이 갈린다.** 밴 사례는 전부 **OAuth 토큰을 추출해 비공식 클라이언트로 백엔드를 친** 패턴(OpenClaw/Pi/OpenCode)이다. User-Agent/시그니처 탐지가 그 비공식 클라이언트를 잡았다. **반면 VibeLign의 확정 설계는 공식 `agy` 바이너리를 subprocess로 실행해 stdin/stdout만 relay**하는 것 — 네트워크 요청은 진짜 공식 바이너리가 보내므로 사용자가 터미널에서 직접 친 것과 구분되지 않고, OpenClaw를 잡은 시그니처 탐지의 근거가 약하다. **즉 VibeLign 패턴은 밴 선례가 없는 회색지대지, 확정 위반이 아니다.** 남는 리스크는 기술 탐지가 아니라 ToS 6조의 넓은 문구 + 공식 축복 부재 + 벤더 재량이다(공개 OSS여도 남는다 — §13-8).

뉘앙스/완화 요인:

- 집행을 촉발한 abuse는 OpenClaw 등 **대량 토큰 하베스팅**(보조 가격 Gemini 2.5 Pro 착취). VibeLign 의도는 1 페르소나·소량·로컬 호출로 성격이 다르다. **단 집행 클로즈와 탐지는 사용량에 게이트되지 않아, 가벼운 사용이 면제된다는 근거는 없다.**
- 최초 "영구 밴" 인상 이후 Google은 초범 자동 해제를 1회 운영(반복 위반은 영구). 정책 자체는 유지.

1차 출처 공백:

- Antigravity 전용 약관 페이지(antigravity.google/terms)는 JS 렌더 실패로 전문 확인 불가 — 구독 vs API 키 권한, 비대화형 호출, 제3자 subprocess 오케스트레이션을 명시 허용/금지하는 **렌더 가능한 1차 클로즈는 확인 못 함.** 승계는 published 클로즈 텍스트가 아니라 **실제 집행으로** 입증됨.
- 커뮤니티 해석(Google 미확인): "구독 = Google 공식 도구만, 제3자 앱은 유료 API 키로." Google 스태프는 확인 요청에 무응답.

배포 일반 제약(§13-8):

- Gemini API 약관: 경쟁 모델 개발 금지 + 리버스 엔지니어링/추출/복제 금지. VibeLign은 무료 OSS·비경쟁이라 거의 무관하나, 사용자 CLI가 API 키로 구성된 경우 일반 적용.

출처(주요): `github.com/google-gemini/gemini-cli/discussions/20632`(Google 스태프), `techzine.eu/.../google-intervenes-in-heavy-use-of-antigravity-and-gemini`, `github.com/openclaw/openclaw/issues/14203`, `discuss.ai.google.dev`(다수 밴 appeal 스레드), `ai.google.dev/gemini-api/terms`, `developers.googleblog.com`(전환 발표), `antigravity.google/terms`(렌더 실패·공백).

### 13-8. 배포 모델: 공개 OSS (GitHub) — 현 상태

VibeLign은 상업 배포가 아니라 **GitHub에 공개된 무료 오픈소스**다. 각 사용자가 자기 머신에서 자기 구독/CLI로 실행한다. 이게 약관 분석에 미치는 영향:

**완화되는 축 (재판매):**

- 재판매·서비스 유료 중계·계정 풀링이 없으므로, 세 벤더의 resale/redistribution 조항은 사실상 적용되지 않는다.
- 경쟁 모델 학습을 하지 않으므로 해당 조항도 무관.

**완화되지 않는 축 (제3자 래핑) — 중요:**

- **무료·OSS라고 더 안전한 게 아니다.** 밴난 OpenClaw·OpenCode·Pi는 전부 무료 오픈소스였다. 벤더는 "돈을 받았는지"가 아니라 "**제3자 도구가 자기 백엔드에 붙는 패턴**"을 단속한다.
- 공개 OSS가 인기를 얻어 많은 사용자를 끌면 OpenClaw처럼 **벤더 스크러티니를 부를 수 있다.**
- 노출은 repo가 아니라 **각 사용자의 계정**에 발생한다(OpenClaw도 repo가 아니라 사용자 계정이 밴됐다). 즉 VibeLign 공개 자체보다 그걸 쓰는 사용자가 리스크를 짊어진다.

**진짜 방어선은 라이선스가 아니라 메커니즘:**

- VibeLign은 토큰을 추출하지 않고 **공식 바이너리를 relay**한다(§13-7) → OpenClaw류와 기술적으로 구분되는 쪽.
- 사용자가 모르고 자기 계정을 걸지 않게 **각 벤더 ToS 회색지대를 앱/README에 정직하게 고지**한다.
- VibeLign은 인증을 다루지 않는다(auth-agnostic relay). CLI 인증은 사용자 설정이다 — 구독-tier 집행이 걱정되는 사용자는 자기 CLI를 API 키로 구성할 수 있으나, VibeLign이 제공하는 인증 경로가 아니라 사용자 본인의 CLI 설정이다.
- OpenAI는 공개/오픈소스 맥락에서 ChatGPT 계정 인증보다 API 키를 권한다(§13-1) — OSS라서 생기는 추가 단서.
