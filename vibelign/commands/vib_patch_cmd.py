# === ANCHOR: VIB_PATCH_CMD_START ===
import json
import importlib
from pathlib import Path
from typing import Any, Dict, Optional, cast

from vibelign.core.codespeak import build_codespeak, parse_codespeak_v0
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.patch_suggester import suggest_patch
from vibelign.core.project_scan import safe_read_text


from vibelign.terminal_render import cli_print
from vibelign.terminal_render import print_ai_response

print = cli_print


def _copy_to_clipboard(text: str) -> None:
    """텍스트를 시스템 클립보드에 복사."""
    import subprocess
    import sys

    try:
        if sys.platform == "darwin":
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-8"))
        elif sys.platform.startswith("linux"):
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
            )
            proc.communicate(text.encode("utf-8"))
        elif sys.platform == "win32":
            proc = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
            proc.communicate(text.encode("utf-16le"))
        else:
            from vibelign.terminal_render import clack_warn
            clack_warn("이 OS에서는 클립보드 복사를 지원하지 않아요.")
            return

        from vibelign.terminal_render import clack_success
        clack_success("AI 전달용 프롬프트가 클립보드에 복사되었어요! 바로 붙여넣기하세요.")
    except FileNotFoundError:
        from vibelign.terminal_render import clack_warn
        clack_warn("클립보드 도구를 찾을 수 없어요. (macOS: pbcopy, Linux: xclip)")


def _allowed_ops_for_action(action: str) -> list[str]:
    return {
        "add": ["insert_after", "insert_before"],
        "remove": ["delete_range"],
        "fix": ["replace_range"],
        "update": ["replace_range"],
        "split": ["replace_range", "insert_after"],
        "apply": ["replace_range"],
    }.get(action, ["replace_range"])


def _target_file_status(target_file: str) -> str:
    if target_file == "[소스 파일 없음]":
        return "no_source_files"
    return "ok"


def _target_anchor_status(target_anchor: str) -> str:
    if target_anchor == "[먼저 앵커를 추가하세요]":
        return "missing"
    if target_anchor == "[없음]":
        return "none"
    if target_anchor.startswith("[추천 앵커: ") and target_anchor.endswith("]"):
        return "suggested"
    return "ok"


def _target_anchor_name(target_anchor: str) -> Optional[str]:
    if target_anchor.startswith("[추천 앵커: ") and target_anchor.endswith("]"):
        return target_anchor[len("[추천 앵커: ") : -1]
    status = _target_anchor_status(target_anchor)
    if status == "ok":
        return target_anchor
    return None


def _patch_status(confidence: str, file_status: str, anchor_status: str) -> str:
    if file_status != "ok":
        return "REFUSED"
    if confidence == "low" or anchor_status in {"missing", "suggested", "none"}:
        return "NEEDS_CLARIFICATION"
    return "READY"


def _preconditions(target_file: str, target_anchor: str) -> list[str]:
    conditions = [f"허용된 파일은 `{target_file}` 하나뿐이어야 합니다."]
    anchor_status = _target_anchor_status(target_anchor)
    anchor_name = _target_anchor_name(target_anchor)
    if anchor_status == "ok" and anchor_name is not None:
        conditions.append(
            f"`{anchor_name}` 안전 구역이 현재 파일에 실제로 있어야 합니다."
        )
    elif anchor_status == "missing":
        conditions.append("실행 전에 먼저 앵커를 추가해야 합니다.")
    elif anchor_status == "suggested" and anchor_name is not None:
        conditions.append(
            f"실행 전에 추천 앵커 `{anchor_name}` 를 먼저 만들어야 합니다."
        )
    return conditions


def _augment_clarifying_questions(
    patch_plan: Dict[str, Any], file_status: str, anchor_status: str
) -> list[str]:
    questions = [
        str(item)
        for item in patch_plan.get("clarifying_questions", [])
        if isinstance(item, str) and item.strip()
    ]
    target_file = str(patch_plan.get("target_file", ""))
    target_anchor = str(patch_plan.get("target_anchor", ""))
    request = str(patch_plan.get("request", ""))

    def add(question: str) -> None:
        if question not in questions:
            questions.append(question)

    if file_status == "no_source_files":
        add("지금 수정할 소스 파일이 없어요. 먼저 어떤 파일을 만들거나 열어야 할까요?")
    if anchor_status == "missing":
        add(
            f"`{target_file}` 안에서 정확히 어느 함수나 구역을 바꾸고 싶은지 말해줄 수 있나요?"
        )
        add(
            f"안전 구역이 아직 없어요. `vib anchor --suggest` 결과를 보고 어떤 구역에 앵커를 만들지 정할까요?"
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


def _build_ready_handoff(
    contract: Dict[str, Any], patch_plan: Dict[str, Any]
) -> Dict[str, Any]:
    root = Path.cwd()
    meta = MetaPaths(root)

    prompt_lines = [
        "You are applying a VibeLign patch contract.",
        "",
        "Before making any changes:",
        "1. Read .vibelign/project_map.json to understand the project structure",
        "2. Check the anchor list for the target file",
        "3. Only modify code within the specified anchor boundaries",
        "4. Check @CONNECTS in .vibelign/anchor_meta.json to avoid breaking related features",
        "",
    ]

    # 앵커 메타 정보가 있으면 target_anchor의 intent/connects 포함
    anchor_name = str(patch_plan.get("target_anchor", ""))
    if anchor_name and anchor_name != "N/A":
        anchor_meta_path = meta.vibelign_dir / "anchor_meta.json"
        if anchor_meta_path.exists():
            try:
                anchor_meta = json.loads(anchor_meta_path.read_text(encoding="utf-8"))
                meta_entry = anchor_meta.get(anchor_name, {})
                if meta_entry.get("intent"):
                    prompt_lines.append(f"Anchor intent: {meta_entry['intent']}")
                if meta_entry.get("connects"):
                    prompt_lines.append(
                        f"Connected anchors (may be affected): {', '.join(meta_entry['connects'])}"
                    )
                if meta_entry.get("warning"):
                    prompt_lines.append(f"Warning: {meta_entry['warning']}")
                prompt_lines.append("")
            except (json.JSONDecodeError, OSError):
                pass

    prompt_lines.extend([
        f"Intent: {contract['intent']}",
        f"CodeSpeak: {patch_plan['codespeak']}",
        f"Allowed files: {', '.join(contract['scope']['allowed_files'])}",
        f"Target anchor: {patch_plan['target_anchor']}",
        f"Allowed operations: {', '.join(contract['allowed_ops'])}",
        "Preconditions:",
    ])
    prompt_lines.extend(f"- {item}" for item in contract["preconditions"])
    prompt_lines.extend(
        [
            "Constraints:",
        ]
    )
    prompt_lines.extend(f"- {item}" for item in patch_plan["constraints"])
    prompt_lines.extend(
        [
            f"Expected result: {contract['expected_result']}",
            "Verification:",
        ]
    )
    prompt_lines.extend(f"- {item}" for item in contract["verification"]["commands"])
    prompt_lines.extend(
        [
            "Do not edit files outside the allowed files list.",
            "If a precondition does not match, stop and report the mismatch instead of guessing.",
        ]
    )
    return {
        "ready": True,
        "target_file": patch_plan["target_file"],
        "target_anchor": patch_plan["target_anchor"],
        "allowed_files": contract["scope"]["allowed_files"],
        "allowed_ops": contract["allowed_ops"],
        "preconditions": contract["preconditions"],
        "constraints": patch_plan["constraints"],
        "verification": contract["verification"]["commands"],
        "prompt": "\n".join(prompt_lines),
    }


def _build_contract(patch_plan: Dict[str, Any]) -> Dict[str, Any]:
    target_file = str(patch_plan["target_file"])
    target_anchor = str(patch_plan["target_anchor"])
    file_status = _target_file_status(target_file)
    anchor_status = _target_anchor_status(target_anchor)
    anchor_name = _target_anchor_name(target_anchor)
    status = _patch_status(str(patch_plan["confidence"]), file_status, anchor_status)
    clarifying_questions = _augment_clarifying_questions(
        patch_plan, file_status, anchor_status
    )
    codespeak_parts = parse_codespeak_v0(str(patch_plan["codespeak"])) or {
        "layer": "core",
        "target": "patch",
        "subject": "request",
        "action": "update",
    }
    assumptions = []
    if status == "NEEDS_CLARIFICATION":
        assumptions.append("요청 범위나 수정 위치가 아직 충분히 분명하지 않습니다.")
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
    user_guidance = []
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
    return {
        "status": status,
        "contract_version": "0.1",
        "intent": str(patch_plan["interpretation"]),
        "codespeak_contract_version": 0,
        "codespeak_parts": codespeak_parts,
        "scope": {
            "allowed_files": [target_file] if file_status == "ok" else [],
            "target_file_status": file_status,
            "target_anchor_status": anchor_status,
            "target_anchor_name": anchor_name,
        },
        "allowed_ops": _allowed_ops_for_action(codespeak_parts["action"]),
        "preconditions": _preconditions(target_file, target_anchor),
        "expected_result": str(patch_plan["interpretation"]),
        "assumptions": assumptions,
        "verification": {
            "commands": ["vib patch --preview", "vib guard --json"],
        },
        "actionable": status == "READY",
        "clarifying_questions": clarifying_questions,
        "user_status": user_status,
        "user_guidance": user_guidance,
    }


def _render_preview(target_path: Path, target_anchor: str) -> str:
    text = safe_read_text(target_path)
    if not text:
        return "[미리보기 불가] 파일 내용을 읽지 못했습니다."
    lines = text.splitlines()
    if target_anchor and target_anchor not in {"[없음]", "[먼저 앵커를 추가하세요]"}:
        anchor_line = next(
            (idx for idx, line in enumerate(lines) if target_anchor in line), None
        )
        if anchor_line is not None:
            start = max(0, anchor_line - 2)
            end = min(len(lines), anchor_line + 8)
            snippet = lines[start:end]
            return "\n".join(snippet)
    return "\n".join(lines[:10])


def _build_patch_data(root: Path, request: str) -> Dict[str, Any]:
    suggestion = suggest_patch(root, request)
    codespeak = build_codespeak(request, root=root)
    confidence = suggestion.confidence
    if confidence == "high" and codespeak.confidence != "high":
        confidence = codespeak.confidence
    return {
        "patch_plan": {
            "schema_version": 1,
            "request": request,
            "interpretation": codespeak.interpretation,
            "target_file": suggestion.target_file,
            "target_anchor": suggestion.target_anchor,
            "codespeak": codespeak.codespeak,
            "constraints": [
                "patch only",
                "keep file structure",
                "no unrelated edits",
            ],
            "confidence": confidence,
            "preview_available": True,
            "clarifying_questions": codespeak.clarifying_questions,
            "rationale": suggestion.rationale,
        },
    }


def _build_patch_data_with_options(
    root: Path, request: str, use_ai: bool, quiet_ai: bool
) -> Dict[str, Any]:
    suggestion = suggest_patch(root, request)
    codespeak = build_codespeak(request, root=root)
    if use_ai:
        ai_codespeak = importlib.import_module("vibelign.core.ai_codespeak")
        ai_explain = importlib.import_module("vibelign.core.ai_explain")
        if ai_explain.has_ai_provider():
            try:
                enhanced = ai_codespeak.enhance_codespeak_with_ai(
                    request, codespeak, quiet=quiet_ai
                )
            except Exception:
                enhanced = None
            if enhanced is not None:
                codespeak = enhanced
    confidence = suggestion.confidence
    if confidence == "high" and codespeak.confidence != "high":
        confidence = codespeak.confidence
    return {
        "patch_plan": {
            "schema_version": 1,
            "request": request,
            "interpretation": codespeak.interpretation,
            "target_file": suggestion.target_file,
            "target_anchor": suggestion.target_anchor,
            "codespeak": codespeak.codespeak,
            "constraints": [
                "patch only",
                "keep file structure",
                "no unrelated edits",
            ],
            "confidence": confidence,
            "preview_available": True,
            "clarifying_questions": codespeak.clarifying_questions,
            "rationale": suggestion.rationale,
        },
    }


def _render_markdown(data: Dict[str, Any], preview_text: Optional[str] = None) -> str:
    patch_plan = data["patch_plan"]
    contract = cast(Dict[str, Any], data.get("contract") or _build_contract(patch_plan))
    handoff = cast(Optional[Dict[str, Any]], data.get("handoff"))
    lines = [
        "# VibeLign 패치 계획",
        "",
        f"지금 상태: {contract['user_status']['title']}",
        "",
        contract["user_status"]["reason"],
        "",
    ]
    if contract["status"] == "NEEDS_CLARIFICATION":
        lines.append("## 먼저 이렇게 해보세요")
        lines.extend(f"- {item}" for item in contract["user_guidance"])
        lines.extend(["", "## 먼저 확인하면 좋은 질문"])
        lines.extend(f"- {item}" for item in contract["clarifying_questions"])
        lines.append("")
    else:
        lines.append("## 이제 이렇게 진행하면 돼요")
        lines.extend(f"- {item}" for item in contract["user_guidance"])
        lines.append("")

    lines.extend(
        [
            "## 수정 대상 요약",
            f"- CodeSpeak : {patch_plan['codespeak']}",
            f"- 파일      : {patch_plan['target_file']}",
            f"- 앵커      : {patch_plan['target_anchor']}",
            f"- 확신 정도 : {patch_plan['confidence']}",
            "",
            "## 이 계획에서 허용하는 범위",
        ]
    )
    for item in contract["scope"]["allowed_files"]:
        lines.append(f"- 허용된 파일: {item}")
    lines.extend(
        [
            f"- 파일 상태: {contract['scope']['target_file_status']}",
            f"- 안전 구역 상태: {contract['scope']['target_anchor_status']}",
            "",
            "## 이 계획이 바로 실행되려면",
        ]
    )
    lines.extend(f"- {item}" for item in contract["preconditions"])
    lines.extend(["", "## 허용된 수정 방식"])
    lines.extend(f"- {item}" for item in contract["allowed_ops"])
    lines.extend(["", "## 왜 이렇게 골랐는지"])
    lines.extend(f"- {item}" for item in patch_plan["rationale"])
    if contract["clarifying_questions"] and contract["status"] != "NEEDS_CLARIFICATION":
        lines.extend(["", "## 먼저 확인하면 좋은 질문"])
        lines.extend(f"- {item}" for item in contract["clarifying_questions"])
    if preview_text is not None:
        lines.extend(["", "## 미리 보기", "```text", preview_text, "```"])
    lines.extend(["", "## 검증할 때 쓸 명령"])
    lines.extend(f"- {item}" for item in contract["verification"]["commands"])
    lines.extend(
        [
            "",
            f"## 다음에 할 일",
            contract["user_status"]["next_step"],
        ]
    )
    if contract["status"] == "READY" and handoff is not None:
        lines.extend(
            [
                "",
                "## AI에게 그대로 전달할 블록",
                "```text",
                str(handoff["prompt"]),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def run_vib_patch(args: Any) -> None:
    root = Path.cwd()
    request = " ".join(args.request).strip()
    data = _build_patch_data_with_options(
        root, request, use_ai=args.ai, quiet_ai=args.json
    )
    patch_plan = data["patch_plan"]
    data["contract"] = _build_contract(patch_plan)
    if data["contract"]["status"] == "READY":
        data["handoff"] = _build_ready_handoff(data["contract"], patch_plan)
    preview_text = None
    target_path = root / patch_plan["target_file"]
    if args.preview and target_path.exists():
        preview_text = _render_preview(target_path, patch_plan["target_anchor"])
        data["preview"] = {
            "schema_version": 1,
            "format": "ascii",
            "target_file": patch_plan["target_file"],
            "target_anchor": patch_plan["target_anchor"],
            "before_summary": "현재 파일 일부 미리보기입니다.",
            "after_summary": "AI 편집 전에 이 구역을 검토하세요.",
            "confidence": patch_plan["confidence"],
            "before_text": preview_text,
        }

    envelope = {"ok": True, "error": None, "data": data}
    meta = MetaPaths(root)

    if args.json:
        text = json.dumps(envelope, indent=2, ensure_ascii=False)
        print(text)
        if args.write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("patch", "json").write_text(
                text + "\n", encoding="utf-8"
            )
        return

    markdown = _render_markdown(data, preview_text=preview_text)
    print_ai_response(markdown)
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("patch", "md").write_text(markdown, encoding="utf-8")

    # --copy: handoff 프롬프트를 클립보드에 복사
    if getattr(args, "copy", False):
        handoff = data.get("handoff")
        if handoff and handoff.get("prompt"):
            _copy_to_clipboard(str(handoff["prompt"]))
        else:
            from vibelign.terminal_render import clack_warn
            clack_warn("아직 AI에게 전달할 프롬프트가 없어요. 요청을 더 구체적으로 써주세요.")


# === ANCHOR: VIB_PATCH_CMD_END ===
