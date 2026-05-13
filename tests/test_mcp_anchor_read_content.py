from __future__ import annotations

import json
from pathlib import Path

from vibelign.mcp.mcp_anchor_handlers import handle_anchor_read_content


def _factory(*, type: str, text: str) -> dict[str, str]:
    return {"type": type, "text": text}


def _write_sample(root: Path) -> None:
    (root / "sample.py").write_text(
        "# === ANCHOR: FOO_START ===\n"
        "def foo() -> int:\n"
        "    return 42\n"
        "# === ANCHOR: FOO_END ===\n"
        "\n"
        "# === ANCHOR: BAR_START ===\n"
        "def bar() -> str:\n"
        "    return \"hi\"\n"
        "# === ANCHOR: BAR_END ===\n",
        encoding="utf-8",
    )


def test_read_content_returns_anchor_body(tmp_path: Path) -> None:
    _write_sample(tmp_path)
    result = handle_anchor_read_content(
        tmp_path,
        {"file": "sample.py", "anchor_name": "FOO"},
        _factory,
    )
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is True
    body = payload["data"]["content"]
    assert "def foo()" in body
    assert "def bar()" not in body
    assert payload["data"]["anchor_name"] == "FOO"


def test_read_content_unknown_anchor(tmp_path: Path) -> None:
    _write_sample(tmp_path)
    result = handle_anchor_read_content(
        tmp_path,
        {"file": "sample.py", "anchor_name": "DOES_NOT_EXIST"},
        _factory,
    )
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "DOES_NOT_EXIST" in payload["error"]


def test_read_content_missing_file(tmp_path: Path) -> None:
    result = handle_anchor_read_content(
        tmp_path,
        {"file": "nope.py", "anchor_name": "X"},
        _factory,
    )
    payload = json.loads(result[0]["text"])
    assert payload["ok"] is False
    assert "nope.py" in payload["error"]


def test_read_content_requires_args(tmp_path: Path) -> None:
    r1 = handle_anchor_read_content(tmp_path, {"anchor_name": "X"}, _factory)
    assert json.loads(r1[0]["text"])["ok"] is False
    r2 = handle_anchor_read_content(tmp_path, {"file": "x.py"}, _factory)
    assert json.loads(r2[0]["text"])["ok"] is False
