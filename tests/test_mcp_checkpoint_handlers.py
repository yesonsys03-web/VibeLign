import importlib
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from vibelign.core.local_checkpoints import list_checkpoints


@dataclass
class TextContent:
    type: str
    text: str


checkpoint_handlers = importlib.import_module("vibelign.mcp.mcp_checkpoint_handlers")
handle_checkpoint_create = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_create,
)
handle_checkpoint_list = cast(
    Callable[[Path, type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_list,
)
handle_checkpoint_restore = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    checkpoint_handlers.handle_checkpoint_restore,
)


class McpCheckpointHandlersTest(unittest.TestCase):
    def test_handle_checkpoint_create_creates_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print('ok')\n", encoding="utf-8")

            result = handle_checkpoint_create(root, {"message": "save"}, TextContent)

            self.assertEqual(len(result), 1)
            self.assertIn("체크포인트 저장 완료", result[0].text)
            self.assertEqual(len(list_checkpoints(root)), 1)

    def test_handle_checkpoint_list_returns_saved_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text("print('ok')\n", encoding="utf-8")
            _ = handle_checkpoint_create(root, {"message": "save"}, TextContent)

            result = handle_checkpoint_list(root, TextContent)

            self.assertEqual(len(result), 1)
            self.assertIn("# 체크포인트 목록", result[0].text)
            self.assertIn("save", result[0].text)

    def test_handle_checkpoint_restore_requires_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            result = handle_checkpoint_restore(root, {}, TextContent)

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].text, "오류: checkpoint_id가 필요합니다.")


if __name__ == "__main__":
    _ = unittest.main()
