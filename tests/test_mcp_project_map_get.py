from __future__ import annotations

import json
from pathlib import Path

from vibelign.mcp.mcp_misc_handlers import handle_project_map_get


def _factory(*, type: str, text: str) -> dict[str, str]:
    return {"type": type, "text": text}


def test_project_map_get_returns_map(tmp_path: Path) -> None:
    vib = tmp_path / ".vibelign"
    vib.mkdir()
    (vib / "project_map.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "project_name": "demo",
                "tree": ["a.py"],
            }
        ),
        encoding="utf-8",
    )
    result = handle_project_map_get(tmp_path, {}, _factory)
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is True
    assert payload["data"]["project_name"] == "demo"
    assert "tree" in payload["data"]


def test_project_map_get_no_map(tmp_path: Path) -> None:
    result = handle_project_map_get(tmp_path, {}, _factory)
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "project_map" in payload["error"].lower()


def test_project_map_get_invalid_json(tmp_path: Path) -> None:
    vib = tmp_path / ".vibelign"
    vib.mkdir()
    (vib / "project_map.json").write_text("not valid json {{{", encoding="utf-8")
    result = handle_project_map_get(tmp_path, {}, _factory)
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "project_map" in payload["error"].lower() or "json" in payload["error"].lower()
