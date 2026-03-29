import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.mcp_server import call_tool
from vibelign.core.codespeak import build_codespeak_result


class McpPatchGetTest(unittest.TestCase):
    async def _call_patch_get_async(self, request: str) -> list[object]:
        return cast(list[object], await call_tool("patch_get", {"request": request}))

    def _call_patch_get(self, root: Path, request: str) -> dict[str, object]:
        previous = Path.cwd()
        try:
            os.chdir(root)
            response = asyncio.run(self._call_patch_get_async(request))
        finally:
            os.chdir(previous)
        self.assertEqual(len(response), 1)
        first = response[0]
        text = cast(str, getattr(first, "text"))
        return cast(dict[str, object], json.loads(text))

    def test_patch_get_uses_shared_builder_subset_for_simple_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "login_guard.py").write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                + "def login_guard():\n    return True\n"
                + "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            payload = self._call_patch_get(root, "fix login guard")

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["target_file"], "login_guard.py")
            self.assertEqual(payload["target_anchor"], "LOGIN_GUARD_LOGIN_GUARD")
            self.assertEqual(payload["status"], "READY")
            steps = cast(list[dict[str, object]], payload["steps"])
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0]["ordinal"], 0)
            self.assertEqual(steps[0]["target_file"], payload["target_file"])
            self.assertEqual(steps[0]["target_anchor"], payload["target_anchor"])
            self.assertIn("def login_guard", cast(str, steps[0]["context_snippet"]))
            strict_patch = cast(dict[str, object], payload["strict_patch"])
            self.assertEqual(strict_patch["schema_version"], 1)
            strict_operations = cast(
                list[dict[str, object]], strict_patch["operations"]
            )
            self.assertEqual(len(strict_operations), 1)
            self.assertIn(
                "LOGIN_GUARD_LOGIN_GUARD_START",
                cast(str, strict_operations[0]["search"]),
            )
            allowed_ops = cast(list[str], payload["allowed_ops"])
            self.assertIn("replace_range", allowed_ops)
            self.assertIsNone(payload["destination_target_file"])
            self.assertIsNone(payload["destination_target_anchor"])

    def test_patch_get_includes_move_destination_fields_from_shared_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "vibelign-gui/src/pages/Home.tsx"
            home.parent.mkdir(parents=True, exist_ok=True)
            _ = home.write_text(
                "// === ANCHOR: HOME_START ===\n"
                + "export function HomePage() {\n"
                + "  return <div>Home</div>;\n"
                + "}\n"
                + "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )
            app = root / "vibelign-gui/src/App.tsx"
            app.parent.mkdir(parents=True, exist_ok=True)
            _ = app.write_text(
                "// === ANCHOR: CHECKPOINTS_START ===\n"
                + "export function CheckpointsMenu() {\n"
                + "  return <nav>CHECKPOINTS</nav>;\n"
                + "}\n"
                + "// === ANCHOR: CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )

            payload = self._call_patch_get(
                root,
                "프로젝트 홈화면의 폴더열기 카드를 상단 메뉴 CHECKPOINTS로 이동해줘",
            )

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["target_file"], "vibelign-gui/src/pages/Home.tsx")
            self.assertEqual(
                payload["destination_target_file"], "vibelign-gui/src/App.tsx"
            )
            self.assertEqual(payload["destination_target_anchor"], "CHECKPOINTS")
            self.assertEqual(payload["status"], "READY")
            steps = cast(list[dict[str, object]], payload["steps"])
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0]["status"], payload["status"])
            move_summary = cast(dict[str, object], payload["move_summary"])
            self.assertIsInstance(move_summary, dict)
            self.assertEqual(move_summary["operation"], "move")

    def test_patch_get_returns_needs_clarification_for_missing_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "login_ui.py").write_text(
                "def render_login():\n    return True\n",
                encoding="utf-8",
            )

            payload = self._call_patch_get(root, "add login guard")

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["status"], "NEEDS_CLARIFICATION")
            clarifying_questions = cast(list[str], payload["clarifying_questions"])
            self.assertTrue(clarifying_questions)
            self.assertTrue(
                any("앵커" in item or "구역" in item for item in clarifying_questions)
            )

    def test_patch_get_empty_request_returns_json_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            payload = self._call_patch_get(root, "")

            self.assertEqual(payload["ok"], False)
            self.assertEqual(payload["error"], "request가 필요합니다.")
            self.assertIsNone(payload["data"])

    def test_patch_get_non_move_destination_mismatch_needs_clarification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "login_button.py").write_text(
                "# === ANCHOR: LOGIN_BUTTON_START ===\n"
                + "def login_button():\n    return 'login'\n"
                + "# === ANCHOR: LOGIN_BUTTON_END ===\n",
                encoding="utf-8",
            )
            _ = (root / "settings_button.py").write_text(
                "# === ANCHOR: SETTINGS_BUTTON_START ===\n"
                + "def settings_button():\n    return 'settings'\n"
                + "# === ANCHOR: SETTINGS_BUTTON_END ===\n",
                encoding="utf-8",
            )

            with patch(
                "vibelign.commands.vib_patch_cmd._build_patch_data",
                return_value={
                    "patch_plan": {
                        "schema_version": 1,
                        "request": "로그인 버튼을 업데이트하고 settings로 옮겨줘",
                        "interpretation": "로그인 버튼을 업데이트하는 요청으로 이해했습니다.",
                        "target_file": "login_button.py",
                        "target_anchor": "LOGIN_BUTTON",
                        "destination_target_file": "settings_button.py",
                        "destination_target_anchor": "SETTINGS_BUTTON",
                        "codespeak": "ui.login.button.update",
                        "confidence": "high",
                        "constraints": [],
                        "clarifying_questions": [],
                        "rationale": ["login 버튼 관련 파일입니다."],
                        "patch_points": {"operation": "update"},
                    },
                    "contract": {
                        "allowed_ops": ["replace_range"],
                        "status": "NEEDS_CLARIFICATION",
                        "clarifying_questions": [
                            "이 요청은 이동(move)으로 해석되지 않았는데 목적지 정보가 함께 잡혔어요. 수정인지 이동인지, 그리고 실제 목적지가 맞는지 한 번만 더 확인해줄 수 있나요?"
                        ],
                        "scope": {
                            "destination_target_file": "settings_button.py",
                            "destination_target_anchor": "SETTINGS_BUTTON",
                        },
                        "move_summary": {"operation": "update"},
                    },
                },
            ):
                payload = self._call_patch_get(
                    root, "로그인 버튼을 업데이트하고 settings로 옮겨줘"
                )

            self.assertEqual(payload["status"], "NEEDS_CLARIFICATION")
            clarifying_questions = cast(list[str], payload["clarifying_questions"])
            self.assertTrue(
                any(
                    "이동(move)" in item and "목적지" in item
                    for item in clarifying_questions
                )
            )

    def test_patch_get_move_with_weak_source_fingerprint_needs_clarification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "vibelign-gui/src/pages/Home.tsx"
            home.parent.mkdir(parents=True, exist_ok=True)
            _ = home.write_text(
                "// === ANCHOR: HOME_START ===\n"
                + "export function HomePage() {\n"
                + "  return <div>Home</div>;\n"
                + "}\n"
                + "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )
            app = root / "vibelign-gui/src/App.tsx"
            app.parent.mkdir(parents=True, exist_ok=True)
            _ = app.write_text(
                "// === ANCHOR: CHECKPOINTS_START ===\n"
                + "export function CheckpointsMenu() {\n"
                + "  return <nav>CHECKPOINTS</nav>;\n"
                + "}\n"
                + "// === ANCHOR: CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )

            weak_move_result = build_codespeak_result(
                "이걸 상단 메뉴 CHECKPOINTS로 옮겨줘",
                codespeak="ui.component.card.move",
                interpretation="카드를 상단 메뉴로 이동하는 요청으로 이해했습니다.",
                confidence="high",
                clarifying_questions=[],
            )
            if weak_move_result is None:
                self.fail("build_codespeak_result should build a move result")

            with patch(
                "vibelign.commands.vib_patch_cmd.build_codespeak",
                return_value=weak_move_result,
            ):
                payload = self._call_patch_get(
                    root, "이걸 상단 메뉴 CHECKPOINTS로 옮겨줘"
                )

            self.assertEqual(payload["status"], "NEEDS_CLARIFICATION")
            steps = cast(list[dict[str, object]], payload["steps"])
            self.assertEqual(steps[0]["status"], payload["status"])
            self.assertIsNone(steps[0]["search_fingerprint"])
            clarifying_questions = cast(list[str], payload["clarifying_questions"])
            self.assertTrue(
                any(
                    "validator" in item or "원본 블록" in item
                    for item in clarifying_questions
                )
            )

    def test_patch_get_multi_intent_request_needs_clarification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "login_button.py").write_text(
                "# === ANCHOR: LOGIN_BUTTON_START ===\n"
                + "def login_button():\n    return 'login'\n"
                + "# === ANCHOR: LOGIN_BUTTON_END ===\n",
                encoding="utf-8",
            )

            multi_intent_result = build_codespeak_result(
                "로그인 버튼 색 바꿔줘",
                codespeak="ui.component.login_button.update",
                interpretation="로그인 버튼 색을 바꾸는 요청으로 이해했습니다.",
                confidence="high",
                clarifying_questions=[],
                sub_intents=["로그인 버튼 색 바꿔줘", "progress bar 추가해줘"],
                target_file="login_button.py",
                target_anchor="LOGIN_BUTTON",
            )
            if multi_intent_result is None:
                self.fail("build_codespeak_result should return a multi-intent result")

            with patch(
                "vibelign.commands.vib_patch_cmd.build_codespeak",
                return_value=multi_intent_result,
            ):
                payload = self._call_patch_get(
                    root, "로그인 버튼 색 바꿔줘 그리고 progress bar 추가해줘"
                )

            self.assertEqual(payload["status"], "NEEDS_CLARIFICATION")
            self.assertEqual(
                payload["sub_intents"],
                ["로그인 버튼 색 바꿔줘", "progress bar 추가해줘"],
            )
            steps = cast(list[dict[str, object]], payload["steps"])
            self.assertEqual(steps[0]["status"], payload["status"])
            self.assertEqual(steps[0]["intent_text"], "로그인 버튼 색 바꿔줘")
            clarifying_questions = cast(list[str], payload["clarifying_questions"])
            self.assertTrue(
                any("한 번에 한 가지 변경" in item for item in clarifying_questions)
            )

    def test_patch_get_multi_intent_fans_out_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "login_button.py").write_text(
                "# === ANCHOR: LOGIN_BUTTON_START ===\n"
                + "def login_button():\n    return 'login'\n"
                + "# === ANCHOR: LOGIN_BUTTON_END ===\n",
                encoding="utf-8",
            )
            _ = (root / "progress_bar.py").write_text(
                "# === ANCHOR: PROGRESS_BAR_START ===\n"
                + "def progress_bar():\n    return 'progress'\n"
                + "# === ANCHOR: PROGRESS_BAR_END ===\n",
                encoding="utf-8",
            )

            payload = self._call_patch_get(
                root, "로그인 버튼 색 바꿔줘 그리고 progress bar 추가해줘"
            )

            self.assertEqual(payload["status"], "NEEDS_CLARIFICATION")
            steps = cast(list[dict[str, object]], payload["steps"])
            self.assertEqual(len(steps), 2)
            self.assertEqual(steps[0]["ordinal"], 0)
            self.assertIsNone(steps[0]["depends_on"])
            self.assertEqual(steps[1]["ordinal"], 1)
            self.assertEqual(steps[1]["depends_on"], 0)
            self.assertEqual(steps[1]["status"], payload["status"])
            self.assertIn("def login_button", cast(str, steps[0]["context_snippet"]))
            self.assertIn("def progress_bar", cast(str, steps[1]["context_snippet"]))


if __name__ == "__main__":
    _ = unittest.main()
