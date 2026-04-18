# === ANCHOR: PATCH_STEPS_START ===
from collections.abc import Callable
from pathlib import Path
from typing import Protocol, cast

from vibelign.core import PatchStep
from vibelign.core.codespeak import CodeSpeakResult


# === ANCHOR: PATCH_STEPS_CONTRACTHELPERSMODULE_START ===
class ContractHelpersModule(Protocol):
    # === ANCHOR: PATCH_STEPS_ALLOWED_OPS_FOR_ACTION_START ===
    def allowed_ops_for_action(self, action: str) -> list[str]: ...
    # === ANCHOR: PATCH_STEPS_ALLOWED_OPS_FOR_ACTION_END ===
    # === ANCHOR: PATCH_STEPS_APPLY_MULTI_INTENT_GATE_START ===
    def apply_multi_intent_gate(
        self, *, status: str, sub_intents: list[str], clarifying_questions: list[str]
    # === ANCHOR: PATCH_STEPS_APPLY_MULTI_INTENT_GATE_END ===
    ) -> tuple[str, list[str]]: ...
    # === ANCHOR: PATCH_STEPS_APPLY_SEARCH_FINGERPRINT_READINESS_GATE_START ===
    def apply_search_fingerprint_readiness_gate(
        self,
        *,
        status: str,
        operation: str,
        search_fingerprint: str | None,
        clarifying_questions: list[str],
    # === ANCHOR: PATCH_STEPS_APPLY_SEARCH_FINGERPRINT_READINESS_GATE_END ===
    ) -> tuple[str, list[str]]: ...
    # === ANCHOR: PATCH_STEPS_APPLY_VALIDATOR_CONTRACT_GATE_START ===
    def apply_validator_contract_gate(
        self,
        *,
        status: str,
        operation: str,
        destination_file: str,
        destination_anchor: str,
        clarifying_questions: list[str],
    # === ANCHOR: PATCH_STEPS_APPLY_VALIDATOR_CONTRACT_GATE_END ===
    ) -> tuple[str, list[str]]: ...
# === ANCHOR: PATCH_STEPS_CONTRACTHELPERSMODULE_END ===
    # === ANCHOR: PATCH_STEPS_BUILD_SEARCH_FINGERPRINT_START ===
    def build_search_fingerprint(
        self, request: str, patch_points: dict[str, object], operation: str
    # === ANCHOR: PATCH_STEPS_BUILD_SEARCH_FINGERPRINT_END ===
    ) -> str | None: ...
    # === ANCHOR: PATCH_STEPS_PATCH_STATUS_START ===
    def patch_status(
        self, confidence: str, file_status: str, anchor_status: str
    # === ANCHOR: PATCH_STEPS_PATCH_STATUS_END ===
    ) -> str: ...
    # === ANCHOR: PATCH_STEPS_TARGET_ANCHOR_STATUS_START ===
    def target_anchor_status(self, target_anchor: str) -> str: ...
    # === ANCHOR: PATCH_STEPS_TARGET_ANCHOR_STATUS_END ===
    # === ANCHOR: PATCH_STEPS_TARGET_FILE_STATUS_START ===
    def target_file_status(self, target_file: str) -> str: ...
    # === ANCHOR: PATCH_STEPS_TARGET_FILE_STATUS_END ===


BuildStepContextSnippet = Callable[[Path, str, str], str | None]
BuildPatchDataWithOptions = Callable[..., dict[str, object]]


# === ANCHOR: PATCH_STEPS_BUILD_PATCH_STEPS_START ===
def build_patch_steps(
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
    build_step_context_snippet: BuildStepContextSnippet,
# === ANCHOR: PATCH_STEPS_BUILD_PATCH_STEPS_END ===
) -> list[PatchStep]:
    file_status = contract_helpers.target_file_status(target_file)
    anchor_status = contract_helpers.target_anchor_status(target_anchor)
    status = contract_helpers.patch_status(confidence, file_status, anchor_status)
    operation = str(codespeak.patch_points.get("operation", codespeak.action))
    if codespeak.patch_points.get("operation") == "move":
        destination_file_status = (
            contract_helpers.target_file_status(destination_target_file)
            if destination_target_file
            else "none"
        )
        destination_anchor_status = (
            contract_helpers.target_anchor_status(destination_target_anchor)
            if destination_target_anchor
            else "none"
        )
        if destination_file_status != "ok" or destination_anchor_status != "ok":
            status = "NEEDS_CLARIFICATION"
    status, _clarifying_questions = contract_helpers.apply_validator_contract_gate(
        status=status,
        operation=operation,
        destination_file=destination_target_file or "",
        destination_anchor=destination_target_anchor or "",
        clarifying_questions=[],
    )
    search_fingerprint = contract_helpers.build_search_fingerprint(
        request, cast(dict[str, object], codespeak.patch_points), operation
    )
    status, _clarifying_questions = (
        contract_helpers.apply_search_fingerprint_readiness_gate(
            status=status,
            operation=operation,
            search_fingerprint=search_fingerprint,
            clarifying_questions=[],
        )
    )
    status, _clarifying_questions = contract_helpers.apply_multi_intent_gate(
        status=status,
        sub_intents=sub_intents or [],
        clarifying_questions=[],
    )
    context_snippet = build_step_context_snippet(root, target_file, target_anchor)
    return [
        PatchStep(
            ordinal=0,
            intent_text=(sub_intents[0] if sub_intents else request),
            codespeak=codespeak.codespeak,
            target_file=target_file,
            target_anchor=target_anchor,
            context_snippet=context_snippet,
            allowed_ops=contract_helpers.allowed_ops_for_action(codespeak.action),
            depends_on=None,
            status=status,
            search_fingerprint=search_fingerprint,
        )
    ]


# === ANCHOR: PATCH_STEPS_BUILD_FANOUT_PATCH_STEPS_START ===
def build_fanout_patch_steps(
    root: Path,
    sub_intents: list[str],
    *,
    use_ai: bool,
    quiet_ai: bool,
    contract_helpers: ContractHelpersModule,
    build_patch_data_with_options: BuildPatchDataWithOptions,
# === ANCHOR: PATCH_STEPS_BUILD_FANOUT_PATCH_STEPS_END ===
) -> list[PatchStep]:
    steps: list[PatchStep] = []
    for ordinal, sub_intent in enumerate(sub_intents):
        sub_data = build_patch_data_with_options(
            root,
            sub_intent,
            use_ai=use_ai,
            quiet_ai=quiet_ai,
            enable_step_fanout=False,
            lazy_fanout=False,
        )
        sub_plan = cast(dict[str, object], sub_data["patch_plan"])
        sub_steps = cast(list[object] | None, sub_plan.get("steps")) or []
        if sub_steps:
            first_step = cast(dict[str, object], sub_steps[0])
            step_status, _clarifying_questions = (
                contract_helpers.apply_multi_intent_gate(
                    status=str(first_step.get("status", "NEEDS_CLARIFICATION")),
                    sub_intents=sub_intents,
                    clarifying_questions=[],
                )
            )
            steps.append(
                PatchStep(
                    ordinal=ordinal,
                    intent_text=str(first_step.get("intent_text", sub_intent)),
                    codespeak=(
                        str(first_step.get("codespeak"))
                        if first_step.get("codespeak") is not None
                        else None
                    ),
                    target_file=str(first_step.get("target_file", "")),
                    target_anchor=str(first_step.get("target_anchor", "")),
                    context_snippet=(
                        str(first_step.get("context_snippet"))
                        if first_step.get("context_snippet") is not None
                        else None
                    ),
                    allowed_ops=[
                        str(item)
                        for item in cast(
                            list[object], first_step.get("allowed_ops", [])
                        )
                    ],
                    depends_on=(ordinal - 1 if ordinal > 0 else None),
                    status=step_status,
                    search_fingerprint=(
                        str(first_step.get("search_fingerprint"))
                        if first_step.get("search_fingerprint") is not None
                        else None
                    ),
                )
            )
            continue

        steps.append(
            PatchStep(
                ordinal=ordinal,
                intent_text=sub_intent,
                depends_on=(ordinal - 1 if ordinal > 0 else None),
                context_snippet=None,
                status="NEEDS_CLARIFICATION",
            )
        )
    return steps
# === ANCHOR: PATCH_STEPS_END ===
