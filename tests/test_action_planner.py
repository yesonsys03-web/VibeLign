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


if __name__ == "__main__":
    unittest.main()
