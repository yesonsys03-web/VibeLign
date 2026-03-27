import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from typing import Any

from vibelign.commands.vib_patch_cmd import run_vib_patch


class VibPatchContractV0Test(unittest.TestCase):
    def _run_patch_json(self, root: Path, args: SimpleNamespace) -> dict[str, Any]:
        previous = Path.cwd()
        try:
            os.chdir(root)
            with patch("vibelign.commands.vib_patch_cmd.print") as mocked:
                run_vib_patch(args)
                output = mocked.call_args[0][0]
        finally:
            os.chdir(previous)
        return json.loads(output)

    def test_vib_patch_json_includes_contract_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_ui.py").write_text(
                "# === ANCHOR: LOGIN_UI_RENDER_LOGIN_START ===\n"
                "def render_login():\n    return True\n"
                "# === ANCHOR: LOGIN_UI_RENDER_LOGIN_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=["add", "login", "guard"],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            self.assertIn(contract["status"], {"READY", "NEEDS_CLARIFICATION"})
            self.assertEqual(contract["contract_version"], "0.1")
            self.assertEqual(contract["codespeak_contract_version"], 0)
            self.assertIn("layer", contract["codespeak_parts"])
            self.assertIn("title", contract["user_status"])
            self.assertIn("reason", contract["user_status"])
            self.assertIn("next_step", contract["user_status"])
            self.assertTrue(isinstance(contract["scope"]["allowed_files"], list))
            self.assertTrue(isinstance(contract["allowed_ops"], list))
            self.assertTrue(isinstance(contract["preconditions"], list))
            self.assertTrue(isinstance(contract["verification"]["commands"], list))

    def test_vib_patch_json_marks_missing_anchor_as_needs_clarification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_ui.py").write_text(
                "def render_login():\n    return True\n", encoding="utf-8"
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=["add", "login", "guard"],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")
            self.assertEqual(contract["scope"]["target_anchor_status"], "missing")
            self.assertFalse(contract["actionable"])
            self.assertIn("조금 더 알려주면", contract["user_status"]["title"])
            self.assertIn("지금은 바로 수정하지 마세요.", contract["user_guidance"])
            self.assertTrue(contract["clarifying_questions"])
            self.assertTrue(
                any(
                    "앵커" in item or "구역" in item
                    for item in contract["clarifying_questions"]
                )
            )

    def test_vib_patch_preview_json_includes_before_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_ui.py").write_text(
                "# === ANCHOR: LOGIN_UI_RENDER_LOGIN_START ===\n"
                "def render_login():\n    return True\n"
                "# === ANCHOR: LOGIN_UI_RENDER_LOGIN_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=["add", "login", "guard"],
                    ai=False,
                    json=True,
                    preview=True,
                    write_report=False,
                ),
            )

            preview = payload["data"]["preview"]
            self.assertIn("before_text", preview)
            self.assertIn("def render_login", preview["before_text"])

    def test_vib_patch_json_ready_status_has_run_now_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_guard.py").write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=["fix", "login", "guard"],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            self.assertEqual(contract["status"], "READY")
            self.assertIn(
                "지금은 바로 AI에게 전달해도 괜찮아요.", contract["user_guidance"]
            )

    def test_vib_patch_json_extracts_move_patch_points(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = root / "vibelign-gui/src/pages/Home.tsx"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export function HomePage() {\n"
                "  return <div>Home</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=[
                        "프로젝트",
                        "홈화면의",
                        "폴더열기",
                        "카드를",
                        "상단",
                        "메뉴",
                        "CHECKPOINTS로",
                        "이동해줘",
                    ],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            patch_points = contract["patch_points"]
            self.assertEqual(patch_points["operation"], "move")
            self.assertIn("홈화면", patch_points["source"])
            self.assertIn("폴더열기", patch_points["source"])
            self.assertIn("상단 메뉴 CHECKPOINTS", patch_points["destination"])
            self.assertIn("카드", patch_points["object"])

    def test_vib_patch_json_resolves_move_destination_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "vibelign-gui/src/pages/Home.tsx"
            home.parent.mkdir(parents=True, exist_ok=True)
            home.write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export function HomePage() {\n"
                "  return <div>Home</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )
            app = root / "vibelign-gui/src/App.tsx"
            app.parent.mkdir(parents=True, exist_ok=True)
            app.write_text(
                "// === ANCHOR: CHECKPOINTS_START ===\n"
                "export function CheckpointsMenu() {\n"
                "  return <nav>CHECKPOINTS</nav>;\n"
                "}\n"
                "// === ANCHOR: CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=[
                        "프로젝트",
                        "홈화면의",
                        "폴더열기",
                        "카드를",
                        "상단",
                        "메뉴",
                        "CHECKPOINTS로",
                        "이동해줘",
                    ],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            self.assertEqual(contract["status"], "READY")
            self.assertEqual(
                contract["scope"]["destination_target_file"], "vibelign-gui/src/App.tsx"
            )
            self.assertEqual(contract["scope"]["destination_anchor_status"], "ok")
            self.assertIn(
                "vibelign-gui/src/App.tsx", contract["scope"]["allowed_files"]
            )
            self.assertIn(
                "지금 바로 진행할 수 있어요", contract["user_status"]["title"]
            )
            handoff = payload["data"].get("handoff")
            if handoff is not None:
                prompt = handoff["prompt"]
                self.assertIn("File: vibelign-gui/src/pages/Home.tsx", prompt)
                self.assertIn("Destination file: vibelign-gui/src/App.tsx", prompt)
                self.assertNotIn(
                    "File: vibelign-gui/src/pages/Home.tsx, vibelign-gui/src/App.tsx",
                    prompt,
                )

    def test_vib_patch_move_source_ignores_backend_checkpoint_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "vibelign-gui/src/pages/Home.tsx"
            home.parent.mkdir(parents=True, exist_ok=True)
            home.write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export function HomePage() {\n"
                "  return <div>Home</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )
            app = root / "vibelign-gui/src/App.tsx"
            app.parent.mkdir(parents=True, exist_ok=True)
            app.write_text(
                "// === ANCHOR: CHECKPOINTS_START ===\n"
                "export function App() {\n"
                "  return <nav>CHECKPOINTS</nav>;\n"
                "}\n"
                "// === ANCHOR: CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )
            backend = root / "vibelign/core/local_checkpoints.py"
            backend.parent.mkdir(parents=True, exist_ok=True)
            backend.write_text(
                "# === ANCHOR: LOCAL_CHECKPOINTS_START ===\n"
                "def list_local_checkpoints():\n"
                "    return []\n"
                "# === ANCHOR: LOCAL_CHECKPOINTS_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=[
                        "프로젝트",
                        "홈화면의",
                        "폴더열기",
                        "카드를",
                        "상단",
                        "메뉴",
                        "CHECKPOINTS로",
                        "이동해줘",
                    ],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            self.assertEqual(contract["status"], "READY")
            self.assertEqual(
                payload["data"]["patch_plan"]["target_file"],
                "vibelign-gui/src/pages/Home.tsx",
            )
            self.assertEqual(
                payload["data"]["patch_plan"]["destination_target_file"],
                "vibelign-gui/src/App.tsx",
            )
            self.assertNotEqual(
                payload["data"]["patch_plan"]["target_file"],
                "vibelign/core/local_checkpoints.py",
            )

    def test_vib_patch_json_ready_status_includes_handoff_block(self):
        """Test that READY status includes AI handoff block with prompt."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_guard.py").write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=["fix", "login", "guard"],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            handoff = payload["data"].get("handoff")
            self.assertIsNotNone(handoff, "handoff should be present for READY status")
            self.assertTrue(handoff.get("ready"), "handoff.ready should be True")
            self.assertIn("prompt", handoff, "handoff should include prompt")
            self.assertIn("target_file", handoff, "handoff should include target_file")
            self.assertIn(
                "target_anchor", handoff, "handoff should include target_anchor"
            )
            self.assertIn(
                "allowed_files", handoff, "handoff should include allowed_files"
            )
            self.assertIn("allowed_ops", handoff, "handoff should include allowed_ops")
            # Verify prompt contains key elements
            prompt = handoff["prompt"]
            self.assertIn("VibeLign patch contract", prompt)
            self.assertIn("login_guard.py", prompt)
            self.assertIn("LOGIN_GUARD_LOGIN_GUARD", prompt)

    def test_vib_patch_needs_clarification_has_no_handoff(self):
        """Test that NEEDS_CLARIFICATION status does NOT include handoff block."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_ui.py").write_text(
                "def render_login():\n    return True\n", encoding="utf-8"
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=["add", "login", "guard"],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")
            handoff = payload["data"].get("handoff")
            self.assertIsNone(
                handoff, "handoff should NOT be present for NEEDS_CLARIFICATION"
            )


if __name__ == "__main__":
    unittest.main()
