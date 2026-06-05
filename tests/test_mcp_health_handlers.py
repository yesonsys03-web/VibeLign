import importlib
import json
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from unittest.mock import patch


@dataclass
class TextContent:
    type: str
    text: str


health_handlers = importlib.import_module("vibelign.mcp.mcp_health_handlers")
handle_doctor_run = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    health_handlers.handle_doctor_run,
)
handle_guard_check = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    health_handlers.handle_guard_check,
)


class McpHealthHandlersTest(unittest.TestCase):
    def test_handle_doctor_run_returns_rendered_json_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("vibelign.core.doctor_v2.build_doctor_envelope") as build:
                with patch(
                    "vibelign.core.doctor_v2.render_doctor_json",
                    return_value='{"ok": true}',
                ):
                    build.return_value = {"ok": True}
                    result = handle_doctor_run(root, {"strict": False}, TextContent)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text, '{"ok": true}')

    def test_handle_guard_check_returns_rendered_guard_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "vibelign.commands.vib_guard_cmd._build_guard_envelope"
            ) as build:
                build.return_value = {"data": {"status": "warn"}}
                result = handle_guard_check(
                    root, {"strict": False, "since_minutes": 30}, TextContent
                )

        self.assertEqual(len(result), 1)
        payload = cast(dict[str, object], json.loads(result[0].text))
        self.assertEqual(payload, {"data": {"status": "warn"}})


if __name__ == "__main__":
    _ = unittest.main()
