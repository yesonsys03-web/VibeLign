import importlib
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast


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
      "why": "Recently modified by watch integration work."
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
        self.assertIn("Live working changes", content)
        self.assertNotIn("Recent factual changes", content)
        self.assertIn("Warnings / risks", content)
        self.assertIn("Verification snapshot", content)
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
