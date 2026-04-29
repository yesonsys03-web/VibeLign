# VibeLign 규칙 수정안

*작성일: 2026-04-17*
*목적: AI가 규칙을 안 지키는 문제를 해결하기 위한 규칙 체계 전반 개선안*

---

## 0. 이번 수정의 핵심 정리 (2026-04-21 반영)

이 문서는 처음에는 "문서에 숫자 규칙을 더 넣고, precheck / pre-commit / structure_planner 자동 연동까지 빠르게 붙이자"는 방향으로 작성됐다. 하지만 실제 코드베이스와 현재 AGENTS safe mode 계약을 대조해보면, **문제의 본질은 규칙 부재보다 실행 경로에서의 강제 부족**에 가깝다.

따라서 이 문서의 우선순위는 아래처럼 정리한다.

1. **먼저 할 것(MVP)**: 문서 수치화 + `vib guard` 차단 + 레거시 대형 파일 동결
2. **나중에 할 것**: pre-commit 강화, anchor warning 자동화, Claude hook precheck 확장
3. **장기 과제**: `structure_planner` 기반 함수 단위 자동 분리 제안

즉, 이 기획안은 "모든 경로를 한 번에 강제"하는 문서가 아니라, **현재 구조와 충돌하지 않는 최소 강제 경로부터 도입**하는 문서로 읽어야 한다.

또한 이 문서의 **실행 기준이 되는 최종 본안은 §12-5 / §12-6** 이다. 앞쪽 섹션은 문제 진단과 아이디어 설명, 중간 설계 기록을 포함하고 있으므로, 실제 착수 순서와 구현 범위는 §12-5 / §12-6 기준으로 해석한다.

---

## 1. 문제 진단

### 현상
AI가 새 기능 추가 시 기존 파일에 계속 코드를 추가해서 파일 줄수가 비대해짐. 규칙 파일에 "파일을 작게 유지"라고 적혀있지만 안 지킴.

### 근본 원인 분석

**규칙 자체의 문제:**

| 현재 상태 | 문제 |
|-----------|------|
| §6 "파일 성장 제어" — 소프트 가이드, 수치 없음 | AI가 해석을 자유롭게 함 ("300줄도 작은 거 아닌가?") |
| §6-1 함수 40/80줄은 명시 | 파일 전체 줄수 상한은 없음 → 작은 함수를 하나의 파일에 계속 추가하는 패턴 |
| 코드(risk_analyzer, watch_rules)에만 임계값 존재 | 문서에 없으니 AI가 모름 |
| AGENTS.md가 "watch_rules 한도를 지켜라"만 언급 | 숫자가 코드에 위임되어 있어 AI가 직접 확인 안 함 |

**강제력의 문제:**

| 영역 | 현재 | 문제 |
|------|------|------|
| `vib doctor` | 500/800/1000줄 감지 | 실행해야만 보임, 차단 아님 |
| `vib watch` | 700/1000줄 경고 | 경고일 뿐, AI가 무시 가능 |
| `vib guard` | 플랜의 `max_lines_added`만 검사 | **파일 전체 줄수 상한 검사 없음** |
| pre-commit hook | 줄수 체크 **없음** | AI가 1000줄 파일에 추가해도 커밋 통과 |
| structure_planner | 150줄 초과 → 새 파일 판정 | AI가 판정을 따를지는 자율 |

### 핵심 결론
초기 결론은 맞지만 표현을 더 정확히 바꾸면 다음과 같다.

**문제는 "규칙이 없다"가 아니라, 규칙이 AI의 실제 작업 경로에 약하게 연결되어 있다는 점이다.**

- 문서(`AI_DEV_SYSTEM_SINGLE_FILE.md`, `AGENTS.md`, export된 `RULES.md`)에 규칙은 이미 존재한다.
- 하지만 숫자 기준이 진입점 문서에 충분히 노출되지 않고,
- 실제 차단은 `guard`/hook 쪽에서만 일부 가능하거나 아예 없으며,
- 현재 safe mode 계약(`patch_get → target_anchor-only edit → guard_check → checkpoint_create`) 바깥의 자동 분기까지 한 번에 가정하면 설계가 과해진다.

따라서 방향은 **안내 문서 보강 + 실행 경로 차단 강화**가 맞고, 자동 분리 엔진까지 초기에 약속하는 것은 범위를 넘는다.

---

## 2. 규칙 문서 수정안

### 대상 파일: `AI_DEV_SYSTEM_SINGLE_FILE.md`

### 2-1. §6 "파일 성장 제어" 섹션 수정

**현재 (소프트 가이드, 수치 없음):**
> small/medium/large/huge 4단계 분류

**수정안:**

```markdown
## §6 파일 성장 제어

### 파일 줄수 상한 (절대 규칙)

| 파일 줄수 | 조치 |
|-----------|------|
| ≤ 300줄 | 정상. 새 함수/클래스 추가 가능 |
| 301~500줄 | ⚠️ 경고. 새 함수/클래스 추가 전 분리 검토 권장. 신규 기능은 가능하면 새 파일 기본값 |
| 501줄 이상 | ❌ 차단. 이 파일에 새 코드 추가 금지. 새 파일 분리 또는 §10 레거시 동결 규칙 적용 |

### 신규 기능 추가 시 권장 절차

1. **대상 파일 줄수 확인** — 300줄 초과면 기존 파일 확장보다 새 파일을 기본값으로 검토
2. **새 모듈 우선 판단** — 새 기능이면 새 파일/모듈/컴포넌트가 기본 선택지
3. **필요 시 `vib plan-structure` 참고** — 초기에는 강제가 아니라 후보 경로 제안기로 사용
4. **기존 파일 수정은 최소화** — 연결 코드(import / wiring) 위주로 제한

### 금지 패턴

- 기존 파일 하단에 새 함수/클래스 계속 추가 ❌
- "일단 여기에 넣고 나중에 분리" ❌
- entry 파일에 비즈니스 로직 추가 ❌
```

### 2-2. §6-1 "함수 설계" 섹션 보강

**현재:**
> 40줄 초과 → 분리 고려, 80줄 초과 → 무조건 분리

**추가:**

```markdown
### 함수 줄수 (기존 유지)

| 함수 줄수 | 조치 |
|-----------|------|
| ≤ 40줄 | 정상 |
| 41~80줄 | 분리 고려 |
| 81줄 이상 | ❌ 무조건 분리 |

### 클래스 줄수 (신규 추가)

| 클래스 줄수 | 조치 |
|-------------|------|
| ≤ 200줄 | 정상 |
| 201~300줄 | 분리 고려. 메서드를 mixin 또는 helper로 추출 |
| 301줄 이상 | ❌ 무조건 분리 |
```

### 2-3. §4 "구조 안전" 섹션 보강

**추가:**

```markdown
### catch-all 파일 방지

다음 패턴이 감지되면 즉시 리팩토링:

- `utils.py` / `helpers.py` / `misc.py` 같은 잡동사니 파일이 200줄 초과
- 하나의 파일에 서로 관련 없는 함수가 5개 이상
- import 수가 15개 초과 (의존성 과다 = 책임 과다)
```

### 2-4. 진입점 규칙 파일도 같이 갱신

`AI_DEV_SYSTEM_SINGLE_FILE.md` 만 고치면 불충분하다. 실제 AI 진입점에서 먼저 보이는 `AGENTS.md`, `CLAUDE.md`, 그리고 `vibelign_exports/claude/RULES.md` 같은 요약 규칙 파일에도 최소한 아래 수치는 반영해야 한다.

- 파일 300줄 경고 / 500줄 차단
- 함수 80줄 초과 금지
- 신규 기능은 큰 기존 파일에 덧붙이지 말고 새 파일 기본값

다만 여기에는 **정본 전체를 복붙하지 않는다.** `AI_DEV_SYSTEM_SINGLE_FILE.md` 전체를 `AGENTS.md`/`CLAUDE.md`에 그대로 복제하면 정본이 여러 개가 되어 유지보수가 어려워진다. 따라서 진입점 파일에는 **핵심 규칙 5~10줄 요약만 승격 배치**하고, 상세 규칙은 계속 정본 문서를 참조하게 두는 편이 맞다.

정리하면 **정본은 `AI_DEV_SYSTEM_SINGLE_FILE.md`**, **세션 진입 계약은 `AGENTS.md`/`CLAUDE.md`**, **툴별 진입점 요약은 export된 `RULES.md`** 로 역할을 분리해야 한다.

---

## 3. AGENTS.md / CLAUDE.md 수정안

**현재:**
> watch_rules 한도를 지키고, 기존 파일 비대화 대신 새 파일 선호

**수정안:**

```markdown
## 필수 규칙 (모든 AI 에이전트)

1. AI_DEV_SYSTEM_SINGLE_FILE.md를 반드시 읽고 따를 것
2. **파일 줄수 절대 상한**:
   - 300줄 초과 파일은 새 기능 추가 전 분리 우선 검토
   - 500줄 초과 파일은 새 코드 추가 차단 (기존 대형 파일은 §10 baseline 동결 규칙 적용)
3. **함수 80줄, 클래스 300줄 초과 금지**
4. 신규 기능은 큰 기존 파일에 덧붙이지 말고 새 파일/모듈/컴포넌트를 기본값으로 검토
5. VibeLign safe mode 계약(`patch_get → target_anchor-only edit → guard_check → checkpoint_create`)은 유지
6. 상세 규칙은 `AI_DEV_SYSTEM_SINGLE_FILE.md`를 참조
```

`CLAUDE.md`도 같은 원칙으로 맞춘다. 중요한 점은 **전체 규칙 문서를 복제하는 게 아니라, 세션 진입점 상단에 짧은 핵심 규칙만 승격**하는 것이다.

숫자를 `AGENTS.md`/`CLAUDE.md`에도 직접 넣는 이유: AI가 `AI_DEV_SYSTEM_SINGLE_FILE.md`를 안 읽거나 대충 읽을 수 있기 때문이다. 진입점에서 핵심 수치를 바로 보여줘야 효과적이다. 다만 **여기에서 `vib plan-structure`를 보편적 필수 절차로 승격하면 현재 safe mode 계약과 충돌할 수 있으므로**, 초반에는 "새 파일 우선" 원칙과 수치 노출에 집중하는 편이 맞다.

---

## 4. 코드 레벨 강제 수정안

### 4-1. `vib guard`에 파일 전체 줄수 상한 추가

**현재:** 플랜의 `max_lines_added`만 검사. 파일 총 줄수는 안 봄.

**수정:**

```python
# vib_guard_cmd.py 에 추가

from vibelign.core.project_scan import line_count

FILE_LINE_WARN = 300
FILE_LINE_BLOCK = 500

def check_file_growth(changed_files: list[Path]) -> list[Issue]:
    issues = []
    for path in changed_files:
        lines = line_count(path)
        if lines > FILE_LINE_BLOCK:
            issues.append(Issue(
                severity="block",
                message=f"❌ {path.name}: {lines}줄 — 500줄 초과. 새 파일로 분리 필수",
            ))
        elif lines > FILE_LINE_WARN:
            issues.append(Issue(
                severity="warn",
                message=f"⚠️ {path.name}: {lines}줄 — 300줄 초과. 분리 검토 필요",
            ))
    return issues
```

guard 판정에 block 이슈가 있으면 실패 처리.

### 4-2. pre-commit hook에 줄수 체크 추가

**현재:** pre-commit hook에 줄수 체크 없음.

**수정:** `git_hooks.py`의 pre-commit 로직에 추가:

```python
# 커밋 대상 파일 중 줄수 초과 파일 차단
for rel_path in staged_files:
    if Path(rel_path).suffix in ALLOWED_EXTS:
        staged_text = git_show(f":{rel_path}")
        lines = len(staged_text.splitlines())
        if lines > 500:
            print(f"❌ BLOCKED: {rel_path} ({lines}줄) — 500줄 초과. 분리 후 커밋하세요.")
            sys.exit(1)
```

핵심은 **working tree가 아니라 staged 기준으로 판정**해야 한다는 점이다. 실제 구현에서는 기존 guard git 헬퍼를 재사용하는 편이 더 안전하다.

### 4-3. structure_planner 강제 연동

**현재:** `vib plan-structure`가 150줄 초과 파일에 새 파일 생성 판정을 하지만 강제가 아님.

**수정:** Claude hook(PreToolUse)에서 파일 수정 전 자동 체크. 다만 **초기 버전은 function-level 분리 강제가 아니라 파일 단위 가이드 제공** 수준으로 제한한다:

```python
# vib_precheck_cmd.py 에 추가
def precheck_file_write(target_path: Path):
    lines = line_count(target_path)
    if lines > 300:
        suggestion = suggest_new_module_path(target_path)
        if suggestion is not None:
            return Block(
                reason=f"{target_path.name}은 {lines}줄. "
                       f"우선 {suggestion} 같은 새 파일 경로를 검토하세요"
            )
    return Allow()
```

### 4-4. 앵커 메타에 자동 경고 삽입

**현재:** anchor_meta.json의 `warning` 필드가 수동 입력 의존.

**수정:** `generate_code_based_intents()`에서 파일 줄수 기반 자동 경고:

```python
# anchor_tools.py generate_code_based_intents() 에 추가
if file_line_count > 300:
    for anchor_name in file_anchors:
        meta[anchor_name]["warning"] = (
            f"이 파일은 {file_line_count}줄. "
            f"새 기능 추가 금지. 새 모듈로 분리할 것"
        )
```

AI가 앵커를 수정하려 할 때 warning을 보게 되니까 자연스럽게 억제.

---

## 5. 규칙 적용 강도 매트릭스

| 계층 | 시점 | 강도 | MVP 반영 | 후속 반영 |
|------|------|------|----------|-----------|
| AGENTS.md | AI 세션 시작 | 안내 | ✅ 핵심 수치 명시 | 유지 |
| AI_DEV_SYSTEM.md §6 | AI 세션 시작 | 안내 | ✅ 300/500줄 명시 | 유지 |
| export된 RULES.md | AI 툴 진입점 | 안내 | ✅ 핵심 수치 반영 | 유지 |
| vib guard | 작업 완료 후 | **차단** | ✅ 300경고/500차단 + legacy 동결 | 유지 |
| pre-commit hook | 커밋 시 | **차단** | 보류 | Phase 3 |
| anchor_meta warning | 코드 수정 시 | 억제 | 보류 | Phase 4 |
| Claude hook precheck | 파일 쓰기 전 | **차단** | 보류 | Phase 5 |
| structure_planner | 파일 수정 전 | 권고/가이드 | 보류 | 파일 단위 제안부터 |
| vib doctor | 수동 실행 | 보고 | 유지 | 유지 |
| vib watch | 실시간 | 경고 | 유지 | 유지 |

**핵심 요지:** 이 문서의 1차 목표는 모든 계층을 동시에 완성하는 것이 아니라, **문서 + guard + legacy 동결**만으로도 AI가 큰 파일을 더 키우는 행동을 먼저 줄이는 것이다.

---

## 6. AI가 규칙을 안 지키는 일반적 원인과 대응

### 원인 1: 컨텍스트 거리 문제
대화 초반에 준 규칙은 대화가 길어지면 영향력 약해짐.

**대응:** 앵커 메타 warning에 규칙을 녹임 → AI가 해당 코드 수정할 때 바로 봄. 진입점(AGENTS.md)에 핵심 수치를 직접 명시.

### 원인 2: 규칙의 모호성
"파일을 작게 유지" → AI가 매번 다르게 해석.

**대응:** 구체적 숫자로 교체. "300줄 초과 금지", "함수 80줄 초과 금지". 해석 여지 없앰.

### 원인 3: "도움이 되려는 본능"과 충돌
사용자가 "이거 빨리 고쳐줘"라고 하면 규칙보다 요청 수행 우선.

**대응:** 1차는 guard 차단까지만 도입한다. pre-commit 과 precheck 는 효과는 크지만 구현 비용과 우회/성능 이슈가 있으므로, guard 만으로 부족하다는 사용 증거를 보고 난 뒤 후속 단계에서 붙인다.

### 원인 4: 강제력 없음
md 파일에 적혀있지만 안 지켜도 아무 일 안 일어남.

**대응:** 우선 `vib guard`를 실제 차단 경로로 만든다. 그 다음 필요가 확인되면 pre-commit hook을 올린다. 순서를 거꾸로 두면 설계 복잡도만 먼저 증가한다.

### 원인 5: 규칙 전달 위치
AI가 규칙을 인식하는 강도 순서:
1. 시스템 프롬프트 (가장 강함)
2. 대화 직전 메시지
3. AGENTS.md / CLAUDE.md (중간)
4. 프로젝트 docs 폴더 (약함)

**대응:** 핵심 규칙(줄수 상한)은 `AGENTS.md`/`CLAUDE.md` 최상단에 배치하고, export된 `RULES.md`에도 짧게 반영한다. 보조 규칙은 `AI_DEV_SYSTEM_SINGLE_FILE.md`에 상세화한다. 실행 시점 재확인은 초기에는 guard 중심으로 시작한다.

---

## 7. 작업 순서 (요약)

> 이 섹션은 큰 흐름만 빠르게 요약한 것이다. **실제 착수 순서와 범위 판단은 §12-5 / §12-6을 최종 기준으로** 삼는다.

### Phase 1 — 문서 수정 (즉시, 30분)
- `AI_DEV_SYSTEM_SINGLE_FILE.md` §6 수정 (줄수 수치 추가)
- `AGENTS.md` / `CLAUDE.md` 상단에 핵심 규칙 요약 승격 배치
- `vibelign_exports/claude/RULES.md` 같은 요약 규칙 파일에도 핵심 수치 반영
- 정본 전체 복제가 아니라 핵심 규칙 5~10줄만 승격
- safe mode 계약은 바꾸지 않음

### Phase 2 — guard 강화 (1일)
- `vib guard`에 파일 전체 줄수 상한 검사 추가
- 300줄 경고 / 500줄 차단
- §10 legacy baseline 동결 같이 구현

### Phase 3 — pre-commit hook 추가 (후속)
- `vib guard --strict` 경로 기준으로 staged 판정 보강
- hook marker migration 과 기존 설치본 갱신 포함
- 별도 중복 체크 스크립트 추가는 하지 않음

### Phase 4 — 앵커 메타 자동 경고 (후속)
- `generate_code_based_intents()`에서 300줄 초과 파일의 앵커에 warning 자동 삽입

### Phase 5 — Claude hook precheck 연동 (후속)
- Write/Edit/MultiEdit 모두 커버
- 초기에는 structure_planner 강제가 아니라 파일 단위 가이드 연동 수준으로 제한

정리하면 §7은 **문서 → guard → 후속 연동** 이라는 큰 흐름을 보여주는 요약이고, 실제 구현 세부 범위는 뒤의 §12-5 / §12-6에서 잠근다.

---

## 8. guard + plan-structure 연동 설계 (후속 확장)

> 이 섹션은 **장기 UX 목표** 설명이다. MVP 범위는 아니며, 현재 기준의 초기 구현은 guard + 파일 단위 가이드까지만 포함한다.

### 문제
guard가 차단만 하면 사용자(특히 코알못)에게 불편. "뭘 어쩌라는 거야?" 상태가 됨. 사용자가 직접 `vib plan-structure`를 따로 실행하는 건 비현실적.

### 해결: 차단 + 대안 제시 = 가이드

이상적인 UX는 차단 메시지가 대안까지 같이 주는 것이다. 다만 초기 버전에서 guard가 항상 `plan-structure`를 자동 실행한다고 가정하면 현재 코드베이스 능력을 넘어선다. 따라서 이 섹션은 **장기 목표 설명**으로 읽고, 초기 구현은 파일 단위 힌트 또는 "`vib plan-structure <file>`를 실행하세요" 수준의 가이드부터 시작한다.

### 자동 연동 흐름

```
AI가 파일 수정 시도
  │
  ├→ guard 자동 체크
  │   └→ 줄수 초과 감지 (예: 520줄)
  │
  ├→ (후속 단계에서) plan-structure 또는 파일 단위 제안 실행
  │   └→ 우선은 새 파일 후보 경로 또는 파일 단위 힌트 산출
  │
  └→ AI에게 통합 메시지 전달:
       "❌ vibelign/core/auth.py는 520줄이에요.
        이 파일에 새 코드를 더하지 말고 `vibelign/core/auth_extension.py` 같은
        새 모듈로 분리하는 방안을 먼저 검토하세요."
  
  → AI가 대안 경로로 작업 자동 진행
  → 사용자는 아무것도 안 해도 됨
```

### 구현 포인트 (장기 확장안)

```python
# vib_guard_cmd.py 수정

def check_file_growth_with_plan(path: Path, root: Path) -> GuardResult:
    lines = count_lines(path)
    
    if lines <= 300:
        return Allow()
    
    if lines <= 500:
        return Warn(f"⚠️ {path.name}: {lines}줄 — 분리 검토 필요")
    
    # 500줄 초과 → 후속 단계에서만 plan-structure 연동 검토
    plan = run_structure_planner(root, target_file=path)
    
    suggestion = ""
    if plan.required_new_files:
        for new_file in plan.required_new_files:
            suggestion += f"\n  → {new_file.functions} 을 {new_file.path} 로 분리"
    
    return Block(
        message=f"❌ {path.name}: {lines}줄 초과.",
        suggestion=suggestion or "vib plan-structure로 분리 경로를 확인하세요",
        auto_plan=plan  # AI가 바로 활용할 수 있는 구조화된 데이터
    )
```

### AI가 받는 메시지 예시 (좋은 UX)

**나쁜 UX (차단만):**
```
❌ auth.py: 520줄 — 500줄 초과. 커밋 불가.
```

**좋은 UX (차단 + 대안):**
```
❌ auth.py: 520줄 초과.
  → 이 파일에 새 코드를 추가하지 마세요
  → `vibelign/core/auth_extension.py` 같은 새 모듈 경로를 먼저 검토하세요
  → auth.py에는 import + 기존 공개 API만 유지하세요
```

AI는 이 메시지를 받으면 자동으로 새 파일에 작업하고, 사용자는 결과만 보면 됨.

### pre-commit hook (후속 단계에서 동일 구조로 적용)

커밋 시점에 500줄 초과 파일이 있으면 — **§12-5 Phase 3 이후** 다음 동작을 도입 대상으로 본다:
1. 차단
2. plan-structure 결과 출력
3. "위 경로로 분리 후 다시 커밋하세요"

### Claude hook precheck (후속 단계에서 동일 구조로 적용)

AI가 파일 쓰기 전(PreToolUse 단계) — **§12-5 Phase 5 이후** 다음 동작을 도입 대상으로 본다:
1. 대상 파일 줄수 체크
2. 300줄 초과면 plan-structure 자동 실행
3. "이 파일 대신 {new_path}에 작성하세요" 리다이렉트

### 사용자 경험 비교

| 시나리오 | 수정 전 | 수정 후 |
|----------|---------|---------|
| AI가 500줄 파일에 추가 | 그냥 추가됨 → 파일 비대화 | 자동 차단 + 분리 경로 제시 → AI가 새 파일로 |
| 사용자가 기능 요청 | AI가 대충 기존 파일에 넣음 | AI가 structure plan 받아서 올바른 위치에 작성 |
| 커밋 시도 | 통과 | 줄수 초과면 차단 + 대안 안내 |
| 사용자 수동 작업 | 없음 | **여전히 없음** (전부 자동) |

### 설계 철학

**"차단"이 아니라 "가이드"다.** 규칙은 제약이지만, 제약 + 자동 대안 제시 = 가이드. 사용자는 "뭘 해야 할지 모르겠는" 상태에서 "VibeLign이 알려주는 대로 하면 되는" 상태로 바뀜. VibeLign 없이 코딩하는 것보다 편한 경험을 만드는 것이 목표.

---

## 9. 임계값 설정 근거

| 임계값 | 근거 |
|--------|------|
| **300줄 (경고)** | 일반적으로 단일 모듈이 하나의 책임을 유지하기 좋은 상한. 이 이상이면 복수 책임이 섞이기 시작 |
| **500줄 (차단)** | risk_analyzer 기존 임계값과 일치. 이 이상은 거의 확실히 분리 필요 |
| **80줄 (함수)** | 기존 AI_DEV_SYSTEM.md 규칙 유지. 화면 하나에 전체가 보이는 크기 |
| **300줄 (클래스)** | 함수 80줄 × 3~4개 메서드 + 프로퍼티. 단일 클래스의 합리적 상한 |
| **150줄 (structure_planner)** | 기존 코드 임계값 유지. 이 이상이면 새 파일 **제안 기준** (초기에는 강제가 아닌 가이드) |

임계값은 `.vibelign/config.json` 같은 설정 파일로 프로젝트별 커스터마이징 가능하게 만들면 좋음 (Phase 5 이후).

---

## 9-1. 검증 방법

수정 후 효과 확인:

1. **즉시 확인:** AI에게 "기존 파일(400줄)에 새 함수 추가해줘" 요청 → AI가 분리를 제안하는지
2. **guard 확인:** 500줄 초과 파일 수정 후 `vib guard` 실행 → 차단되는지
3. **pre-commit 확인:** 500줄 초과 파일 `git commit` → 거부되는지
4. **앵커 확인:** 300줄 초과 파일의 anchor_meta.json에 warning 자동 삽입됐는지
5. **장기 추적:** 프로젝트 전체 파일 줄수 분포가 개선되는지 (doctor 리포트)

---

## 10. 기존 프로젝트 전환 전략

### 문제

규칙을 바로 적용하면 기존 2000줄 파일 때문에 guard/pre-commit이 전부 차단해서 아무 작업도 못 하는 상황이 발생한다.

### 핵심 원칙

**"기존 파일 줄수가 이미 500줄 넘어도, 더 늘리지만 않으면 OK"**

```
기존 파일 2000줄 → 2000줄 유지 = ✅ 통과
기존 파일 2000줄 → 2050줄 증가 = ❌ 차단 ("이 파일에 추가 금지, 새 파일로")
```

### 적용 규칙 매트릭스

| 파일 상태 | 적용 규칙 |
|-----------|-----------|
| 신규 파일 | 300줄 경고 / 500줄 차단 (바로 적용) |
| 기존 500줄 이하 | 300줄 경고 / 500줄 차단 (바로 적용) |
| 기존 500줄 초과 | 현재 줄수 동결. **증가만 차단**. 수정 시 분리 유도 |

### 구현 방법

> **최종 권장 전략은 §12-3 (6)** — legacy list는 **커밋**하고 머지는 래칫 merge driver로 자동 해결한다. 이 섹션의 서술은 초기 설계 기록으로 남겨두고, 실제 구현 시 §12-3 (6)을 기준으로 따른다.

#### 1. 레거시 허용 목록 자동 생성

`.vibelign/legacy_large_files.json`에 현재 500줄 초과 파일 목록을 자동 등록:

```json
{
  "generated_at": "2026-04-17",
  "schema_version": 1,
  "files": {
    "src-tauri/src/lib.rs": {"baseline_lines": 1102, "target": 500},
    "vibelign/core/anchor_tools.py": {"baseline_lines": 747, "target": 400}
  }
}
```

- `baseline_lines`: 등록 시점의 줄수. 이 줄수까지 허용
- `target`: 장기적으로 도달해야 할 목표 줄수

#### 2. guard/pre-commit의 판정 로직

```python
def check_file_growth(path: Path, legacy_list: dict) -> Verdict:
    current_lines = count_lines(path)
    rel = str(path.relative_to(root))
    
    if rel in legacy_list:
        baseline = legacy_list[rel]["baseline_lines"]
        if current_lines > baseline:
            return Block(f"❌ 레거시 파일 {rel}: {baseline}줄 → {current_lines}줄 증가. 새 파일로 분리 필수")
        elif current_lines < baseline:
            return Praise(f"✅ {rel}: {baseline}줄 → {current_lines}줄 감소! 리팩토링 진행 중")
        else:
            return Allow()
    else:
        # 신규/일반 파일 — 표준 규칙 적용
        if current_lines > 500:
            return Block(f"❌ {rel}: {current_lines}줄 — 500줄 초과")
        elif current_lines > 300:
            return Warn(f"⚠️ {rel}: {current_lines}줄 — 분리 검토 필요")
        return Allow()
```

#### 3. 점진적 축소 유도

기존 대형 파일은 수정할 때마다 일부를 분리하도록 유도:

- 2000줄 파일에서 함수 수정 요청 → "이 함수를 새 파일로 추출하면서 수정해라" 가이드
- 한 번에 전부 리팩토링하는 게 아니라 **수정 기회마다 조금씩 줄여나가는** 방식
- 줄수 감소 시 "✅ 리팩토링 진행 중" 칭찬 메시지 → AI 동기 부여

#### 4. `vib start --refresh`로 마이그레이션

기존 프로젝트에서 `vib start --refresh` 실행하면:

1. 규칙 파일을 최신 버전으로 업데이트
2. 현재 500줄 초과 파일 스캔 → 레거시 허용 목록 자동 생성
3. guard/pre-commit 설정 업데이트
4. "기존 대형 파일 N개 발견. 레거시 허용 목록에 등록했어요" 안내

사용자 입장에서는 `vib start --refresh` 한 번이면 끝. 기존 프로젝트가 깨지지 않으면서 새 규칙이 적용됨.

### 참고: `vib start` 수정 필요

`vib start`가 프로젝트 초기화 시 규칙 파일을 생성하는 커맨드이므로:

- 신규 프로젝트: `vib start` 실행 시 수정된 §6(줄수 수치 포함) 버전으로 규칙 파일 생성
- 기존 프로젝트: `vib start --refresh`로 규칙 파일 업데이트 + 레거시 허용 목록 생성
- guard/hook 설정도 `vib start` 시점에 연동

---

## 11. 엣지케이스 대응

> **Phase 라벨 기준**: 아래 각 EC 에 적힌 "단계: Phase N" 라벨은 이 섹션이 처음 작성된 초기 작업 순서(§7) 기준이다. 실제 실행 순서는 **§12-5 의 Phase 계획이 최종**이다. 충돌 시 §12-5 를 따른다.

### 11개 엣지케이스 + 대응책

#### EC-1. 분리 시 순환 import 발생

**상황:** A.py에서 함수를 B.py로 분리했는데, B.py가 다시 A.py를 import해야 하는 경우.

**대응:** plan-structure가 분리 경로 제안할 때 `import_resolver.py`로 import 그래프를 사전 분석. 순환 가능성 감지되면 분리 경로를 조정하거나 "이 함수는 분리하면 순환 참조가 생깁니다. 다른 함수를 먼저 분리하세요" 안내.

**난이도:** 어려움. import_resolver 연동 + 순환 감지 로직 필요.
**단계:** Phase 3 (장기)

---

#### EC-2. 분리 불가능한 파일 유형

**상황:** 설정 파일, 마이그레이션, 자동 생성 코드, 테스트 파일 등은 구조상 분리 불가.

**대응:** `.vibelign/config.json`에 예외 패턴 등록:

```json
{
  "line_limit_exclude": [
    "*.test.*",
    "*.spec.*",
    "tests/**",
    "migrations/**",
    "*.generated.*",
    "*.config.*"
  ]
}
```

guard/pre-commit이 이 패턴에 매칭되는 파일은 줄수 체크 건너뜀.

**난이도:** 쉬움. 설정 파일 + glob 매칭.
**단계:** Phase 1

---

#### EC-3. plan-structure가 잘못된 분리 경로 제시

**상황:** plan-structure가 부적절한 경로 제안 → AI가 그대로 따라서 구조 망침.

**대응:** 확신도(confidence) 기반 분기:
- 확신 높음 → 자동 제안 ("이 경로로 분리하세요")
- 확신 낮음 → 선택지 제공 ("A 또는 B 중 선택하세요")
- 확신 없음 → 제안 생략 ("수동으로 분리 경로를 지정하세요")

plan-structure 결과에 `confidence` 필드를 추가하고, guard가 이를 보고 메시지 톤을 조절.

**난이도:** 중간. plan-structure에 confidence 로직 추가.
**단계:** Phase 2

---

#### EC-4. baseline 요요 현상

**상황:** 레거시 파일 2000줄 → 1500줄로 줄임 → baseline이 2000이니까 다시 2000까지 늘어나도 허용.

**대응:** **래칫(ratchet) 방식** — baseline은 내려가기만 하고 올라가지 않음:

```python
def update_baseline(rel: str, current_lines: int, legacy_list: dict):
    if current_lines < legacy_list[rel]["baseline_lines"]:
        legacy_list[rel]["baseline_lines"] = current_lines  # 자동 갱신
        save_legacy_list(legacy_list)
```

커밋 성공할 때마다 줄수가 줄었으면 baseline 자동 하향 조정. 한 번 줄이면 다시 못 늘림.

**난이도:** 쉬움. baseline 갱신 로직 한 줄.
**단계:** Phase 1

---

#### EC-5. 동시 다중 분리 시 중간 상태 충돌

**상황:** guard가 "3개 함수를 3개 새 파일로"라고 제안. AI가 순차 처리 중 중간 상태에서 또 guard가 걸림.

**대응:** `--refactoring` 모드 도입:
- 이 모드에서는 줄수 증가를 임시 허용
- 커밋 시점에서 최종 검증 (pre-commit hook)
- 리팩토링 세션이 끝나면 자동 해제

또는: guard를 파일 단위가 아닌 **커밋 단위**로 판정. 커밋 전체의 줄수 변화를 보고 "순 증가"인지 "분리 작업 중"인지 판단.

**난이도:** 중간. 세션 상태 관리 또는 diff 기반 판정.
**단계:** Phase 2

---

#### EC-6. 프론트엔드 컴포넌트 파일 임계값

**상황:** React 컴포넌트가 JSX + 스타일 + 로직 한 파일에 500줄 넘는 건 흔한 패턴. 분리하면 props drilling 지옥.

**대응:** 확장자별 임계값 차등 적용:

```json
{
  "line_limits": {
    "default": {"warn": 300, "block": 500},
    ".tsx": {"warn": 500, "block": 700},
    ".jsx": {"warn": 500, "block": 700},
    ".vue": {"warn": 500, "block": 700},
    ".rs": {"warn": 400, "block": 600},
    ".py": {"warn": 300, "block": 500}
  }
}
```

**난이도:** 쉬움. 설정 파일 확장.
**단계:** Phase 1

---

#### EC-7. 줄수 세기 기준 불일치

**상황:** 빈 줄, 주석, import, 앵커 마커, docstring이 줄수에 포함되면 실제 로직은 적은데 줄수만 높음.

**대응:** "실제 코드 줄수" 기준 사용. 다음을 제외:
- 빈 줄
- 주석 전용 줄 (`#`, `//`, `/* */`)
- 앵커 마커 줄 (`=== ANCHOR: ===`)
- import/require 줄

`risk_analyzer.py`에 이미 비슷한 로직이 있으므로 재사용. guard/pre-commit에서도 동일 함수 호출.

**난이도:** 중간. 코드 줄수 카운터 정교화.
**단계:** Phase 2

---

#### EC-8. guard + plan-structure 성능 문제

**상황:** guard 실행 시 plan-structure가 자동 실행되면 대형 프로젝트에서 느려짐. 줄수 초과 파일 10개면 10번 실행.

**대응:**
- plan-structure 결과를 `.vibelign/plan_cache.json`에 캐싱
- 파일 mtime/hash가 안 바뀌었으면 캐시 재사용
- guard는 줄수 체크만 먼저 하고(빠름), 차단 대상에 대해서만 plan-structure 실행(느린 부분 최소화)

**난이도:** 중간. 캐시 인프라.
**단계:** Phase 2

---

#### EC-9. 사용자가 force 우회

**상황:** guard 차단해도 `--skip-guard`나 `--force`로 우회.

**대응:**
- 우회 옵션 자체는 제공 (개발자가 필요한 경우 있음)
- 우회 시 `.vibelign/audit_log.json`에 기록: 누가, 언제, 어떤 파일, 어떤 규칙 우회
- `vib doctor` 리포트에 "guard 우회 N회" 표시
- 팀 사용 시 PR 리뷰에서 이 로그 참조 가능

**난이도:** 쉬움. 로깅.
**단계:** Phase 1

---

#### EC-10. 멀티 브랜치 레거시 목록 충돌

**상황:** A 브랜치에서 파일 분리 → 줄수 감소. B 브랜치에서는 안 줄임. 머지 시 `legacy_large_files.json` 충돌.

**대응:** 두 가지 옵션:

**옵션 A:** `legacy_large_files.json`을 `.gitignore`에 넣고 로컬 전용으로 관리. 각 브랜치에서 `vib start --refresh` 실행하면 현재 상태 기준으로 재생성. ⚠️ **§12-3 (6) 에서 이 전략은 철회됨** — CI 쪽에 legacy list 가 없으면 모든 PR 이 깨지므로, 커밋 + 래칫 merge driver 를 최종 권장으로 한다.

**옵션 B:** 레거시 목록 대신 **diff 기반 판정**으로 전환. 레거시 목록 없이 `git diff --stat`으로 "이 커밋에서 줄수가 늘었는가"만 판단. 파일 자체가 크든 작든 "늘리지 마라"만 적용.

**옵션 C (최종 권장, §12-3 (6)):** legacy list 를 **커밋**하고, 머지 충돌은 `.gitattributes` + custom merge driver 로 래칫 자동 해결.

**난이도:** 옵션 A/B 는 쉬움~중간. 옵션 C 는 merge driver 구현 포함이므로 중간.
**단계:** 옵션 C 를 기본. 옵션 A/B 는 대안 참고용으로만 남김.

---

#### EC-11. `vib start --refresh` 미실행

**상황:** 사용자가 refresh 안 하면 규칙 파일 옛날 버전, 레거시 목록 미생성.

**대응:** `vib guard` 실행 시 규칙 파일 버전 자동 체크:

```python
if rules_version < CURRENT_RULES_VERSION:
    print("⚠️ 규칙이 업데이트됐어요. `vib start --refresh` 실행하세요.")
    print("   (현재: v{rules_version}, 최신: v{CURRENT_RULES_VERSION})")
```

차단까진 안 하고 안내만. `vib watch`에서도 주기적으로 체크해서 알림.

**난이도:** 쉬움. 버전 비교.
**단계:** Phase 1

---

### 엣지케이스 대응 우선순위 요약

| 단계 | 대상 | 난이도 |
|------|------|--------|
| **Phase 1 (즉시)** | EC-2 예외 패턴, EC-4 래칫, EC-6 확장자별 임계값, EC-9 우회 로그, EC-10 레거시 로컬, EC-11 버전 체크 | 쉬움 |
| **Phase 2 (1~2주)** | EC-3 confidence, EC-5 리팩토링 모드, EC-7 코드 줄수 기준, EC-8 캐싱 | 중간 |
| **Phase 3 (장기)** | EC-1 순환 import 감지 | 어려움 |

Phase 1만 해도 80%는 커버됨. 나머지는 실사용하면서 실제로 터지는 것만 우선 수정.

---

## 12. 플랫폼 호환성 및 구현 수정사항 (2026-04-21 추가)

실제 코드베이스(`vibelign/core/`, `vibelign/commands/`) 점검 결과, §4 스니펫은 **Windows(특히 한글 cp949 로캘)에서 즉시 크래시**한다. 기존 헬퍼와 불일치하는 부분도 있어 아래 항목을 반영해야 한다.

### 12-1. CRITICAL — Windows 에서 바로 깨지는 것

#### (1) `read_text()` 에 인코딩 명시 필수

**문제**
```python
lines = path.read_text().count('\n')  # 기획안 §4-1, §4-2, §4-3 전부
```
한글 Windows 기본 인코딩은 cp949. UTF-8 한글 코멘트/문자열 있는 파일에서 `UnicodeDecodeError` → guard/pre-commit/precheck 크래시.

**수정** — 기존 `vibelign/core/project_scan.py` 의 헬퍼를 재사용한다. 이미 Windows 검증 완료된 경로.

```python
from vibelign.core.project_scan import line_count, safe_read_text

lines = line_count(path)          # splitlines 기반, UTF-8 강제, 예외 안전
text = safe_read_text(path)       # UTF-8 + errors=ignore (실제 구현: vibelign/core/project_scan.py:38)
```

직접 `read_text` 를 쓰는 경우에도 반드시 인코딩을 명시:
```python
text = path.read_text(encoding="utf-8", errors="replace")
# 또는 기존 헬퍼와 동작을 맞추고 싶으면 errors="ignore"
```

#### (2) `count('\n')` 을 새 기준으로 도입하지 말 것

`risk_analyzer`/`doctor` 는 이미 `line_count(path) = len(text.splitlines())` 을 쓴다. 기획안이 `count('\n')` 을 도입하면:
- 끝줄에 개행 없는 파일에서 off-by-one
- doctor 는 500줄로 보고, guard 는 499줄로 판정 → 사용자 혼란

**수정**: `line_count()` 한 곳만 사용. EC-7 (실제 코드 줄수) 도입 시에도 여기서만 로직 변경.

#### (3) 레거시 JSON 경로 키 정규화

**문제** — `str(path.relative_to(root))` 는 Windows 에서 `"src-tauri\\src\\lib.rs"`, Unix 에서 `"src-tauri/src/lib.rs"`. 키 불일치로 **모든 레거시 파일이 "신규 파일" 로 오판 → 500줄 block 대폭발**.

추가로 macOS 는 한글 파일명이 NFD 로 반환되는 경우가 있음. 기존 `vib_guard_cmd.py:_decode_guard_git_path` 가 `unicodedata.normalize("NFC", ...)` 쓰는 이유.

**수정**
```python
import unicodedata

def _normalize_legacy_key(root: Path, path: Path) -> str:
    rel = path.resolve().relative_to(root.resolve())
    return unicodedata.normalize("NFC", rel.as_posix())

def _lookup_legacy(legacy_list: dict, root: Path, path: Path) -> dict | None:
    key = _normalize_legacy_key(root, path)
    return legacy_list.get(key)
```

reader 는 양방향 호환(backslash → forward slash 변환) 유지.

### 12-2. HIGH — 설계 자체의 현실 불일치

#### (4) `structure_planner` API 재검토

**문제** — 기획안 §4-3, §8 은 `run_structure_planner(target_file=path)` 로 "이 파일 분리안" 을 뽑는다고 가정. 실제 `build_structure_plan(root, feature: str, ...)` 은 **기능 설명 문자열** 을 받아서 새 파일 경로 제안만 한다. 함수 단위 분리 엔진이 **지금은 없음**.

§8 의
> "handle_login() 을 auth_handler.py 로, refresh_session() 을 session_manager.py 로"

이 메시지는 현재 엔진으로 생성 불가. function-level AST 분석 신규 구현이 필요하고, 이는 Phase 2 에 들어갈 분량이 아니다.

**수정 — 2단계로 분할**
- **v1 (Phase 2 포함)**: 파일 단위 제안만. "auth.py 가 520줄이니 `vibelign/core/auth_extension.py` 로 신규 모듈 생성" 수준. 기존 `build_structure_plan` 을 `target_path` 파라미터 받도록 확장 (`scope` 에 파일 디렉터리 넣는 식).
- **v2 (별도 Phase, 장기)**: `function_splitter.py` 신규 — AST 파싱 기반 함수 단위 분리안. §8 의 풍부한 메시지는 v2 완성 후 활성화.

#### (5) Claude hook PreToolUse 가 `Write` 만 본다

**문제** — `vib_precheck_cmd.py:52` 는 `tool_name == "Write"` 일 때만 검사. 기획안은 `Edit`/`MultiEdit`/`NotebookEdit` 을 고려하지 않음. Edit 으로 500줄 파일에 100줄 추가하는 시나리오 그대로 통과.

**수정** — payload 파서를 도구별로 분기:

```python
def _payload_file_info(payload: dict[str, object]) -> tuple[str | None, str | None]:
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None, None
    raw = cast(dict[str, object], tool_input)
    file_path = raw.get("file_path")
    if not isinstance(file_path, str):
        return None, None

    if tool_name == "Write":
        content = raw.get("content")
        return (file_path, content) if isinstance(content, str) else (None, None)
    if tool_name in {"Edit", "MultiEdit"}:
        # 기존 파일 + patch 미리보기로 최종 크기 계산
        existing = _read_existing_or_empty(file_path)
        simulated = _apply_edits_simulate(existing, raw)
        return file_path, simulated
    return None, None
```

### 12-3. MEDIUM — 돌아가지만 사고 나기 쉬운 것

#### (6) 레거시 목록은 **커밋**한다 (EC-10 재검토)

EC-10 옵션 A(gitignore + 로컬 전용) 는 CI 를 깨뜨린다:
- 로컬: refresh 한 개발자 → 통과
- CI: legacy list 없음 → 기존 2000줄 파일 전부 500줄 block → 모든 PR 실패

**수정 — 커밋하되 머지 충돌은 래칫으로 자동 해결**

```python
# 머지 시 양쪽 baseline 중 더 작은 쪽 채택 (EC-4 래칫의 연장)
def merge_legacy_lists(ours: dict, theirs: dict) -> dict:
    merged = dict(ours)
    for rel, entry in theirs.items():
        if rel not in merged:
            merged[rel] = entry
            continue
        # 더 낮은 baseline 선택 = 리팩토링 진행 기록 보존
        merged[rel]["baseline_lines"] = min(
            ours[rel]["baseline_lines"],
            entry["baseline_lines"],
        )
    return merged
```

`.gitattributes` 에 `legacy_large_files.json merge=vibelign-ratchet` 등록 + 커스텀 merge driver 연결하면 자동 해결.

#### (7) staged vs working tree 분기

**문제** — §4-2 pre-commit 스니펫은 `path.read_text()` (=working tree). 커밋되는 건 staged content. working tree 와 staged 가 다른 상태(부분 add) 에서 **검사 회피 가능**.

**수정** — 기존 `vib_guard_cmd.py` 의 `_new_file_text(root, rel_path, staged_only=True)` + `_run_guard_git(root, ["show", f":{rel_path}"])` 재사용:

```python
def _staged_line_count(root: Path, rel_path: str) -> int:
    ok, staged = _run_guard_git(root, ["show", f":{rel_path}"])
    if ok:
        return len(staged.splitlines())
    try:
        return line_count(root / rel_path)  # fallback
    except OSError:
        return 0
```

pre-commit 경로는 **반드시 staged 기준으로** 세고, guard 일반 실행 경로는 기존 동작(explain_report 의 `staged_only` 플래그) 유지.

#### (8) 바이너리/비소스 파일 필터 누락

changed files 에 `.png`, `.ico`, `.pdf`, `.sqlite`, PyInstaller 산출물이 들어오면 `read_text(encoding="utf-8")` 예외. 기획안 §EC-2 는 "설정 파일/테스트/migrations" 만 제외.

**수정** — 기존 `COMMENT_PREFIX` (vibelign/core/anchor_tools.py) = 소스 확장자 allowlist 이걸 재사용:

```python
from vibelign.core.anchor_tools import COMMENT_PREFIX

_LINE_LIMIT_EXTS = set(COMMENT_PREFIX.keys())  # .py .js .ts .tsx .rs ...

def _is_line_limit_target(path: Path) -> bool:
    if path.suffix.lower() not in _LINE_LIMIT_EXTS:
        return False
    # 기존 exclude glob 도 같이 체크 (EC-2)
    return not _matches_exclude_patterns(path)
```

Node `dist/`, PyInstaller `build/`, 체크포인트 `.vibelign/checkpoints/` 은 별도 exclude 에 기본 포함.

#### (9) pre-commit 에서 `plan-structure` 자동 실행의 속도 문제

**문제** — `build_structure_plan` 은 project_map 전체 로드. 500줄 초과 파일 10개면 10번 실행 = 커밋마다 수 초~수십 초 지연. 사용자가 `--no-verify` 남용 경로로 갈 실제 위험.

**수정 — 캐싱은 pre-commit 자동 연동보다 먼저 구현한다**:

```python
# .vibelign/plan_cache.json
{
  "vibelign/core/auth.py": {
    "mtime": 1713628800.0,
    "hash": "sha1:abc123...",
    "plan": { ... plan JSON ... },
    "cached_at": "2026-04-21T..."
  }
}
```

guard 는 (a) 줄수 체크 먼저 (빠름), (b) block 대상에 대해서만 cache lookup → miss 면 plan-structure 실행. pre-commit 은 plan-structure 를 동기 실행하지 않고 **"`vib plan-structure <file>` 을 실행하세요" 안내만** 하는 것도 대안. (§8 의 "자동 가이드" 는 `vib watch` 나 Claude hook 같은 비동기/backgound 경로가 더 적합.)

#### (10) pre-commit hook 마커 버전 bump

현재 `_HOOK_MARKER = "# vibelign: pre-commit-enforcement v2"` (vibelign/core/git_hooks.py:12).

**수정** — 규칙이 바뀌면:
1. 마커 `v2` → `v3`
2. `install_pre_commit_secret_hook` 이 v2 마커 감지 시 자동으로 v3 로 교체 (기존 "existing-hook" 반환 말고 "migrated" 추가)
3. 기존 프로젝트에서 `vib start --refresh` 시점에 hook 재설치

### 12-4. MVP 실행용 체크리스트

아래 순서대로 진행하면 된다. 핵심은 **문서 → guard → legacy 동결**까지만 먼저 끝내고, 나머지는 후속으로 남기는 것이다.

#### Phase 1 — 문서 반영

- [ ] `AI_DEV_SYSTEM_SINGLE_FILE.md` §6에 300/500 줄 기준 반영
- [ ] `AGENTS.md` / `CLAUDE.md` 상단에 핵심 규칙 요약 반영
- [ ] `vibelign_exports/claude/RULES.md`에 동일 핵심 수치 반영
- [ ] `AI_DEV_SYSTEM_SINGLE_FILE.md` 전체를 `AGENTS.md`/`CLAUDE.md`에 복제하지 않았는지 확인
- [ ] 문서 diff 에서 safe mode 계약 문구(`patch_get → target_anchor-only edit → guard_check → checkpoint_create`)가 바뀐 부분이 없는지 확인
- [ ] 문서 표현에서 `vib plan-structure`를 보편 필수 절차로 올리는 문구가 새로 들어가지 않았는지 확인

#### Phase 2 — `vib guard` MVP 구현

- [ ] 줄수 카운트는 `line_count(path)` 헬퍼 재사용 (`count('\n')` 신규 도입 금지)
- [ ] `read_text()` 직접 호출이 필요하면 `encoding="utf-8"` + `errors="replace"` (또는 헬퍼와 동일하게 `errors="ignore"`) 명시, 혹은 `safe_read_text()` 재사용
- [ ] 줄수 체크 대상은 `COMMENT_PREFIX.keys()` allowlist 기반으로 제한
- [ ] 300줄 경고 / 500줄 차단 로직 추가
- [ ] 기존 500줄 초과 파일은 **baseline 동결** 방식으로 증가만 차단
- [ ] 레거시 JSON 키는 `.as_posix()` + `unicodedata.normalize("NFC", ...)` 로 표준화
- [ ] legacy list 는 **커밋**하고, 이후 머지 전략은 래칫 방식으로 정리

#### Phase 2 검증

- [ ] 300줄 이하 파일은 정상 통과 확인
- [ ] 301~500줄 파일은 warn 판정 확인
- [ ] 신규/일반 파일 500줄 초과는 block 판정 확인
- [ ] 기존 legacy 대형 파일은 줄수 증가 없으면 통과, 증가하면 block 확인
- [ ] Windows/한글 파일명 경로에서도 decode/경로 정규화 문제 없는지 확인
- [ ] macOS 의 NFD (자모 분리) 한글 파일명이 legacy list 키 조회 시 정상 매칭되는지 확인 (`_normalize_legacy_key` 의 `unicodedata.normalize("NFC", ...)` 동작 검증)

#### 후속 Phase로 미루는 항목

- [ ] pre-commit 경로 staged 판정 (`git show :rel_path`) 연동
- [ ] hook 마커 버전 bump + migration
- [ ] Claude hook precheck 를 `Write`/`Edit`/`MultiEdit` 모두 커버하도록 확장
- [ ] structure_planner 연동은 **파일 단위 v1** 부터 시작, 함수 단위 분리는 별도 Phase
- [ ] pre-commit 의 plan-structure 자동 실행 전 **캐시를 먼저 구현**

### 12-5. 수정된 Phase 계획 (기존 §7 대체)

| Phase | 내용 | 난이도 |
|-------|------|--------|
| **Phase 1** | 문서 수정 (§2, §3). `AGENTS.md`/`CLAUDE.md`에 핵심 규칙 요약 승격, export된 `RULES.md`까지 수치 반영. safe mode 계약은 유지 | 쉬움 |
| **Phase 2** | `vib guard` 에 줄수 체크 + legacy list. 경로 정규화, staged/working 분기, 바이너리 필터 포함 | 중간 |
| **Phase 3** | pre-commit hook 마커 v3 + migration. 500줄 staged block | 쉬움 |
| **Phase 4** | 앵커 메타 자동 warning (§4-4). `line_count` + NFC 재사용 | 쉬움 |
| **Phase 5** | Claude hook precheck 확장 (Write/Edit/MultiEdit 커버). 파일 단위 가이드 연동 | 중간 |
| **Phase 6 (장기)** | function-splitter AST 구현. §8 의 풍부한 메시지 활성화. EC-1 순환 import 감지 | 어려움 |

이 표가 **현재 문서의 최종 실행 계획** 이다. 앞쪽 §7은 요약일 뿐이고, 뒤의 §13은 연구 메모이므로 이 계획을 대체하지 않는다.

Phase 1~2 만 해도 실질적 효과는 대부분 확보된다. 그 이후 단계는 guard만으로 부족하다는 증거가 생길 때 순차적으로 올린다.

---

### 12-6. 추가 보강 사항 (2026-04-22 검토 반영)

§12 플랫폼 호환성 검토 이후 재대조에서 발견된 7개 항목. 이 섹션은 앞 문서를 전면 대체하는 새 정책이 아니라, **§12-5 실행 계획을 실제 코드와 맞게 보정하는 구현 보강 메모** 다. 따라서 범위·순서의 최종 기준은 계속 §12-5에 두고, 세부 구현 해석이 충돌하는 지점만 §12-6 수정사항을 우선 적용한다.

#### (11) pre-commit = `vib guard --strict` 호출 [High]

`vibelign/core/git_hooks.py:88` 의 hook 스크립트는 실제로 `vib guard --strict` (fallback: `vibelign guard --strict`) 만 호출한다. 따라서 §4-2 의 "pre-commit hook 에 줄수 체크 추가" 는 별도 python 체크 스크립트를 hook shell 에 끼워 넣는 작업이 **아니다**. guard 내부에 줄수 체크를 넣으면 pre-commit 에도 자동 반영된다.

**수정** — §12-5 Phase 3 을 "pre-commit 자체 구현" 이 아니라 **"staged_only 경로 검증 + `_HOOK_MARKER` v2 → v3 bump + 기존 설치본 migration"** 로 범위 축소. 중복 python 체크 스크립트 금지.

#### (12) Phase 1 은 Python 문자열 리터럴 편집 [High]

`AI_DEV_SYSTEM_SINGLE_FILE.md`, `AGENTS.md`, `RULES.md` 는 저장소에 정적 .md 로 있는 게 아니라 Python 소스 상수로 박혀 있다:

- `vibelign/core/ai_dev_system.py` — AI_DEV_SYSTEM_CONTENT 정본
- `vibelign/commands/export_cmd.py:545` — `_RULES` / AGENTS·CLAUDE 요약 섹션 문자열
- `vibelign/commands/vib_start_cmd.py:249` — 생성 매핑 `("AI_DEV_SYSTEM_SINGLE_FILE.md", AI_DEV_SYSTEM_CONTENT)`

**수정** — §12-4 Phase 1 체크리스트에 다음 3개 항목을 추가 적용:

- [ ] `vibelign/core/ai_dev_system.py` 의 AI_DEV_SYSTEM_CONTENT 상수 수정 (정본)
- [ ] `vibelign/commands/export_cmd.py` 의 `_RULES` 및 AGENTS/CLAUDE 요약 문자열 수정 (export 전용 요약)
- [ ] `vibelign/commands/vib_start_cmd.py` 생성 매핑 최신 값 반영 확인

".md 편집" 만으로 끝난 PR 은 검증 누락. PR diff 에 Python 파일 변경이 반드시 포함되어야 한다.

#### (13) Claude precheck 줄수 체크는 기존 `_planning_status` 에 삽입 [Medium]

`vibelign/commands/vib_precheck_cmd.py:83` `_planning_status()` 는 이미 `small_fix_line_threshold` + `classify_structure_path` + `is_structure_production_kind` 기반 gating 중. §4-3 의 새 `precheck_file_write` 를 별도로 추가하면 병렬 gating 두 개가 된다.

**수정**
- 새 함수 대신 `_planning_status` 내부에 줄수 분기 삽입 또는 그 뒤 체이닝.
- Edit/MultiEdit 시뮬레이션은 기존 `_added_line_count()` (SequenceMatcher 기반) 이 이미 diff 라인 계산을 하므로 재사용.

#### (14) EC-4 래칫의 자동 갱신 시점 확정 필요 [High]

"커밋 성공 시 baseline 자동 하향" 은 현 hook 구조에서 실제로 자동이 아니다. `git_hooks.py` 에 **post-commit hook 이 없고**, pre-commit 에서 JSON 을 수정해도 staged 에 포함되지 않아 변경이 사라진다.

**수정 — 다음 중 하나로 명시 결정**
- **(a)** `.git/hooks/post-commit` 신설 + 별도 `vib ratchet --update` 커맨드 호출 (반자동)
- **(b)** `vib guard` / `vib doctor` 실행 시 갱신 — 실질 "준-수동" 래칫
- **(c)** pre-commit 이 legacy list 수정 후 `git add` + 현재 커밋에 amend — 비권장 (커밋 해시 변경 및 우회 위험)

**기본값 (b)**. 증거 축적 후 장기에 **(a)** 로 승격. §10 과 §EC-4 의 "자동" 문구는 (b) 기준으로 해석.

#### (15) `vib doctor` 임계값 정합 [Medium]

`vibelign/core/risk_analyzer.py:145,159,170,181` 은 **500/800/1000** 3단계 severity. guard 의 **300/500** 과 불일치하면 동일 파일에 대해 두 도구가 서로 다른 경고를 내서 사용자 혼란.

**수정 — Phase 2 에 doctor 정합 조정 포함**

| 계층 | 기준 줄수 | 의미 |
|---|---|---|
| guard warn / doctor info | 300+ | 분리 검토 |
| guard block / doctor medium | 500+ | 신규 코드 차단 + 우선 리팩토링 |
| doctor high | 800+ | 강력 권고 |
| doctor critical | 1000+ | 동결 권장 |

doctor info 를 300 으로 내려 guard warn 과 정렬. 상위 단계(500/800/1000) 는 유지.

#### (16) EC-6 `.tsx` 임계값 근거 보강 [Low]

현 EC-6 의 `.tsx warn:500 block:700` 은 설정 예시 수준이고 검증된 수치가 아니다. React 컴포넌트 500줄은 이미 과도.

**수정**
- Phase 1 설정 확정 **전에** 실제 프로젝트 `.tsx` 파일 줄수 분포를 `vib doctor` 로 수집.
- p75 기준으로 재산정 (일반적으로 400/600 수준).
- 필요 시 JSX return 블록과 로직 영역을 분리 카운트하는 별도 통계 도입.

#### (17) 새 파일 생성 시 anchor 템플릿 지침 [Low]

`vibelign/commands/vib_precheck_cmd.py:201` `_has_anchor_markers` 가 앵커 없는 새 파일을 차단한다. "새 파일 우선" 정책과 결합하면 anchor 템플릿 없이는 AI 경로가 막힌다.

**수정 — §2-1 문서 본문에 다음 지침 추가**
- 새 파일 생성 시 최소 `<FILENAME>_START` / `<FILENAME>_END` anchor 한 쌍을 파일 맨 위/아래에 삽입 필수.
- 공개 함수는 선택적으로 각각 `<FUNC>_START` / `<FUNC>_END` 로 감쌀 것.
- 자동 스캐폴드 (`vib scaffold --new-file <path>`) 는 **Phase 5 이후 장기 과제** 로 분리.

---

#### 12-6 요약: 위험도별 반영 지점

| 위험도 | 번호 | 주제 | 반영 위치 |
|---|---|---|---|
| High | (11) | pre-commit = guard 중복 방지 | §12-5 Phase 3 범위 축소 |
| High | (12) | Python 리터럴 체크리스트 3항목 | §12-4 Phase 1 |
| High | (14) | 래칫 갱신 시점 (b) 확정 | §10 / EC-4 |
| Medium | (13) | precheck 이중 gating 방지 | §4-3 |
| Medium | (15) | doctor 임계값 정합 | §12-5 Phase 2 |
| Low | (16) | .tsx 임계값 분포 기반 재산정 | §EC-6, Phase 1 선행 |
| Low | (17) | 새 파일 anchor 템플릿 | §2-1 |

Phase 1 진입 전: (12)·(16) 선반영.
Phase 2 실행 중: (11)·(13)·(14)·(15) 구현과 함께 결정.
(17) 은 문서 수정 시 병행.

---

*§12 는 2026-04-21 플랫폼 호환성 점검 세션에서 추가. 실제 코드(`vibelign/commands/vib_guard_cmd.py`, `vibelign/core/git_hooks.py`, `vibelign/core/risk_analyzer.py`, `vibelign/core/structure_planner.py`, `vibelign/core/anchor_tools.py`, `vibelign/commands/vib_precheck_cmd.py`) 대조 결과 기반.*

---

## 13. 후속 연구 메모 — 동적 규칙 체계는 별도 RFC 로 분리

§1~§12-6 의 현재 제안은 **고정 임계값(300/500/80/300) + legacy list + guard 중심 강제** 를 전제로 한다. 이 문서의 채택 범위도 여기에 맞춘다. 따라서 아래 메모는 **현 기획안의 override 가 아니라, guard MVP 가 실제로 운영된 뒤 검토할 별도 연구 주제** 로만 남긴다.

즉, **현재 채택안의 최종 기준은 §12-5 / §12-6** 이며, 본 섹션은 그 결정을 대체하지 않는다.

### 13-1. 왜 이 메모를 남기는가

2026-04-22 기준 VibeLign 자체 코드베이스를 보면, 고정 숫자만으로는 설명되지 않는 긴장점이 있다.

| 대상 | 분포 | 관찰 |
|---|---|---|
| Python 137개 | p50=129 / p75=322 / p90=615 / p99=1500 / max=1748 | 300 warn 은 설명력이 있지만, 500 block 은 기존 대형 파일이 많은 저장소에서는 충돌 가능성이 큼 |
| TSX (GUI) | max=1184 (Onboarding.tsx) | 프론트엔드 파일은 언어/도메인별 예외 논의가 필요함 |
| Rust (Tauri) | lib.rs=1767 | 구조상 큰 진입/등록 파일이 생기는 언어는 별도 취급 가능성이 있음 |

이 관찰은 중요하지만, **곧바로 현재 MVP 정책을 갈아엎어야 한다는 뜻은 아니다.** 지금 단계에서 더 중요한 것은 “AI가 큰 파일을 계속 키우는 행동을 먼저 줄이는 것” 이고, 그 목적에는 §12-5 / §12-6 경로가 더 직접적이다.

### 13-2. 왜 지금은 동적 체계로 가지 않는가

동적 규칙 체계는 흥미롭지만, 현재 문서에 바로 편입하면 범위가 너무 커진다.

- `thresholds.json` 같은 신규 정책 파일 도입
- `vib calibrate` 같은 신규 커맨드 도입
- 세션 패턴 추적을 위한 상태 저장(`session_state.json`)
- guard / doctor / precheck / hook 의 정책 소스 재정렬
- 기존 §2 / §4 / §9 / §12-5 의 의미 자체 재작성

이건 “Phase 2 이후 후속 개선” 이 아니라 **정책 엔진 재설계** 에 가깝다. 따라서 본 문서의 MVP 성격과 충돌한다.

### 13-3. 별도 RFC 로 승격할 조건

아래 조건이 쌓일 때에만 동적 규칙 체계를 별도 RFC 로 올린다.

1. §12-5 Phase 1~2 가 실제로 적용된 상태로 **최소 4주 이상 운영** 되어 있을 것 (또는 `vib guard` 가 실제 판정을 내린 누적 이력 30건 이상). 단순 "적용 순간" 이 아니라 운영 데이터가 쌓인 뒤를 뜻한다.
2. `vib guard` 운영 결과, 고정 300/500 기준이 반복적으로 과차단 또는 과소차단을 만든다는 증거가 있을 것
3. 언어별/도메인별 예외가 실제 사용자 시나리오에서 반복 확인될 것
4. precheck / hook / doctor / guard 간 정책 정합을 다시 설계할 여력이 있을 것

즉, **증거가 쌓이기 전에는 동적 체계를 현재안에 섞지 않는다.**

### 13-4. 후속 RFC 에서 다룰 후보 주제

다음 항목은 버리지 않고, 별도 연구 주제로 보존한다.

- 프로젝트 분포 기반 warn/block 보정
- 확장자별 또는 디렉터리별 임계값 차등 적용
- 세션 단위 패턴 감지(같은 파일 반복 확장, 세션 내 급격한 증가)
- PR / 커밋 단위 변화율(ΔLOC) 기반 판정 — 절대 줄수와 독립적으로 "확장 vs 유지보수" 를 구분하는 접근
- `vib calibrate` 류의 정책 측정/제안 워크플로
- Dogfooding 결과를 반영하는 floor 재산정

다만 이 항목들은 **현재 문서의 Phase 계획을 대체하지 않으며**, 구현 착수 전 별도 문서에서 다시 문제 정의부터 검증해야 한다.

### 13-5. 현재 문서의 최종 결론 재확인

이 문서의 목적은 동적 정책 엔진 설계가 아니라, **현재 구조를 크게 흔들지 않고 AI의 대형 파일 비대화를 먼저 줄이는 최소 강제 경로를 정하는 것** 이다.

따라서 이 문서의 최종 채택안은 다음과 같다.

- **문서 수치화**: `AI_DEV_SYSTEM_SINGLE_FILE.md`, `AGENTS.md`, `CLAUDE.md`, export 규칙 요약에 핵심 수치 노출
- **실제 차단 경로**: `vib guard` 를 기준 enforcement path 로 강화
- **레거시 보호**: 기존 대형 파일은 baseline 동결로 증가만 차단
- **후속 연동**: pre-commit / anchor warning / Claude precheck 확장은 §12-5 순서대로 후속 적용

정리하면, **이 문서는 §12-5 / §12-6 까지가 본안이고, §13 은 별도 RFC 후보 메모** 다.

---

*§13 메모는 2026-04-22 세션에서 추가된 동적 규칙 아이디어를 보존하기 위한 것이다. 다만 본 문서에서는 채택안을 대체하지 않고, guard MVP 운영 뒤 별도 RFC 로 재검토할 후보 주제로만 유지한다.*

---

## 14. Phase 1~2 착수 전 엣지케이스 대응 (2026-04-22 추가)

§11 의 EC-1~11 과 §12-6 의 (11)~(17) 이후 Phase 1~2 **실행 시나리오** 를 재점검한 결과, 구조 설계와는 별개로 실제 코딩/롤아웃 단계에서 터질 수 있는 케이스가 더 있다. 이 섹션은 §12-5 Phase 계획의 **착수 전 리스크 해소** 가이드로만 기능한다 (기획 방향 변경 아님).

### 14-1. Phase 1 (문서/Python 리터럴 편집) 엣지케이스

#### P1-A. Python 리터럴 내 embedded backtick / triple-quote [High]

`ai_dev_system.py` 의 `AI_DEV_SYSTEM_CONTENT` 상수는 triple-quoted string 에 마크다운 코드블록(```\`\`\`\```)을 이미 포함한다. 새 300/500 규칙 설명을 추가하며 triple-quote 경계가 깨질 위험.

**대응**
- 수정 시 f-string 변환 금지, raw triple-quote 유지
- CI 에 `python -c "import vibelign.core.ai_dev_system"` 검증 스텝 추가
- PR 시 `grep -c '"""' vibelign/core/ai_dev_system.py` 로 개수 균형 확인

#### P1-B. `vib start --refresh` 가 사용자 수동 편집을 덮어씀 [High]

사용자가 CLAUDE.md 에 팀 규칙을 수동 추가한 상태에서 refresh 시 소실 위험.

**대응**
- Phase 1 착수 전 **현재 `vib_start_cmd.py` 가 overwrite 방식인지 merge 방식인지 먼저 조사**
- 덮어쓰기면 다음 중 선택:
  - (a) **Marker 기반 merge** — `<!-- vibelign:managed-start --> ... <!-- vibelign:managed-end -->` 블록만 교체, 외부 사용자 편집 보존
  - (b) **자동 백업** — `CLAUDE.md.bak.2026-04-22` 로 타임스탬프 백업 후 덮어쓰기
  - (c) **Diff 승인** — refresh 가 diff 출력 후 `--yes` 플래그로만 적용

(a) 가 장기적으로 가장 안전. Phase 1 에 최소한 (b) 는 도입.

#### P1-C. Export 다중 툴 브랜치 동기화 [Medium]

`vibelign_exports/{claude,cursor,opencode}/RULES.md` 가 각자 존재 (향후 gemini/windsurf 추가 가능). `export_cmd.py` 의 `_RULES` 가 단일 상수면 자동 동기화되지만, 툴별 분기가 있으면 누락 발생.

**대응**
- Phase 1 착수 전 `export_cmd.py` 조사 — `_RULES` 가 단일 상수인지 툴별 분기인지 확인
- 툴별 분기면 하나의 정본 상수에서 파생되도록 리팩토링 선행
- PR 체크리스트에 "export 대상 툴 전체 diff 확인" 명시

#### P1-D. Phase 1 배포 후 Phase 2 배포 전 "말-행동 불일치" 기간 [Medium]

문서는 "500줄 초과 금지" 라고 써있지만 guard 는 아직 block 안 함. AI/사용자가 규칙을 무시하는 학습 효과 발생 가능.

**대응**
- **Phase 1 + Phase 2 를 동일 릴리즈에 묶어서 배포** (권장)
- 분리 배포 시 Phase 1 문서에 "실제 차단은 vN+1 부터 적용 — 그 전까지는 권고" 명시

#### P1-E. 한글 + Windows 에디터의 저장 인코딩 [Medium]

Python 3 는 기본 UTF-8 이지만 일부 Windows 에디터가 cp949 로 저장하면 한글 깨짐.

**대응**
- `.editorconfig` 에 `charset = utf-8` 명시 (있는지 확인)
- CI 에 인코딩 검증 스텝 — `file -i vibelign/core/ai_dev_system.py | grep -q 'utf-8'`

#### P1-F. safe mode 계약 문구 다중 출현 [Low]

`patch_get → target_anchor-only edit → guard_check → checkpoint_create` 문구가 소스 내 여러 곳에 반복 등장할 수 있음.

**대응** — 수정 전 `grep -rn "patch_get" vibelign/` 로 모든 출현 위치 선확인. 단일 출처로 일관 수정.

### 14-2. Phase 2 (guard + legacy 동결) 엣지케이스

#### P2-A. **분리 패러독스 — legacy 리팩토링이 새 block 을 만듦** [Critical]

`anchor_tools.py` 1196 legacy 를 800 + 400 로 분할하면:
- 원본: 1196 → 800 (baseline 자동 하향 OK)
- 새 파일 400: green field 판정 → **300 warn 초과**

즉 **"파일 작게 만들라" 는 규칙이 리팩토링 자체를 block 하는 자기모순**.

**대응 — 선택 가능한 3가지**
- (a) **커밋 단위 의도 감지** — 같은 커밋에서 (src 파일 줄수 감소) + (동일 확장자 새 파일 생성) + (새 파일에 src 에서 제거된 함수 시그니처 일부 존재) → 새 파일의 first-commit 은 warn 면제, 그 커밋 줄수를 새 baseline 으로 등록
- (b) **명시적 의도 선언** — `vib refactor-split <src> <new1> [<new2>...]` 명령. 실행 후 N 커밋 동안 해당 파일들은 warn 면제, N 커밋 후 정상 규칙 복귀
- (c) **Legacy 분할 모드** — `vib legacy extract <src> <anchor>` 가 지정 anchor 블록을 새 파일로 이동하며 src/new 모두 baseline 재계산

**권고**: (b) 를 기본 도입. (a) 는 오탐 위험 커서 장기. (c) 는 Phase 6 과 묶어 검토. **Phase 2 시작 전 (b) 구현 포함 결정 필수.**

#### P2-B. Legacy 파일 rename 시 키 단절 [High]

`anchor_tools.py` → `anchor_core.py` 로 rename. git 은 rename 감지하지만 `legacy_large_files.json` 의 키는 옛 이름 → 새 이름은 "신규 1196줄 파일" 로 block.

**대응**
- Guard 가 `git status --porcelain` / `git log --follow` 로 rename 감지
- Rename 감지 시 legacy JSON 키 자동 갱신 + **같은 커밋에 staging 포함**
- 구현: `vib guard` 가 rename 발견 시 JSON 수정 → "legacy list 갱신을 staging 하세요" 메시지 + 자동 `git add legacy_large_files.json` 옵션

#### P2-C. Legacy 파일 삭제 시 고아 엔트리 [Low]

파일 삭제됐으나 JSON 에 record 남음.

**대응** — `vib doctor --cleanup-legacy` 가 고아 감지 + 제거 제안 (자동 실행 아님).

#### P2-D. Merge commit / rebase / amend 에서 hook 미실행 [High]

- `git merge --no-ff`: pre-commit 기본 미실행
- `git rebase`: 각 commit 마다 pre-commit 미실행 (interactive rebase `--exec` 외)
- `git commit --amend`: 실행됨
- 결과: rebase 로 500줄 초과시키면 **block 우회**

**대응 — 필수 3가지 조합**
- (1) **서버 사이드 CI 강제** — `vib guard --strict` 를 main/develop branch protection 에 필수 check 등록. pre-commit 만으론 불완전
- (2) `.git/hooks/post-merge` 추가 hook — merge 후 `vib guard --strict` 실행, 실패 시 사용자에게 경고
- (3) `pre-push` hook 도 `vib guard --strict` 실행 — push 단계에서 다시 검증

(1) 이 가장 강력하고 필수. (2)(3) 은 로컬 UX 보조.

#### P2-E. CRLF / autocrlf 로 로컬-CI 카운트 불일치 [Medium]

Windows autocrlf=true → 저장소 LF, 워킹트리 CRLF. `splitlines()` 는 양쪽 처리하지만 **파일 마지막 CRLF 유무로 ±1 차이** → 같은 커밋인데 로컬/CI 판정 다름 = 재현 불가능 버그.

**대응 — staged content 통일 (§12-6 (11) 경로와 동일)**
- guard 카운트를 **반드시 `git show :rel_path`** 기반으로 (staged content)
- working tree `path.read_text()` 는 non-staged 경로에서만 사용
- `.gitattributes` 에 `* text=auto eol=lf` 를 프로젝트 default 로 권장

이 대응은 §12-6 (11) 과 묶어 동시 구현.

#### P2-F. Symlink / Submodule 파일 [Medium]

- Symlink: `path.resolve()` 하면 원본 가리켜서 경로 일관성 깨짐 + infinite loop 가능
- Submodule: `relative_to(root)` ValueError + 별도 리포 소속이라 guard 대상 아님

**대응** — `iter_project_files` 확장:
```python
if path.is_symlink(): continue
if (path / ".git").is_file(): continue  # submodule marker
```
`has_ignored_part` 에 `.gitmodules` 경로 모두 제외 포함.

#### P2-G. `legacy_large_files.json` 수동 조작 방지 [Medium]

사용자가 block 회피 위해 baseline 을 2000 → 3000 으로 수동 상향 편집 가능. EC-4 래칫은 자동 **하향만** 규정.

**대응 — 3단 방어**
- (1) JSON 에 `integrity` 필드 — baseline_lines 의 해시 (SHA1 short). guard 가 불일치 감지 시 warn + audit log
- (2) Git 히스토리 audit — `git log -p legacy_large_files.json | grep baseline` 으로 baseline 상향 이력 자동 감지
- (3) PR 리뷰 시 JSON diff 검토 체크리스트 명시

(1) 은 구현 간단, (2) 는 CI 에서 수행, (3) 은 문서/프로세스.

#### P2-H. 초기 프로젝트 — legacy list 부재 시 동작 [Low]

신규 프로젝트에서 `legacy_large_files.json` 없음.

**대응** — 파일 없으면 "빈 리스트" 로 해석 (모든 파일 green field 규칙). `vib start --refresh` 가 현재 500+ 파일 스캔 → 초기 JSON 자동 생성. 사용자 확인 후 커밋.

#### P2-I. Guard 성능 — 대량 changed_files 의 I/O [Medium]

100+ 파일 변경 시 매번 read 하면 pre-commit 이 수 초 지연 → `--no-verify` 남용 유발.

**대응 — 3단 최적화**
- (1) changed_files scope 엄수 — 변경되지 않은 파일은 절대 읽지 않음
- (2) 일괄 조회 — `git show :rel_path` 대신 `git cat-file --batch` 사용 (한 번의 프로세스 호출)
- (3) mtime + size 기반 캐시 (`.vibelign/line_count_cache.json`) — 파일 변경 없으면 카운트 재사용

(1) 이 기본, (2) 는 10+ 파일 시 유의미, (3) 은 장기 최적화.

#### P2-J. `vib watch` 와의 정합 [Medium]

현재 watch 는 700/1000 경고. §12-6 (15) 는 doctor 만 정렬. guard=300/500, doctor=300/500/800/1000, watch=700/1000 → **3개 도구 3종류 숫자** = 사용자 혼란.

**대응** — Phase 2 범위에 **watch 재정렬 포함**:
- watch warn = 300 (guard warn 과 일치)
- watch alarm = 500 (guard block 과 일치)
- 또는 watch 를 disable (guard/doctor 로 충분)

`vibelign/core/watch_engine.py` 수정. §12-6 (15) 표에 watch 행 추가 필요.

#### P2-K. Revert 시 ratchet 이 block 을 만드는 역설 [Low]

1500 → 1400 감소 커밋 후 baseline 1400. 이 커밋 revert 하면 파일이 1500 복귀 → baseline 1400 초과 → block. **의도가 revert 인데 block**.

**대응**
- Guard 가 revert commit 감지 (`git log -1 --format=%s | grep '^Revert '`) → baseline 임시 복구 모드
- 또는 `vib ratchet --restore-baseline <file> <value>` 수동 복구 명령
- P2-G 수동 조작 방지와 충돌 방지 위해 `--restore-baseline` 은 git revert 직후에만 허용

#### P2-L. Legacy 파일에서 함수 제거로 줄수 감소 후 복원 [Low]

P2-K 와 동일 구조. 같은 대응 적용.

### 14-3. 공통 운영 이슈

#### X-A. 한국어 에러 메시지의 국제화 [Low]

기획안 메시지 전부 한국어. 영문 로캘 사용자 읽기 어려움.

**대응**
- Phase 2 는 한국어 유지
- Phase 5 이후 `VIB_LANG=en` 환경변수로 영문 지원
- 구조화 로그 병기 — `{"code": "file_line_limit", "ko": "...", "en": "..."}` 로 CI 파서 친화

#### X-B. 팀원 간 vib 버전 불일치 [Medium]

A=v2.1(Phase 2), B=v2.0(Phase 1 만). A 커밋은 block, B 는 통과 → main 이 B 기준 깨진 상태로 유지.

**대응**
- `legacy_large_files.json` 에 `required_min_vib_version` 필드 추가
- Guard 가 버전 체크, 낮은 버전에게 "업그레이드 필요" warn (block 아님 — 배포 시차 허용)
- **CI 가 고정 vib 버전으로 실행** — 실 진실의 근원은 CI. 로컬은 보조

### 14-4. Phase 2 착수 전 필수 결정 3가지 (Critical / High 요약)

1. **P2-A 분리 패러독스 해결 방식 확정** — (a) 자동 감지 / (b) `vib refactor-split` 명령 / (c) `vib legacy extract`. (b) 기본 권고. **Phase 2 의 legacy 구현과 동시 출시 필수**.

2. **P2-D 서버 사이드 CI 필수화** — pre-commit hook 만으로는 merge/rebase 에서 뚫림. main branch protection 에 `vib guard --strict` 를 required check 로 등록하는 게 Phase 2 의 안전성 전제. 로컬 hook (pre-commit + post-merge + pre-push) 은 보조.

3. **P2-E staged content 통일** — guard 의 줄수 카운트를 **반드시 `git show :rel_path` 기반**으로. working tree read 는 staged 가 없을 때의 fallback 으로만. §12-6 (11) 과 묶어 동시 구현.

### 14-5. Severity 매트릭스

| 카테고리 | Critical | High | Medium | Low |
|---|---|---|---|---|
| Phase 1 | — | P1-A, P1-B | P1-C, P1-D, P1-E | P1-F |
| Phase 2 | **P2-A** | P2-B, P2-D | P2-E, P2-F, P2-G, P2-I, P2-J | P2-C, P2-H, P2-K, P2-L |
| 공통 | — | — | X-B | X-A |

Phase 2 착수 전 **Critical 1개 + High 2개 해결** 필수. 나머지는 Phase 2 구현 중 병행 또는 Phase 3~5 에 흡수.

### 14-6. §12-4 Phase 1 체크리스트에 추가할 항목

§14-1 을 §12-4 Phase 1 체크리스트에 병합:

- [ ] `vib_start_cmd.py` 의 refresh 동작 (overwrite vs merge) 확인 (P1-B)
- [ ] `export_cmd.py` 의 `_RULES` 가 단일 상수인지 확인 (P1-C)
- [ ] Phase 1+2 동시 릴리즈 또는 "차단 v2.1 부터" 명시 결정 (P1-D)
- [ ] CI 에 `import vibelign.core.ai_dev_system` 검증 + encoding 검증 스텝 추가 (P1-A, P1-E)
- [ ] `grep -rn "patch_get"` 으로 safe mode 계약 문구 모든 출현 선확인 (P1-F)

---

*§14 는 2026-04-22 Phase 1~2 착수 전 엣지케이스 점검 세션에서 추가. §11 (EC-1~11) 과 §12-6 ((11)~(17)) 이후 **실행 시나리오** 를 재점검한 결과로, 기획 방향 변경 없이 착수 전 리스크 해소 가이드 역할만 한다. Critical 1건 (P2-A 분리 패러독스) + High 3건 (P1-A/P1-B/P2-B/P2-D) 은 Phase 착수 전 해결 필수.*

---

*이 문서는 2026-04-17 Claude Dispatch 세션에서 작성. AI_DEV_SYSTEM_SINGLE_FILE.md §6 수정, AGENTS.md 보강, guard/pre-commit/precheck 코드 수정의 근거 문서로 사용.*
