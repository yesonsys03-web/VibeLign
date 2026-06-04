"""End-to-end dispatch wiring tests for anchor_read_content and project_map_get.

These tests verify that the DISPATCH_TABLE keys are spelled correctly and that
the full call_tool_dispatch path reaches the real handlers (not mocked).
Handler correctness is covered in test_mcp_anchor_read_content.py and
test_mcp_project_map_get.py; this file only checks the routing wiring.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

from vibelign.core.meta_paths import MetaPaths
from vibelign.mcp.mcp_dispatch import call_tool_dispatch


def _tc(**kw: Any) -> Any:
    return {"type": kw.get("type"), "text": kw.get("text")}


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestDispatchAnchorReadContent:
    """call_tool_dispatch("anchor_read_content", ...) reaches the real handler."""

    def setup_method(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        MetaPaths(self.root).ensure_vibelign_dirs()
        # Write a minimal anchored file so the handler can return ok=True
        (self.root / "sample.py").write_text(
            "# === ANCHOR: FOO_START ===\n"
            "def foo() -> int:\n"
            "    return 42\n"
            "# === ANCHOR: FOO_END ===\n",
            encoding="utf-8",
        )

    def teardown_method(self):
        self._tmp.cleanup()

    def test_dispatch_returns_ok_envelope(self):
        """Dispatching anchor_read_content with valid args returns ok=True envelope."""
        result = _run(call_tool_dispatch(
            "anchor_read_content",
            {"file": "sample.py", "anchor_name": "FOO"},
            root=self.root,
            text_content=_tc,
        ))
        assert len(result) == 1
        payload = json.loads(result[0]["text"])
        assert "ok" in payload, f"envelope missing 'ok' key: {payload}"
        assert payload["ok"] is True

    def test_dispatch_unknown_key_returns_error_text(self):
        """A misspelled key in DISPATCH_TABLE would return the 'unknown tool' message
        instead of a JSON envelope — this serves as the negative proof."""
        result = _run(call_tool_dispatch(
            "anchor_read_content_TYPO",
            {"file": "sample.py", "anchor_name": "FOO"},
            root=self.root,
            text_content=_tc,
        ))
        # The dispatcher returns plain text (not JSON) for unknown tools
        text = result[0]["text"]
        assert "알 수 없는 도구" in text

    def test_removed_patch_tools_return_unknown_text(self):
        for tool_name in ["patch_get", "patch_apply", "doctor_patch"]:
            result = _run(call_tool_dispatch(
                tool_name,
                {"request": "fix login"},
                root=self.root,
                text_content=_tc,
            ))
            text = result[0]["text"]
            assert "알 수 없는 도구" in text


class TestDispatchProjectMapGet:
    """call_tool_dispatch("project_map_get", ...) reaches the real handler."""

    def setup_method(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        MetaPaths(self.root).ensure_vibelign_dirs()
        # Write a minimal project_map.json so the handler can return ok=True
        vib = self.root / ".vibelign"
        vib.mkdir(exist_ok=True)
        (vib / "project_map.json").write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "project_name": "test-project",
                    "tree": ["sample.py"],
                }
            ),
            encoding="utf-8",
        )

    def teardown_method(self):
        self._tmp.cleanup()

    def test_dispatch_returns_ok_envelope(self):
        """Dispatching project_map_get with a valid map returns ok=True envelope."""
        result = _run(call_tool_dispatch(
            "project_map_get",
            {},
            root=self.root,
            text_content=_tc,
        ))
        assert len(result) == 1
        payload = json.loads(result[0]["text"])
        assert "ok" in payload, f"envelope missing 'ok' key: {payload}"
        assert payload["ok"] is True

    def test_dispatch_unknown_key_returns_error_text(self):
        """A misspelled DISPATCH_TABLE key produces the 'unknown tool' sentinel."""
        result = _run(call_tool_dispatch(
            "project_map_get_TYPO",
            {},
            root=self.root,
            text_content=_tc,
        ))
        text = result[0]["text"]
        assert "알 수 없는 도구" in text
