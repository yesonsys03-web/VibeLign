import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from typing import Any

from vibelign.commands.vib_patch_cmd import run_vib_patch
from vibelign.core.structure_policy import is_generated_artifact_path
from vibelign.core.codespeak import build_codespeak_result


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
            self.assertIn("intent_ir", contract)
            self.assertIn("layer", contract["codespeak_parts"])
            self.assertIn("title", contract["user_status"])
            self.assertIn("reason", contract["user_status"])
            self.assertIn("next_step", contract["user_status"])
            self.assertTrue(isinstance(contract["scope"]["allowed_files"], list))
            self.assertTrue(isinstance(contract["allowed_ops"], list))
            self.assertTrue(isinstance(contract["preconditions"], list))
            self.assertTrue(isinstance(contract["verification"]["commands"], list))
            self.assertIn("schema_version", payload["data"]["patch_plan"])
            self.assertIn("patch_points", payload["data"]["patch_plan"])
            steps = payload["data"]["patch_plan"]["steps"]
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0]["ordinal"], 0)
            self.assertEqual(steps[0]["intent_text"], "add login guard")
            self.assertEqual(
                steps[0]["target_file"], payload["data"]["patch_plan"]["target_file"]
            )
            self.assertEqual(
                steps[0]["target_anchor"],
                payload["data"]["patch_plan"]["target_anchor"],
            )
            self.assertIn("def render_login", steps[0]["context_snippet"])

    def test_generated_artifact_policy_identifies_shared_build_paths(self):
        self.assertTrue(
            is_generated_artifact_path("vibelign-gui/src-tauri/target/debug")
        )
        self.assertTrue(is_generated_artifact_path("dist/app.js"))
        self.assertFalse(is_generated_artifact_path("vibelign/vib_cli.py"))

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
            strict_patch = payload["data"]["strict_patch"]
            self.assertEqual(strict_patch["schema_version"], 1)
            self.assertFalse(strict_patch["apply_ready"])
            self.assertEqual(len(strict_patch["operations"]), 1)
            self.assertIn(
                "LOGIN_GUARD_LOGIN_GUARD_START",
                strict_patch["operations"][0]["search"],
            )
            self.assertEqual(
                strict_patch["operations"][0]["replace"],
                "[REPLACE_WITH_UPDATED_BLOCK_KEEPING_ANCHOR_MARKERS]",
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
            steps = payload["data"]["patch_plan"]["steps"]
            self.assertEqual(len(steps), 1)
            self.assertEqual(steps[0]["status"], contract["status"])
            self.assertEqual(steps[0]["allowed_ops"], contract["allowed_ops"])
            handoff = payload["data"].get("handoff")
            self.assertIsNotNone(handoff)
            prompt = handoff["prompt"]
            self.assertIn(
                "For move edits, keep changes scoped to source `vibelign-gui/src/pages/Home.tsx` / `HOME` and destination `vibelign-gui/src/App.tsx` / `CHECKPOINTS` only.",
                prompt,
            )
            self.assertNotIn(
                "Edit only `vibelign-gui/src/pages/Home.tsx` within anchor `HOME`.",
                prompt,
            )
            self.assertEqual(
                payload["data"]["patch_plan"]["intent_ir"]["operation"], "move"
            )
            self.assertEqual(
                payload["data"]["patch_plan"]["source_resolution"]["role"], "source"
            )
            self.assertEqual(
                payload["data"]["patch_plan"]["destination_resolution"]["role"],
                "destination",
            )
            self.assertEqual(contract["move_summary"]["operation"], "move")
            self.assertIn("intent_ir", contract)
            self.assertIn(
                "vibelign-gui/src/App.tsx", contract["scope"]["allowed_files"]
            )
            self.assertIn(
                "지금 바로 진행할 수 있어요", contract["user_status"]["title"]
            )
            strict_patch = payload["data"].get("strict_patch")
            self.assertIsNotNone(strict_patch)
            self.assertEqual(len(strict_patch["operations"]), 2)
            self.assertEqual(strict_patch["operations"][0]["ordinal"], 0)
            self.assertEqual(strict_patch["operations"][1]["ordinal"], 1)
            self.assertIn("HOME_START", strict_patch["operations"][0]["search"])
            self.assertIn("CHECKPOINTS_START", strict_patch["operations"][1]["search"])
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
            self.assertIn("Validator gate (must follow before editing):", prompt)
            self.assertIn(
                "SEARCH text must be copied from the real source exactly", prompt
            )
            self.assertIn("matches a unique location inside the allowed anchor", prompt)
            self.assertIn("CodeSpeak:", prompt)
            self.assertNotIn("Return the edit as strict patch JSON", prompt)

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

    def test_vib_patch_json_non_move_destination_mismatch_aligns_step_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_button.py").write_text(
                "# === ANCHOR: LOGIN_BUTTON_START ===\n"
                "def login_button():\n    return 'login'\n"
                "# === ANCHOR: LOGIN_BUTTON_END ===\n",
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
                        "steps": [
                            {
                                "ordinal": 0,
                                "intent_text": "로그인 버튼을 업데이트하고 settings로 옮겨줘",
                                "codespeak": "ui.login.button.update",
                                "target_file": "login_button.py",
                                "target_anchor": "LOGIN_BUTTON",
                                "allowed_ops": ["replace_range"],
                                "depends_on": None,
                                "status": "NEEDS_CLARIFICATION",
                                "search_fingerprint": "로그인 버튼을 업데이트하고 settings로 옮겨줘",
                            }
                        ],
                    },
                    "contract": {
                        "status": "NEEDS_CLARIFICATION",
                        "contract_version": "0.1",
                        "codespeak_contract_version": 0,
                        "codespeak_parts": {
                            "layer": "ui",
                            "target": "login",
                            "subject": "button",
                            "action": "update",
                        },
                        "patch_points": {"operation": "update"},
                        "scope": {
                            "allowed_files": ["login_button.py", "settings_button.py"],
                            "target_file_status": "ok",
                            "target_anchor_status": "ok",
                            "target_anchor_name": "LOGIN_BUTTON",
                            "destination_file_status": "ok",
                            "destination_anchor_status": "ok",
                            "destination_target_file": "settings_button.py",
                            "destination_target_anchor": "SETTINGS_BUTTON",
                        },
                        "allowed_ops": ["replace_range"],
                        "preconditions": [
                            "허용된 파일은 `login_button.py` 하나뿐이어야 합니다."
                        ],
                        "expected_result": "로그인 버튼을 업데이트하는 요청으로 이해했습니다.",
                        "assumptions": [
                            "요청 범위나 수정 위치가 아직 충분히 분명하지 않습니다."
                        ],
                        "verification": {
                            "commands": ["vib patch --preview", "vib guard --json"]
                        },
                        "actionable": False,
                        "clarifying_questions": [
                            "이 요청은 이동(move)으로 해석되지 않았는데 목적지 정보가 함께 잡혔어요. 수정인지 이동인지, 그리고 실제 목적지가 맞는지 한 번만 더 확인해줄 수 있나요?"
                        ],
                        "user_status": {
                            "title": "조금 더 알려주면 바로 도와줄 수 있어요",
                            "reason": "바꿀 위치나 범위가 아직 충분히 분명하지 않아서, 지금 바로 수정하면 엉뚱한 곳을 건드릴 수 있어요.",
                            "next_step": "먼저 질문에 답하거나 앵커를 추가한 뒤 다시 시도하세요.",
                        },
                        "user_guidance": ["지금은 바로 수정하지 마세요."],
                        "move_summary": {
                            "operation": "update",
                            "source": "",
                            "destination": "settings_button.py",
                        },
                        "intent_ir": None,
                    },
                },
            ):
                payload = self._run_patch_json(
                    root,
                    SimpleNamespace(
                        request=[
                            "로그인",
                            "버튼을",
                            "업데이트하고",
                            "settings로",
                            "옮겨줘",
                        ],
                        ai=False,
                        json=True,
                        preview=False,
                        write_report=False,
                    ),
                )

            contract = payload["data"]["contract"]
            step = payload["data"]["patch_plan"]["steps"][0]
            self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")
            self.assertEqual(step["status"], contract["status"])

    def test_vib_patch_json_move_with_weak_source_fingerprint_downgrades(self):
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
                "vibelign.patch.patch_builder.build_codespeak",
                return_value=weak_move_result,
            ):
                payload = self._run_patch_json(
                    root,
                    SimpleNamespace(
                        request=["이걸", "상단", "메뉴", "CHECKPOINTS로", "옮겨줘"],
                        ai=False,
                        json=True,
                        preview=False,
                        write_report=False,
                    ),
                )

            contract = payload["data"]["contract"]
            step = payload["data"]["patch_plan"]["steps"][0]
            self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")
            self.assertEqual(step["status"], contract["status"])
            self.assertIsNone(step["search_fingerprint"])
            self.assertTrue(
                any(
                    "validator" in item or "원본 블록" in item
                    for item in contract["clarifying_questions"]
                )
            )

    def test_vib_patch_json_multi_intent_request_needs_clarification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "login_button.py"
            target.write_text(
                "# === ANCHOR: LOGIN_BUTTON_START ===\n"
                "def login_button():\n    return 'login'\n"
                "# === ANCHOR: LOGIN_BUTTON_END ===\n",
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
                "vibelign.patch.patch_builder.build_codespeak",
                return_value=multi_intent_result,
            ):
                payload = self._run_patch_json(
                    root,
                    SimpleNamespace(
                        request=[
                            "로그인",
                            "버튼",
                            "색",
                            "바꿔줘",
                            "그리고",
                            "progress",
                            "bar",
                            "추가해줘",
                        ],
                        ai=False,
                        json=True,
                        preview=False,
                        write_report=False,
                    ),
                )

            contract = payload["data"]["contract"]
            step = payload["data"]["patch_plan"]["steps"][0]
            self.assertEqual(
                payload["data"]["patch_plan"]["sub_intents"],
                ["로그인 버튼 색 바꿔줘", "progress bar 추가해줘"],
            )
            self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")
            self.assertEqual(step["status"], contract["status"])
            self.assertEqual(step["intent_text"], "로그인 버튼 색 바꿔줘")
            self.assertTrue(
                any(
                    "한 번에 한 가지 변경" in item
                    for item in contract["clarifying_questions"]
                )
            )

    def test_vib_patch_json_multi_intent_fans_out_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_button.py").write_text(
                "# === ANCHOR: LOGIN_BUTTON_START ===\n"
                "def login_button():\n    return 'login'\n"
                "# === ANCHOR: LOGIN_BUTTON_END ===\n",
                encoding="utf-8",
            )
            (root / "progress_bar.py").write_text(
                "# === ANCHOR: PROGRESS_BAR_START ===\n"
                "def progress_bar():\n    return 'progress'\n"
                "# === ANCHOR: PROGRESS_BAR_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=[
                        "로그인",
                        "버튼",
                        "색",
                        "바꿔줘",
                        "그리고",
                        "progress",
                        "bar",
                        "추가해줘",
                    ],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            steps = payload["data"]["patch_plan"]["steps"]
            self.assertEqual(contract["status"], "NEEDS_CLARIFICATION")
            self.assertEqual(len(steps), 2)
            self.assertEqual(steps[0]["ordinal"], 0)
            self.assertIsNone(steps[0]["depends_on"])
            self.assertEqual(steps[0]["status"], contract["status"])
            self.assertEqual(steps[1]["ordinal"], 1)
            self.assertEqual(steps[1]["depends_on"], 0)
            self.assertEqual(steps[1]["status"], contract["status"])
            self.assertIn("def login_button", steps[0]["context_snippet"])
            self.assertIn("def progress_bar", steps[1]["context_snippet"])

    def test_vib_patch_json_lazy_fanout_sets_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "login_button.py").write_text(
                "# === ANCHOR: LOGIN_BUTTON_START ===\n"
                "def login_button():\n    return 'login'\n"
                "# === ANCHOR: LOGIN_BUTTON_END ===\n",
                encoding="utf-8",
            )
            (root / "progress_bar.py").write_text(
                "# === ANCHOR: PROGRESS_BAR_START ===\n"
                "def progress_bar():\n    return 'progress'\n"
                "# === ANCHOR: PROGRESS_BAR_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=[
                        "로그인",
                        "버튼",
                        "색",
                        "바꿔줘",
                        "그리고",
                        "progress",
                        "bar",
                        "추가해줘",
                    ],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                    lazy_fanout=True,
                ),
            )

            plan = payload["data"]["patch_plan"]
            pending = plan.get("pending_sub_intents")
            self.assertIsInstance(pending, list)
            self.assertEqual(pending, ["progress bar 추가해줘"])
            self.assertEqual(
                plan.get("sub_intents"),
                ["로그인 버튼 색 바꿔줘", "progress bar 추가해줘"],
            )
            self.assertTrue(
                any("lazy fan-out" in str(x) for x in plan["clarifying_questions"])
            )
            steps = plan["steps"]
            self.assertEqual(len(steps), 1)

    def test_vib_patch_json_state_persistence_request_downgrades_generic_app_target(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app = root / "vibelign-gui/src/App.tsx"
            app.parent.mkdir(parents=True, exist_ok=True)
            app.write_text(
                "// === ANCHOR: APP_START ===\n"
                "export default function App() {\n"
                "  return <div>menu tabs</div>;\n"
                "}\n"
                "// === ANCHOR: APP_END ===\n",
                encoding="utf-8",
            )
            home = root / "vibelign-gui/src/pages/Home.tsx"
            home.parent.mkdir(parents=True, exist_ok=True)
            home.write_text(
                "// === ANCHOR: HOME_START ===\n"
                "export function Home() {\n"
                "  return <div>Home</div>;\n"
                "}\n"
                "// === ANCHOR: HOME_END ===\n",
                encoding="utf-8",
            )
            hook_card = (
                root / "vibelign-gui/src/components/cards/security/ClaudeHookCard.tsx"
            )
            hook_card.parent.mkdir(parents=True, exist_ok=True)
            hook_card.write_text(
                "// === ANCHOR: CLAUDE_HOOK_CARD_START ===\n"
                "export function ClaudeHookCard() {\n"
                "  const enabled = true;\n"
                "  return <div>claude hook enable status</div>;\n"
                "}\n"
                "// === ANCHOR: CLAUDE_HOOK_CARD_END ===\n",
                encoding="utf-8",
            )

            payload = self._run_patch_json(
                root,
                SimpleNamespace(
                    request=[
                        "클로드",
                        "훅",
                        "enable",
                        "시키고",
                        "다른",
                        "메뉴",
                        "갔다",
                        "오면",
                        "enable",
                        "상태가",
                        "유지되지",
                        "않아",
                        "수정해줘",
                    ],
                    ai=False,
                    json=True,
                    preview=False,
                    write_report=False,
                ),
            )

            contract = payload["data"]["contract"]
            self.assertEqual(
                payload["data"]["patch_plan"]["target_file"],
                "vibelign-gui/src/components/cards/security/ClaudeHookCard.tsx",
            )
            self.assertEqual(
                payload["data"]["patch_plan"]["target_anchor"],
                "CLAUDE_HOOK_CARD",
            )
            self.assertEqual(contract["status"], "READY")
            self.assertEqual(contract["clarifying_questions"], [])
            self.assertIsNotNone(payload["data"].get("handoff"))


if __name__ == "__main__":
    unittest.main()
