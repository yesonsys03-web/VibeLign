import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.vib_secrets_cmd import run_vib_secrets
from vibelign.core.git_hooks import HookInstallResult
from vibelign.core.secret_scan import SecretFinding, SecretScanResult


class VibSecretsCommandTest(unittest.TestCase):
    def test_install_hook_success_mentions_strict_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch(
                    "vibelign.commands.vib_secrets_cmd.resolve_project_root",
                    return_value=root,
                ),
                patch(
                    "vibelign.commands.vib_secrets_cmd.install_pre_commit_secret_hook",
                    return_value=HookInstallResult(
                        status="installed", path=root / ".git" / "hooks" / "pre-commit"
                    ),
                ),
                patch(
                    "vibelign.commands.vib_secrets_cmd.clack_success"
                ) as mocked_success,
                patch("vibelign.commands.vib_secrets_cmd.clack_info"),
            ):
                run_vib_secrets(
                    Namespace(staged=False, install_hook=True, uninstall_hook=False)
                )

            self.assertIn("strict guard", mocked_success.call_args[0][0])

    def test_existing_hook_guidance_mentions_guard_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch(
                    "vibelign.commands.vib_secrets_cmd.resolve_project_root",
                    return_value=root,
                ),
                patch(
                    "vibelign.commands.vib_secrets_cmd.install_pre_commit_secret_hook",
                    return_value=HookInstallResult(
                        status="existing-hook",
                        path=root / ".git" / "hooks" / "pre-commit",
                    ),
                ),
                patch("vibelign.commands.vib_secrets_cmd.clack_warn"),
                patch("vibelign.commands.vib_secrets_cmd.clack_info") as mocked_info,
            ):
                with self.assertRaises(SystemExit):
                    run_vib_secrets(
                        Namespace(staged=False, install_hook=True, uninstall_hook=False)
                    )

            info_text = "\n".join(
                str(call.args[0]) for call in mocked_info.call_args_list
            )
            self.assertIn("vib secrets --staged", info_text)
            self.assertIn("vib guard --strict", info_text)


    def test_all_flag_runs_history_scan_and_reports_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            finding = SecretFinding(
                path="abc12345:app.py",
                rule_id="generic-secret",
                line_number=3,
                snippet="...6789",
            )
            with (
                patch(
                    "vibelign.commands.vib_secrets_cmd.resolve_project_root",
                    return_value=root,
                ),
                patch(
                    "vibelign.commands.vib_secrets_cmd.scan_all_history",
                    return_value=SecretScanResult(findings=[finding]),
                ) as mocked_scan,
                patch("vibelign.commands.vib_secrets_cmd.clack_error"),
                patch("vibelign.commands.vib_secrets_cmd.clack_warn") as mocked_warn,
                patch("vibelign.commands.vib_secrets_cmd.clack_info"),
            ):
                with self.assertRaises(SystemExit):
                    run_vib_secrets(
                        Namespace(
                            staged=False,
                            install_hook=False,
                            uninstall_hook=False,
                            all=True,
                        )
                    )
            mocked_scan.assert_called_once()
            warn_output = "\n".join(
                str(c.args[0]) for c in mocked_warn.call_args_list
            )
            self.assertIn("abc12345:app.py", warn_output)
            self.assertIn("generic-secret", warn_output)

    def test_all_flag_clean_repo_reports_no_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch(
                    "vibelign.commands.vib_secrets_cmd.resolve_project_root",
                    return_value=root,
                ),
                patch(
                    "vibelign.commands.vib_secrets_cmd.scan_all_history",
                    return_value=SecretScanResult(findings=[]),
                ),
                patch(
                    "vibelign.commands.vib_secrets_cmd.clack_success"
                ) as mocked_success,
                patch("vibelign.commands.vib_secrets_cmd.clack_info"),
            ):
                run_vib_secrets(
                    Namespace(
                        staged=False,
                        install_hook=False,
                        uninstall_hook=False,
                        all=True,
                    )
                )
            self.assertGreaterEqual(mocked_success.call_count, 1)


if __name__ == "__main__":
    unittest.main()
