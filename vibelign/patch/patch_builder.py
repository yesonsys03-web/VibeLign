# === ANCHOR: PATCH_BUILDER_START ===
import importlib
from dataclasses import replace
from pathlib import Path
from collections.abc import Callable
from typing import Protocol, cast

from vibelign.core import PatchPlan, PatchStep
from vibelign.core.codespeak import CodeSpeakResult, build_codespeak
from vibelign.core.context_chunk import fetch_anchor_context_window
from vibelign.core.patch_suggester import _infer_new_file_path
from vibelign.core.strict_patch import build_strict_patch_artifact

MAX_SUB_INTENT_FANOUT = 5

JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject = dict[str, JsonValue]


# === ANCHOR: PATCH_BUILDER_SUGGESTIONLIKE_START ===
class SuggestionLike(Protocol):
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]
# === ANCHOR: PATCH_BUILDER_SUGGESTIONLIKE_END ===


# === ANCHOR: PATCH_BUILDER_RELATED_FILES_POSTPROCESS_START ===
def _extract_codespeak_action(codespeak: object) -> str:
    return getattr(codespeak, "action", "update") or "update"


def _extract_codespeak_subject(codespeak: object) -> str:
    return getattr(codespeak, "subject", "") or ""


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


def _postprocess_related_files(
    related_files: list[dict[str, object]],
    operation: str,
    action: str,
    *,
    root: Path,
    best_path: Path,
    codespeak_subject: str,
) -> list[dict[str, object]]:
    if operation == "move":
        return []
    result = list(related_files)
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
    return _dedupe_related_files(result)
# === ANCHOR: PATCH_BUILDER_RELATED_FILES_POSTPROCESS_END ===


# === ANCHOR: PATCH_BUILDER_CONTRACTHELPERSMODULE_START ===
class ContractHelpersModule(Protocol):
    # === ANCHOR: PATCH_BUILDER_ALLOWED_OPS_FOR_ACTION_START ===
    def allowed_ops_for_action(self, action: str) -> list[str]: ...
    # === ANCHOR: PATCH_BUILDER_ALLOWED_OPS_FOR_ACTION_END ===
    # === ANCHOR: PATCH_BUILDER_APPLY_MULTI_INTENT_GATE_START ===
    def apply_multi_intent_gate(
        self, *, status: str, sub_intents: list[str], clarifying_questions: list[str]
    # === ANCHOR: PATCH_BUILDER_APPLY_MULTI_INTENT_GATE_END ===
    ) -> tuple[str, list[str]]: ...
    # === ANCHOR: PATCH_BUILDER_APPLY_SEARCH_FINGERPRINT_READINESS_GATE_START ===
    def apply_search_fingerprint_readiness_gate(
        self,
        *,
        status: str,
        operation: str,
        search_fingerprint: str | None,
        clarifying_questions: list[str],
    # === ANCHOR: PATCH_BUILDER_APPLY_SEARCH_FINGERPRINT_READINESS_GATE_END ===
    ) -> tuple[str, list[str]]: ...
    # === ANCHOR: PATCH_BUILDER_APPLY_VALIDATOR_CONTRACT_GATE_START ===
    def apply_validator_contract_gate(
        self,
        *,
        status: str,
        operation: str,
        destination_file: str,
        destination_anchor: str,
        clarifying_questions: list[str],
    # === ANCHOR: PATCH_BUILDER_APPLY_VALIDATOR_CONTRACT_GATE_END ===
    ) -> tuple[str, list[str]]: ...
    # === ANCHOR: PATCH_BUILDER_BUILD_CONTRACT_START ===
# === ANCHOR: PATCH_BUILDER_CONTRACTHELPERSMODULE_END ===
    def build_contract(self, patch_plan: dict[str, object]) -> dict[str, object]: ...
    # === ANCHOR: PATCH_BUILDER_BUILD_CONTRACT_END ===
    # === ANCHOR: PATCH_BUILDER_BUILD_SEARCH_FINGERPRINT_START ===
    def build_search_fingerprint(
        self, request: str, patch_points: dict[str, object], operation: str
    # === ANCHOR: PATCH_BUILDER_BUILD_SEARCH_FINGERPRINT_END ===
    ) -> str | None: ...
    # === ANCHOR: PATCH_BUILDER_PATCH_STATUS_START ===
    def patch_status(
        self, confidence: str, file_status: str, anchor_status: str
    # === ANCHOR: PATCH_BUILDER_PATCH_STATUS_END ===
    ) -> str: ...
    # === ANCHOR: PATCH_BUILDER_TARGET_ANCHOR_STATUS_START ===
    def target_anchor_status(self, target_anchor: str) -> str: ...
    # === ANCHOR: PATCH_BUILDER_TARGET_ANCHOR_STATUS_END ===
    # === ANCHOR: PATCH_BUILDER_TARGET_FILE_STATUS_START ===
    def target_file_status(self, target_file: str) -> str: ...
    # === ANCHOR: PATCH_BUILDER_TARGET_FILE_STATUS_END ===


# === ANCHOR: PATCH_BUILDER_PREVIEWHELPERSMODULE_START ===
class PreviewHelpersModule(Protocol):
    # === ANCHOR: PATCH_BUILDER_RENDER_PREVIEW_START ===
    def render_preview(self, target_path: Path, target_anchor: str) -> str: ...
    # === ANCHOR: PATCH_BUILDER_RENDER_PREVIEW_END ===
    # === ANCHOR: PATCH_BUILDER_BUILD_STEP_CONTEXT_SNIPPET_START ===
    def build_step_context_snippet(
        self, root: Path, target_file: str, target_anchor: str
    # === ANCHOR: PATCH_BUILDER_BUILD_STEP_CONTEXT_SNIPPET_END ===
# === ANCHOR: PATCH_BUILDER_PREVIEWHELPERSMODULE_END ===
    ) -> str | None: ...
    # === ANCHOR: PATCH_BUILDER_BUILD_PREVIEW_PAYLOAD_START ===
    def build_preview_payload(
        self, root: Path, target_file: str, target_anchor: str, confidence: object
    # === ANCHOR: PATCH_BUILDER_BUILD_PREVIEW_PAYLOAD_END ===
    ) -> dict[str, object] | None: ...


# === ANCHOR: PATCH_BUILDER_STEPHELPERSMODULE_START ===
class StepHelpersModule(Protocol):
    # === ANCHOR: PATCH_BUILDER_BUILD_PATCH_STEPS_START ===
    def build_patch_steps(
        self,
        *,
        root: Path,
        request: str,
        codespeak: CodeSpeakResult,
        target_file: str,
        target_anchor: str,
        confidence: str,
        sub_intents: list[str] | None,
        destination_target_file: str | None,
        destination_target_anchor: str | None,
        contract_helpers: ContractHelpersModule,
        build_step_context_snippet: Callable[[Path, str, str], str | None],
    # === ANCHOR: PATCH_BUILDER_BUILD_PATCH_STEPS_END ===
    ) -> list[PatchStep]: ...

    # === ANCHOR: PATCH_BUILDER_BUILD_FANOUT_PATCH_STEPS_START ===
    def build_fanout_patch_steps(
        self,
        root: Path,
        sub_intents: list[str],
        *,
        use_ai: bool,
        quiet_ai: bool,
# === ANCHOR: PATCH_BUILDER_STEPHELPERSMODULE_END ===
        contract_helpers: ContractHelpersModule,
        build_patch_data_with_options: Callable[..., dict[str, object]],
    # === ANCHOR: PATCH_BUILDER_BUILD_FANOUT_PATCH_STEPS_END ===
    ) -> list[PatchStep]: ...


# === ANCHOR: PATCH_BUILDER_RENDERHELPERSMODULE_START ===
class RenderHelpersModule(Protocol):
    # === ANCHOR: PATCH_BUILDER_BUILD_CONSTRAINTS_START ===
# === ANCHOR: PATCH_BUILDER_RENDERHELPERSMODULE_END ===
    def build_constraints(self, codespeak: object) -> list[str]: ...
    # === ANCHOR: PATCH_BUILDER_BUILD_CONSTRAINTS_END ===


# === ANCHOR: PATCH_BUILDER_TARGETINGHELPERSMODULE_START ===
class TargetingHelpersModule(Protocol):
    # === ANCHOR: PATCH_BUILDER_ENHANCE_CODESPEAK_START ===
    def enhance_codespeak(
        self,
        request: str,
        codespeak: CodeSpeakResult,
        *,
        use_ai: bool,
        quiet_ai: bool,
        import_module: Callable[[str], object],
    # === ANCHOR: PATCH_BUILDER_ENHANCE_CODESPEAK_END ===
    ) -> CodeSpeakResult: ...

    # === ANCHOR: PATCH_BUILDER_RESOLVE_PATCH_TARGETING_START ===
    def resolve_patch_targeting(
        self,
        root: Path,
        request: str,
        codespeak: CodeSpeakResult,
        *,
# === ANCHOR: PATCH_BUILDER_TARGETINGHELPERSMODULE_END ===
        use_ai: bool,
        coerce_json_object: Callable[[object], object],
    # === ANCHOR: PATCH_BUILDER_RESOLVE_PATCH_TARGETING_END ===
    ) -> dict[str, object]: ...


# === ANCHOR: PATCH_BUILDER_FANOUTHELPERSMODULE_START ===
class FanoutHelpersModule(Protocol):
    # === ANCHOR: PATCH_BUILDER_APPLY_LAZY_FANOUT_START ===
    def apply_lazy_fanout(
        self,
        request: str,
        sub_first: dict[str, object],
        sub_intents: list[str],
# === ANCHOR: PATCH_BUILDER_FANOUTHELPERSMODULE_END ===
    # === ANCHOR: PATCH_BUILDER_APPLY_LAZY_FANOUT_END ===
    ) -> dict[str, object]: ...


# === ANCHOR: PATCH_BUILDER__CONTRACT_HELPERS_START ===
def _contract_helpers() -> ContractHelpersModule:
    return cast(
        ContractHelpersModule,
        cast(object, importlib.import_module("vibelign.patch.patch_contract_helpers")),
    )
# === ANCHOR: PATCH_BUILDER__CONTRACT_HELPERS_END ===


# === ANCHOR: PATCH_BUILDER__PREVIEW_HELPERS_START ===
def _preview_helpers() -> PreviewHelpersModule:
    return cast(
        PreviewHelpersModule,
        cast(object, importlib.import_module("vibelign.patch.patch_preview")),
    )
# === ANCHOR: PATCH_BUILDER__PREVIEW_HELPERS_END ===


# === ANCHOR: PATCH_BUILDER__STEP_HELPERS_START ===
def _step_helpers() -> StepHelpersModule:
    return cast(
        StepHelpersModule,
        cast(object, importlib.import_module("vibelign.patch.patch_steps")),
    )
# === ANCHOR: PATCH_BUILDER__STEP_HELPERS_END ===


# === ANCHOR: PATCH_BUILDER__RENDER_HELPERS_START ===
def _render_helpers() -> RenderHelpersModule:
    return cast(
        RenderHelpersModule,
        cast(object, importlib.import_module("vibelign.patch.patch_render")),
    )
# === ANCHOR: PATCH_BUILDER__RENDER_HELPERS_END ===


# === ANCHOR: PATCH_BUILDER__TARGETING_HELPERS_START ===
def _targeting_helpers() -> TargetingHelpersModule:
    return cast(
        TargetingHelpersModule,
        cast(object, importlib.import_module("vibelign.patch.patch_targeting")),
    )
# === ANCHOR: PATCH_BUILDER__TARGETING_HELPERS_END ===


# === ANCHOR: PATCH_BUILDER__FANOUT_HELPERS_START ===
def _fanout_helpers() -> FanoutHelpersModule:
    return cast(
        FanoutHelpersModule,
        cast(object, importlib.import_module("vibelign.patch.patch_fanout")),
    )
# === ANCHOR: PATCH_BUILDER__FANOUT_HELPERS_END ===


# === ANCHOR: PATCH_BUILDER__BUILD_READY_HANDOFF_START ===
def _build_ready_handoff(
    contract: dict[str, object],
    patch_plan: dict[str, object],
    strict_patch: dict[str, object] | None = None,
# === ANCHOR: PATCH_BUILDER__BUILD_READY_HANDOFF_END ===
) -> dict[str, object]:
    build_ready_handoff = cast(
        Callable[
            [dict[str, object], dict[str, object], dict[str, object] | None],
            dict[str, object],
        ],
        importlib.import_module("vibelign.patch.patch_handoff").build_ready_handoff,
    )
    return build_ready_handoff(contract, patch_plan, strict_patch)


# === ANCHOR: PATCH_BUILDER_BUILD_CONTRACT_START ===
def build_contract(patch_plan: dict[str, object]) -> dict[str, object]:
    return _contract_helpers().build_contract(patch_plan)
# === ANCHOR: PATCH_BUILDER_BUILD_CONTRACT_END ===


# === ANCHOR: PATCH_BUILDER__COERCE_JSON_VALUE_START ===
def _coerce_json_value(value: object) -> JsonValue:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_coerce_json_value(item) for item in cast(list[object], value)]
    if isinstance(value, dict):
        return {
            str(key): _coerce_json_value(item)
            for key, item in cast(dict[object, object], value).items()
        }
    return str(value)
# === ANCHOR: PATCH_BUILDER__COERCE_JSON_VALUE_END ===


# === ANCHOR: PATCH_BUILDER__COERCE_JSON_OBJECT_START ===
def _coerce_json_object(value: object) -> JsonObject | None:
    if not isinstance(value, dict):
        return None
    return {
        str(key): _coerce_json_value(item)
        for key, item in cast(dict[object, object], value).items()
    }
# === ANCHOR: PATCH_BUILDER__COERCE_JSON_OBJECT_END ===


# === ANCHOR: PATCH_BUILDER__DESTINATION_FIELD_START ===
def _destination_field(
    suggestion: SuggestionLike | None,
    field_name: str,
# === ANCHOR: PATCH_BUILDER__DESTINATION_FIELD_END ===
) -> str | None:
    if suggestion is None:
        return None
    value = getattr(suggestion, field_name, None)
    return value if isinstance(value, str) else None


# === ANCHOR: PATCH_BUILDER__RENDER_PREVIEW_START ===
def _render_preview(target_path: Path, target_anchor: str) -> str:
    return _preview_helpers().render_preview(target_path, target_anchor)
# === ANCHOR: PATCH_BUILDER__RENDER_PREVIEW_END ===


# === ANCHOR: PATCH_BUILDER__BUILD_STEP_CONTEXT_SNIPPET_START ===
def _build_step_context_snippet(
    root: Path, target_file: str, target_anchor: str
# === ANCHOR: PATCH_BUILDER__BUILD_STEP_CONTEXT_SNIPPET_END ===
) -> str | None:
    if not target_file or target_file == "[소스 파일 없음]":
        return None
    target_path = root / target_file
    if not target_path.exists():
        return None
    window = fetch_anchor_context_window(target_path, target_anchor)
    if window and window.strip():
        return window
    snippet = _render_preview(target_path, target_anchor)
    return snippet if snippet.strip() else None


# === ANCHOR: PATCH_BUILDER__BUILD_PATCH_STEPS_START ===
def _build_patch_steps(
    *,
    root: Path,
    request: str,
    codespeak: CodeSpeakResult,
    target_file: str,
    target_anchor: str,
    confidence: str,
    sub_intents: list[str] | None,
    destination_target_file: str | None,
    destination_target_anchor: str | None,
# === ANCHOR: PATCH_BUILDER__BUILD_PATCH_STEPS_END ===
) -> list[PatchStep]:
    return _step_helpers().build_patch_steps(
        root=root,
        request=request,
        codespeak=codespeak,
        target_file=target_file,
        target_anchor=target_anchor,
        confidence=confidence,
        sub_intents=sub_intents,
        destination_target_file=destination_target_file,
        destination_target_anchor=destination_target_anchor,
        contract_helpers=_contract_helpers(),
        build_step_context_snippet=_build_step_context_snippet,
    )


# === ANCHOR: PATCH_BUILDER__BUILD_FANOUT_PATCH_STEPS_START ===
def _build_fanout_patch_steps(
    root: Path,
    sub_intents: list[str],
    *,
    use_ai: bool,
    quiet_ai: bool,
# === ANCHOR: PATCH_BUILDER__BUILD_FANOUT_PATCH_STEPS_END ===
) -> list[PatchStep]:
    return _step_helpers().build_fanout_patch_steps(
        root,
        sub_intents,
        use_ai=use_ai,
        quiet_ai=quiet_ai,
        contract_helpers=_contract_helpers(),
        build_patch_data_with_options=_build_patch_data_with_options,
    )


# === ANCHOR: PATCH_BUILDER__BUILD_CONSTRAINTS_START ===
def _build_constraints(codespeak: object) -> list[str]:
    return _render_helpers().build_constraints(codespeak)
# === ANCHOR: PATCH_BUILDER__BUILD_CONSTRAINTS_END ===


# === ANCHOR: PATCH_BUILDER__BUILD_PATCH_DATA_WITH_OPTIONS_START ===
def _build_patch_data_with_options(
    root: Path,
    request: str,
    use_ai: bool,
    quiet_ai: bool,
    enable_step_fanout: bool = True,
    lazy_fanout: bool = False,
# === ANCHOR: PATCH_BUILDER__BUILD_PATCH_DATA_WITH_OPTIONS_END ===
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
    targeting = _targeting_helpers().resolve_patch_targeting(
        root,
        request,
        codespeak,
        use_ai=use_ai,
        coerce_json_object=cast(Callable[[object], object], _coerce_json_object),
    )
    suggestion = cast(SuggestionLike, targeting["suggestion"])
    source_resolution = cast(JsonObject | None, targeting["source_resolution"])
    destination_suggestion = cast(
        SuggestionLike | None, targeting["destination_suggestion"]
    )
    destination_resolution = cast(
        JsonObject | None, targeting["destination_resolution"]
    )
    confidence = str(targeting["confidence"])
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
        related_files=_postprocess_related_files(
            getattr(suggestion, "related_files", []),
            codespeak.patch_points.get("operation", "update"),
            _extract_codespeak_action(codespeak),
            root=root,
            best_path=root / suggestion.target_file,
            codespeak_subject=_extract_codespeak_subject(codespeak),
        ),
        steps=steps,
    )
    codespeak_generated = codespeak.codespeak != "" and codespeak.confidence != "none"
    plan_dict = patch_plan.to_dict()
    plan_dict["codespeak_generated"] = codespeak_generated
    return {"patch_plan": plan_dict}


# === ANCHOR: PATCH_BUILDER__BUILD_PATCH_DATA_START ===
def _build_patch_data(
    root: Path,
    request: str,
    *,
    use_ai: bool = False,
    quiet_ai: bool = True,
    preview: bool = False,
    lazy_fanout: bool = False,
# === ANCHOR: PATCH_BUILDER__BUILD_PATCH_DATA_END ===
) -> dict[str, object]:
    data = _build_patch_data_with_options(
        root,
        request,
        use_ai=use_ai,
        quiet_ai=quiet_ai,
        lazy_fanout=lazy_fanout,
    )
    patch_plan = cast(dict[str, object], data["patch_plan"])
    contract = build_contract(patch_plan)
    data["contract"] = contract
    strict_patch = build_strict_patch_artifact(root, patch_plan, contract)
    if strict_patch is not None:
        data["strict_patch"] = strict_patch
    if contract["status"] == "READY":
        data["handoff"] = _build_ready_handoff(contract, patch_plan, strict_patch)

    if preview:
        target_file = str(patch_plan["target_file"])
        target_anchor = str(patch_plan["target_anchor"])
        preview_payload = _preview_helpers().build_preview_payload(
            root, target_file, target_anchor, patch_plan["confidence"]
        )
        if preview_payload is not None:
            data["preview"] = preview_payload

    return data


# === ANCHOR: PATCH_BUILDER_BUILD_PATCH_DATA_START ===
def build_patch_data(
    root: Path,
    request: str,
    *,
    use_ai: bool = False,
    quiet_ai: bool = True,
    preview: bool = False,
    lazy_fanout: bool = False,
# === ANCHOR: PATCH_BUILDER_BUILD_PATCH_DATA_END ===
) -> dict[str, object]:
    return _build_patch_data(
        root,
        request,
        use_ai=use_ai,
        quiet_ai=quiet_ai,
        preview=preview,
        lazy_fanout=lazy_fanout,
    )
# === ANCHOR: PATCH_BUILDER_END ===
