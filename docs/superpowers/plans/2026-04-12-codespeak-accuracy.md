# CodeSpeak 정확도 개선 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** patch_suggester 결과를 AI CodeSpeak 생성의 입력으로 전달하여 규칙 기반 편향을 제거하고, confidence=low 게이트를 완화하여 프롬프트 생성률을 높인다.

**Architecture:** 실행 순서를 뒤집는다 — 현재 CodeSpeak(규칙) → AI 보정 → targeting 순서를 targeting → AI CodeSpeak(파일/앵커 포함) 순서로 변경. `patch_contract_helpers.py`의 NEEDS_CLARIFICATION 게이트를 완화하여 CodeSpeak이 성공적으로 생성되면 confidence=low여도 프롬프트를 생성한다.

**Tech Stack:** Python 3.12, unittest, vibelign 내부 모듈

---

### Task 1: `patch_status` 게이트 완화 — 테스트

`patch_contract_helpers.py`의 `patch_status` 함수에 `codespeak_generated` 파라미터를 추가하여, confidence=low여도 CodeSpeak이 성공적으로 생성되었으면 READY를 반환한다.

**Files:**
- Modify: `vibelign/patch/patch_contract_helpers.py:122-131`
- Test: `tests/test_patch_contract_helpers.py` (new or existing)

- [ ] **Step 1: 기존 테스트 확인**

Run: `python -m pytest tests/ -k "patch_status" -v 2>&1 | head -30`

기존 `patch_status` 테스트가 있는지 확인한다. 없으면 Step 2에서 신규 파일을 생성한다.

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_patch_contract_gate.py`를 생성한다:

```python
import unittest
from vibelign.patch.patch_contract_helpers import patch_status


class TestPatchStatusGateRelax(unittest.TestCase):
    def test_low_confidence_without_codespeak_returns_needs_clarification(self):
        result = patch_status("low", "ok", "ok", codespeak_generated=False)
        self.assertEqual(result, "NEEDS_CLARIFICATION")

    def test_low_confidence_with_codespeak_returns_ready(self):
        result = patch_status("low", "ok", "ok", codespeak_generated=True)
        self.assertEqual(result, "READY")

    def test_high_confidence_returns_ready_regardless(self):
        result = patch_status("high", "ok", "ok", codespeak_generated=False)
        self.assertEqual(result, "READY")

    def test_file_not_ok_still_refused(self):
        result = patch_status("low", "missing", "ok", codespeak_generated=True)
        self.assertEqual(result, "REFUSED")

    def test_low_confidence_missing_anchor_without_codespeak(self):
        result = patch_status("low", "ok", "missing", codespeak_generated=False)
        self.assertEqual(result, "NEEDS_CLARIFICATION")

    def test_low_confidence_missing_anchor_with_codespeak(self):
        """anchor가 missing이면 codespeak 여부와 무관하게 NEEDS_CLARIFICATION."""
        result = patch_status("low", "ok", "missing", codespeak_generated=True)
        self.assertEqual(result, "NEEDS_CLARIFICATION")

    def test_medium_confidence_suggested_anchor_without_codespeak(self):
        result = patch_status("medium", "ok", "suggested", codespeak_generated=False)
        self.assertEqual(result, "NEEDS_CLARIFICATION")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `python -m pytest tests/test_patch_contract_gate.py -v`
Expected: TypeError — `patch_status()` got unexpected keyword argument `codespeak_generated`

- [ ] **Step 4: `patch_status` 구현 수정**

`vibelign/patch/patch_contract_helpers.py:122-131`을 수정한다:

```python
# === ANCHOR: PATCH_CONTRACT_HELPERS_PATCH_STATUS_START ===
def patch_status(
    confidence: str,
    file_status: str,
    anchor_status: str,
    *,
    codespeak_generated: bool = False,
) -> str:
    if file_status != "ok":
        return "REFUSED"
    if anchor_status in {"missing", "suggested", "none"}:
        return "NEEDS_CLARIFICATION"
    if confidence == "low" and not codespeak_generated:
        return "NEEDS_CLARIFICATION"
    return "READY"


# === ANCHOR: PATCH_CONTRACT_HELPERS_PATCH_STATUS_END ===
```

핵심 변경: `confidence == "low"` 조건과 `anchor_status` 조건을 분리한다. anchor가 나쁘면 무조건 NEEDS_CLARIFICATION. confidence=low이면서 codespeak가 없을 때만 NEEDS_CLARIFICATION.

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_patch_contract_gate.py -v`
Expected: 7 passed

- [ ] **Step 6: 기존 테스트 회귀 확인**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py tests/test_bench_patch_command.py -v`
Expected: 기존 테스트 전부 통과 (72 passed, 5 xfailed). `patch_status`의 새 파라미터가 기본값 `False`이므로 기존 호출자는 영향 없음.

- [ ] **Step 7: 커밋**

```bash
git add tests/test_patch_contract_gate.py vibelign/patch/patch_contract_helpers.py
git commit -m "feat(contract): relax NEEDS_CLARIFICATION gate when codespeak is generated"
```

---

### Task 2: `build_contract`에서 `codespeak_generated` 전달

`build_contract`가 `patch_status`를 호출할 때 `codespeak_generated` 플래그를 전달하도록 수정한다. `patch_plan`에 `codespeak_generated` 필드가 있으면 이를 사용한다.

**Files:**
- Modify: `vibelign/patch/patch_contract_helpers.py:355-378`
- Test: `tests/test_patch_contract_gate.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_patch_contract_gate.py`에 추가:

```python
from vibelign.patch.patch_contract_helpers import build_contract


class TestBuildContractCodespeakGate(unittest.TestCase):
    def _make_patch_plan(self, confidence="high", codespeak_generated=False):
        return {
            "target_file": "ok:pages/login.py",
            "target_anchor": "ok:LOGIN_HANDLE_LOGIN",
            "codespeak": "ui.component.login.fix",
            "confidence": confidence,
            "request": "로그인 에러 수정",
            "patch_points": {"operation": "update"},
            "clarifying_questions": [],
            "sub_intents": [],
            "codespeak_generated": codespeak_generated,
        }

    def test_build_contract_low_confidence_with_codespeak_is_ready(self):
        plan = self._make_patch_plan(confidence="low", codespeak_generated=True)
        contract = build_contract(plan)
        self.assertEqual(contract["status"], "READY")

    def test_build_contract_low_confidence_without_codespeak_is_needs_clarification(self):
        plan = self._make_patch_plan(confidence="low", codespeak_generated=False)
        contract = build_contract(plan)
        self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_patch_contract_gate.py::TestBuildContractCodespeakGate -v`
Expected: FAIL — low confidence + codespeak_generated=True still returns NEEDS_CLARIFICATION

- [ ] **Step 3: `build_contract`에서 `codespeak_generated` 전달**

`vibelign/patch/patch_contract_helpers.py:378`의 `patch_status` 호출을 수정:

```python
    codespeak_generated = bool(patch_plan.get("codespeak_generated", False))
    status = patch_status(
        str(patch_plan["confidence"]),
        file_status,
        anchor_status,
        codespeak_generated=codespeak_generated,
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_patch_contract_gate.py -v`
Expected: 전부 통과

- [ ] **Step 5: 기존 테스트 회귀 확인**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py tests/test_bench_patch_command.py -v`
Expected: 기존 전부 통과

- [ ] **Step 6: 커밋**

```bash
git add vibelign/patch/patch_contract_helpers.py tests/test_patch_contract_gate.py
git commit -m "feat(contract): pass codespeak_generated flag through build_contract"
```

---

### Task 3: AI CodeSpeak 프롬프트 변경 — 파일/앵커 정보 전달

`ai_codespeak.py`의 `build_codespeak_ai_prompt`를 수정하여 규칙 기반 CodeSpeak 결과 대신 patch_suggester 결과(파일, 앵커, confidence, rationale)를 전달한다.

**Files:**
- Modify: `vibelign/core/ai_codespeak.py:39-74`
- Modify: `vibelign/core/ai_codespeak.py:118-156`
- Test: `tests/test_ai_codespeak_prompt.py` (new)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_ai_codespeak_prompt.py`를 생성:

```python
import unittest
from vibelign.core.ai_codespeak import build_codespeak_ai_prompt
from vibelign.core.codespeak import build_codespeak


class TestAICodespeakPromptWithTargeting(unittest.TestCase):
    def test_prompt_contains_file_and_anchor_when_provided(self):
        rule_result = build_codespeak("테스트 요청")
        prompt = build_codespeak_ai_prompt(
            "에러 메시지가 사라지지 않아",
            rule_result,
            target_file="pages/login.py",
            target_anchor="LOGIN_RENDER_LOGIN_ERROR",
            target_confidence="high",
            target_rationale=["login 키워드 매칭", "render_error 앵커 매칭"],
        )
        self.assertIn("pages/login.py", prompt)
        self.assertIn("LOGIN_RENDER_LOGIN_ERROR", prompt)
        self.assertNotIn("규칙 기반 해석", prompt)

    def test_prompt_falls_back_without_targeting(self):
        rule_result = build_codespeak("테스트 요청")
        prompt = build_codespeak_ai_prompt(
            "에러 메시지가 사라지지 않아",
            rule_result,
        )
        self.assertIn("규칙 기반 해석", prompt)
        self.assertNotIn("patch_suggester", prompt)

    def test_prompt_includes_rationale(self):
        rule_result = build_codespeak("테스트 요청")
        prompt = build_codespeak_ai_prompt(
            "에러 메시지가 사라지지 않아",
            rule_result,
            target_file="pages/login.py",
            target_anchor="LOGIN_RENDER_LOGIN_ERROR",
            target_confidence="high",
            target_rationale=["login 키워드 매칭"],
        )
        self.assertIn("login 키워드 매칭", prompt)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_ai_codespeak_prompt.py -v`
Expected: TypeError — `build_codespeak_ai_prompt()` got unexpected keyword argument `target_file`

- [ ] **Step 3: `build_codespeak_ai_prompt` 시그니처 및 구현 수정**

`vibelign/core/ai_codespeak.py:39-74`를 수정:

```python
# === ANCHOR: AI_CODESPEAK_BUILD_CODESPEAK_AI_PROMPT_START ===
def build_codespeak_ai_prompt(
    request: str,
    rule_result: CodeSpeakResult,
    *,
    target_file: str | None = None,
    target_anchor: str | None = None,
    target_confidence: str | None = None,
    target_rationale: list[str] | None = None,
) -> str:
# === ANCHOR: AI_CODESPEAK_BUILD_CODESPEAK_AI_PROMPT_END ===
    targeting_block = ""
    if target_file and target_anchor:
        rationale_text = "\n".join(f"  - {r}" for r in (target_rationale or []))
        targeting_block = f"""
patch_suggester가 찾은 수정 위치:
- 파일: {target_file}
- 앵커: {target_anchor}
- confidence: {target_confidence or 'unknown'}
- 근거:
{rationale_text}

이 정보를 바탕으로 앵커 이름에서 layer, subject를 추론하고,
요청 문맥에서 action을 판단하세요."""
    else:
        targeting_block = f"""현재 규칙 기반 해석:
- codespeak: {rule_result.codespeak}
- interpretation: {rule_result.interpretation}
- confidence: {rule_result.confidence}"""

    return f"""다음 사용자 요청을 CodeSpeak로 해석해주세요.

규칙:
- JSON만 출력하세요.
- 형식은 다음 키를 반드시 포함하세요:
  codespeak, interpretation, confidence, clarifying_questions
- 선택 키 patch_points: 객체이며 문자열 필드만 사용합니다.
  (operation, source, destination, object, behavior_constraint)
  규칙 추출이 비어 있을 때만 채워 넣으세요. 확실하지 않으면 생략합니다.
- `codespeak`는 layer.target.subject.action 형식만 허용합니다.
- `action`은 다음 어휘 중 하나만 사용하세요: add, remove, update, move, fix, apply, split.
  (예: persistence_enable, enable, disable 같은 임의 동사는 금지)
- `subject`는 한글 없이 영문 snake_case 만 허용합니다.
- confidence 는 high, medium, low 중 하나입니다.
- clarifying_questions 는 문자열 배열입니다.
- 한국어 interpretation 을 작성하세요.

사용자 요청:
{request}

{targeting_block}

출력 예시:
{{
  "codespeak": "ui.component.progress_bar.add",
  "interpretation": "진행 상태를 보여주는 progress bar를 UI에 추가하는 요청으로 해석했습니다.",
  "confidence": "high",
  "clarifying_questions": []
}}
"""
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_ai_codespeak_prompt.py -v`
Expected: 3 passed

- [ ] **Step 5: `enhance_codespeak_with_ai` 시그니처 업데이트**

`vibelign/core/ai_codespeak.py:118-156`에서 `enhance_codespeak_with_ai`에도 targeting 파라미터를 전달:

```python
# === ANCHOR: AI_CODESPEAK_ENHANCE_CODESPEAK_WITH_AI_START ===
def enhance_codespeak_with_ai(
    request: str,
    rule_result: CodeSpeakResult,
    quiet: bool = False,
    *,
    target_file: str | None = None,
    target_anchor: str | None = None,
    target_confidence: str | None = None,
    target_rationale: list[str] | None = None,
    # === ANCHOR: AI_CODESPEAK_ENHANCE_CODESPEAK_WITH_AI_END ===
) -> CodeSpeakResult | None:
    prompt = build_codespeak_ai_prompt(
        request,
        rule_result,
        target_file=target_file,
        target_anchor=target_anchor,
        target_confidence=target_confidence,
        target_rationale=target_rationale,
    )
    # ... 나머지 동일
```

- [ ] **Step 6: 기존 테스트 회귀 확인**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py tests/test_bench_patch_command.py -v`
Expected: 전부 통과 (새 파라미터 모두 기본값 None이므로 기존 호출자 영향 없음)

- [ ] **Step 7: 커밋**

```bash
git add vibelign/core/ai_codespeak.py tests/test_ai_codespeak_prompt.py
git commit -m "feat(codespeak): AI prompt accepts targeting info from patch_suggester"
```

---

### Task 4: 실행 순서 변경 — targeting을 CodeSpeak 보정 앞으로

`patch_builder.py`의 `_build_patch_data_with_options`에서 실행 순서를 뒤집는다: targeting(파일/앵커 결정)을 먼저 수행하고, 그 결과를 AI CodeSpeak 보정에 전달한다.

**Files:**
- Modify: `vibelign/patch/patch_builder.py:385-488`
- Modify: `vibelign/patch/patch_targeting.py:50-72`
- Test: `tests/test_patch_builder_order.py` (new)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_patch_builder_order.py`를 생성:

```python
import unittest
from unittest.mock import patch as mock_patch, MagicMock
from pathlib import Path
import tempfile

from vibelign.commands.bench_fixtures import prepare_patch_sandbox


class TestExecutionOrderReversed(unittest.TestCase):
    """enhance_codespeak에 targeting 결과가 전달되는지 확인."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.sandbox = prepare_patch_sandbox(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_enhance_codespeak_receives_targeting_info(self):
        """enhance_codespeak가 target_file, target_anchor를 인자로 받는다."""
        captured = {}

        original_enhance = None

        def _capture_enhance(request, codespeak, *, use_ai, quiet_ai, import_module, **kwargs):
            captured.update(kwargs)
            return codespeak

        with mock_patch(
            "vibelign.patch.patch_builder._targeting_helpers"
        ) as mock_helpers:
            helpers_instance = MagicMock()
            mock_helpers.return_value = helpers_instance

            helpers_instance.enhance_codespeak.side_effect = _capture_enhance

            from vibelign.core.patch_suggester import PatchSuggestion
            mock_suggestion = PatchSuggestion(
                request="에러 메시지 변경",
                target_file="pages/login.py",
                target_anchor="LOGIN_HANDLE_LOGIN",
                confidence="high",
                rationale=["test"],
            )
            helpers_instance.resolve_patch_targeting.return_value = {
                "suggestion": mock_suggestion,
                "source_resolution": None,
                "destination_suggestion": None,
                "destination_resolution": None,
                "confidence": "high",
            }

            from vibelign.patch.patch_builder import _build_patch_data_with_options
            _build_patch_data_with_options(
                self.sandbox, "에러 메시지 변경", use_ai=True, quiet_ai=True
            )

        self.assertIn("target_file", captured)
        self.assertEqual(captured["target_file"], "pages/login.py")
        self.assertIn("target_anchor", captured)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_patch_builder_order.py -v`
Expected: FAIL — `target_file` not in captured (현재는 enhance_codespeak에 targeting 정보가 전달되지 않음)

- [ ] **Step 3: `enhance_codespeak` 시그니처에 targeting 파라미터 추가**

`vibelign/patch/patch_targeting.py:50-72`를 수정:

```python
# === ANCHOR: PATCH_TARGETING_ENHANCE_CODESPEAK_START ===
def enhance_codespeak(
    request: str,
    codespeak: CodeSpeakResult,
    *,
    use_ai: bool,
    quiet_ai: bool,
    import_module: Callable[[str], object],
    target_file: str | None = None,
    target_anchor: str | None = None,
    target_confidence: str | None = None,
    target_rationale: list[str] | None = None,
# === ANCHOR: PATCH_TARGETING_ENHANCE_CODESPEAK_END ===
) -> CodeSpeakResult:
    if not use_ai:
        return codespeak
    ai_codespeak = cast(AICodeSpeakLike, import_module("vibelign.core.ai_codespeak"))
    ai_explain = cast(AIExplainLike, import_module("vibelign.core.ai_explain"))
    if not ai_explain.has_ai_provider():
        return codespeak
    try:
        enhanced = ai_codespeak.enhance_codespeak_with_ai(
            request,
            codespeak,
            quiet=quiet_ai,
            target_file=target_file,
            target_anchor=target_anchor,
            target_confidence=target_confidence,
            target_rationale=target_rationale,
        )
    except Exception:
        enhanced = None
    return cast(CodeSpeakResult, enhanced) if enhanced is not None else codespeak
```

`AICodeSpeakLike` 프로토콜도 업데이트해야 한다. `vibelign/patch/patch_targeting.py:40-47`:

```python
    def enhance_codespeak_with_ai(
        self,
        request: str,
        rule_result: object,
        quiet: bool = False,
        *,
        target_file: str | None = None,
        target_anchor: str | None = None,
        target_confidence: str | None = None,
        target_rationale: list[str] | None = None,
    ) -> object | None: ...
```

- [ ] **Step 4: `_build_patch_data_with_options` 실행 순서 변경**

`vibelign/patch/patch_builder.py:385-488`를 수정. 핵심: targeting을 먼저 수행하고, 그 결과를 enhance_codespeak에 전달.

```python
) -> dict[str, object]:
    codespeak = build_codespeak(request, root=root)

    if codespeak.sub_intents and len(codespeak.sub_intents) > MAX_SUB_INTENT_FANOUT:
        codespeak = replace(
            codespeak,
            sub_intents=None,
            clarifying_questions=list(codespeak.clarifying_questions)
            + [
                f"한 번에 나눌 수 있는 작업은 최대 {MAX_SUB_INTENT_FANOUT}개예요. "
                + "요청을 나눠서 다시 시도해 주세요."
            ],
        )
    if lazy_fanout and codespeak.sub_intents and len(codespeak.sub_intents) > 1:
        sub_first = _build_patch_data_with_options(
            root,
            codespeak.sub_intents[0],
            use_ai,
            quiet_ai,
            enable_step_fanout=False,
            lazy_fanout=False,
        )
        return _fanout_helpers().apply_lazy_fanout(
            request, sub_first, list(codespeak.sub_intents)
        )

    # --- targeting 먼저 ---
    targeting = _targeting_helpers().resolve_patch_targeting(
        root,
        request,
        codespeak,
        use_ai=use_ai,
        coerce_json_object=cast(Callable[[object], object], _coerce_json_object),
    )
    suggestion = cast(SuggestionLike, targeting["suggestion"])
    confidence = str(targeting["confidence"])

    # --- AI CodeSpeak 보정 (targeting 결과 전달) ---
    codespeak = _targeting_helpers().enhance_codespeak(
        request,
        codespeak,
        use_ai=use_ai,
        quiet_ai=quiet_ai,
        import_module=importlib.import_module,
        target_file=suggestion.target_file,
        target_anchor=suggestion.target_anchor,
        target_confidence=confidence,
        target_rationale=suggestion.rationale,
    )

    source_resolution = cast(JsonObject | None, targeting["source_resolution"])
    destination_suggestion = cast(
        SuggestionLike | None, targeting["destination_suggestion"]
    )
    destination_resolution = cast(
        JsonObject | None, targeting["destination_resolution"]
    )
    steps = (
        _build_fanout_patch_steps(
            root,
            codespeak.sub_intents,
            use_ai=use_ai,
            quiet_ai=quiet_ai,
        )
        if enable_step_fanout
        and codespeak.sub_intents
        and len(codespeak.sub_intents) > 1
        else _build_patch_steps(
            root=root,
            request=request,
            codespeak=codespeak,
            target_file=suggestion.target_file,
            target_anchor=suggestion.target_anchor,
            confidence=confidence,
            sub_intents=codespeak.sub_intents,
            destination_target_file=_destination_field(
                destination_suggestion, "target_file"
            ),
            destination_target_anchor=_destination_field(
                destination_suggestion, "target_anchor"
            ),
        )
    )

    codespeak_generated = codespeak.codespeak != "" and codespeak.confidence != "none"

    patch_plan = PatchPlan(
        schema_version=1,
        request=request,
        interpretation=codespeak.interpretation,
        target_file=suggestion.target_file,
        target_anchor=suggestion.target_anchor,
        source_resolution=source_resolution,
        destination_target_file=_destination_field(
            destination_suggestion, "target_file"
        ),
        destination_target_anchor=_destination_field(
            destination_suggestion, "target_anchor"
        ),
        destination_resolution=destination_resolution,
        codespeak=codespeak.codespeak,
        intent_ir=_coerce_json_object(
            codespeak.intent_ir.to_dict() if codespeak.intent_ir else None
        ),
        patch_points=codespeak.patch_points,
        sub_intents=codespeak.sub_intents,
        pending_sub_intents=None,
        constraints=_build_constraints(codespeak),
        confidence=confidence,
        preview_available=True,
        clarifying_questions=codespeak.clarifying_questions,
        rationale=suggestion.rationale,
        destination_rationale=getattr(destination_suggestion, "rationale", []),
        steps=steps,
    )
    plan_dict = patch_plan.to_dict()
    plan_dict["codespeak_generated"] = codespeak_generated
    return {"patch_plan": plan_dict}
```

핵심 변경 요약:
1. `resolve_patch_targeting`을 `enhance_codespeak` 앞으로 이동
2. `enhance_codespeak`에 `target_file`, `target_anchor`, `target_confidence`, `target_rationale` 전달
3. `codespeak_generated` 플래그를 `patch_plan` dict에 추가

- [ ] **Step 5: PatchPlan에 codespeak_generated 필드 확인**

`PatchPlan` dataclass에 `codespeak_generated` 필드가 필요한지 확인한다. plan_dict에 직접 추가하는 방식이면 dataclass 수정은 불필요하다 (Step 4에서 `plan_dict["codespeak_generated"] = ...`로 처리).

- [ ] **Step 6: 테스트 통과 확인**

Run: `python -m pytest tests/test_patch_builder_order.py -v`
Expected: PASS

- [ ] **Step 7: 기존 테스트 회귀 확인**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py tests/test_bench_patch_command.py tests/test_patch_contract_gate.py -v`
Expected: 전부 통과

- [ ] **Step 8: 커밋**

```bash
git add vibelign/patch/patch_builder.py vibelign/patch/patch_targeting.py tests/test_patch_builder_order.py
git commit -m "feat(patch): reverse execution order — targeting before AI CodeSpeak"
```

---

### Task 5: 통합 테스트 — 벤치마크 회귀 확인

전체 벤치마크 20개 시나리오에서 회귀가 없는지 확인한다.

**Files:**
- Test: `tests/test_patch_accuracy_scenarios.py` (existing)
- Test: `tests/test_bench_patch_command.py` (existing)

- [ ] **Step 1: 전체 테스트 스위트 실행**

Run: `python -m pytest tests/ -v 2>&1 | tail -30`
Expected: 전부 통과 (72+ passed, 5 xfailed, 0 failed)

- [ ] **Step 2: 벤치마크 det 모드 확인**

Run: `python -m pytest tests/test_patch_accuracy_scenarios.py -v`
Expected: 15 passed (det), 5 xfailed

- [ ] **Step 3: 벤치마크 baseline diff 확인**

Run: `python -m pytest tests/test_bench_patch_command.py -v`
Expected: 전부 통과

- [ ] **Step 4: 수동 vib patch 테스트**

실제 `vib patch` 명령으로 CodeSpeak 결과를 확인한다:

```bash
cd /path/to/test/project
vib patch "에러 메시지가 사라지지 않아" --ai --dry-run
```

Expected: CodeSpeak의 action이 `fix`이고, 파일/앵커가 정확해야 한다.

- [ ] **Step 5: confidence=low 시나리오 확인**

```bash
vib patch "로그인 잠금 해제" --ai --dry-run
```

Expected: 이전에 NEEDS_CLARIFICATION이었던 요청이 이제 프롬프트를 생성해야 한다 (confidence=low + codespeak_generated=true → READY).

- [ ] **Step 6: 결과 정리 및 커밋**

문제가 발견되면 수정 후 커밋. 문제가 없으면 baseline 업데이트:

```bash
vib bench --patch --update-baseline
git add tests/benchmark/patch_accuracy_baseline.json
git commit -m "test(bench): update baseline after codespeak accuracy improvement"
```
