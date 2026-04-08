import importlib
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from vibelign.core.protected_files import get_protected


@dataclass
class TextContent:
    type: str
    text: str


protect_handlers = importlib.import_module("vibelign.mcp.mcp_protect_handlers")
handle_protect_add = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    protect_handlers.handle_protect_add,
)


class McpProtectHandlersTest(unittest.TestCase):
    def test_handle_protect_add_requires_file_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_protect_add(root, {}, TextContent)

        self.assertEqual(len(result), 1)
        self.assertIn("file_paths가 필요합니다", result[0].text)

    def test_handle_protect_add_saves_new_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_protect_add(
                root,
                {"file_paths": ["src/app.py", "src/lib.py"]},
                TextContent,
            )

            protected = get_protected(root)

        self.assertEqual(len(result), 1)
        self.assertIn("2개 파일", result[0].text)
        self.assertIn("src/app.py", protected)
        self.assertIn("src/lib.py", protected)


if __name__ == "__main__":
    _ = unittest.main()
