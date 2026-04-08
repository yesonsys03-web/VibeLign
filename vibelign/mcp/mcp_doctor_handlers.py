# === ANCHOR: MCP_DOCTOR_HANDLERS_START ===
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


# === ANCHOR: MCP_DOCTOR_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_DOCTOR_HANDLERS___CALL___START ===
# === ANCHOR: MCP_DOCTOR_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_DOCTOR_HANDLERS___CALL___END ===


# === ANCHOR: MCP_DOCTOR_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_DOCTOR_HANDLERS__TEXT_END ===


# === ANCHOR: MCP_DOCTOR_HANDLERS_HANDLE_DOCTOR_PLAN_START ===
def handle_doctor_plan(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_DOCTOR_HANDLERS_HANDLE_DOCTOR_PLAN_END ===
) -> list[object]:
    from vibelign.action_engine.action_planner import generate_plan
    from vibelign.core.doctor_v2 import analyze_project_v2

    strict = bool(arguments.get("strict", False))
    report = analyze_project_v2(root, strict=strict)
    plan = generate_plan(report)
    return _text(text_content, json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))


# === ANCHOR: MCP_DOCTOR_HANDLERS_HANDLE_DOCTOR_PATCH_START ===
def handle_doctor_patch(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_DOCTOR_HANDLERS_HANDLE_DOCTOR_PATCH_END ===
) -> list[object]:
    from vibelign.action_engine.action_planner import generate_plan
    from vibelign.action_engine.generators.patch_generator import generate_patch_preview
    from vibelign.core.doctor_v2 import analyze_project_v2

    strict = bool(arguments.get("strict", False))
    report = analyze_project_v2(root, strict=strict)
    plan = generate_plan(report)
    preview = generate_patch_preview(plan, root)
    return _text(text_content, preview)


# === ANCHOR: MCP_DOCTOR_HANDLERS_HANDLE_DOCTOR_APPLY_START ===
def handle_doctor_apply(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
# === ANCHOR: MCP_DOCTOR_HANDLERS_HANDLE_DOCTOR_APPLY_END ===
) -> list[object]:
    from vibelign.action_engine.action_planner import generate_plan
    from vibelign.action_engine.executors.action_executor import execute_plan
    from vibelign.core.doctor_v2 import analyze_project_v2

    strict = bool(arguments.get("strict", False))
    report = analyze_project_v2(root, strict=strict)
    plan = generate_plan(report)
    execution_result = execute_plan(plan, root, force=True, quiet=True)
    output = {
        "ok": not execution_result.aborted,
        "checkpoint_id": execution_result.checkpoint_id,
        "done": execution_result.done_count,
        "manual": execution_result.manual_count,
        "results": [
            {
                "action_type": item.action.action_type,
                "status": item.status,
                "detail": item.detail,
            }
            for item in execution_result.results
        ],
    }
    return _text(text_content, json.dumps(output, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_DOCTOR_HANDLERS_END ===
