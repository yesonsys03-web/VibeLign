# CodeSpeak 정확도 개선 설계

## 문제

한국어 구어체 요청 → CodeSpeak 변환이 전반적으로 부정확.

- 규칙 기반 CodeSpeak이 먼저 생성되고, AI 보정이 그 결과에 편향됨
- "돌아오지 않아" → "돌아" → 이동 → `move`로 오분류 (정답: `fix`)
- Gemini Flash Lite가 편향된 규칙 결과를 교정할 능력 부족
- confidence=low이면 프롬프트 자체가 생성 안 됨 (NEEDS_CLARIFICATION 차단)

## 핵심 변경

### 1. 실행 순서 뒤집기

```
현재:  요청 → CodeSpeak(규칙) → AI 보정 → patch_suggester → contract → 출력
제안:  요청 → patch_suggester → AI CodeSpeak 생성(파일/앵커 포함) → contract → 출력
                                  ↓ (AI 없으면)
                            규칙 기반 fallback
```

patch_suggester가 이미 정확한 파일/앵커를 찾고 있으므로 (20 시나리오 AI 19/20), 그 결과를 AI CodeSpeak 생성의 입력으로 활용한다.

### 2. AI CodeSpeak 프롬프트 변경

기존 프롬프트에서 규칙 기반 CodeSpeak 결과를 제거하고, patch_suggester 결과를 전달:

```
사용자 요청: {request}

patch_suggester가 찾은 수정 위치:
- 파일: {target_file} [{category}]
- 앵커: {target_anchor}
- confidence: {confidence}
- 근거: {rationale 요약}

이 정보를 바탕으로 CodeSpeak을 생성하세요.
```

AI가 앵커 이름(예: `LOGIN_RENDER_LOGIN_ERROR`)에서 layer, subject를 직접 추론하고, 요청 문맥("사라지지 않아")에서 action을 판단.

### 3. contract 게이트 완화

```python
# 현재
if confidence == "low" or anchor_status in {"missing", "suggested", "none"}:
    return "NEEDS_CLARIFICATION"

# 제안
if confidence == "low" and codespeak_generated:
    return "READY"  # 경고와 함께 프롬프트 생성
if confidence == "low" and not codespeak_generated:
    return "NEEDS_CLARIFICATION"  # 현재와 동일
```

CodeSpeak이 성공적으로 생성되었으면 confidence=low여도 프롬프트를 생성한다. 사용자에게 confidence가 낮다는 경고는 표시.

## 수정 대상 파일

| 파일 | 변경 내용 |
|---|---|
| `vibelign/patch/patch_builder.py` | 실행 순서 변경: targeting 먼저, CodeSpeak 나중 |
| `vibelign/core/ai_codespeak.py` | 프롬프트 변경: 규칙 결과 대신 파일/앵커 정보 전달 |
| `vibelign/patch/patch_contract_helpers.py` | confidence=low 게이트 완화 |
| `vibelign/core/codespeak.py` | 변경 없음 (fallback으로 유지) |

## 건드리지 않는 것

- `patch_suggester.py` — 이미 검증 완료 (20 시나리오)
- `patch_render.py` — 출력 포맷 유지
- `patch_output.py` — 유지

## 테스트

- 기존 벤치마크 시나리오 20개로 CodeSpeak action 필드 정답률 측정
- confidence=low 시나리오에서 프롬프트 생성 여부 확인
- 기존 patch accuracy 테스트 72개 회귀 없음 확인
