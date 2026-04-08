import tempfile
import unittest
from pathlib import Path

from vibelign.action_engine.executors.action_executor import execute_plan
from vibelign.action_engine.models.action import Action
from vibelign.action_engine.models.plan import Plan


class ActionExecutorTest(unittest.TestCase):
    def test_execute_plan_applies_add_anchor_for_mcp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "vibelign" / "mcp" / "mcp_handler_registry.py"
            target.parent.mkdir(parents=True)
            target.write_text("def handler():\n    return 1\n", encoding="utf-8")

            plan = Plan(
                actions=[
                    Action(
                        action_type="add_anchor",
                        description="missing anchor in MCP file",
                        target_path="vibelign/mcp/mcp_handler_registry.py",
                        command="vib doctor --fix",
                        depends_on=[],
                    )
                ],
                source_score=0,
                generated_at="2026-04-08T00:00:00+00:00",
                warnings=[],
            )

            result = execute_plan(plan, root, force=True, quiet=True)

            self.assertEqual(1, result.done_count)
            self.assertEqual(0, result.manual_count)
            content = target.read_text(encoding="utf-8")
            self.assertIn("ANCHOR", content)


if __name__ == "__main__":
    unittest.main()
