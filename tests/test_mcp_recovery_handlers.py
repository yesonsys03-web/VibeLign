import json
import importlib
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, cast
from unittest import mock

from vibelign.core.recovery.models import RecoveryOption, RecoveryPlan, RecoverySignalSet


@dataclass
class TextContent:
    type: str
    text: str


recovery_handlers = importlib.import_module("vibelign.mcp.mcp_recovery_handlers")
handle_recovery_preview = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[object]],
    recovery_handlers.handle_recovery_preview,
)


class McpRecoveryHandlersTest(unittest.TestCase):
    def test_recovery_preview_returns_read_only_plan_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = RecoveryPlan(
                plan_id="rec_test",
                mode="read_only",
                level=1,
                summary="Preview only",
                options=[RecoveryOption(option_id="opt_test", level=1, label="Explain only")],
                no_files_modified=True,
            )
            with mock.patch(
                "vibelign.mcp.mcp_recovery_handlers.collect_basic_signals",
                return_value=RecoverySignalSet(changed_paths=["src/app.py"]),
            ) as collect_mock:
                with mock.patch(
                    "vibelign.mcp.mcp_recovery_handlers.build_recovery_plan",
                    return_value=plan,
                ) as plan_mock:
                    result = handle_recovery_preview(root, {}, TextContent)
            payload = json.loads(cast(TextContent, result[0]).text)

        collect_mock.assert_called_once_with(root)
        plan_mock.assert_called_once()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["provenance"], "recovery_planner_preview")
        self.assertEqual(payload["plan"]["mode"], "read_only")
        self.assertTrue(payload["plan"]["no_files_modified"])
        self.assertEqual(payload["plan"]["options"][0]["option_id"], "opt_test")

    def test_recovery_preview_writes_audit_without_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = RecoveryPlan(
                plan_id="rec_test",
                mode="read_only",
                level=0,
                summary="No changes",
            )
            with mock.patch(
                "vibelign.mcp.mcp_recovery_handlers.collect_basic_signals",
                return_value=RecoverySignalSet(),
            ):
                with mock.patch(
                    "vibelign.mcp.mcp_recovery_handlers.build_recovery_plan",
                    return_value=plan,
                ):
                    _ = handle_recovery_preview(root, {}, TextContent)
            audit_text = (root / ".vibelign" / "memory_audit.jsonl").read_text(encoding="utf-8")

        self.assertIn("recovery_preview", audit_text)
        self.assertFalse((root / ".vibelign" / "state.json").exists())


if __name__ == "__main__":
    _ = unittest.main()
