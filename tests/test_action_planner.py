import unittest

from vibelign.action_engine.action_planner import generate_plan


class ActionPlannerTest(unittest.TestCase):
    def test_generate_plan_prefers_recommended_command(self):
        report = {
            "project_score": 60,
            "issues": [
                {
                    "found": "앵커가 없어요",
                    "next_step": "앵커를 자동으로 추가한 뒤 다시 doctor를 실행해요",
                    "recommended_command": "vib doctor --fix",
                    "path": "foo.py",
                }
            ],
        }

        plan = generate_plan(report)

        self.assertEqual("vib doctor --fix", plan.actions[0].command)

    def test_generate_plan_treats_mcp_anchor_issue_as_add_anchor(self):
        report = {
            "project_score": 60,
            "issues": [
                {
                    "found": "vibelign/mcp/mcp_handler_registry.py에 안전 구역 표시(앵커)가 없어요",
                    "next_step": "mcp_handler_registry.py에 앵커를 추가하면 AI가 딱 그 부분만 안전하게 고칠 수 있어요",
                    "recommended_command": "vib doctor --fix",
                    "path": "vibelign/mcp/mcp_handler_registry.py",
                    "category": "anchor",
                }
            ],
        }

        plan = generate_plan(report)

        self.assertEqual("add_anchor", plan.actions[0].action_type)
        self.assertEqual("vib doctor --fix", plan.actions[0].command)

    def test_generate_plan_does_not_treat_mcp_path_structure_issue_as_fix_mcp(self):
        report = {
            "project_score": 60,
            "issues": [
                {
                    "found": "vibelign/mcp/mcp_handler_registry.py에 기능이 너무 많이 들어 있어요 (44개) — AI가 어디를 건드려야 할지 헷갈릴 수 있어요",
                    "next_step": "mcp_handler_registry.py을 기능별로 파일을 나눠보세요",
                    "path": "vibelign/mcp/mcp_handler_registry.py",
                    "category": "structure",
                }
            ],
        }

        plan = generate_plan(report)

        action_types = [a.action_type for a in plan.actions]
        self.assertIn("split_file", action_types)
        # split_file은 add_anchor에 의존하므로 add_anchor가 먼저 와야 함
        if "add_anchor" in action_types:
            self.assertLess(
                action_types.index("add_anchor"),
                action_types.index("split_file"),
            )

    def test_generate_plan_does_not_treat_generic_vib_start_hint_as_project_map(self):
        report = {
            "project_score": 60,
            "issues": [
                {
                    "found": "OpenCode 준비 파일이 일부 없어요",
                    "next_step": "`vib start --tools opencode` 를 다시 실행하면 OpenCode 준비 파일을 자동으로 채워줘요",
                    "recommended_command": "vib start --tools opencode",
                    "category": "metadata",
                }
            ],
        }

        plan = generate_plan(report)

        self.assertEqual("review", plan.actions[0].action_type)

    def test_generate_plan_does_not_treat_prepared_tool_issue_as_fix_mcp(self):
        report = {
            "project_score": 60,
            "issues": [
                {
                    "found": "OpenCode 준비 파일이 일부 없어요",
                    "next_step": "`vib start --tools opencode` 를 다시 실행하면 OpenCode 준비 파일을 자동으로 채워줘요",
                    "recommended_command": "vib start --tools opencode",
                    "category": "metadata",
                }
            ],
        }

        plan = generate_plan(report)

        self.assertEqual("review", plan.actions[0].action_type)

    def test_generate_plan_treats_project_map_issue_as_fix_project_map(self):
        report = {
            "project_score": 60,
            "issues": [
                {
                    "found": ".vibelign/project_map.json 파일을 읽을 수 없습니다",
                    "next_step": "vib start 를 다시 실행하면 자동으로 고쳐져요",
                    "path": ".vibelign/project_map.json",
                    "category": "metadata",
                    "check_type": "invalid_project_map",
                }
            ],
        }

        plan = generate_plan(report)

        self.assertEqual("fix_project_map", plan.actions[0].action_type)


if __name__ == "__main__":
    unittest.main()
