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


def test_project_map_get_non_dict_root_rejected(tmp_path: Path) -> None:
    vib = tmp_path / ".vibelign"
    vib.mkdir()
    (vib / "project_map.json").write_text("[1, 2, 3]", encoding="utf-8")
    result = handle_project_map_get(tmp_path, {}, _factory)
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "shape" in payload["error"].lower() or "object" in payload["error"].lower()


def test_project_map_get_os_error_does_not_leak_path(tmp_path: Path) -> None:
    """When OSError occurs reading the map, the error message must not include
    the absolute filesystem path (only the error class name is acceptable)."""
    import os
    vib = tmp_path / ".vibelign"
    vib.mkdir()
    map_path = vib / "project_map.json"
    map_path.write_text("{}", encoding="utf-8")
    # Remove read permission to trigger PermissionError (subclass of OSError)
    try:
        os.chmod(map_path, 0)
        result = handle_project_map_get(tmp_path, {}, _factory)
    finally:
        os.chmod(map_path, 0o644)  # restore so tmp_path cleanup works
    payload = json.loads(result[0]["text"])
    # Either ok=True (if running as root and permission was ignored) — skip in that case
    if payload["ok"] is True:
        import pytest
        pytest.skip("running with elevated permissions, chmod did not restrict")
    assert payload["ok"] is False
    # The absolute path of tmp_path must NOT appear in the error string
    assert str(tmp_path) not in payload["error"]
    assert str(map_path) not in payload["error"]
