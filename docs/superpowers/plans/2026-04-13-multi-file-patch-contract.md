# Multi-File Patch Contract 구현 계획

> **상태:** 구현 완료 (2026-04-13)
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

## 검토 결과 요약

이 기획의 방향 자체는 맞지만, 현재 초안에는 실제 코드 흐름과 어긋나는 지점이 네 군데 있다.

1. `PatchSuggestion`에 `related_files`를 추가해도, 현재 `vibelign/patch/patch_builder.py`와 `vibelign/core/patch_plan.py` 경로를 거치며 값이 사라진다.
2. 목표는 '역할이 붙은 multi-file contract'인데, 초안의 `scope["allowed_files"]` 예시는 여전히 `list[str]`라서 `patch_render.py` / `patch_handoff.py`에서 역할/앵커/이유를 표현할 수 없다.
3. 초안은 `index.ts`가 이미 `LOW_PRIORITY_NAMES`로 제외된다고 적었지만, 실제 `vibelign/core/patch_suggester.py`의 `LOW_PRIORITY_NAMES`에는 `__init__.*`만 있다. barrel/re-export 필터는 새로 설계해야 한다.
4. 렌더러 위치를 'grep으로 확인 필요'라고 남겨두었지만 실제 반영 지점은 이미 `vibelign/patch/patch_render.py` 와 `vibelign/patch/patch_handoff.py`로 확인된다.

이 문서는 위 네 가지를 반영해서, **데이터 모델 → suggestion 채움 → patch_plan 전파 → contract 표현 → render/handoff → 회귀 테스트** 순서로 다시 정리한 실행 계획이다.

---

## Goal

`vib patch`가 여러 파일 수정이 필요한 요청에 대해 단일 파일만 지정하는 문제를 해결한다.

- `PatchSuggestion` 단계에서 관련 파일들을 구조화해 수집한다.
- `patch_plan` / `contract` / `handoff`까지 같은 정보를 일관되게 전파한다.
- 기존 단일 파일 JSON/Markdown 출력은 유지하면서, multi-file일 때만 richer scope를 추가한다.

## Architecture

현재 `patch_suggester.py`는 이미 `_build_import_pool_expansion()`으로 1-hop import 후보를 계산할 수 있다. 이번 변경의 핵심은 그 후보를 단순 내부 보조 정보로 끝내지 않고, 아래 3계층에 명시적으로 올리는 것이다.

1. `PatchSuggestion.related_files`: 타겟 외 관련 파일 목록
2. `patch_plan.related_files`: downstream contract/render 단계로 넘길 payload
3. `contract.scope.allowed_file_details`: 역할/앵커/사유를 포함한 multi-file scope

호환성 때문에 `scope["allowed_files"]`는 **기존처럼 `list[str]`를 유지**하고, 새 구조는 `scope["allowed_file_details"]`에 추가한다.

### 책임 분리: suggest vs build

`suggest_patch()`는 codespeak/operation 정보가 없다. codespeak 파싱은 `patch_builder.py`의 `build_codespeak()`에서 일어난다. 따라서:

- **`suggest_patch()`**: import 그래프 기반 raw `related_files`만 채움 (operation 무관, 항상 실행)
- **`patch_builder.py`**: codespeak 파싱 후 operation 기반 후처리
  - `move` → `related_files`를 `[]`로 비움
  - `add`/`create` → `_infer_new_file_path()`로 new_file 항목 추가
  - 그 외 → raw 그대로 유지

이렇게 하면 `suggest_patch()`가 codespeak에 의존하지 않고, operation 판단은 이미 codespeak을 가진 `patch_builder.py`에서만 일어난다.

### CodeSpeak 접근 안정성

`patch_builder.py`에서 operation/action/subject를 읽을 때는 **계획서 예시의 속성명(`codespeak.codespeak_parts`, `codespeak.subject`)을 그대로 전제하지 않는다.** 실제 `CodeSpeakResult` 구현이 노출하는 필드명을 먼저 확인한 뒤, 그 구현에 맞춘 helper로 감싼다.

권장 방식:

```python
def _extract_codespeak_action(codespeak: object) -> str:
    ...

def _extract_codespeak_subject(codespeak: object) -> str:
    ...
```

규칙:
- `_build_patch_data_with_options()` 본문에서 속성 체인을 직접 여러 번 쓰지 않는다.
- action/subject 추출은 helper 한 곳으로 모은다.
- 실제 구현 필드명이 계획 예시와 다르면, **코드를 구현에 맞춘다. 계획 예시를 억지로 맞추지 않는다.**

### 관련도 필터 전략

import 그래프 결과는 이미 구조적으로 연결된 파일이므로, **토큰 겹침 필터를 적용하지 않는다.** "watch 실시간 로그 추가" 요청에서 `lib/vib.ts`는 import로 연결되지만 토큰 겹침은 약하다. 토큰 필터를 걸면 정작 필요한 파일이 빠진다.

필터 기준은 barrel 제외 + max 3개 제한만 적용한다.

### role 매핑

`project_map.classify_path()`는 `ui | service | logic | core`를 반환하지만, 스키마의 role은 `primary | routing | component | data_source | utility | new_file`이다. 매핑 함수를 추가한다:

```python
_CLASSIFY_TO_ROLE = {
    "ui": "component",
    "service": "data_source",
    "logic": "utility",
    "core": "utility",
}

def _classify_to_role(classify_result: str | None) -> str:
    if classify_result is None:
        return "utility"
    return _CLASSIFY_TO_ROLE.get(classify_result, "utility")
```

단, 이 매핑은 기본 추론이다. target file의 직접 import인 경우 구조적 위치에서 더 정확한 role을 판단할 수 있으면 override한다 (예: `lib/` 하위면 `data_source`, `components/` 하위면 `component`).

## Tech Stack

Python 3.11+, pytest, pathlib

## Non-Goals

- 이번 변경에서 strict patch를 진짜 multi-operation 자동 생성기로 확장하는 것까지는 포함하지 않는다.
- 2-hop 이상 import graph 탐색은 하지 않는다.
- unrelated file fan-out, 프로젝트 전역 planner, 대규모 AI 후보 재설계는 하지 않는다.

## Compatibility Contract

- 단일 파일 요청이면 `related_files == []` 로 유지하고 기존 출력과 동작을 그대로 보존한다.
- 기존 `contract.scope.allowed_files: list[str]`는 유지한다.
- 추가 메타데이터는 `contract.scope.allowed_file_details: list[dict]`에만 넣는다.
- `move`는 기존 source/destination 2-file contract를 유지하고, 일반 `related_files` fan-out은 적용하지 않는다.
- 새 파일 제안은 contract에 드러나더라도 실제 파일 존재를 전제하지 않는다. precondition 문구에서 '새로 생성될 파일'임을 분리해 표시한다.

## Blocking Risk Closures

아래 4개는 구현 전에 계획 차원에서 먼저 잠가야 하는 블로킹 리스크다.

1. **`PatchPlan.related_files` 누락 금지**
   - `PatchSuggestion`만 바꾸고 `PatchPlan`을 안 바꾸면 multi-file 정보가 직렬화 경로에서 사라진다.
   - 따라서 Task 0은 선택이 아니라 **선행 차단 작업**이다.

2. **`PatchContract.from_context()` 시그니처 먼저 확장**
   - `patch_contract_helpers.py`에서 `related_files`를 넘기기 전에, `vibelign/core/patch_contract.py`의 `from_context()` 시그니처를 먼저 늘린다.
   - 순서를 반대로 하면 런타임 `TypeError`가 날 수 있다.

3. **render / handoff는 단일 파일 분기 유지**
   - `allowed_file_details`가 비어 있으면 기존 single-file 출력 문자열을 유지한다.
   - multi-file일 때만 details 기반 다중 행 포맷으로 전환한다.
   - 즉, 새 포맷은 '대체'가 아니라 '조건부 확장'이다.

4. **문서 내 예시 코드는 ASCII quote만 사용**
   - 코드 블록의 문자열/딕셔너리 예시는 모두 `'` 또는 `"`만 사용한다.
   - 스마트 쿼트는 복붙 시 바로 깨지므로 금지한다.

## 새 데이터 스키마

`related_files`와 `allowed_file_details`는 동일한 payload shape를 공유한다.

```python
{
    "file": "vibelign-gui/src/lib/vib.ts",       # root-relative path
    "role": "data_source",                      # routing | component | data_source | utility | new_file
    "anchor": "VIB",                            # 없으면 None
    "reason": "watch 로그 스트림 함수 제공",     # 왜 포함됐는지
    "exists": True,                              # 새 파일 제안이면 False
}
```

---

## Task 0: 데이터 흐름 먼저 고정

**Why first:** 초안에는 이 단계가 빠져 있어서, `PatchSuggestion.related_files`를 추가해도 `patch_plan`에 전달되지 않는다.

**Blocking invariant:** Task 0이 끝나기 전에는 Task 4 (`PatchContract`) 구현으로 넘어가지 않는다.

**Files:**
- Edit: `vibelign/core/patch_plan.py` (PATCH_PLAN_PATCHPLAN 앵커, 26-51행)
- Edit: `vibelign/patch/patch_builder.py` (PATCH_BUILDER_SUGGESTIONLIKE 앵커 21-26행, PatchPlan 생성 463-491행)
- Test: `tests/test_vib_patch_contract_v0.py`

- [x] **Step 1: 실패 테스트 작성**

```python
def test_build_patch_data_keeps_related_files_in_patch_plan(tmp_path):
    # suggestion.related_files가 patch_plan까지 살아남는지 검증
```

검증 포인트:
- `patch_plan["related_files"]` 존재
- 단일 파일 요청이면 `[]`
- multi-file 요청이면 dict list 유지

- [x] **Step 2: `PatchPlan` 확장**

`vibelign/core/patch_plan.py:47` — `steps` 필드 바로 위에 추가:

```python
related_files: list[dict[str, JsonValue]] = field(default_factory=list)
```

`to_dict()`는 `asdict(self)`이므로 자동으로 직렬화된다.

- [x] **Step 3: `patch_builder.py`에서 전파**

**3a.** `SuggestionLike` protocol (patch_builder.py:21-26)은 수정하지 않는다.
기존 protocol에 필드를 추가하면 하위 호환이 깨질 수 있으므로
`getattr(suggestion, "related_files", [])` 패턴으로 안전하게 읽는다.

**3b.** `PatchPlan(...)` 생성 (patch_builder.py:463-491)에 인자 추가:

```python
patch_plan = PatchPlan(
    schema_version=1,
    ...
    steps=steps,
    related_files=getattr(suggestion, "related_files", []),  # NEW
)
```

`plan_dict`는 `patch_plan.to_dict()`에서 나오므로 별도 처리 불필요.

- [x] **Step 4: serializer 회귀 테스트 추가**

```python
def test_patch_plan_to_dict_keeps_related_files_shape():
    plan = PatchPlan(
        schema_version=1,
        request="test",
        interpretation="test",
        target_file="src/App.tsx",
        target_anchor="APP",
        related_files=[
            {
                "file": "src/lib/vib.ts",
                "role": "data_source",
                "anchor": "VIB",
                "reason": "stream source",
                "exists": True,
            }
        ],
    )
    data = plan.to_dict()
    assert data["related_files"][0]["file"] == "src/lib/vib.ts"
```

이 테스트는 '필드가 있다'보다 더 중요하다. `asdict()` 경로에서 list[dict] shape가 깨지지 않는지 확인해야 한다.

---

## Task 1: `PatchSuggestion`에 `related_files` 필드 추가

**Files:**
- Edit: `vibelign/core/patch_suggester.py` (`PatchSuggestion` dataclass)
- Create: `tests/test_multi_file_suggestion.py`

- [x] **Step 1: 실패 테스트 작성**

```python
from vibelign.core.patch_suggester import PatchSuggestion

def test_patch_suggestion_has_related_files():
    suggestion = PatchSuggestion(
        request="로그 뷰어 추가",
        target_file="src/App.tsx",
        target_anchor="APP",
        confidence="high",
        rationale=["test"],
        related_files=[],
    )
    assert suggestion.related_files == []

def test_patch_suggestion_to_dict_includes_related_files():
    suggestion = PatchSuggestion(
        request="test",
        target_file="a.tsx",
        target_anchor="A",
        confidence="high",
        rationale=[],
        related_files=[
            {
                "file": "b.tsx",
                "role": "data_source",
                "anchor": "B",
                "reason": "state owner",
                "exists": True,
            }
        ],
    )
    data = suggestion.to_dict()
    assert data["related_files"][0]["role"] == "data_source"
```

- [x] **Step 2: dataclass 확장**

```python
related_files: list[dict[str, object]] = field(default_factory=list)
```

`Optional[None]`보다 `default_factory=list`가 낫다. downstream code에서 `None` 분기보다 empty list가 훨씬 안전하고, 기존 단일 파일 동작도 그대로 유지된다.

- [x] **Step 3: 회귀 확인**

기존 `to_dict()` 기반 JSON 경로가 깨지지 않는지 확인한다.

---

## Task 2: import graph 기반 raw `related_files` 생성

`suggest_patch()`는 codespeak/operation을 모른다. 따라서 여기서는 **import 그래프 기반 raw 후보만 채우고**, operation 필터링은 Task 2b에서 `patch_builder.py`가 처리한다.

**Files:**
- Edit: `vibelign/core/patch_suggester.py`
- Test: `tests/test_multi_file_suggestion.py`

- [x] **Step 1: 실패 테스트 작성**

```python
def test_suggest_patch_populates_related_files_from_import_graph(tmp_path):
    # App.tsx -> lib/vib.ts 연결에서 related_files가 채워지는지 검증
```

검증 포인트:
- `result.related_files`가 비어 있지 않음
- 각 항목에 `file`, `role`, `anchor`, `reason`, `exists` 포함
- `target_file` 자체는 related_files에 중복 삽입되지 않음

- [x] **Step 2: helper 추가**

`patch_suggester.py`에 아래 helper들을 추가한다.

```python
_BARREL_NAMES = {"index.ts", "index.tsx", "index.js", "index.jsx"}

def _is_barrel_like(path: Path) -> bool:
    return path.name in _BARREL_NAMES or path.name in LOW_PRIORITY_NAMES

_CLASSIFY_TO_ROLE = {
    "ui": "component",
    "service": "data_source",
    "logic": "utility",
    "core": "utility",
}

def _classify_to_role(classify_result: str | None, rel_path: str) -> str:
    # 경로 기반 override: lib/ 하위면 data_source, components/ 하위면 component
    if "/lib/" in rel_path or rel_path.startswith("lib/"):
        return "data_source"
    if "/components/" in rel_path or rel_path.startswith("components/"):
        return "component"
    if classify_result is None:
        return "utility"
    return _CLASSIFY_TO_ROLE.get(classify_result, "utility")

def _build_related_file_entry(
    root: Path, path: Path, project_map: object | None
) -> dict[str, object]:
    rel = relpath_str(root, path)
    classify_result = (
        project_map.classify_path(rel) if project_map is not None else None
    )
    anchors = extract_anchors(path)
    return {
        "file": rel,
        "role": _classify_to_role(classify_result, rel),
        "anchor": anchors[0] if anchors else None,
        "reason": f"target file이 import하는 파일",
        "exists": True,
    }

def _filter_related_files(
    *,
    root: Path,
    target_path: Path,
    candidates: list[Path],
    project_map: object | None,
    max_related: int = 3,
) -> list[dict[str, object]]:
    ...
```

필터 기준 (**토큰 겹침 필터 없음** — import 그래프 결과는 이미 구조적으로 연결):
- target file 제외
- 중복 path 제거
- barrel/re-export 파일 제외 (`_is_barrel_like()`)
- 최대 3개

`_filter_related_files`의 시그니처에서 `request_tokens` 파라미터를 제거한다. 토큰 필터를 걸면 "watch 실시간 로그 추가" 같은 요청에서 `lib/vib.ts`처럼 토큰 겹침이 약하지만 구조적으로 필요한 파일이 빠진다.

- [x] **Step 3: `suggest_patch()`에 연결**

`best_path`와 `anchor`가 최종 결정된 뒤 (AI 선택 후 포함), 아래 순서로 `suggestion.related_files`를 채운다.

1. `_build_import_pool_expansion(best_path, root, max_hops=1)` 호출
2. `_filter_related_files(...)` 적용 (barrel 제외 + max 3)
3. `PatchSuggestion(..., related_files=...)`로 반환

**`suggest_patch()`에서는 operation 판단을 하지 않는다.** move든 add든 항상 raw related_files를 채운다. operation 기반 필터링은 Task 2b에서 처리.

---

## Task 2b: `patch_builder.py`에서 operation 기반 후처리

`suggest_patch()`가 채운 raw `related_files`를 codespeak operation에 따라 필터링/확장한다. 이 단계에서는 codespeak이 이미 파싱된 상태이므로 operation을 정확히 알 수 있다.

**Files:**
- Edit: `vibelign/patch/patch_builder.py` (`_build_patch_data_with_options` 함수, 377-495행)
- Test: `tests/test_multi_file_suggestion.py`

- [x] **Step 1: 실패 테스트 작성**

```python
def test_move_request_clears_related_files():
    # move 요청이면 patch_plan.related_files가 []로 비워지는지 검증

def test_add_request_appends_new_file_candidate():
    # add 요청이면 new_file 항목이 추가되는지 검증
```

- [x] **Step 2: 후처리 함수 추가**

`patch_builder.py`에 아래 함수를 추가한다:

```python
def _postprocess_related_files(
    related_files: list[dict[str, object]],
    operation: str,
    action: str,
    *,
    root: Path,
    best_path: Path,
    codespeak_subject: str,
) -> list[dict[str, object]]:
    # move → 비움
    if operation == "move":
        return []
    result = list(related_files)
    # add/create → 새 파일 컨벤션 추론 시도
    if action in ("add", "create"):
        new_file = _infer_new_file_path(
            root=root,
            subject=codespeak_subject,
            action=action,
            sibling_dir=best_path.parent,
        )
        if new_file is not None:
            rel = str(new_file.relative_to(root))
            if not any(rf.get("file") == rel for rf in result):
                result.append({
                    "file": rel,
                    "role": "new_file",
                    "anchor": None,
                    "reason": "컨벤션 추론으로 제안된 새 파일",
                    "exists": False,
                })
    return result
```

**Dedupe invariant:** `related_files` 중복 제거는 항상 `file` path 문자열 기준으로 한다. first-win 규칙을 사용해서 먼저 들어온 항목을 유지하고, 뒤에서 들어온 중복 항목(existing/new_file/destination 충돌 포함)은 버린다.

```python
def _dedupe_related_files(items: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    result: list[dict[str, object]] = []
    for item in items:
        path = item.get("file")
        if not isinstance(path, str) or path in seen:
            continue
        seen.add(path)
        result.append(item)
    return result
```

적용 규칙:
- import graph에서 나온 existing file와 `new_file` candidate가 같은 경로면 existing file를 유지한다.
- move의 `destination_file`과 같은 경로가 `related_files`에 들어오면 contract 단계에서 중복 출력하지 않는다.
- `allowed_files`와 `allowed_file_details` 모두 path 기준 dedupe 결과를 기반으로 만든다.

- [x] **Step 3: `_build_patch_data_with_options()`에 연결**

`PatchPlan(...)` 생성 직전 (patch_builder.py:463 부근):

```python
raw_related = getattr(suggestion, "related_files", [])
operation = codespeak.patch_points.get("operation", "update")
action = codespeak.codespeak_parts.get("action", "update") if hasattr(codespeak, "codespeak_parts") else "update"
final_related = _postprocess_related_files(
    raw_related,
    operation,
    action,
    root=root,
    best_path=root / suggestion.target_file,
    codespeak_subject=codespeak.subject or "",
)

patch_plan = PatchPlan(
    ...
    related_files=final_related,
)
```

주의: `_infer_new_file_path()`는 `patch_suggester.py`에 정의하되, `patch_builder.py`에서 import해서 사용. 이미 `patch_builder.py`는 `patch_targeting.py`를 통해 `patch_suggester` 계열 모듈에 간접 의존하므로 순환 의존 없음.

추가 주의:
- `action = codespeak.codespeak_parts.get(...)` / `codespeak.subject` 같은 예시는 **개념 설명용**이다.
- 실제 구현에서는 Task 2b 상단 helper (`_extract_codespeak_action`, `_extract_codespeak_subject`)를 통해 현재 `CodeSpeakResult` 구조에 맞게 읽는다.
- `final_related`를 `PatchPlan(...)`에 넣기 전에 `_dedupe_related_files(final_related)`를 반드시 한 번 더 통과시킨다.

---

## Task 3: 새 파일 생성 컨벤션 추론

**Files:**
- Edit: `vibelign/core/patch_suggester.py` (함수 정의)
- Edit: `vibelign/patch/patch_builder.py` (호출부 — Task 2b에서 연결)
- Test: `tests/test_multi_file_suggestion.py`

- [x] **Step 1: 실패 테스트 작성**

```python
def test_infer_new_file_path_by_convention(tmp_path):
    # sibling_dir 패턴을 기준으로 새 파일 경로를 제안하는지 검증
```

- [x] **Step 2: `_infer_new_file_path()` 구현**

```python
def _infer_new_file_path(
    *,
    root: Path,
    subject: str,
    action: str,
    sibling_dir: Path,
) -> Path | None:
    ...
```

로직:
1. `action`이 `add` / `create`가 아니면 종료
2. subject와 매칭되는 기존 파일이 있으면 종료
3. sibling dir에서 확장자 / casing 규칙 추론
4. 제안 경로가 이미 존재하면 종료

- [x] **Step 3: `related_files`에 `new_file` 항목으로 추가**

예시:

```python
{
    "file": "vibelign-gui/src/components/WatchLog.tsx",
    "role": "new_file",
    "anchor": None,
    "reason": "컨벤션 추론으로 제안된 새 파일",
    "exists": False,
}
```

주의:
- 새 파일 제안은 import graph 기반 항목과 섞이므로 dedupe 규칙 필요
- `move` / `update` 요청에는 절대 붙지 않아야 한다

---

## Task 4: `PatchContract`에 multi-file scope 추가

**Files:**
- Edit: `vibelign/core/patch_contract.py` (PATCH_CONTRACT_FROM_CONTEXT 앵커 43-63행, scope 구성 96-109행)
- Edit: `vibelign/patch/patch_contract_helpers.py` (preconditions 142-160행, build_contract 364-497행)
- Test: `tests/test_vib_patch_contract_v0.py`
- Create: `tests/test_multi_file_contract.py`

- [x] **Step 1: 실패 테스트 작성**

```python
def test_contract_keeps_allowed_files_legacy_list_and_details():
    patch_plan = {
        "target_file": "src/App.tsx",
        "target_anchor": "APP",
        "confidence": "high",
        "interpretation": "로그 뷰어 추가",
        "codespeak": "ui.component.watch_log.add",
        "patch_points": {"operation": "add"},
        "related_files": [
            {
                "file": "src/lib/vib.ts",
                "role": "data_source",
                "anchor": "VIB",
                "reason": "watch 로그 스트림 함수 제공",
                "exists": True,
            }
        ],
    }
    result = build_contract(patch_plan)
    scope = result["scope"]
    # legacy list 유지
    assert scope["allowed_files"] == ["src/App.tsx", "src/lib/vib.ts"]
    # 새 details 필드
    assert scope["allowed_file_details"][0]["role"] == "primary"
    assert scope["allowed_file_details"][1]["role"] == "data_source"
```

- [x] **Step 2: `PatchContract.from_context()` 확장**

**Blocking order:** 이 단계가 끝나기 전에는 `patch_contract_helpers.py` 호출부를 수정하지 않는다.

**2a.** 시그니처에 `related_files` 파라미터 추가 (patch_contract.py:43-63):

```python
def from_context(
    cls,
    *,
    ...
    user_guidance: list[str],
    related_files: list[dict[str, object]] | None = None,  # NEW
) -> PatchContract:
```

**2b.** scope 구성 (patch_contract.py:96-109) 확장:

```python
# 기존 allowed_files는 list[str] 유지
related = related_files or []
all_files = [
    item
    for item in [target_file, destination_file]
    + [rf["file"] for rf in related if isinstance(rf, dict) and "file" in rf]
    if item and item != "[소스 파일 없음]" and item != "None"
]

# primary target의 details entry
target_detail = {
    "file": target_file,
    "role": "primary",
    "anchor": anchor_name,
    "reason": "직접 수정 대상",
    "exists": True,
}
file_details = [target_detail] + [
    rf for rf in related if isinstance(rf, dict)
]

scope={
    "allowed_files": list(dict.fromkeys(all_files)),  # 중복 제거, 순서 유지
    "allowed_file_details": file_details,
    ...  # 기존 필드 유지
},
```

주의:
- 여기서는 `patch_plan[...]`를 직접 읽지 말고 `from_context()` 인자로 받은 `target_file`, `anchor_name`, `destination_file`만 사용한다.
- 이렇게 해야 `PatchContract.from_context()`가 patch_plan 구체 shape에 덜 결합된다.

- [x] **Step 3: `preconditions()` 문구 개선**

patch_contract_helpers.py:142-160 수정:

```python
def preconditions(
    target_file: str,
    target_anchor: str,
    related_files: list[dict[str, object]] | None = None,
) -> list[str]:
    related = related_files or []
    existing = [rf for rf in related if rf.get("exists", True)]
    new_files = [rf for rf in related if not rf.get("exists", True)]
    
    if not existing and not new_files:
        conditions = [f"허용된 파일은 `{target_file}` 하나뿐이어야 합니다."]
    else:
        file_list = ", ".join(
            [f"`{target_file}`"] + [f"`{r['file']}`" for r in existing]
        )
        conditions = [f"허용된 파일은 {file_list} 총 {1 + len(existing)}개입니다."]
    
    if new_files:
        for nf in new_files:
            conditions.append(f"새로 생성될 파일 후보: `{nf['file']}` ({nf.get('reason', '')})")
    
    # 앵커 조건은 기존 로직 유지
    ...
```

- [x] **Step 4: `build_contract()`에서 related_files 전달**

patch_contract_helpers.py:364-494 — `build_contract()` 함수 내:

```python
related_files_raw = patch_plan.get("related_files", [])
related_files = (
    [rf for rf in cast(list[object], related_files_raw) if isinstance(rf, dict)]
    if isinstance(related_files_raw, list)
    else []
)
```

이 값을 `preconditions(target_file, target_anchor, related_files=related_files)`와
`PatchContract.from_context(..., related_files=related_files)` 양쪽에 전달.

---

## Task 5: render / handoff 출력 반영

**Files:**
- Edit: `vibelign/patch/patch_render.py` (PATCH_RENDER_RENDER_MARKDOWN 앵커, 42행 allowed_files 읽기, 81-82행 렌더링)
- Edit: `vibelign/patch/patch_handoff.py` (93행 allowed_files_scope, 176-179행 Allowed files 출력, 196-206행 return dict)
- Test: `tests/test_vib_patch_render.py`

- [x] **Step 1: `patch_render.py` multi-file 표시 추가**

현재 코드 (patch_render.py:42,81-82):

```python
allowed_files = cast(list[object], scope.get("allowed_files", []))
...
for item in allowed_files:
    lines.append(f"- 허용된 파일: {item}")
```

변경: `allowed_file_details`가 있으면 역할 정보와 함께 렌더링, 없으면 기존 유지.

**Branching invariant:** `allowed_file_details`가 빈 리스트면 기존 single-file 루프를 그대로 탄다.
즉, single-file 출력 문구는 snapshot 호환 대상으로 취급한다.

```python
allowed_file_details = cast(list[dict[str, object]], scope.get("allowed_file_details", []))
if allowed_file_details:
    for detail in allowed_file_details:
        role = detail.get("role", "")
        anchor = detail.get("anchor", "")
        reason = detail.get("reason", "")
        exists = detail.get("exists", True)
        anchor_text = f", {anchor} 앵커" if anchor else ""
        new_marker = " [신규]" if not exists else ""
        lines.append(f"- 허용된 파일: {detail['file']} ({role}{anchor_text}){new_marker} — {reason}")
else:
    for item in allowed_files:
        lines.append(f"- 허용된 파일: {item}")
```

- [x] **Step 2: `patch_handoff.py` multi-file 핸드오프 보강**

**2a.** allowed_files 출력 (patch_handoff.py:176-179) 확장:

현재 코드:
```python
(
    f"Allowed files: {', '.join(str(item) for item in allowed_files_scope)}"
    if allowed_files_scope
    else None
),
```

변경: `allowed_file_details`가 있으면 여러 줄로 풀어쓴다.

```python
allowed_file_details = cast(
    list[dict[str, object]],
    scope.get("allowed_file_details", []),
)
if allowed_file_details:
    prompt_lines.append("Allowed files:")
    for detail in allowed_file_details:
        role = detail.get("role", "")
        anchor = detail.get("anchor")
        exists = detail.get("exists", True)
        anchor_tag = f", anchor={anchor}" if anchor else ""
        new_tag = ", new" if not exists else ""
        prompt_lines.append(f"  - {detail['file']} [{role}{anchor_tag}{new_tag}]")
else:
    if allowed_files_scope:
        prompt_lines.append(
            f"Allowed files: {', '.join(str(item) for item in allowed_files_scope)}"
        )
```

주의: 이 블록은 기존 `prompt_lines.extend(...)` 리스트 안의 조건부 항목을 대체하므로, 리스트 바깥으로 빼서 별도 if/else로 처리해야 한다.

**2b.** `validator_gate_rules_text()` (patch_handoff.py:26-50)는 **수정하지 않는다.**
validator 강제 범위는 여전히 primary target + destination 중심이어야 한다.
related files는 '수정 가능 범위'이지 validator가 강제할 대상이 아니다.

**2c.** return dict (patch_handoff.py:196-206)에 `allowed_file_details` 추가:

```python
return {
    "ready": True,
    ...
    "allowed_files": scope.get("allowed_files", []),
    "allowed_file_details": scope.get("allowed_file_details", []),  # NEW
    ...
}
```

- [x] **Step 3: 단일 파일 호환 테스트 유지**

기존 테스트가 기대하는 문자열이 깨질 수 있으므로, 기존 assertion을 대체하지 말고 multi-file 전용 테스트를 추가하거나 범위를 넓힌다.

검증 포인트:
- single-file 핸드오프 prompt에 `"Allowed files: src/App.tsx"` 한 줄 형식 유지
- multi-file 핸드오프 prompt에 `"Allowed files:"` + 들여쓰기 목록 형식
- return dict에 `allowed_file_details` 키 존재

- [x] **Step 4: snapshot 호환 테스트 추가**

```python
def test_single_file_handoff_keeps_legacy_allowed_files_line():
    ...

def test_multi_file_handoff_uses_indented_allowed_file_details_block():
    ...
```

이 단계는 render/handoff가 가장 쉽게 회귀를 만드는 부분이라서 필수다.

---

## Task 6: 회귀 테스트 및 실제 시나리오 검증

**Files:**
- Edit: `tests/test_patch_targeting_regressions.py`
- Edit: `tests/test_vib_patch_contract_v0.py`
- Edit: `tests/test_vib_patch_render.py`
- Create: `tests/test_multi_file_suggestion.py`
- Create: `tests/test_multi_file_builder.py`
- Create: `tests/test_multi_file_contract.py`

- [x] **Step 1: suggestion 계층 테스트**

시나리오:
- App.tsx + lib/vib.ts import 관계 → `suggest_patch()`의 raw related_files에 vib.ts 포함
- 단일 파일 색상 변경 요청 → import 없는 파일이면 `related_files == []`

- [x] **Step 1b: patch_builder 후처리 테스트**

시나리오:
- move 요청 → `patch_plan.related_files == []` (raw에 있어도 후처리에서 비워짐)
- add 요청 → `patch_plan.related_files`에 new_file 항목 추가됨
- update 요청 → raw 그대로 유지
- path 중복(existing + new_file candidate)이 있으면 first-win 규칙으로 하나만 남음

이 단계는 suggestion 레벨과 분리해서 `tests/test_multi_file_builder.py`에 둔다. 그래야 실패했을 때 원인이 import-graph 생성인지, builder 후처리인지 바로 분리된다.

- [x] **Step 2: contract 계층 테스트**

시나리오:
- legacy `allowed_files` list 유지
- `allowed_file_details`에 role/anchor/reason/exists 포함
- new_file candidate 포함 시 preconditions 문구 정상

- [x] **Step 3: render/handoff 테스트**

시나리오:
- multi-file markdown에 역할 표시
- multi-file handoff prompt에 allowed file details 표시
- single-file handoff 문구는 기존 핵심 문장 유지
- single-file render markdown에서 기존 `- 허용된 파일: ...` 형식 유지
- `new_file` candidate는 `[신규]` 또는 동등한 명확 표식으로 표시

- [x] **Step 4: 실제 회귀 파일에 추가**

`tests/test_patch_targeting_regressions.py`에 아래 케이스를 추가한다.

- '상단 폴더열기 탭 오른쪽으로 watch 실시간 로그 추가'
  - target: `vibelign-gui/src/App.tsx`
  - related: `vibelign-gui/src/lib/vib.ts`
  - optional new file: `vibelign-gui/src/components/WatchLog.tsx`
- '버튼 색상 바꿔줘'
  - related 없음
- '이 함수를 다른 파일로 이동'
  - destination만 있고 related fan-out 없음

- [x] **Step 5: 실행 커맨드**

```bash
pytest tests/test_multi_file_suggestion.py -v
pytest tests/test_multi_file_builder.py -v
pytest tests/test_multi_file_contract.py -v
pytest tests/test_vib_patch_render.py -v
pytest tests/test_vib_patch_contract_v0.py -v
pytest tests/test_patch_targeting_regressions.py -v
```

---

## 구현 순서 및 의존성

```text
Task 0   patch_plan 데이터 흐름 고정
  ↓
Task 1   PatchSuggestion.related_files 추가
  ↓
Task 2   import graph → raw related_files 채우기 (suggest_patch)
  ↓
Task 2b  operation 기반 후처리 (patch_builder) ← Task 3 결과 사용
  ↓
Task 4   contract.scope.allowed_file_details 추가
  ↓
Task 5   render / handoff 출력 반영
  ↓
Task 6   회귀 테스트

Task 3   new_file 컨벤션 추론 (patch_suggester에 함수 정의)
         → Task 2b에서 호출
```

병렬 가능 범위:
- Task 2와 Task 3은 파일이 분리되므로 병렬 가능 (Task 3은 함수 정의만, 호출은 Task 2b)
- Task 4와 Task 5는 contract shape가 먼저 정해진 뒤 진행

---

## Risks

### 1. Payload shape drift

`PatchSuggestion`만 바꾸고 `PatchPlan`/`patch_builder`를 안 바꾸면 기능이 반쪽짜리로 끝난다.

**Mitigation added in this plan:** Task 0에서 `PatchPlan.related_files` 추가 + `PatchPlan.to_dict()` 회귀 테스트를 선행한다.

### 2. Legacy consumer breakage

기존 테스트와 downstream consumer는 `allowed_files`가 string list라는 전제를 가진다. 그래서 **대체가 아니라 병행 필드 추가**가 안전하다.

**Mitigation added in this plan:** Task 5에서 single-file branch를 기존 문자열 그대로 유지하는 snapshot 테스트를 추가한다.

### 3. Over-expansion noise

App.tsx 같은 상위 파일은 import가 많다. 토큰 겹침 필터는 구조적으로 필요한 파일을 걸러내는 부작용이 있어서 제외했다. 대신 barrel 제외 + max 3개 제한으로 노이즈를 통제한다. max 3이 부족하면 추후 조정 가능.

**Mitigation added in this plan:** `_is_barrel_like()` 별도 helper + `max_related=3` 하드캡.

### 4. New-file false positives

`add` 요청이라고 항상 새 파일이 필요한 것은 아니다. 기존 파일 매칭 실패 + sibling convention 확인이 둘 다 만족될 때만 제안해야 한다.

**Mitigation added in this plan:** builder 후처리에서 existing/new_file path 충돌 시 existing entry를 우선 유지하고, `tests/test_multi_file_builder.py`로 dedupe 규칙을 잠근다.

### 5. `from_context()` signature mismatch

`patch_contract_helpers.py`가 `related_files`를 전달하기 시작한 뒤에도 `PatchContract.from_context()`가 구 시그니처면 바로 런타임 에러가 난다.

**Mitigation added in this plan:** Task 4에서 `from_context()` 시그니처 확장을 호출부 수정보다 먼저 수행한다.

### 6. CodeSpeak field drift

계획 예시의 `codespeak.codespeak_parts` / `codespeak.subject`가 실제 `CodeSpeakResult` 구현과 다를 수 있다. 이 상태로 속성명을 하드코딩하면 builder 단계에서 바로 깨진다.

**Mitigation added in this plan:** Task 2b에서 CodeSpeak 접근을 helper로 캡슐화하고, 실제 구현 필드명 기준으로 읽는다.

### 7. Documentation copy-paste breakage

문서 예시 코드에 스마트 쿼트가 섞이면 구현자가 그대로 복붙했을 때 Python 구문 오류가 난다.

**Mitigation added in this plan:** 모든 코드 예시는 ASCII quote만 사용하고, 이 문서 자체도 그 규칙으로 정리한다.

---

## Definition of Done

- `PatchSuggestion`이 `related_files`를 항상 안정적으로 반환한다.
- `patch_plan` JSON에 `related_files`가 포함된다.
- `contract.scope.allowed_files`는 기존 string list를 유지한다.
- `contract.scope.allowed_file_details`가 multi-file metadata를 제공한다.
- `patch_render.py` / `patch_handoff.py`가 multi-file 정보를 사람이 읽기 좋게 보여준다.
- move / single-file 요청 회귀가 깨지지 않는다.
- 관련 pytest 스위트가 모두 통과한다.
