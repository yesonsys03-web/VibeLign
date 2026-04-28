import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_start_cmd import run_vib_start
from vibelign.core.git_hooks import HookInstallResult


class VibStartHooksTest(unittest.TestCase):
    def test_existing_foreign_hook_guidance_mentions_secrets_and_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".vibelign").mkdir(parents=True, exist_ok=True)
            (root / ".vibelign" / "state.json").write_text(
                '{"schema_version": 1}\n', encoding="utf-8"
            )
            previous = Path.cwd()
            try:
                os.chdir(root)
                with (
                    patch(
                        "vibelign.commands.vib_start_cmd._selected_start_tools",
                        return_value=[],
                    ),
                    patch(
                        "vibelign.commands.vib_start_cmd._setup_project",
                        return_value={"created": [], "updated": []},
                    ),
                    patch("vibelign.commands.vib_start_cmd.remove_old_hook"),
                    patch("vibelign.commands.vib_start_cmd.setup_hook_if_needed"),
                    patch(
                        "vibelign.commands.vib_start_cmd.detect_tool",
                        return_value=None,
                    ),
                    patch(
                        "vibelign.commands.vib_start_cmd._has_git",
                        return_value=True,
                    ),
                    patch(
                        "vibelign.commands.vib_start_cmd.install_pre_commit_secret_hook",
                        return_value=HookInstallResult(
                            status="existing-hook",
                            path=root / ".git" / "hooks" / "pre-commit",
                        ),
                    ),
                    patch(
                        "vibelign.commands.vib_start_cmd.build_doctor_envelope",
                        return_value={"data": {"project_score": 100, "status": "Safe"}},
                    ),
                    patch(
                        "vibelign.commands.vib_start_cmd._print_tool_readiness_summary"
                    ),
                    patch(
                        "vibelign.core.fast_tools.has_fd",
                        return_value=True,
                    ),
                    patch(
                        "vibelign.core.fast_tools.has_rg",
                        return_value=True,
                    ),
                    patch("vibelign.core.auto_install.try_install_fast_tools"),
                    patch(
                        "vibelign.core.auto_install.ensure_pyproject_toml",
                        return_value=False,
                    ),
                    patch("vibelign.commands.vib_start_cmd.clack_warn") as mocked_warn,
                    patch("vibelign.commands.vib_start_cmd.clack_info") as mocked_info,
                    patch("vibelign.commands.vib_start_cmd.clack_intro"),
                    patch("vibelign.commands.vib_start_cmd.clack_step"),
                    patch("vibelign.commands.vib_start_cmd.clack_success"),
                    patch("vibelign.commands.vib_start_cmd.clack_outro"),
                ):
                    run_vib_start(
                        Namespace(
                            all_tools=False,
                            tools=None,
                            force=False,
                            quickstart=False,
                        )
                    )

                warn_text = "\n".join(
                    str(call.args[0]) for call in mocked_warn.call_args_list
                )
                info_text = "\n".join(
                    str(call.args[0]) for call in mocked_info.call_args_list
                )
                self.assertIn("자동으로 연결하지 않았어요", warn_text)
                self.assertIn("vib secrets --staged", info_text)
                self.assertIn("vib guard --strict", info_text)
            finally:
                os.chdir(previous)


    def test_vib_start_installs_post_commit_record_hook(self) -> None:
        import subprocess
        from vibelign.commands.vib_start_cmd import run_vib_start

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.vib_start_cmd._selected_start_tools", return_value=[]):
                    run_vib_start(Namespace(all_tools=False, tools=None, force=False, quickstart=False))
            finally:
                os.chdir(previous)

            hook = root / ".git" / "hooks" / "post-commit"
            self.assertTrue(hook.exists())
            self.assertIn("post-commit-record v1", hook.read_text())


if __name__ == "__main__":
    unittest.main()
