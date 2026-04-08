import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from typing import cast
from unittest.mock import patch

from vibelign.commands.vib_checkpoint_cmd import run_vib_checkpoint
from vibelign.commands.vib_doctor_cmd import run_vib_doctor
from vibelign.commands.vib_undo_cmd import run_vib_undo


def _json_object(raw: object) -> dict[str, object]:
    return cast(dict[str, object], json.loads(str(raw)))


class GuiCliContractsTest(unittest.TestCase):
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


if __name__ == "__main__":
    _ = unittest.main()
