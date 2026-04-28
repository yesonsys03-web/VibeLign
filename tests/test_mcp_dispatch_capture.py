import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import load_work_memory
from vibelign.mcp.mcp_dispatch import call_tool_dispatch


def _tc(**kw: Any) -> Any:
    return {"type": kw.get("type"), "text": kw.get("text")}


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TransferMCPToolsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        MetaPaths(self.root).ensure_vibelign_dirs()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _wm(self):
        return load_work_memory(MetaPaths(self.root).work_memory_path)

    def test_set_decision_appends_to_decisions(self):
        _run(call_tool_dispatch("transfer_set_decision",
            {"text": "1-B 옵션 채택"}, root=self.root, text_content=_tc))
        self.assertEqual(self._wm()["decisions"][-1], "1-B 옵션 채택")

    def test_set_verification_appends_to_verification(self):
        _run(call_tool_dispatch("transfer_set_verification",
            {"text": "pytest -> 12 passed"}, root=self.root, text_content=_tc))
        self.assertIn("12 passed", self._wm()["verification"][-1])

    def test_set_relevant_appends_to_relevant_files(self):
        _run(call_tool_dispatch("transfer_set_relevant",
            {"path": "vibelign/core/work_memory.py", "why": "core"},
            root=self.root, text_content=_tc))
        self.assertEqual(
            self._wm()["relevant_files"][-1],
            {"path": "vibelign/core/work_memory.py", "why": "core"})

    def test_set_decision_requires_text(self):
        result = _run(call_tool_dispatch("transfer_set_decision",
            {}, root=self.root, text_content=_tc))
        self.assertIn("text 인자가 필요", result[0]["text"])
