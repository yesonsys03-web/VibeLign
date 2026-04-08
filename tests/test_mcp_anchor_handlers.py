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


anchor_handlers = importlib.import_module("vibelign.mcp.mcp_anchor_handlers")
handle_anchor_run = cast(
    Callable[[Path, type[TextContent]], list[TextContent]],
    anchor_handlers.handle_anchor_run,
)


class McpAnchorHandlersTest(unittest.TestCase):
    def test_handle_anchor_run_creates_anchor_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text(
                "def main():\n    return True\n", encoding="utf-8"
            )

            result = handle_anchor_run(root, TextContent)
            index_path = root / ".vibelign" / "anchor_index.json"
            self.assertEqual(len(result), 1)
            self.assertTrue(index_path.exists())

    def test_handle_anchor_run_writes_valid_anchor_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "app.py").write_text(
                "def main():\n    return True\n", encoding="utf-8"
            )

            _ = handle_anchor_run(root, TextContent)
            payload = cast(
                dict[str, object],
                json.loads(
                    (root / ".vibelign" / "anchor_index.json").read_text(
                        encoding="utf-8"
                    )
                ),
            )

        self.assertEqual(payload["schema_version"], 1)
        self.assertIn("anchors", payload)
        self.assertIn("files", payload)


if __name__ == "__main__":
    _ = unittest.main()
