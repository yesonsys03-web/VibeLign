import importlib
import tempfile
import unittest
from unittest import mock
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from vibelign.core.memory.store import add_memory_decision, load_memory_state


@dataclass
class TextContent:
    type: str
    text: str


transfer_handlers = importlib.import_module("vibelign.mcp.mcp_transfer_handlers")
handle_handoff_create = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    transfer_handlers.handle_handoff_create,
)
handle_project_context_get = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    transfer_handlers.handle_project_context_get,
)


class McpTransferHandlersTest(unittest.TestCase):
    def test_handle_handoff_create_requires_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_handoff_create(root, {}, TextContent)

        self.assertEqual(len(result), 1)
        self.assertIn("session_summary와 first_next_action", result[0].text)

    def test_handle_handoff_create_writes_project_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_handoff_create(
                root,
                {
                    "session_summary": "fixed auth flow",
                    "first_next_action": "run guard check",
                },
                TextContent,
            )

            content = (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")

        self.assertEqual(len(result), 1)
        self.assertIn("Session Handoff 블록 생성 완료", result[0].text)
        self.assertIn("## Session Handoff", content)
        self.assertIn("fixed auth flow", content)

    def test_handle_handoff_create_persists_structured_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = handle_handoff_create(
                root,
                {
                    "session_summary": "fixed auth flow",
                    "first_next_action": "run guard check",
                    "verification": ["pytest transfer handlers passed"],
                },
                TextContent,
            )
            content = (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")
            state = load_memory_state(root / ".vibelign" / "work_memory.json")

        self.assertIn("pytest transfer handlers passed", content)
        self.assertEqual(
            [item.command for item in state.verification],
            ["pytest transfer handlers passed"],
        )
        self.assertIsNotNone(state.next_action)
        assert state.next_action is not None
        self.assertEqual(state.next_action.text, "run guard check")

    def test_handle_handoff_create_enriches_from_work_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            _ = (vg_dir / "work_memory.json").write_text(
                """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "vibelign/core/watch_engine.py",
      "message": "watch engine updated",
      "action": "Run MCP transfer regression tests."
    }
  ],
  "relevant_files": [
    {
      "path": "vibelign/core/watch_engine.py",
      "why": "Explicit pick from transfer_set_relevant.",
      "source": "explicit"
    }
  ],
  "warnings": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "warning",
      "path": "vibelign/core/watch_engine.py",
      "message": "Large file warning",
      "action": "Keep edits localized."
    }
  ],
  "decisions": [],
  "verification": ["uv run pytest tests/test_mcp_transfer_handlers.py"]
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            result = handle_handoff_create(
                root,
                {
                    "session_summary": "mcp supplied summary",
                    "first_next_action": "mcp supplied next action",
                },
                TextContent,
            )
            content = (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")

        self.assertEqual(len(result), 1)
        self.assertIn("mcp supplied summary", content)
        self.assertIn("mcp supplied next action", content)
        self.assertIn("Relevant files", content)
        # v2.0.37: "Live working changes" → "Working tree truth" + "Supporting watch context"
        self.assertIn("Working tree truth", content)
        self.assertNotIn("Recent factual changes", content)
        self.assertIn("Warnings / risks", content)
        self.assertIn("Verification snapshot", content)
        # work_memory recent_event 가 git status 에 없으므로 Supporting watch context 로 흘러야 함
        self.assertIn("Supporting watch context", content)
        self.assertIn("watch engine updated", content)

    def test_handle_handoff_create_preserves_mcp_priority_over_work_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            _ = (vg_dir / "work_memory.json").write_text(
                """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "vibelign/core/watch_engine.py",
      "message": "watch engine updated",
      "action": "work memory next action"
    }
  ],
  "relevant_files": [],
  "warnings": [],
  "decisions": [],
  "verification": []
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            _ = handle_handoff_create(
                root,
                {
                    "session_summary": "mcp summary wins",
                    "first_next_action": "mcp next action wins",
                },
                TextContent,
            )
            content = (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")

        self.assertIn("mcp summary wins", content)
        self.assertIn("mcp next action wins", content)
        self.assertNotIn("현재 세션에서 `vibelign/core/watch_engine.py`", content)
        self.assertNotIn("- 다음 할 일: work memory next action", content)

    def test_handle_handoff_create_warns_without_importing_stale_watch_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            _ = (vg_dir / "work_memory.json").write_text(
                """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "vibelign/core/watch_engine.py",
      "message": "stale watch event",
      "action": "Do not trust stale watch data."
    }
  ],
  "relevant_files": [],
  "warnings": [],
  "decisions": [],
  "verification": []
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with mock.patch(
                "vibelign.commands.vib_transfer_cmd._get_work_memory_staleness_warning",
                return_value="work_memory/watch data may be stale; trust git status first.",
            ):
                _ = handle_handoff_create(
                    root,
                    {
                        "session_summary": "mcp supplied summary",
                        "first_next_action": "mcp supplied next action",
                    },
                    TextContent,
                )
            content = (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")

        self.assertIn("work_memory/watch data may be stale", content)
        self.assertNotIn("stale watch event", content)

    def test_handle_handoff_create_keeps_verification_when_work_memory_is_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vg_dir = root / ".vibelign"
            vg_dir.mkdir()
            _ = (vg_dir / "work_memory.json").write_text(
                """
{
  "schema_version": 1,
  "updated_at": "2026-04-26T00:00:00Z",
  "recent_events": [
    {
      "time": "2026-04-26T00:00:00Z",
      "kind": "modified",
      "path": "vibelign/core/watch_engine.py",
      "message": "stale watch event"
    }
  ],
  "relevant_files": [],
  "warnings": [],
  "decisions": [],
  "verification": ["old verification from work memory"]
}
""".strip()
                + "\n",
                encoding="utf-8",
            )

            with mock.patch(
                "vibelign.commands.vib_transfer_cmd._get_work_memory_staleness_warning",
                return_value="work_memory/watch data may be stale; trust git status first.",
            ):
                _ = handle_handoff_create(
                    root,
                    {
                        "session_summary": "mcp supplied summary",
                        "first_next_action": "mcp supplied next action",
                        "verification": ["fresh mcp verification passed"],
                    },
                    TextContent,
                )
            content = (root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8")
            state = load_memory_state(root / ".vibelign" / "work_memory.json")

        self.assertIn("fresh mcp verification passed", content)
        self.assertIn("old verification from work memory", content)
        self.assertEqual(state.verification[-1].command, "fresh mcp verification passed")

    def test_handle_handoff_create_preserves_typed_memory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory_path = root / ".vibelign" / "work_memory.json"
            add_memory_decision(memory_path, "Keep typed MCP handoff decision")

            _ = handle_handoff_create(
                root,
                {
                    "session_summary": "mcp supplied summary",
                    "first_next_action": "mcp supplied next action",
                    "verification": ["mcp verification passed"],
                },
                TextContent,
            )
            state = load_memory_state(memory_path)

        self.assertEqual(
            [item.text for item in state.decisions],
            ["Keep typed MCP handoff decision"],
        )
        self.assertEqual(state.verification[-1].command, "mcp verification passed")
        self.assertIsNotNone(state.next_action)
        assert state.next_action is not None
        self.assertEqual(state.next_action.text, "mcp supplied next action")

    def test_handle_project_context_get_returns_existing_file_when_present(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "PROJECT_CONTEXT.md").write_text(
                "cached context", encoding="utf-8"
            )

            result = handle_project_context_get(root, {}, TextContent)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, "cached context")


if __name__ == "__main__":
    _ = unittest.main()
