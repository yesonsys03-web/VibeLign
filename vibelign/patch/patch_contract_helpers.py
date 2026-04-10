# === ANCHOR: PATCH_CONTRACT_HELPERS_START ===
from typing import cast

from vibelign.core import PatchContract
from vibelign.core.codespeak import parse_codespeak_v0
from vibelign.core.patch_suggester import tokenize

_STATEFUL_UI_KEYWORDS = {
    "persist",
    "state",
    "remember",
    "remembered",
    "enable",
    "enabled",
    "disable",
    "disabled",
    "status",
    "유지",
    "보존",
    "상태",
    "활성화",
    "비활성화",
    "켜",
    "꺼",
    "enable",
}

_NAV_CONTEXT_KEYWORDS = {
    "menu",
    "tab",
    "tabs",
    "navigate",
    "navigation",
    "page",
    "screen",
    "메뉴",
    "탭",
    "페이지",
    "화면",
    "갔다",
    "돌아",
}

_LOW_SIGNAL_FOCUS_TOKENS = (
    _STATEFUL_UI_KEYWORDS
    | _NAV_CONTEXT_KEYWORDS
    | {
        "app",
        "home",
        "page",
        "screen",
        "component",
        "ui",
        "this",
        "that",
        "other",
        "다른",
        "다시",
        "갔다",
        "오면",
        "수정",
        "fix",
        "update",
    }
)

_GENERIC_UI_TARGET_TOKENS = {"app", "layout", "home", "page", "screen"}


# === ANCHOR: PATCH_CONTRACT_HELPERS_ALLOWED_OPS_FOR_ACTION_START ===
def allowed_ops_for_action(action: str) -> list[str]:
    return {
        "add": ["insert_after", "insert_before"],
        "remove": ["delete_range"],
        "fix": ["replace_range"],
        "update": ["replace_range"],
        "split": ["replace_range", "insert_after"],
        "apply": ["replace_range"],
    }.get(action, ["replace_range"])


# === ANCHOR: PATCH_CONTRACT_HELPERS_ALLOWED_OPS_FOR_ACTION_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_TARGET_FILE_STATUS_START ===
def target_file_status(target_file: str) -> str:
    if target_file == "[소스 파일 없음]":
        return "no_source_files"
    return "ok"


# === ANCHOR: PATCH_CONTRACT_HELPERS_TARGET_FILE_STATUS_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_TARGET_ANCHOR_STATUS_START ===
def target_anchor_status(target_anchor: str) -> str:
    if target_anchor == "[먼저 앵커를 추가하세요]":
        return "missing"
    if target_anchor == "[없음]":
        return "none"
    if target_anchor.startswith("[추천 앵커: ") and target_anchor.endswith("]"):
        return "suggested"
    return "ok"


# === ANCHOR: PATCH_CONTRACT_HELPERS_TARGET_ANCHOR_STATUS_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_TARGET_ANCHOR_NAME_START ===
def target_anchor_name(target_anchor: str) -> str | None:
    if target_anchor.startswith("[추천 앵커: ") and target_anchor.endswith("]"):
        return target_anchor[len("[추천 앵커: ") : -1]
    status = target_anchor_status(target_anchor)
    if status == "ok":
        return target_anchor
    return None


# === ANCHOR: PATCH_CONTRACT_HELPERS_TARGET_ANCHOR_NAME_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_PATCH_STATUS_START ===
def patch_status(confidence: str, file_status: str, anchor_status: str) -> str:
    if file_status != "ok":
        return "REFUSED"
    if confidence == "low" or anchor_status in {"missing", "suggested", "none"}:
        return "NEEDS_CLARIFICATION"
    return "READY"


# === ANCHOR: PATCH_CONTRACT_HELPERS_PATCH_STATUS_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_PRECONDITIONS_START ===
def preconditions(target_file: str, target_anchor: str) -> list[str]:
    conditions = [f"허용된 파일은 `{target_file}` 하나뿐이어야 합니다."]
    anchor_status_value = target_anchor_status(target_anchor)
    anchor_name_value = target_anchor_name(target_anchor) or ""
    if anchor_status_value == "ok" and anchor_name_value:
        conditions.append(
            f"`{anchor_name_value}` 안전 구역이 현재 파일에 실제로 있어야 합니다."
        )
    elif anchor_status_value == "missing":
        conditions.append("실행 전에 먼저 앵커를 추가해야 합니다.")
    elif anchor_status_value == "suggested" and anchor_name_value:
        conditions.append(
            f"실행 전에 추천 앵커 `{anchor_name_value}` 를 먼저 만들어야 합니다."
        )
    return conditions


# === ANCHOR: PATCH_CONTRACT_HELPERS_PRECONDITIONS_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_AUGMENT_CLARIFYING_QUESTIONS_START ===
def augment_clarifying_questions(
    patch_plan: dict[str, object],
    file_status: str,
    anchor_status: str,
    # === ANCHOR: PATCH_CONTRACT_HELPERS_AUGMENT_CLARIFYING_QUESTIONS_END ===
) -> list[str]:
    raw_questions = patch_plan.get("clarifying_questions", [])
    question_items = (
        cast(list[object], raw_questions) if isinstance(raw_questions, list) else []
    )
    questions = [
        str(item) for item in question_items if isinstance(item, str) and item.strip()
    ]
    target_file = str(patch_plan.get("target_file", ""))
    target_anchor = str(patch_plan.get("target_anchor", ""))
    request = str(patch_plan.get("request", ""))

    # === ANCHOR: PATCH_CONTRACT_HELPERS_ADD_START ===
    def add(question: str) -> None:
        if question not in questions:
            questions.append(question)

    # === ANCHOR: PATCH_CONTRACT_HELPERS_ADD_END ===

    if file_status == "no_source_files":
        add("지금 수정할 소스 파일이 없어요. 먼저 어떤 파일을 만들거나 열어야 할까요?")
    if anchor_status == "missing":
        add(
            f"`{target_file}` 안에서 정확히 어느 함수나 구역을 바꾸고 싶은지 말해줄 수 있나요?"
        )
        add(
            "안전 구역이 아직 없어요. `vib anchor --suggest` 결과를 보고 어떤 구역에 앵커를 만들지 정할까요?"
        )
    if anchor_status == "suggested":
        add(
            f"추천된 안전 구역 `{target_anchor}` 근처를 바꾸고 싶은 게 맞나요? 맞다면 앵커를 먼저 만들게요."
        )
    if anchor_status == "none":
        add(
            "어느 파일이나 위치를 바꾸고 싶은지 한 단계만 더 구체적으로 말해줄 수 있나요?"
        )
    if not questions:
        add(
            f"`{request}` 요청에서 가장 먼저 바꾸고 싶은 화면, 파일, 또는 함수 이름이 있나요?"
        )
        add("추가인지 수정인지, 또는 버그 수정인지 알려줄 수 있나요?")
    return questions


# === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_VALIDATOR_CONTRACT_GATE_START ===
def apply_validator_contract_gate(
    *,
    status: str,
    operation: str,
    destination_file: str,
    destination_anchor: str,
    clarifying_questions: list[str],
    # === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_VALIDATOR_CONTRACT_GATE_END ===
) -> tuple[str, list[str]]:
    questions = list(clarifying_questions)
    if (
        status != "REFUSED"
        and operation != "move"
        and (destination_file or destination_anchor)
    ):
        question = (
            "이 요청은 이동(move)으로 해석되지 않았는데 목적지 정보가 함께 잡혔어요. "
            "수정인지 이동인지, 그리고 실제 목적지가 맞는지 한 번만 더 확인해줄 수 있나요?"
        )
        if question not in questions:
            questions.append(question)
        return "NEEDS_CLARIFICATION", questions
    return status, questions


# === ANCHOR: PATCH_CONTRACT_HELPERS_NORMALIZE_SEARCH_FINGERPRINT_START ===
def normalize_search_fingerprint(text: str) -> str | None:
    normalized = " ".join(text.split()).strip()
    return normalized or None


# === ANCHOR: PATCH_CONTRACT_HELPERS_NORMALIZE_SEARCH_FINGERPRINT_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_IS_USABLE_SEARCH_FINGERPRINT_START ===
def is_usable_search_fingerprint(fingerprint: str | None) -> bool:
    if not fingerprint:
        return False
    normalized = fingerprint.casefold()
    if normalized in {"it", "this", "that", "이것", "이걸", "그것", "저것"}:
        return False
    return len(tokenize(fingerprint)) >= 2


# === ANCHOR: PATCH_CONTRACT_HELPERS_IS_USABLE_SEARCH_FINGERPRINT_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_BUILD_SEARCH_FINGERPRINT_START ===
def build_search_fingerprint(
    request: str,
    patch_points: dict[str, object],
    operation: str,
    # === ANCHOR: PATCH_CONTRACT_HELPERS_BUILD_SEARCH_FINGERPRINT_END ===
) -> str | None:
    if operation == "move":
        source_text = str(patch_points.get("source", ""))
        fingerprint = normalize_search_fingerprint(source_text)
        if not is_usable_search_fingerprint(fingerprint):
            return None
        return fingerprint
    return normalize_search_fingerprint(request)


# === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_SEARCH_FINGERPRINT_READINESS_GATE_START ===
def apply_search_fingerprint_readiness_gate(
    *,
    status: str,
    operation: str,
    search_fingerprint: str | None,
    clarifying_questions: list[str],
    # === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_SEARCH_FINGERPRINT_READINESS_GATE_END ===
) -> tuple[str, list[str]]:
    questions = list(clarifying_questions)
    if (
        status != "REFUSED"
        and operation == "move"
        and not is_usable_search_fingerprint(search_fingerprint)
    ):
        question = "이동할 원본 블록을 validator가 정확히 찾으려면, 먼저 옮길 대상의 현재 이름이나 문구를 더 구체적으로 알려줄 수 있나요?"
        if question not in questions:
            questions.append(question)
        return "NEEDS_CLARIFICATION", questions
    return status, questions


# === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_MULTI_INTENT_GATE_START ===
def apply_multi_intent_gate(
    *,
    status: str,
    sub_intents: list[str],
    clarifying_questions: list[str],
    # === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_MULTI_INTENT_GATE_END ===
) -> tuple[str, list[str]]:
    questions = list(clarifying_questions)
    if status != "REFUSED" and len(sub_intents) > 1:
        question = "지금 요청에는 수정 의도가 여러 개 섞여 있어요. 우선 한 번에 한 가지 변경만 말해줄 수 있나요?"
        if question not in questions:
            questions.append(question)
        return "NEEDS_CLARIFICATION", questions
    return status, questions


# === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_STATEFUL_UI_TARGET_GATE_START ===
def apply_stateful_ui_target_gate(
    *,
    status: str,
    request: str,
    target_file: str,
    target_anchor: str,
    layer: str,
    operation: str,
    clarifying_questions: list[str],
) -> tuple[str, list[str]]:
    questions = list(clarifying_questions)
    if status == "REFUSED" or operation == "move" or layer != "ui":
        return status, questions

    request_tokens = set(tokenize(request))
    has_stateful_signal = bool(request_tokens & _STATEFUL_UI_KEYWORDS)
    has_navigation_signal = bool(request_tokens & _NAV_CONTEXT_KEYWORDS)
    if not has_stateful_signal or not has_navigation_signal:
        return status, questions

    target_tokens = set(tokenize(f"{target_file} {target_anchor}"))
    is_generic_ui_target = bool(target_tokens & _GENERIC_UI_TARGET_TOKENS)
    if not is_generic_ui_target:
        return status, questions

    focus_tokens = [
        token for token in request_tokens if token not in _LOW_SIGNAL_FOCUS_TOKENS
    ]
    if not focus_tokens:
        return status, questions
    if any(token in target_tokens for token in focus_tokens):
        return status, questions

    question = (
        "지금 요청은 메뉴 이동 뒤에도 유지되어야 하는 UI 상태 문제로 보이는데, "
        f"현재 추천된 `{target_file}` / `{target_anchor}` 만으로는 관련 상태 소유 위치가 충분히 드러나지 않아요. "
        "문제가 보이는 카드나 컴포넌트 이름을 한 번만 더 알려줄 수 있나요?"
    )
    if question not in questions:
        questions.append(question)
    return "NEEDS_CLARIFICATION", questions


# === ANCHOR: PATCH_CONTRACT_HELPERS_APPLY_STATEFUL_UI_TARGET_GATE_END ===


# === ANCHOR: PATCH_CONTRACT_HELPERS_BUILD_CONTRACT_START ===
def build_contract(patch_plan: dict[str, object]) -> dict[str, object]:
    target_file = str(patch_plan["target_file"])
    target_anchor = str(patch_plan["target_anchor"])
    destination_file = str(patch_plan.get("destination_target_file") or "")
    destination_anchor = str(patch_plan.get("destination_target_anchor") or "")
    patch_points = cast(dict[str, object], patch_plan.get("patch_points", {}))
    sub_intents_raw = patch_plan.get("sub_intents", [])
    sub_intents = (
        [str(item) for item in cast(list[object], sub_intents_raw) if str(item).strip()]
        if isinstance(sub_intents_raw, list)
        else []
    )
    operation = str(patch_points.get("operation", "update"))
    file_status = target_file_status(target_file)
    anchor_status = target_anchor_status(target_anchor)
    anchor_name_value = target_anchor_name(target_anchor) or ""
    destination_file_status = (
        target_file_status(destination_file) if destination_file else "none"
    )
    destination_anchor_status = (
        target_anchor_status(destination_anchor) if destination_anchor else "none"
    )
    status = patch_status(str(patch_plan["confidence"]), file_status, anchor_status)
    if operation == "move" and (
        destination_file_status != "ok" or destination_anchor_status != "ok"
    ):
        status = "NEEDS_CLARIFICATION"
    clarifying_questions = augment_clarifying_questions(
        patch_plan, file_status, anchor_status
    )
    status, clarifying_questions = apply_validator_contract_gate(
        status=status,
        operation=operation,
        destination_file=destination_file,
        destination_anchor=destination_anchor,
        clarifying_questions=clarifying_questions,
    )
    search_fingerprint = build_search_fingerprint(
        str(patch_plan.get("request", "")), patch_points, operation
    )
    status, clarifying_questions = apply_search_fingerprint_readiness_gate(
        status=status,
        operation=operation,
        search_fingerprint=search_fingerprint,
        clarifying_questions=clarifying_questions,
    )
    status, clarifying_questions = apply_multi_intent_gate(
        status=status,
        sub_intents=sub_intents,
        clarifying_questions=clarifying_questions,
    )
    codespeak_parts = parse_codespeak_v0(str(patch_plan["codespeak"])) or {
        "layer": "core",
        "target": "patch",
        "subject": "request",
        "action": "update",
    }
    status, clarifying_questions = apply_stateful_ui_target_gate(
        status=status,
        request=str(patch_plan.get("request", "")),
        target_file=target_file,
        target_anchor=target_anchor,
        layer=codespeak_parts["layer"],
        operation=operation,
        clarifying_questions=clarifying_questions,
    )
    assumptions: list[str] = []
    if status == "NEEDS_CLARIFICATION":
        assumptions.append("요청 범위나 수정 위치가 아직 충분히 분명하지 않습니다.")
    else:
        clarifying_questions = []
    user_status = {
        "READY": {
            "title": "지금 바로 진행할 수 있어요",
            "reason": "바꿀 파일과 안전 구역이 정해져 있어서, 이 계획을 AI에게 전달해도 괜찮아요.",
            "next_step": "이제 이 계획을 AI 도구에 전달해서 수정 작업을 진행하세요.",
        },
        "NEEDS_CLARIFICATION": {
            "title": "조금 더 알려주면 바로 도와줄 수 있어요",
            "reason": "바꿀 위치나 범위가 아직 충분히 분명하지 않아서, 지금 바로 수정하면 엉뚱한 곳을 건드릴 수 있어요.",
            "next_step": "먼저 질문에 답하거나 앵커를 추가한 뒤 다시 시도하세요.",
        },
        "REFUSED": {
            "title": "지금은 먼저 준비가 필요해요",
            "reason": "수정할 수 있는 파일이나 기본 조건이 아직 맞지 않아서, 바로 진행하면 안 돼요.",
            "next_step": "프로젝트 상태를 먼저 확인하고, 수정할 대상 파일이 있는지부터 다시 살펴보세요.",
        },
    }[status]
    user_guidance: list[str]
    if status == "READY":
        user_guidance = [
            "지금은 바로 AI에게 전달해도 괜찮아요.",
            "전달하기 전에 미리 보기와 바꿀 파일을 한 번만 더 확인하세요.",
            "전달한 뒤에는 `vib guard`로 결과를 다시 확인하세요.",
        ]
    elif status == "NEEDS_CLARIFICATION":
        user_guidance = [
            "지금은 바로 수정하지 마세요.",
            "먼저 아래 질문에 답하거나, 요청을 더 구체적으로 써주세요.",
            "안전 구역이 없다고 나오면 `vib anchor --suggest` 또는 `vib anchor --auto`를 먼저 실행하세요.",
        ]
    else:
        user_guidance = [
            "지금은 바로 수정하면 안 돼요.",
            "먼저 프로젝트 상태와 대상 파일부터 다시 확인하세요.",
        ]
    contract = PatchContract.from_context(
        status=status,
        patch_plan=patch_plan,
        codespeak_parts=codespeak_parts,
        file_status=file_status,
        anchor_status=anchor_status,
        anchor_name=anchor_name_value,
        destination_file_status=destination_file_status,
        destination_anchor_status=destination_anchor_status,
        destination_file=destination_file,
        destination_anchor=destination_anchor,
        allowed_ops=allowed_ops_for_action(codespeak_parts["action"]),
        preconditions=preconditions(target_file, target_anchor),
        assumptions=assumptions,
        clarifying_questions=clarifying_questions,
        user_status=user_status,
        user_guidance=user_guidance,
    )
    return cast(dict[str, object], contract.to_dict())


# === ANCHOR: PATCH_CONTRACT_HELPERS_BUILD_CONTRACT_END ===
# === ANCHOR: PATCH_CONTRACT_HELPERS_END ===
