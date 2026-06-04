import io
import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock
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
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "vibelign" / "core" / "new.py"),
                        "content": "def x():\n    return True\n",
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
                "schema_version: 1\nclaude_hook_enabled: true\n", encoding="utf-8"
            )
            code, _out, _err = self._run_precheck(
                root,
                {
                    "tool_name": "Read",
                    "tool_input": {"file_path": str(root / "foo.py")},
                },
            )
            self.assertEqual(code, 0)

    def test_tests_python_file_skips_before_anchor_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: true\n", encoding="utf-8"
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "tests" / "test_new.py"),
                        "content": "def test_ok():\n    assert True\n",
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
                "schema_version: 1\nclaude_hook_enabled: true\n", encoding="utf-8"
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "vibelign" / "core" / "README.md"),
                        "content": "hello\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_planning_required_blocks_new_production_file_with_vib_plan_guidance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: true\nsmall_fix_line_threshold: 2\n",
                encoding="utf-8",
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "oauth_provider.py"
                        ),
                        "content": "# === ANCHOR: OAUTH_PROVIDER_START ===\n"
                        "def x():\n    return True\n"
                        "# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertIn("vib plan", err)
            self.assertNotIn("plan-structure", err)

    def test_small_new_production_file_without_plan_is_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: true\nsmall_fix_line_threshold: 10\n",
                encoding="utf-8",
            )
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(root / "vibelign" / "core" / "tiny_helper.py"),
                        "content": "# === ANCHOR: TINY_HELPER_START ===\n"
                        "def tiny_helper():\n    return True\n"
                        "# === ANCHOR: TINY_HELPER_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_stale_plan_json_does_not_allow_large_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign" / "plans").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "plan_oauth",
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".vibelign" / "plans" / "plan_oauth.json").write_text(
                '{"required_new_files": ["vibelign/core/oauth_provider.py"]}\n',
                encoding="utf-8",
            )
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: true\nsmall_fix_line_threshold: 2\n",
                encoding="utf-8",
            )
            code, _out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(
                            root / "vibelign" / "core" / "oauth_provider.py"
                        ),
                        "content": "# === ANCHOR: OAUTH_PROVIDER_START ===\n"
                        "def x():\n    import os\n    import sys\n    return True\n"
                        "# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 2)
            self.assertIn("vib plan", err)

    def test_anchor_missing_soft_blocks_even_when_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: true\nsmall_fix_line_threshold: 10\n",
                encoding="utf-8",
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
                "schema_version: 1\nclaude_hook_enabled: true\nsmall_fix_line_threshold: 2\n",
                encoding="utf-8",
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
                        "content": "# === ANCHOR: WATCH_ENGINE_START ===\n"
                        "def x():\n    import os\n    import sys\n    import json\n    return True\n"
                        "# === ANCHOR: WATCH_ENGINE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_outside_project_absolute_path_allows_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nclaude_hook_enabled: true\n", encoding="utf-8"
            )
            outside = Path(tempfile.mkdtemp(prefix="vibelign-precheck-outside-")) / "outside.py"
            code, out, err = self._run_precheck(
                root,
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(outside),
                        "content": "# === ANCHOR: OUTSIDE_START ===\n"
                        "def x():\n    return True\n"
                        "# === ANCHOR: OUTSIDE_END ===\n",
                    },
                },
            )
            self.assertEqual(code, 0)
            self.assertIn('"permissionDecision": "allow"', out)
            self.assertEqual(err, "")

    def test_direct_terminal_use_shows_stdin_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdin_mock = Mock()
            stdin_mock.isatty.return_value = True
            previous = Path.cwd()
            stdout = io.StringIO()
            stderr = io.StringIO()
            try:
                os.chdir(root)
                with (
                    patch("sys.stdin", stdin_mock),
                    patch("sys.stdout", stdout),
                    patch("sys.stderr", stderr),
                ):
                    with self.assertRaises(SystemExit) as exc:
                        run_vib_precheck(Namespace())
            finally:
                os.chdir(previous)
            self.assertEqual(int(exc.exception.code or 0), 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("stdin JSON payload", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
