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

    def test_handle_guard_check_clears_verification_gate_on_non_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(parents=True, exist_ok=True)
            state_path = meta_dir / "state.json"
            _ = state_path.write_text(
                json.dumps(
                    {
                        "patch_session": {
                            "session_id": "seed",
                            "needs_verification": True,
                            "active": True,
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            with patch(
                "vibelign.commands.vib_guard_cmd._build_guard_envelope"
            ) as build:
                build.return_value = {"data": {"status": "warn"}}
                result = handle_guard_check(
                    root, {"strict": False, "since_minutes": 30}, TextContent
                )

            state = cast(
                dict[str, object], json.loads(state_path.read_text(encoding="utf-8"))
            )

        patch_session = cast(dict[str, object], state["patch_session"])
        self.assertEqual(len(result), 1)
        self.assertFalse(bool(patch_session["needs_verification"]))
        self.assertEqual(patch_session["guard_status"], "warn")


if __name__ == "__main__":
    _ = unittest.main()
