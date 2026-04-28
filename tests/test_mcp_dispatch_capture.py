import asyncio
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch as mock_patch
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.work_memory import load_work_memory
from vibelign.mcp import mcp_dispatch
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


class DispatchAutoCaptureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        MetaPaths(self.root).ensure_vibelign_dirs()

    def tearDown(self):
        self.tmp.cleanup()

    def _wm(self):
        return load_work_memory(MetaPaths(self.root).work_memory_path)

    def test_guard_check_logs_verification(self):
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"guard_check": lambda r, a, t: [{"type": "text", "text": "guard: ok"}]}):
            _run(call_tool_dispatch("guard_check", {}, root=self.root, text_content=_tc))
        self.assertTrue(any("guard" in v for v in self._wm()["verification"]))

    def test_checkpoint_create_logs_recent_event_not_decision(self):
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"checkpoint_create": lambda r, a, t: [{"type": "text", "text": "saved"}]}):
            _run(call_tool_dispatch("checkpoint_create",
                {"message": "v2.0.35 작업 전 안전 저장"},
                root=self.root, text_content=_tc))
        wm = self._wm()
        self.assertEqual(wm["decisions"], [])  # 핵심: decisions 안 건드림
        self.assertTrue(
            any(e.get("kind") == "checkpoint" for e in wm["recent_events"]),
            f"checkpoint event missing: {wm['recent_events']}",
        )
        self.assertEqual(wm["relevant_files"], [])

    def test_patch_apply_with_strict_patch_logs_relevant_file_only(self):
        strict = {
            "target": {
                "file": "vibelign/core/work_memory.py",
                "anchor": "WORK_MEMORY_ADD_DECISION",
            },
            "operation": "replace",
        }
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"patch_apply": lambda r, a, t: [{"type": "text", "text": "applied"}]}):
            _run(call_tool_dispatch("patch_apply",
                {"strict_patch": strict},
                root=self.root, text_content=_tc))
        wm = self._wm()
        self.assertEqual(wm["decisions"], [])
        self.assertTrue(
            any(rf["path"] == "vibelign/core/work_memory.py"
                for rf in wm["relevant_files"]),
            f"relevant_files missing: {wm['relevant_files']}",
        )

    def test_patch_apply_dry_run_skipped(self):
        strict = {
            "target": {"file": "vibelign/core/work_memory.py"},
            "dry_run": True,
        }
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"patch_apply": lambda r, a, t: [{"type": "text", "text": "would apply"}]}):
            _run(call_tool_dispatch("patch_apply",
                {"strict_patch": strict},
                root=self.root, text_content=_tc))
        self.assertEqual(self._wm()["relevant_files"], [])

    def test_patch_apply_top_level_dry_run_skipped(self):
        strict = {
            "target": {"file": "vibelign/core/work_memory.py"},
        }
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"patch_apply": lambda r, a, t: [{"type": "text", "text": "would apply"}]}):
            _run(call_tool_dispatch("patch_apply",
                {"strict_patch": strict, "dry_run": True},
                root=self.root, text_content=_tc))
        self.assertEqual(self._wm()["relevant_files"], [])

    def test_other_tools_have_no_side_effect(self):
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"random_tool": lambda r, a, t: [{"type": "text", "text": "x"}]}):
            _run(call_tool_dispatch("random_tool", {},
                root=self.root, text_content=_tc))
        wm = self._wm()
        self.assertEqual(wm["decisions"], [])
        self.assertEqual(wm["verification"], [])
        self.assertEqual(wm["recent_events"], [])
        self.assertEqual(wm["relevant_files"], [])

    def test_capture_failure_does_not_break_tool_result(self):
        """work_memory write 실패해도 도구 결과는 정상 반환."""
        with mock_patch.dict(mcp_dispatch.DISPATCH_TABLE,
            {"guard_check": lambda r, a, t: [{"type": "text", "text": "g"}]}):
            with mock_patch("vibelign.mcp.mcp_dispatch.add_verification",
                side_effect=Exception("disk full")):
                result = _run(call_tool_dispatch("guard_check", {},
                    root=self.root, text_content=_tc))
        self.assertEqual(result[0]["text"], "g")
