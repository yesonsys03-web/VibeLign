import importlib
import json
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


misc_handlers = importlib.import_module("vibelign.mcp.mcp_misc_handlers")
handle_anchor_list = cast(
    Callable[[Path, type[TextContent]], list[TextContent]],
    misc_handlers.handle_anchor_list,
)
handle_config_get = cast(
    Callable[[Path, type[TextContent]], list[TextContent]],
    misc_handlers.handle_config_get,
)


class McpMiscHandlersTest(unittest.TestCase):
    def test_handle_anchor_list_requires_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_anchor_list(root, TextContent)

        self.assertEqual(len(result), 1)
        self.assertIn("앵커 인덱스가 없습니다", result[0].text)

    def test_handle_anchor_list_returns_index_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(parents=True, exist_ok=True)
            _ = (meta_dir / "anchor_index.json").write_text(
                json.dumps({"anchors": []}, ensure_ascii=False), encoding="utf-8"
            )

            result = handle_anchor_list(root, TextContent)

        payload = cast(dict[str, object], json.loads(result[0].text))
        self.assertIn("anchors", payload)

    def test_handle_config_get_returns_missing_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_config_get(root, TextContent)

        self.assertEqual(len(result), 1)
        self.assertIn("설정 파일이 없습니다", result[0].text)


if __name__ == "__main__":
    _ = unittest.main()
