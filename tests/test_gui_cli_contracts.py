import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_backup_db_viewer_cmd import run_vib_backup_db_viewer
from vibelign.commands.vib_backup_db_maintenance_cmd import run_vib_backup_db_maintenance
from vibelign.commands.vib_checkpoint_cmd import run_vib_checkpoint
from vibelign.commands.vib_doctor_cmd import run_vib_doctor
from vibelign.commands.vib_undo_cmd import run_vib_undo


def _json_object(raw: object) -> dict[str, object]:
    return cast(dict[str, object], json.loads(str(raw)))


class GuiCliContractsTest(unittest.TestCase):
    def test_agent_memory_cards_are_wired_into_gui_home(self):
        root = Path(__file__).resolve().parents[1]
        session_card = root / "vibelign-gui" / "src" / "components" / "agent-memory" / "SessionMemoryCard.tsx"
        recovery_card = root / "vibelign-gui" / "src" / "components" / "agent-memory" / "RecoveryOptionsCard.tsx"
        home_text = (root / "vibelign-gui" / "src" / "pages" / "Home.tsx").read_text(encoding="utf-8")
        order_text = (root / "vibelign-gui" / "src" / "hooks" / "useCardOrder.ts").read_text(encoding="utf-8")
        vib_text = (root / "vibelign-gui" / "src" / "lib" / "vib.ts").read_text(encoding="utf-8")

        self.assertTrue(session_card.exists())
        self.assertTrue(recovery_card.exists())
        self.assertIn("SessionMemoryCard", home_text)
        self.assertIn("RecoveryOptionsCard", home_text)
        self.assertIn('"session-memory"', order_text)
        self.assertIn('"recovery-options"', order_text)
        self.assertIn("memorySummary", vib_text)
        self.assertIn("recoveryPreview", vib_text)
        self.assertIn("verificationFreshness", vib_text)
        self.assertIn("safeCheckpointCandidate", vib_text)
        self.assertIn("driftCandidates", recovery_card.read_text(encoding="utf-8"))

    def test_top_level_help_mentions_backup_db_commands(self):
        from vibelign.cli.cli_base import MAIN_DESCRIPTION
        from vibelign.commands.vib_manual_cmd import GROUPS, MANUAL

        self.assertIn("backup-db-viewer", MAIN_DESCRIPTION)
        self.assertIn("backup-db-maintenance", MAIN_DESCRIPTION)
        self.assertIn("backup-db-viewer", MANUAL)
        self.assertIn("backup-db-maintenance", MANUAL)

        grouped_commands = {
            command for _title, commands in GROUPS for command in commands
        }
        self.assertIn("backup-db-viewer", grouped_commands)
        self.assertIn("backup-db-maintenance", grouped_commands)

    def test_doctor_json_exposes_fields_consumed_by_gui(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "main.py").write_text("print('ok')\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.vib_doctor_cmd.print") as mocked:
                    run_vib_doctor(
                        Namespace(
                            strict=False,
                            json=True,
                            write_report=False,
                            fix=False,
                            detailed=False,
                            fix_hints=False,
                            plan=False,
                            patch=False,
                            apply=False,
                            force=False,
                        )
                    )
                    payload = _json_object(cast(object, mocked.call_args.args[0]))
            finally:
                os.chdir(previous)

            data = cast(dict[str, object], payload["data"])
            self.assertIn("project_score", data)
            self.assertIn("status", data)
            self.assertIn("issues", data)
            self.assertIn("recommended_actions", data)

    def test_checkpoint_and_undo_json_expose_fields_consumed_by_gui(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "card.tsx"
            _ = target.write_text("export const card = 1\n", encoding="utf-8")

            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch(
                    "vibelign.commands.vib_checkpoint_cmd.print"
                ) as mocked_create:
                    run_vib_checkpoint(Namespace(message=["gui", "save"], json=True))
                    created = _json_object(
                        cast(object, mocked_create.call_args.args[0])
                    )

                with patch("vibelign.commands.vib_checkpoint_cmd.print") as mocked_list:
                    run_vib_checkpoint(Namespace(message=["list"], json=True))
                    listed = _json_object(cast(object, mocked_list.call_args.args[0]))

                checkpoints = cast(list[dict[str, object]], listed["checkpoints"])
                checkpoint_id = str(checkpoints[0]["checkpoint_id"])
                _ = target.write_text("export const card = 2\n", encoding="utf-8")

                with patch("vibelign.commands.vib_undo_cmd.print") as mocked_undo:
                    run_vib_undo(
                        Namespace(
                            checkpoint_id=checkpoint_id,
                            force=True,
                            json=True,
                        )
                    )
                    restored = _json_object(cast(object, mocked_undo.call_args.args[0]))
            finally:
                os.chdir(previous)

            self.assertTrue(created["ok"])
            self.assertIn("file_count", created)
            self.assertIn("context_updated", created)

            self.assertTrue(checkpoints)
            self.assertIn("checkpoint_id", checkpoints[0])
            self.assertIn("message", checkpoints[0])
            self.assertIn("created_at", checkpoints[0])

            self.assertTrue(restored["ok"])
            self.assertEqual(restored["checkpoint_id"], checkpoint_id)
            self.assertIn("message", restored)
            self.assertIn("restored_at", restored)

    def test_backup_dashboard_json_exposes_metadata_consumed_by_gui(self):
        class Summary:
            checkpoint_id = "cp_gui_auto"
            message = "vibelign: checkpoint - before work"
            created_at = "2026-04-30T10:00:00+09:00"
            pinned = False
            file_count = 3
            pruned_count = 0
            pruned_bytes = 0
            total_size_bytes = 4096
            trigger = "post_commit"
            git_commit_message = "Add dashboard"
            files = [
                {"relative_path": "src/app.py", "size": 1024},
                {"path": "docs/plan.md", "size_bytes": 3072},
            ]

        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(Path(tmp))
                with patch(
                    "vibelign.commands.vib_checkpoint_cmd.list_for_cli",
                    return_value=([Summary()], None),
                ), patch("vibelign.commands.vib_checkpoint_cmd.print") as mocked_list:
                    run_vib_checkpoint(Namespace(message=["list"], json=True))
                    listed = _json_object(cast(object, mocked_list.call_args.args[0]))
            finally:
                os.chdir(previous)

        checkpoints = cast(list[dict[str, object]], listed["checkpoints"])
        self.assertEqual(checkpoints[0]["checkpoint_id"], "cp_gui_auto")
        self.assertEqual(checkpoints[0]["total_size_bytes"], 4096)
        self.assertEqual(checkpoints[0]["trigger"], "post_commit")
        self.assertEqual(checkpoints[0]["git_commit_message"], "Add dashboard")
        self.assertEqual(
            checkpoints[0]["files"],
            [
                {"relative_path": "src/app.py", "size": 1024},
                {"relative_path": "docs/plan.md", "size": 3072},
            ],
        )

    def test_backup_db_viewer_json_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_PROJECT_ROOT": str(root)}, clear=False), patch(
                "vibelign.commands.vib_backup_db_viewer_cmd.inspect_backup_db",
                return_value={
                    "db_exists": False,
                    "checkpoint_count": 0,
                    "checkpoints": [],
                    "retention_policy": None,
                    "object_store": {"exists": False, "compression_summary": []},
                },
            ), patch("vibelign.commands.vib_backup_db_viewer_cmd.print") as mocked_print:
                code = run_vib_backup_db_viewer(Namespace(root=str(root), json=True))
                payload = _json_object(cast(object, mocked_print.call_args.args[0]))

        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["db_exists"])
        self.assertEqual(payload["checkpoints"], [])

    def test_backup_db_viewer_json_error_is_user_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_PROJECT_ROOT": str(root)}, clear=False), patch(
                "vibelign.commands.vib_backup_db_viewer_cmd.inspect_backup_db",
                side_effect=RuntimeError("RUST_ENGINE_UNAVAILABLE: missing"),
            ), patch("vibelign.commands.vib_backup_db_viewer_cmd.print") as mocked_print:
                code = run_vib_backup_db_viewer(Namespace(root=str(root), json=True))
                payload = _json_object(cast(object, mocked_print.call_args.args[0]))

        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("백업 관리 DB를 읽을 수 없어요", str(payload["error"]))

    def test_backup_db_maintenance_json_contract_defaults_to_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, {"VIBELIGN_PROJECT_ROOT": str(root)}, clear=False), patch(
                "vibelign.commands.vib_backup_db_maintenance_cmd.maintain_backup_db",
                return_value={
                    "result": "backup_db_maintenance",
                    "mode": "dry_run",
                    "db_exists": True,
                    "planned_action": "noop",
                },
            ) as mocked_maintain, patch("vibelign.commands.vib_backup_db_maintenance_cmd.print") as mocked_print:
                code = run_vib_backup_db_maintenance(
                    Namespace(root=str(root), json=True, apply=False)
                )
                payload = _json_object(cast(object, mocked_print.call_args.args[0]))

        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "dry_run")
        self.assertEqual(mocked_maintain.call_args.args, (root.resolve(),))
        self.assertEqual(mocked_maintain.call_args.kwargs, {"apply": False})

    def test_lazy_cli_propagates_command_return_code(self):
        from vibelign.cli.cli_runtime import run_cli_with_args

        def build_parser():
            import argparse

            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            cmd = sub.add_parser("fail")
            cmd.set_defaults(func=lambda _args: 7)
            return parser

        self.assertEqual(run_cli_with_args(build_parser, ["fail"]), 7)

    def test_backup_dashboard_lint_is_wired_into_gui_npm_lint(self):
        root = Path(__file__).resolve().parents[1]
        package = json.loads((root / "vibelign-gui" / "package.json").read_text(encoding="utf-8"))
        lint_script = str(package["scripts"]["lint"])

        self.assertIn("lint-backup-copy.mjs", lint_script)
        self.assertTrue((root / "vibelign-gui" / "scripts" / "lint-backup-copy.mjs").exists())


if __name__ == "__main__":
    _ = unittest.main()
