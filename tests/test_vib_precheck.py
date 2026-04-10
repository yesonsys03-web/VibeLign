import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_precheck_cmd import run_vib_precheck


class VibPrecheckTest(unittest.TestCase):
    def _run_precheck(
        self, root: Path, payload: dict[str, object]
    ) -> tuple[int, str, str]:
        previous = Path.cwd()
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            os.chdir(root)
            with (
                patch("sys.stdin", io.StringIO(json.dumps(payload))),
                patch("sys.stdout", stdout),
                patch("sys.stderr", stderr),
            ):
                try:
                    run_vib_precheck(Namespace())
                except SystemExit as exc:
                    return int(exc.code or 0), stdout.getvalue(), stderr.getvalue()
            return 0, stdout.getvalue(), stderr.getvalue()
        finally:
            os.chdir(previous)

    def test_disabled_hook_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: false\n", encoding="utf-8"
            )
            code, _out, _err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "foo.py"),
                        "content": "print(1)\n",
                    },
                },
            )
            self.assertEqual(code, 0)

    def test_claude_hook_disabled_keeps_precheck_non_strict_for_production_write(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: false\n", encoding="utf-8"
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "oauth_provider.py"
                        ),
                        "content": "def oauth_provider():\n    return True\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertEqual(out, "")
            self.assertEqual(err, "")

    def test_non_write_payload_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, _err = self._run_precheck(
                root,
                {
                    "tool_name": "Read",
                    "tool_input": {
                        "file_path": str(root / "foo.py"),
                        "content": "print(1)\n",
                    },
                },
            )
            self.assertEqual(code, 0)

    def test_tests_python_file_skips_before_anchor_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "tests" / "test_example.py"),
                        "content": "def test_ok():\n    assert True\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_support_python_path_outside_production_scope_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "scripts" / "release.py"),
                        "content": "def main():\n    return 0\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_non_source_file_inside_production_prefix_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "vibelign" / "core" / "schema.json"),
                        "content": '{"ok": true}\n',
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_non_source_non_production_path_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, out, _err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "README.md"),
                        "content": "hello\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)

    def test_planning_required_blocks_new_production_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "oauth_provider.py"
                        ),
                        "content": "# === ANCHOR: OAUTH_PROVIDER_START ===\ndef x():\n    return True\n# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertIn("vib plan-structure를 먼저 실행하세요", err)

    def test_active_plan_outside_scope_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign" / "plans").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "plan_watch",
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "plans" / "plan_watch.json").write_text(
                json.dumps(
                    {
                        "id": "plan_watch",
                        "schema_version": 1,
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/watch_engine.py",
                                "anchor": "WATCH_ENGINE",
                                "allowed_change_types": ["edit"],
                                "max_lines_added": 20,
                            }
                        ],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                        "evidence": {},
                        "scope": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "vibelign" / "core" / "other.py"),
                        "content": "# === ANCHOR: OTHER_START ===\ndef x():\n    return True\n# === ANCHOR: OTHER_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertIn("활성 구조 계획 범위를 벗어났습니다", err)

    def test_anchor_missing_soft_blocks_even_when_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            src = root / "vibelign" / "core"
            src.mkdir(parents=True, exist_ok=True)
            target = src / "watch_engine.py"
            target.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(target),
                        "content": "def x():\n    return True\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertIn("앵커가 없습니다", err)

    def test_large_single_file_existing_edit_without_plan_is_not_auto_blocked(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nsmall_fix_line_threshold: 2\n", encoding="utf-8"
            )
            src = root / "vibelign" / "core"
            src.mkdir(parents=True, exist_ok=True)
            target = src / "watch_engine.py"
            target.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def x():\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(target),
                        "content": "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    import os\n    import sys\n    import json\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_override_true_skips_planning_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign" / "plans").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "plan_watch",
                            "feature": "watch 수정",
                            "override": True,
                            "override_reason": "manual",
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "oauth_provider.py"
                        ),
                        "content": "# === ANCHOR: OAUTH_PROVIDER_START ===\ndef x():\n    return True\n# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertEqual(err, "")

    def test_outside_project_absolute_path_allows_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            outside = (
                Path(tempfile.mkdtemp(prefix="vibelign-precheck-outside-", dir="/tmp"))
                / "outside.py"
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(outside),
                        "content": "# === ANCHOR: OUTSIDE_START ===\ndef x():\n    return True\n# === ANCHOR: OUTSIDE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_malformed_plan_dict_missing_required_fields_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign" / "plans").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "bad_plan",
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "plans" / "bad_plan.json").write_text(
                json.dumps(
                    {"id": "bad_plan", "schema_version": 1},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "watch_engine.py"
                        ),
                        "content": "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertEqual(
                err,
                "구조 계획 상태가 올바르지 않습니다. plan 파일과 state를 확인하세요\n",
            )
            self.assertEqual(_out, "")

    def test_missing_plan_file_blocks_with_state_error_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "missing_plan",
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "watch_engine.py"
                        ),
                        "content": "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertEqual(
                err,
                "구조 계획 상태가 올바르지 않습니다. plan 파일과 state를 확인하세요\n",
            )
            self.assertEqual(_out, "")

    def test_invalid_plan_state_blocks_with_state_error_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": None,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "watch_engine.py"
                        ),
                        "content": "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertEqual(
                err,
                "구조 계획 상태가 올바르지 않습니다. plan 파일과 state를 확인하세요\n",
            )
            self.assertEqual(_out, "")

    def test_key_complete_but_wrong_typed_plan_payload_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign" / "plans").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "bad_shape_plan",
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "plans" / "bad_shape_plan.json").write_text(
                json.dumps(
                    {
                        "id": "bad_shape_plan",
                        "schema_version": 1,
                        "allowed_modifications": {},
                        "required_new_files": {},
                        "forbidden": [],
                        "messages": {},
                        "evidence": {},
                        "scope": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "watch_engine.py"
                        ),
                        "content": "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertIn("구조 계획 상태가 올바르지 않습니다", err)

    def test_valid_plan_with_anchors_allows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign" / "plans").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "plan_watch",
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "plans" / "plan_watch.json").write_text(
                json.dumps(
                    {
                        "id": "plan_watch",
                        "schema_version": 1,
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/watch_engine.py",
                                "anchor": "WATCH_ENGINE",
                                "allowed_change_types": ["edit"],
                                "max_lines_added": 20,
                            }
                        ],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                        "evidence": {},
                        "scope": {},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\n", encoding="utf-8"
            )
            src = root / "vibelign" / "core"
            src.mkdir(parents=True, exist_ok=True)
            target = src / "watch_engine.py"
            target.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            code, out, _err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(target),
                        "content": "# === ANCHOR: WATCH_ENGINE_START ===\ndef x():\n    import os\n    return True\n# === ANCHOR: WATCH_ENGINE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)


if __name__ == "__main__":
    unittest.main()
