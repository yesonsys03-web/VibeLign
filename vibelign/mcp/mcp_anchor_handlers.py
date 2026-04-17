# === ANCHOR: MCP_ANCHOR_HANDLERS_START ===
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, cast

from vibelign.core.meta_paths import MetaPaths


# === ANCHOR: MCP_ANCHOR_HANDLERS_TEXTCONTENTFACTORY_START ===
class TextContentFactory(Protocol):
    # === ANCHOR: MCP_ANCHOR_HANDLERS___CALL___START ===
# === ANCHOR: MCP_ANCHOR_HANDLERS_TEXTCONTENTFACTORY_END ===
    def __call__(self, *, type: str, text: str) -> object: ...
    # === ANCHOR: MCP_ANCHOR_HANDLERS___CALL___END ===


# === ANCHOR: MCP_ANCHOR_HANDLERS__TEXT_START ===
def _text(factory: TextContentFactory, text: str) -> list[object]:
    return [factory(type="text", text=text)]
# === ANCHOR: MCP_ANCHOR_HANDLERS__TEXT_END ===


# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_RUN_START ===
def handle_anchor_run(root: Path, text_content: TextContentFactory) -> list[object]:
    from vibelign.core.anchor_tools import (
        collect_anchor_index,
        collect_anchor_metadata,
        insert_module_anchors,
        recommend_anchor_targets,
    )
    from vibelign.core.project_map import load_project_map

    meta = MetaPaths(root)
    meta.ensure_vibelign_dirs()
    project_map, _ = load_project_map(root)
    recommendations = recommend_anchor_targets(
        root, allowed_exts=None, project_map=project_map
    )
    targets = [root / str(item["path"]) for item in recommendations]
    changed: list[str] = []
    for path in targets:
        if insert_module_anchors(path):
            changed.append(str(path.relative_to(root)))
    index = collect_anchor_index(root, allowed_exts=None)
    metadata = collect_anchor_metadata(root, allowed_exts=None)
    payload = {"schema_version": 1, "anchors": index, "files": metadata}
    _ = meta.anchor_index_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if meta.state_path.exists():
        state = cast(object, json.loads(meta.state_path.read_text(encoding="utf-8")))
        if isinstance(state, dict):
            state["last_anchor_run_at"] = datetime.now(timezone.utc).isoformat()
            _ = meta.state_path.write_text(
                json.dumps(state, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    if changed:
        text = f"✓ 앵커 삽입 완료 — {len(changed)}개 파일\n" + "\n".join(
            f"  - {item}" for item in changed
        )
    else:
        text = "모든 파일에 이미 앵커가 있습니다."
    return _text(text_content, text)
# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_RUN_END ===


def _parse_allowed_exts(raw: object) -> set[str] | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    exts: set[str] = set()
    for token in raw.split(","):
        t = token.strip().lower()
        if not t:
            continue
        exts.add(t if t.startswith(".") else f".{t}")
    return exts or None


def _str_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    out: list[str] = [item for item in value if isinstance(item, str) and item]
    return out if out else None


# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_AUTO_INTENT_START ===
def handle_anchor_auto_intent(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.ai_explain import has_ai_provider
    from vibelign.core.anchor_tools import (
        extract_anchors,
        generate_anchor_intents_with_ai,
        generate_code_based_intents,
    )
    from vibelign.core.project_scan import iter_source_files

    force = bool(arguments.get("force", False))
    allowed_exts = _parse_allowed_exts(arguments.get("only_ext"))
    anchored: list[Path] = [
        path
        for path in iter_source_files(root)
        if (allowed_exts is None or path.suffix.lower() in allowed_exts)
        and extract_anchors(path)
    ]
    code_count = generate_code_based_intents(root, anchored) if anchored else 0
    ai_available = has_ai_provider()
    ai_count = 0
    if ai_available and anchored:
        ai_count = generate_anchor_intents_with_ai(root, anchored, force=force)

    meta = MetaPaths(root)
    payload = {
        "ok": True,
        "error": None,
        "data": {
            "code_count": code_count,
            "ai_count": ai_count,
            "total_anchors": len(anchored),
            "ai_available": ai_available,
            "forced": force,
            "anchor_meta_path": str(meta.anchor_meta_path.relative_to(root)),
        },
    }
    return _text(text_content, json.dumps(payload, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_AUTO_INTENT_END ===


# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_SET_INTENT_START ===
def handle_anchor_set_intent(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.anchor_tools import get_anchor_intent, set_anchor_intent

    name = arguments.get("anchor_name")
    intent = arguments.get("intent")
    if not isinstance(name, str) or not name.strip():
        err = {"ok": False, "error": "anchor_name is required", "data": None}
        return _text(text_content, json.dumps(err, ensure_ascii=False))
    if not isinstance(intent, str) or not intent.strip():
        err = {"ok": False, "error": "intent is required", "data": None}
        return _text(text_content, json.dumps(err, ensure_ascii=False))
    connects = _str_list(arguments.get("connects"))
    aliases = _str_list(arguments.get("aliases"))
    warning_raw = arguments.get("warning")
    warning = warning_raw if isinstance(warning_raw, str) else None
    description_raw = arguments.get("description")
    description = description_raw if isinstance(description_raw, str) else None
    set_anchor_intent(
        root,
        name,
        intent,
        connects=connects,
        warning=warning,
        aliases=aliases,
        description=description,
    )
    entry = get_anchor_intent(root, name)
    payload = {
        "ok": True,
        "error": None,
        "data": {"anchor_name": name, "entry": entry},
    }
    return _text(text_content, json.dumps(payload, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_SET_INTENT_END ===


# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_GET_META_START ===
def handle_anchor_get_meta(
    root: Path,
    arguments: dict[str, object],
    text_content: TextContentFactory,
) -> list[object]:
    from vibelign.core.anchor_tools import load_anchor_meta

    data = load_anchor_meta(root)
    name = arguments.get("anchor_name")
    if isinstance(name, str) and name.strip():
        entry = data.get(name, {})
        payload = {
            "ok": True,
            "error": None,
            "data": {"anchor_name": name, "entry": entry},
        }
    else:
        payload = {"ok": True, "error": None, "data": {"meta": data}}
    return _text(text_content, json.dumps(payload, indent=2, ensure_ascii=False))
# === ANCHOR: MCP_ANCHOR_HANDLERS_HANDLE_ANCHOR_GET_META_END ===
# === ANCHOR: MCP_ANCHOR_HANDLERS_END ===
