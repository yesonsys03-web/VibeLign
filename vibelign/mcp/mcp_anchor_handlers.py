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
# === ANCHOR: MCP_ANCHOR_HANDLERS_END ===
