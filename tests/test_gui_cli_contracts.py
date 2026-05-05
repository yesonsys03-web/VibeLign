import json
import os
import subprocess
import tempfile
import unittest
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_backup_db_viewer_cmd import run_vib_backup_db_viewer
from vibelign.commands.vib_backup_db_maintenance_cmd import run_vib_backup_db_maintenance
from vibelign.commands.vib_checkpoint_cmd import run_vib_checkpoint
from vibelign.commands.vib_doctor_cmd import run_vib_doctor
from vibelign.commands.vib_memory_cmd import run_vib_memory_show
from vibelign.commands.vib_recover_cmd import run_vib_recover
from vibelign.commands.vib_undo_cmd import run_vib_undo
from vibelign.core.memory.audit import memory_audit_path
from vibelign.core.memory.store import add_memory_relevant_file, load_memory_state


def _json_object(raw: object) -> dict[str, object]:
    return cast(dict[str, object], json.loads(str(raw)))


@dataclass
class _RecoverArgs:
    explain: bool
    preview: bool = False
    recommend: bool = False
    phrase: str = ""
    file: str | None = None
    json: bool = False
    apply: bool = False
    checkpoint_id: str = ""
    sandwich_checkpoint_id: str = ""
    confirmation: str = ""
    plan_id: str | None = None
    candidate_id: str | None = None
    option_id: str | None = None
    recommendation_provider: str | None = None


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
        self.assertIn("recoveryRecommend", vib_text)
        self.assertIn('"memory", "proposal-create"', vib_text)
        self.assertIn('"--relevant-file"', vib_text)
        self.assertIn('"--verification"', vib_text)
        self.assertIn('"--risk-note"', vib_text)
        self.assertNotIn('"transfer", "--handoff", "--ai"', vib_text)
        self.assertIn('["memory", "show", "--json"]', vib_text)
        self.assertIn('["recover", "--preview", "--json"]', vib_text)
        self.assertIn('["recover", "--recommend", "--phrase", phrase]', vib_text)
        self.assertIn("verificationFreshness", vib_text)
        self.assertIn("safeCheckpointCandidate", vib_text)
        self.assertIn("requireRecord", vib_text)
        self.assertIn("requireString", vib_text)
        self.assertIn("requireRecordArray", vib_text)
        self.assertIn("p0_summaries", vib_text)
        self.assertIn("drift_candidates[${index}].why_outside_zone", vib_text)
        recovery_text = recovery_card.read_text(encoding="utf-8")
        transfer_text = (root / "vibelign-gui" / "src" / "components" / "cards" / "transfer" / "TransferCard.tsx").read_text(encoding="utf-8")
        self.assertIn("driftCandidates", recovery_text)
        self.assertIn("복구 후보 추천 보기", recovery_text)
        self.assertIn("검토가 필요한 파일", recovery_text)
        self.assertIn("미리보기 전용", recovery_text)
        self.assertNotIn("Drift candidates", recovery_text)
        self.assertNotIn("READ ONLY", recovery_text)
        session_text = session_card.read_text(encoding="utf-8")
        self.assertIn("지금 하던 일", session_text)
        self.assertIn("다음에 할 일", session_text)
        self.assertIn(".vibelign/work_memory.json", session_text)
        self.assertIn("수락해서 세션 메모리에 저장", session_text)
        self.assertIn(".vibelign/work_memory.json", transfer_text)
        self.assertIn("PROJECT_CONTEXT.md에 반영", transfer_text)
        self.assertNotIn("지금 하던 일 기록", session_text)
        self.assertNotIn("전문가용 작업 기록", session_text)

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

    def test_memory_and_recovery_json_contracts_match_gui_schema_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch("vibelign.commands.vib_memory_cmd.print") as mocked_memory:
                    run_vib_memory_show(Namespace(json=True))
                    memory_payload = _json_object(cast(object, mocked_memory.call_args.args[0]))
                with patch("vibelign.commands.vib_recover_cmd.print") as mocked_recover:
                    run_vib_recover(
                        _RecoverArgs(
                            explain=False,
                            preview=True,
                            file=None,
                            json=True,
                            apply=False,
                            checkpoint_id="",
                            sandwich_checkpoint_id="",
                            confirmation="",
                        )
                    )
                    recovery_payload = _json_object(cast(object, mocked_recover.call_args.args[0]))
                audit_events = [
                    cast(dict[str, object], json.loads(line))["event"]
                    for line in memory_audit_path(root).read_text(encoding="utf-8").splitlines()
                ]
            finally:
                os.chdir(previous)

        self.assertEqual(memory_payload["schema_version"], 1)
        self.assertIn("active_intent", memory_payload)
        self.assertIn("decisions", memory_payload)
        self.assertIn("plan_id", recovery_payload)
        self.assertEqual(recovery_payload["mode"], "read_only")
        self.assertIn("options", recovery_payload)
        self.assertIn("p0_summaries", recovery_payload)

        self.assertIn("memory_summary_read", audit_events)
        self.assertIn("recovery_preview", audit_events)

    def test_memory_show_auto_records_agent_handoff_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory_path = root / ".vibelign" / "work_memory.json"
            add_memory_relevant_file(
                memory_path,
                "src/session_memory.py",
                "agent observed recent work",
                source="observed",
                updated_by="mcp patch_apply",
            )
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {"VIBELIGN_PROJECT_ROOT": str(root)}, clear=False), patch(
                    "vibelign.commands.vib_memory_cmd.print"
                ) as mocked_memory:
                    run_vib_memory_show(Namespace(json=True))
                    memory_payload = _json_object(cast(object, mocked_memory.call_args.args[0]))
                stored = load_memory_state(memory_path)
            finally:
                os.chdir(previous)

        active_intent = cast(dict[str, object], memory_payload["active_intent"])
        next_action = cast(dict[str, object], memory_payload["next_action"])

        self.assertIn("src/session_memory.py", str(active_intent["text"]))
        self.assertIn("vib guard", str(next_action["text"]))
        self.assertEqual(active_intent["source"], "system")
        self.assertEqual(next_action["source"], "system")
        self.assertTrue(active_intent["proposed"])
        self.assertTrue(next_action["proposed"])
        self.assertIsNotNone(stored.active_intent)
        self.assertIsNotNone(stored.next_action)

    def test_memory_show_auto_next_action_includes_concrete_risk_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            memory_path = root / ".vibelign" / "work_memory.json"
            memory_path.parent.mkdir(parents=True, exist_ok=True)
            memory_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "risks": [
                            {
                                "text": "src/app.py — 보호 파일 근처 변경이 감지됨",
                                "source": "observed",
                            }
                        ],
                        "active_intent": {
                            "text": "Handoff decision: tried=SessionMemoryCard shows src/app.tsx; blocked_by=generic expert placeholder; switched_to=show raw active_intent",
                            "source": "system",
                            "proposed": True,
                        },
                        "next_action": {
                            "text": "경고 내용을 먼저 확인하고 필요한 파일만 수정하거나 복구하세요.",
                            "source": "system",
                            "proposed": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            previous = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(os.environ, {"VIBELIGN_PROJECT_ROOT": str(root)}, clear=False), patch(
                    "vibelign.commands.vib_memory_cmd.print"
                ) as mocked_memory:
                    run_vib_memory_show(Namespace(json=True))
                    memory_payload = _json_object(cast(object, mocked_memory.call_args.args[0]))
            finally:
                os.chdir(previous)

        active_intent = cast(dict[str, object], memory_payload["active_intent"])
        next_action = cast(dict[str, object], memory_payload["next_action"])

        self.assertIn("SessionMemoryCard shows src/app.tsx", str(active_intent["text"]))
        self.assertIn("src/app.py", str(next_action["text"]))
        self.assertIn("보호 파일 근처 변경", str(next_action["text"]))
        self.assertNotEqual(
            next_action["text"],
            "경고 내용을 먼저 확인하고 필요한 파일만 수정하거나 복구하세요.",
        )

    def test_gui_json_parser_rejects_malformed_nested_payloads(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            ["node", "scripts/test-vib-json-parsers.mjs"],
            cwd=root / "vibelign-gui",
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("vib JSON parser contract checks passed", result.stdout)

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
        @dataclass
        class Summary:
            checkpoint_id: str = "cp_gui_auto"
            message: str = "vibelign: checkpoint - before work"
            created_at: str = "2026-04-30T10:00:00+09:00"
            pinned: bool = False
            file_count: int = 3
            pruned_count: int = 0
            pruned_bytes: int = 0
            total_size_bytes: int = 4096
            trigger: str = "post_commit"
            git_commit_message: str = "Add dashboard"
            files: tuple[dict[str, object], ...] = (
                {"relative_path": "src/app.py", "size": 1024},
                {"path": "docs/plan.md", "size_bytes": 3072},
            )

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

        def fail_command(_args: object) -> int:
            return 7

        def build_parser():
            import argparse

            parser = argparse.ArgumentParser()
            sub = parser.add_subparsers(dest="command", required=True)
            cmd = sub.add_parser("fail")
            cmd.set_defaults(func=fail_command)
            return parser

        self.assertEqual(run_cli_with_args(build_parser, ["fail"]), 7)

    def test_backup_dashboard_lint_is_wired_into_gui_npm_lint(self):
        root = Path(__file__).resolve().parents[1]
        package = cast(
            dict[str, object],
            json.loads((root / "vibelign-gui" / "package.json").read_text(encoding="utf-8")),
        )
        scripts = cast(dict[str, object], package["scripts"])
        lint_script = str(scripts["lint"])

        self.assertIn("lint-backup-copy.mjs", lint_script)
        self.assertTrue((root / "vibelign-gui" / "scripts" / "lint-backup-copy.mjs").exists())


if __name__ == "__main__":
    _ = unittest.main()
