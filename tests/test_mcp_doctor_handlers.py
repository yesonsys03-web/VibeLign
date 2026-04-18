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


doctor_handlers = importlib.import_module("vibelign.mcp.mcp_doctor_handlers")
handle_doctor_plan = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    doctor_handlers.handle_doctor_plan,
)
handle_doctor_patch = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    doctor_handlers.handle_doctor_patch,
)
handle_doctor_apply = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[TextContent]],
    doctor_handlers.handle_doctor_apply,
)


class McpDoctorHandlersTest(unittest.TestCase):
    def test_handle_doctor_plan_returns_json_plan(self) -> None:
        class FakePlan:
            def to_dict(self) -> dict[str, object]:
                return {"steps": [{"action_type": "split_file"}]}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("vibelign.core.doctor_v2.analyze_project_v2") as analyze:
                with patch(
                    "vibelign.action_engine.action_planner.generate_plan",
                    return_value=FakePlan(),
                ):
                    analyze.return_value = object()
                    result = handle_doctor_plan(root, {"strict": False}, TextContent)

        payload = cast(dict[str, object], json.loads(result[0].text))
        steps = cast(list[dict[str, object]], payload["steps"])
        self.assertEqual(steps[0]["action_type"], "split_file")

    def test_handle_doctor_patch_returns_preview_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("vibelign.core.doctor_v2.analyze_project_v2") as analyze:
                with patch(
                    "vibelign.action_engine.action_planner.generate_plan",
                    return_value=object(),
                ):
                    with patch(
                        "vibelign.action_engine.generators.patch_generator.generate_patch_preview",
                        return_value="preview text",
                    ):
                        analyze.return_value = object()
                        result = handle_doctor_patch(
                            root, {"strict": False}, TextContent
                        )

        self.assertEqual(result[0].text, "preview text")

    def test_handle_doctor_apply_returns_execution_summary(self) -> None:
        class FakeAction:
            action_type: str = "add_anchor"

        class FakeResultItem:
            action: FakeAction = FakeAction()
            status: str = "done"
            detail: str = "ok"

        class FakeExecutionResult:
            aborted: bool = False
            checkpoint_id: str | None = "cp-1"
            done_count: int = 1
            manual_count: int = 0
            results: list[FakeResultItem] = [FakeResultItem()]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("vibelign.core.doctor_v2.analyze_project_v2") as analyze:
                with patch(
                    "vibelign.action_engine.action_planner.generate_plan",
                    return_value=object(),
                ):
                    with patch(
                        "vibelign.action_engine.executors.action_executor.execute_plan",
                        return_value=FakeExecutionResult(),
                    ):
                        analyze.return_value = object()
                        result = handle_doctor_apply(
                            root, {"strict": False}, TextContent
                        )

        payload = cast(dict[str, object], json.loads(result[0].text))
        results = cast(list[dict[str, object]], payload["results"])
        self.assertTrue(bool(payload["ok"]))
        self.assertEqual(payload["checkpoint_id"], "cp-1")
        self.assertEqual(results[0]["action_type"], "add_anchor")


if __name__ == "__main__":
    _ = unittest.main()
