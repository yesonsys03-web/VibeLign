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
