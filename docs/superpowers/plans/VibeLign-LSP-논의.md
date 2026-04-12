# VibeLign LSP 도입 논의 기록

*작성일: 2026-04-11*
*목적: 집 컴에서 이어서 논의할 수 있도록 현재까지의 LSP 관련 논의를 정리*

---

## 1. 출발점 — 논의의 목표

**단 하나의 목적:** `patch`에서 **사용자 자연어 요청 → CodeSpeak 생성**의 정확도 개선.

LSP 도입 자체가 목적이 아니라, 이 목적 달성에 LSP가 얼마나 유효한지, 그리고 현재 VibeLign 코드베이스가 LSP를 받아들일 준비가 됐는지를 검토하는 게 논의의 본질.

---

## 2. LSP가 CodeSpeak 정확도 개선에 도움되는가 — YES (단, 한정된 영역)

### LSP가 실제로 해결하는 것 = "심볼 grounding"

사용자가 자연어로 특정 심볼을 지칭했을 때, 그 심볼이 코드의 어디에 있는지 정확히 꽂아주는 게 LSP의 핵심 가치다.

**예시 1 — "login 함수에 에러 핸들링 추가해줘"**
- 지금: 토큰 "login" 포함된 파일·앵커 스코어링 → 동명 심볼이면 혼동
- LSP: `workspace/symbol`로 `login` 이름 함수 목록 + 파일 + 라인 + 시그니처 + 클래스 소속까지 구조적으로 제공 → LLM이 자신있게 선택 가능

**예시 2 — "여기서 userId를 accountId로 바꿔줘"**
- 지금: 텍스트 치환 → 같은 이름 다른 변수까지 건드릴 위험
- LSP: `prepareRename` + `rename`으로 스코프·참조 정확히 식별

**예시 3 — "null 체크 수정해줘"**
- 지금: 어떤 변수인지 추측
- LSP: `hover` + `diagnostics`로 해당 위치에서 nullable한 실제 변수·타입 정보 제공

### 아키텍처 변화의 본질

```
[지금]
자연어 → 키워드 추출 → 정규식 스캔으로 후보 나열
       → LLM이 추측 기반으로 CodeSpeak 생성

[LSP 도입 후]
자연어 → 키워드 추출 → LSP 쿼리로 정확한 심볼/위치/타입/참조 grounding
       → LLM 프롬프트에 "이 심볼은 여기 있고 시그니처는 이거다"를 함께 전달
       → LLM이 확정된 구조 위에서 CodeSpeak 생성
```

즉 LSP는 **LLM에게 주는 컨텍스트의 질**을 바꿔주는 도구.

### LSP의 한계

1. **자연어 자체는 이해하지 못함** — 사용자 요청이 심볼을 명시하지 않으면("이 파일 깔끔하게 해줘") LSP는 할 일이 없음
2. **신규 코드 생성은 LLM 몫** — LSP는 기존 심볼과의 관계 정보만 제공
3. **LSP 쿼리도 레이턴시 있음** — 캐싱 전략 필요

---

## 3. 현재 코드에서 변경된 점 — 코드맵 + 줄수 표시

사용자가 최근 커밋(`0bde732`)에서 **코드맵에 줄수 표시 로직을 추가**했고, 이 갱신은 **watch 시스템**이 담당한다. watch만 켜놓으면 파일 변경 시 자동으로 줄수가 갱신됨.

### 줄수 표시가 중요한 이유

LLM에 "이 심볼은 file.py의 45~60번째 줄에 있다"를 알려주면 생성된 CodeSpeak가 **위치 기반**으로 앵커링 가능 → 지금 patch 시스템의 SEARCH/REPLACE 텍스트 매칭 문제(주석 속 동일 텍스트, substring 매치, 유일성 검증 실패)가 사라질 수 있음.

### 하지만 숨은 위험

지금 코드맵의 줄수가 정규식/들여쓰기/중괄호 기반으로 추출되고 있다면, 아래 에지 케이스에서 줄수가 틀림:
- JS/TS 객체 리터럴 오인 (함수 범위 잘못 잡힘)
- TS 오버로드 시그니처 (선언부 무시됨)
- Python 중첩 클래스·데코레이터
- 멀티라인 문자열 내 `def`/`class` 키워드

틀린 줄수는 정규식보다 더 위험함 — "LLM이 대충 찍어서 틀린다"가 아니라 **"LLM이 정확한 라인이라고 믿고 틀린다"**가 되기 때문.

### 핵심 관계

- **watch** = "언제 갱신할지" (파일 변경 감지 → 자동 재스캔)
- **정규식 파서** = "무엇을 뽑을지" (심볼 이름, 범위, 줄수)
- **LSP의 역할** = watch가 호출하는 내부 파서를 정규식 → LSP 쿼리로 교체

watch 구조는 건드릴 필요 없고, 파서 레이어만 바꾸는 것.

---

## 4. LSP 도입 준비 상태 — 대부분 "미준비"

현재 코드베이스(commit `0bde732` 기준)가 LSP 교체를 얼마나 쉽게 수용할 수 있는지 5개 축으로 평가.

| 항목 | 평가 | 핵심 근거 |
|------|------|-----------|
| 1. 추상화 레이어 | **미준비** | 18개 파일에서 `anchor_tools`/`project_scan` 직접 import, 단일 facade 없음 |
| 2. 데이터 구조 | **미준비** | character offset 없음, kind 없음, 계층 없음 |
| 3. 호출 집중도 | **부분 준비됨** | guard/doctor는 facade 경유, patch 경로는 직접 하드커플링 |
| 4. 파일 변경 알림 | **부분 준비됨** | watchdog 이벤트가 LSP `didChange`와 의미론적으로 유사. asyncio bridge 필요 |
| 5. 동기/비동기 경계 | **미준비** | core 전체 100% 동기. asyncio는 `mcp_runtime.py` 등 3개 파일에만 고립 |

### 각 항목 상세

**1. 추상화 레이어 — 미준비**

심볼 추출 함수 호출부가 18개 파일·~30개 지점에 산재:
- `strict_patch.py:111` — 패치 적용 핫 경로에서 `extract_anchor_line_ranges` 직접 호출
- `patch_suggester.py:11-14` — `project_scan`, `anchor_tools`, `import_resolver` 3개 직접 import
- `doctor_v2.py:107-115`, `context_chunk.py:14`, `mcp_anchor_handlers.py:28` 등 전방위 직접 의존

추가 이슈: `anchor_tools.py`(747줄) 한 파일에 성격 다른 두 계층이 뒤섞여 있음.
- "VibeLign 고유 앵커 마커 관리" — LSP로 **대체 불가**, 유지 필요
- "소스 코드 구조 파싱" — LSP로 **대체 가능**한 부분

같은 정규식 상수를 공유하며 한 파일에 있어서 교체 경계가 흐릿.

**2. 데이터 구조 — 미준비**

현재 심볼 표현:
```python
SymbolBlock: TypeAlias = tuple[int, int, str, str]  # start_line, end_line, name, indent
```

LSP `DocumentSymbol` 필요 구조:
```json
{
  "name": "...",
  "kind": 12,
  "range": {"start": {"line": 0, "character": 0}, "end": {...}},
  "children": []
}
```

세 가지가 빠짐:
- **character offset** — 줄 단위 patch만 가능한 원인
- **kind** — 함수/클래스/변수 구분 없음
- **children** — 중첩 계층 소실

`scan_cache.py:107-113`의 캐시 엔트리에도 kind 필드 없음.

**3. 호출 지점 집중도 — 부분 준비됨**

- **안전**: `guard_cmd.py`는 `analyze_project()` facade만 사용, `load_project_map` 경유도 문제없음
- **위험**: `strict_patch.py` → `extract_anchor_line_ranges` 하드커플링(이건 LSP 대체 대상 아님, 그대로 유지), `patch_suggester.py:813`는 두 계층 혼합 사용
- `watch_engine.py:417-456`에서 `project_map.json`과 `anchor_index.json` 두 파일을 동시에 씀 → LSP 도입 시 "어디에 동기화할 것인가" 애매

**4. 파일 변경 알림 — 부분 준비됨**

watchdog 이벤트가 LSP와 1:1 매핑 가능:
- `on_modified` ≒ `textDocument/didChange`
- `on_created` ≒ `textDocument/didOpen`
- `on_moved` ≒ `workspace/didRenameFiles`

debounce + batch timer(`watch_engine.py:320-380`)와 incremental invalidation(`scan_cache.py:74,100`)도 이미 있음. 구조적으로 친화적.

**약점**: `threading.Timer` 기반이라 asyncio LSP 클라이언트와 bridge 필요. `_refresh_project_map`이 scan + 두 JSON 파일 쓰기를 타이머 콜백 스레드에서 동기 블록킹 실행.

**5. 동기/비동기 경계 — 미준비**

asyncio 사용처는 `mcp_runtime.py`, `mcp_server.py`, `mcp_dispatch.py` 3파일뿐. core의 심볼 관련 함수 전체가 동기.

asyncio 전면 전환은 18개 파일 rewrite에 해당하므로 현실성 낮음. **별도 `LspClientThread`에 asyncio loop 가두고 동기 Queue API로 노출**하는 방식이 현실적.

---

## 5. LSP 도입 전 선행 리팩토링 Top 3

### 1순위 — `SymbolProvider` Protocol + facade 신설

없는 상태에서 LSP 꽂으면 18개 파일을 한 PR에 수정해야 함. `RegexSymbolProvider`(현재 동작 유지)와 `LspSymbolProvider`(신규)를 같은 Protocol로 교체 가능하게 만들어야 모든 것이 시작됨.

### 2순위 — `scan_cache.py` 스키마 확장

`{name, kind, start_line, start_char, end_line, end_char}` 필드를 캐시 엔트리에 추가. `schema_version`을 2→3으로 bump. `incremental_scan`의 invalidation 플로우가 이미 있어서 watch 이벤트 기반 증분 갱신에 자연스럽게 묻어들어감. 이 단계 이후에야 kind-aware 심볼이 `project_map.json`에 처음으로 저장됨.

### 3순위 — `anchor_tools.py` 물리적 파일 분리

"anchor marker 관리"(VibeLign 고유, 유지)와 "symbol parsing"(LSP 대체 가능)을 같은 파일에 두면 리팩터링 범위가 계속 오염됨. `symbol_extractor.py`로 `_python_symbol_blocks`, `_js_symbol_blocks`, 관련 regex 상수를 이동하면 교체 경계가 명확해짐.

---

## 6. 작업 규모 — 방대함

단계별로 쪼개서 봐야 현실적.

### 1단계 — 구조 리팩토링 (LSP 도입 전 필수 선행) — 약 1~2주

- `SymbolProvider` Protocol + facade 신설
- `anchor_tools.py` 파일 분리 (앵커 관리 vs 심볼 파싱)
- `scan_cache.py` 스키마 확장 + 마이그레이션
- 18개 호출부를 facade 경유로 점진적 교체
- 기존 정규식 로직을 `RegexSymbolProvider` 구현체로 전부 감싸서 회귀 테스트

LSP 안 쓰고 정규식 유지하더라도 이 단계 자체가 코드 정리 + 교체 가능성 확보 가치가 있음.

### 2단계 — LSP 클라이언트 인프라 — 약 1~2주

- `multilspy` 같은 라이브러리 선택 및 의존성 추가
- `LspClientThread` — 별도 스레드에 asyncio loop 가두고 동기 Queue API 노출
- 언어 서버 부트스트랩 (프로젝트 감지, 서버 탐색/설치 가이드, 폴백)
- 워크스페이스 초기화·인덱싱 대기·에러 복구
- watchdog 이벤트 → LSP `didChange` 브릿지

LSP 라이프사이클이 까다로워서 디버깅에 시간 많이 듬.

### 3단계 — `LspSymbolProvider` 구현 + 교체 — 약 0.5~1주

- Protocol 따라서 구현
- Python부터 시작 → 안정화 → TS/JS 추가
- 기존 `RegexSymbolProvider`를 폴백으로 유지 (LSP 실패 시 자동 전환)
- 실제 정확도 비교 측정

### 4단계 — 활용처 확장 — 1주+

- patch_suggester에서 LSP references 활용
- CodeSpeak 생성 시 LSP hover/documentSymbol을 LLM 프롬프트에 주입
- 이 부분이 원래 목표였던 "자연어 → CodeSpeak 정확도 개선"의 실제 구현부

### 총 예상 규모

**집중해서 4~6주.** 중간에 언어 서버 버그나 환경 이슈 만나면 더 길어질 수 있음.

---

## 7. LSP 배포 전략 — 서버는 번들링 못 함

"배포 시 내장"이 이론적으로는 가능하지만 현실적 제약:
- **크기**: pyright만 수십 MB + Node 런타임, TS 서버까지 넣으면 더 커짐
- **플랫폼 의존성**: Node 기반 서버는 OS/아키텍처별 바이너리 필요
- **버전 관리**: 언어 서버는 계속 업데이트됨, 고정 버전 내장은 수명 짧음
- **사용자 환경 충돌**: 사용자가 이미 다른 버전 쓰고 있으면 IDE 경고와 VibeLign 피드백이 달라져 혼란

### 현실적인 방식

- **자동 bootstrap**: 첫 실행 시 `~/.vibelign/servers/` 캐시에 다운로드 (Ruff, Deno 등이 이 방식)
- **사용자 환경 재사용**: 프로젝트에 이미 깔려있으면(node_modules, venv 안이든) 그대로 사용
- **폴백 우선순위**: (1) 프로젝트 로컬 서버 → (2) VibeLign 캐시 서버 → (3) 정규식 폴백

`vib doctor` / `vib start` 시점에 언어 서버 준비 상태 체크 + 안내.

**결론**: 클라이언트 라이브러리는 pip 의존성으로 내장 OK. 서버는 **부트스트랩 방식**이 업계 표준.

---

## 8. 대안 경로 — tree-sitter 또는 에지 케이스 수정

LSP가 "가장 원칙적"이면서 동시에 "가장 비싼" 해결책이라는 점을 고려하면, 중간 단계를 먼저 고려해볼 수 있음.

### 옵션 A — 현재 정규식의 에지 케이스만 핀포인트 수정

- JS 중괄호 파싱 버그, TS 오버로드, Python 데코레이터 문제 등을 개별 수정
- 구조 변화 없음, 1~2일 작업
- 근본적 해결은 아니지만 빠른 개선
- 측정 후 효과 판단

### 옵션 B — tree-sitter 도입

- LSP보다 훨씬 가벼움 — 파서만 제공
- 심볼/범위 정확도는 올려주지만 references·rename·diagnostics 같은 고급 기능 없음
- 설치·통합 비용이 LSP의 1/5 수준
- Python 바인딩 안정적
- **"줄수 정확도"만 원한다면 tree-sitter로 충분할 수 있음**

### 옵션 C — LSP 풀 도입

- 장기적으로 올바른 방향
- 시간·인프라 부담 큼
- 자연어 grounding·타입 정보·diagnostics까지 모두 확보

### 추천 순서

1. **에지 케이스 수정**으로 현재 정확도 한 번 끌어올리기
2. 부족하면 **tree-sitter**로 중간 단계
3. 그래도 한계 느끼면 **LSP**

각 단계마다 "실제 정확도 개선 폭"을 측정하면서 진행. 바로 LSP로 가면 몇 주 쏟았는데 기대만큼 개선 폭이 안 나올 수 있음. 특히 Python 중심 프로젝트면 정규식 파싱도 생각보다 잘 돌아가서 LSP 이득이 작을 수 있음.

---

## 9. 의사결정을 위한 체크리스트

**지금 당장 해야 할 것 (LSP 도입과 무관하게 가치 있음):**
- [ ] 현재 watch + 정규식 조합으로 생성된 줄수의 실제 정확도 측정 (전체 파일 대상, tree-sitter 결과와 비교)
- [ ] JS/TS 파일 비중이 높은지 확인 (정규식 취약점이 체감되는 언어)
- [ ] patch 실패 케이스 수집 — "줄수 오류 → patch 잘못 적용"이 실제로 발생하는지

**측정 결과에 따른 분기:**
- 정확도 95%+ & 현재 patch 실패 드묾 → **LSP 우선순위 낮춤**, 에지 케이스만 수정
- JS/TS 비중 높고 오차 20%+ → **tree-sitter부터** 도입
- 자연어 → CodeSpeak 정확도가 핵심 병목이고 심볼 grounding이 근본 해결책 → **LSP 풀 도입 (선행 리팩토링 포함)**

**선행 리팩토링(SymbolProvider facade 등)은 LSP 도입 여부와 무관하게 가치 있음** — 어느 경로를 가든 1단계는 수행 권장.

---

## 10. 다음 논의 재개 지점

이 문서를 다시 열 때 이어서 논의할 수 있는 지점:

1. 현재 watch가 생성하는 줄수의 실제 정확도를 측정해봤는가? 측정 방법론 상의?
2. JS/TS 사용 비중과 실제 patch 실패 사례를 확인해봤는가?
3. 선행 리팩토링(SymbolProvider facade) 1단계부터 바로 시작할 것인가, 아니면 먼저 tree-sitter로 검증할 것인가?
4. LSP 도입 시 `multilspy` vs `pygls` 직접 구현 중 어느 쪽인가?
5. 언어 서버 부트스트랩 방식(자동 다운로드 vs 수동 안내)에 대한 UX 방향?

---

*이 문서는 2026-04-11 Claude Dispatch 세션에서 이뤄진 논의를 정리한 것. 집 컴에서 LSP 관련 논의를 이어갈 때 참고.*

---

# 제2부 — 후속 논의 (2026-04-11, 같은 날 저녁)

앞의 1~10장은 집 컴 재개용 1차 정리. 아래는 그 위에서 이어진 2차 논의. **핵심 질문이 "LSP를 진짜 도입할지"에서 "도입 판단을 위한 측정을 먼저 할지"로 이동**함.

---

## 11. "LSP 도입하면 CodeSpeak 정확도 개선되는가?" — 조건부 YES

### LSP가 확실히 개선하는 것
1. **동명 심볼 혼동** — `workspace/symbol`로 시그니처·소속 클래스까지 제공 → LLM이 자신있게 선택
2. **줄수 정확도** — JS 객체 리터럴, TS 오버로드, Python 중첩 데코레이터 에지 케이스에서 정규식이 틀리는 걸 LSP는 정확히 잡음
3. **타입 grounding** — `hover`로 "이 변수는 `Optional[User]`다"를 프롬프트에 주입 → null 체크 수정 정확도 ↑
4. **rename/references 정확성** — 텍스트 치환이 건드리면 안 되는 스코프를 LSP는 안 건드림

이 네 가지는 LSP가 아니면 근본 해결 어려움.

### 그럼에도 "결과적 개선"이 보장되지 않는 이유 — 파이프라인은 4단 직렬

```
자연어 → [1] 심볼 grounding → [2] LLM 생성 → [3] patch 포맷 매칭 → [4] 적용
          ↑ LSP가 개선         ↑ LLM 능력      ↑ SEARCH/REPLACE 매칭
```

**가장 약한 고리가 최종 정확도를 결정한다**. LSP는 1단만 강화. 만약 현재 병목이:
- **1번(심볼 grounding)** 지배적 → LSP가 직접 해결 ✓
- **2번(LLM 생성 품질)** 지배적 → LSP 무관, 프롬프트·모델 문제
- **3번(텍스트 매칭 실패)** 지배적 → LSP 도입해도 그대로. character offset 받아도 `strict_patch.py`가 여전히 텍스트 매칭하면 우회 못 함. **CodeSpeak 포맷 자체 변경**이 해법
- **4번(적용 레이어)** 지배적 → 별도 이슈

**즉 "LSP가 결과적 정확도를 개선한다"는 명제는 "현재 병목이 1번이다"라는 전제에 의존**. 그 전제가 검증 안 되면 6~8주 투자가 회수 안 됨.

---

## 12. 의사결정 블로커 — eval 스킬이 필요한 이유

세 가지 선택지(LSP 풀 도입 / tree-sitter / CodeSpeak 포맷 변경) **모두 회수 기간 1주+**. eval 없이 하나를 고르면 "6주 쏟고 5% 개선" 리스크 큼.

**eval 1주 투자 → 나머지 결정 전부 데이터로 정당화**가 훨씬 안전하다는 판단.

### eval 스킬이 측정해야 할 것 — 실패 사유 분해 (G1~G4)

단순 성공률이 아니라 **카테고리별 분포**가 결정표:

| 카테고리 | 측정 방법 | 지배적이면 해결책 |
|---|---|---|
| **G1. 심볼 선택 오류** | 생성된 CodeSpeak가 가리키는 심볼이 ground truth와 다름 | → **LSP 풀 도입** 정당화 |
| **G2. 줄수 오차** | `anchor_spans` 줄수 vs 실제 AST 범위 diff | → **tree-sitter**로 충분 |
| **G3. 텍스트 매칭 실패** | SEARCH 블록이 1회 match 안 됨 (0 or 2+) | → **CodeSpeak 포맷 변경**(anchor_id + 상대 라인) |
| **G4. LLM 생성 오류** | REPLACE 블록이 문법·의도 자체가 틀림 | → 프롬프트·모델 튜닝. 파싱 레이어 무관 |

### 유리한 조건 — 이미 절반은 있음

`tests/benchmark/`에 이미:
- `scenarios.json` (5개 시나리오)
- `sample_project/` (실제 코드)
- `output/condition_A_no_anchor/`, `output/condition_B_with_anchor/` (조건별 프롬프트)
- `vib bench --generate/--score/--report/--json` 서브커맨드

**스캐폴드는 있음. 단 현재 목적이 "앵커 유무 A/B 비교"지 "실패 모드 G1~G4 분류"가 아님 → 상위 분류 레이어 추가 필요**. 완전 재설계 아니라 확장.

---

## 13. 치명적 오류 검사 결과 (2026-04-11, B 단계가 핵심)

eval 설계 **전에** 측정 대상(VibeLign 자체)이 정상 상태인지 확인. A→B→C 순서로 체크.

### A. 런타임 건강성 — **PASS**
- `vib doctor --strict`: exit=1이지만 원인은 "파일 길이·함수 개수" 경고뿐. 파이프라인 정상
- `pytest tests/` (541 pass, 3 subtests, 329초). 실패 0
- patch/anchor 핫스팟 테스트 8개 집중: **94 pass, 3 subtests** (108초)
- `vib bench` 서브커맨드 존재 확인

### B. 데이터 일관성 — **경고: 파서 레이어 버그 4종**

748개 `anchor_spans` 전수 검증 결과:

#### 버그 1. 중복 앵커 이름 (2 파일)
```
vibelign/patch/patch_builder.py::PATCH_BUILDER_BUILD_CONTRACT → lines [60, 255]
vibelign/mcp/mcp_handler_registry.py::MCP_HANDLER_REGISTRY___CALL___ → lines [11, 153]
```
`anchor_index`는 리스트 set-화로 중복 제거 → **두 번째 인스턴스 영원히 접근 불가**. patch_suggester가 `BUILD_CONTRACT` 조회 시 60-63만 반환됨(확인). 94개 patch 테스트가 전부 통과하는데도 살아있음 → **테스트 커버리지 밖**.

#### 버그 2. 유령 span — 문서 문자열 리터럴 오인 (2 파일)
```python
# export_cmd.py:41
- Respect anchor boundaries (`ANCHOR: NAME_START` / `ANCHOR: NAME_END`)
```
이 help 텍스트 때문에 `name='NAME'`인 span이 **7개** 생성. `fast_tools.py`의 `FOO` 예시도 동일. **LSP 논의 본문이 "멀티라인 문자열 내 def/class 오탐"으로 경고한 클래스가 앵커 파서에도 존재함을 실증적으로 확인**.

#### 버그 3. 미완성 span (`end: None`) — 3건
```
export_cmd.py: NAME start=235 end=None
export_cmd.py: NAME start=309 end=None
fast_tools.py: FOO start=111 end=None
```
START만 있고 END 못 찾아서 `end=None`. downstream이 `None`을 int로 쓰면 `TypeError`. 현재는 caller가 `None` guard로 우회.

#### 버그 4. Dunder 이름 정규화 손실 — 3건
```
파일: ANCHOR: CLI_BASE___INIT___START
저장: name='CLI_BASE___INIT'  ← 뒤 underscore 하나 소실
```
파서가 `_START`/`_END` strip할 때 dunder 끝 `_`까지 자름. 줄번호는 정확하지만 name 역참조 실패.

#### 데이터 건강성 숫자
- 총 748 spans
- 줄번호 정확도 (roundtrip OK 721건 기준): **720/721 = 99.86%**
- off-by-1: 0, off-by->1: 1(원인은 중복 앵커로 probe가 헷갈린 것, 실드리프트 아님)
- project_map/anchor_index 동시 갱신(sync 신선)
- protect 목록 0개 (설계대로)

**핵심 판단**: LSP 논의 본문이 걱정한 "줄수 드리프트"는 현 상태에서 **사실상 없음(0.14%)**. 대신 **다른 종류의 파서 버그 4종**이 있고, 이게 LSP 도입보다 훨씬 싸게 고칠 수 있는 실질적 병목.

### C. patch 파이프라인 e2e — **조건부 PASS**
- 관련 테스트 94개 전원 pass. 최근 `e8b1b96` 한글 합성어 회귀도 잡힘
- `scenarios.json` 성격은 A/B 앵커 비교용. G1~G4 분류 하네스 아님 → eval은 상위 레이어 확장 필요
- 기존 caller들이 4종 버그를 암묵 가정(첫 인스턴스만 / None guard)으로 우회 중

---

## 14. 다음 단계 — 4가지 선택지

### 선택지 1 — **파서 버그 4종 먼저 고치고 eval 설계** (권장)
- 소요: 1~2일
- 이유: 모든 버그가 국지적. `anchor_tools.py`의 `extract_anchor_spans`에 4가지만 추가:
  1. 문서 문자열/주석 내 ANCHOR 리터럴 제외 (토큰 아닌 리터럴로 인식)
  2. 중복 감지 시 경고 또는 suffix 자동 할당
  3. END 없는 span은 버리거나 `end=start`로 강제
  4. dunder 끝 `_` 보존 (strip 로직 수정)
- eval baseline이 **의도한 파서 동작** 위에 세워져서 비교 깨끗

### 선택지 2 — 버그를 "측정 대상"으로 취급, 그대로 eval 진행
- 소요: 0일
- 단점: 버그 고치면 baseline 움직임 → LSP 전/후 비교 오염

### 선택지 3 — 최소 기준선: 버그 3(미완성 span)만 고침
- 소요: 30분
- 이유: 버그 3만이 eval runner를 예외로 터뜨릴 수 있음
- 단점: 버그 1·2가 eval 노이즈 상수로 남음

### 선택지 4 — 버그 4종을 eval 첫 시나리오로 정식 등록
- 버그 파일들을 시나리오로 추가 → G1/G3 집계에 자연스럽게 포함
- 장점: 선택지 1·2 장점 결합
- 단점: 기준선 불안정 비용

---

## 15. 사이드 발견 — eval 설계 시 반드시 반영할 것

- **`scenarios.json` 5개 전부 Python**. JS/TS 시나리오 **0개** → 현 상태로 eval 돌리면 "Python 정규식 파싱이 얼마나 잘 돌아가는지"만 측정. LSP/tree-sitter 이득이 가장 큰 JS/TS 영역이 사각지대. **eval 설계 시 JS/TS 시나리오 의도적 추가 필수**
- `vib bench`의 기존 목적은 **"앵커가 AI 정확도에 도움되는가"** (A/B 비교)지 **"실패가 G1~G4 어디에 속하는가"** 분류 아님. 목적 다름. eval은 `vib bench`를 **감싸는 상위 하네스**가 되거나 `vib eval` 새 서브커맨드로 분리
- `doctor_v2.py`가 이미 `analyze_project()` facade 노출 → eval이 재사용 가능
- **ground truth 레이블링 비용**이 eval 품질의 실질적 병목. 20개면 하루, 100개면 일주일. 비용 vs 신뢰도 트레이드오프 먼저 결정
- 자동 분류의 한계: G1과 G4 구분이 어려울 수 있음(심볼 잘못 골랐는데 결과적으로 문법도 깨진 케이스). 처음엔 사람 레이블링 비중 클 것

---

## 16. 수정된 전체 로드맵

```
[1~2시간] 치명적 오류 검사     ← 완료 (2026-04-11)
[1~2일]   선택지 1: 파서 버그 4종 픽스 ← 다음 단계 후보 #1
[30분]    기존 벤치 구조 훑기 (사이드 발견 11/12번 참고)
[반나절]  eval 스펙 초안 (scenarios 포맷, G1~G4 분류 기준, runner IF, 리포트 샘플)
[1주]     eval 스킬 구현 (JS/TS 시나리오 포함)
[0.5주]   첫 측정 — 카테고리 분포 확보
[분기점]  결과 보고 LSP / tree-sitter / 포맷 변경 중 결정
```

**다음 세션 진입점**:
1. 선택지 1·3·4 중 어느 것으로 가나? (타임라인 압박 정도에 따라)
2. 선택지 1이면 → `anchor_tools.py`의 `extract_anchor_spans` 함수 위치부터 찾고 4가지 픽스 계획
3. 선택지 3/4이면 → 바로 eval 스펙 초안 작성
4. ground truth 레이블링 예산 결정 (20개 vs 100개)
5. JS/TS 시나리오 몇 개를 언제 추가할지

---

## 17. 제2부 요약 한 줄

**LSP는 방향으로는 맞지만 충분조건 아님. 병목이 심볼 grounding(G1)인지 검증하는 eval 스킬이 선행 조건이며, 그 전에 `anchor_tools.py` 파서 레이어 버그 4종을 고쳐야 baseline이 깨끗해짐.**

---

*제2부는 2026-04-11 저녁 세션 기록. 제1부와 합쳐 LSP 의사결정 전체 컨텍스트를 구성. 다음 세션은 위 16장 진입점 중 하나를 선택해서 재개.*
