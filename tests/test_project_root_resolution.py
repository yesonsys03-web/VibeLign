import tempfile
import unittest
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

from vibelign.commands.protect_cmd import run_protect
from vibelign.commands.vib_anchor_cmd import run_vib_anchor
from vibelign.commands.vib_checkpoint_cmd import run_vib_checkpoint
from vibelign.commands.vib_doctor_cmd import run_vib_doctor
from vibelign.commands.vib_explain_cmd import run_vib_explain
from vibelign.commands.vib_init_cmd import run_vib_init
from vibelign.commands.vib_transfer_cmd import run_transfer
from vibelign.commands.watch_cmd import run_watch_cmd
from vibelign.core.project_root import (
    find_parent_vibelign_root,
    resolve_project_root,
)


class ProjectRootResolutionTest(unittest.TestCase):
    @dataclass
    class _ExplainArgs:
        file: str | None
        since_minutes: int
        json: bool
        write_report: bool
        ai: bool

    def test_resolve_project_root_falls_back_to_current_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(resolve_project_root(root), root.resolve())
            self.assertIsNone(find_parent_vibelign_root(root))

    def test_resolve_project_root_uses_nearest_ancestor_with_vibelign(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "apps" / "gui"
            child.mkdir(parents=True)
            (root / ".vibelign").mkdir()

            self.assertEqual(find_parent_vibelign_root(child), root.resolve())
            self.assertEqual(resolve_project_root(child), root.resolve())

    def test_resolve_project_root_prefers_nested_explicit_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "apps" / "gui"
            child.mkdir(parents=True)
            (root / ".vibelign").mkdir()
            (child / ".vibelign").mkdir()

            self.assertEqual(find_parent_vibelign_root(child), child.resolve())
            self.assertEqual(resolve_project_root(child), child.resolve())

    def test_init_from_nested_directory_reuses_parent_vibelign_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            (root / ".vibelign").mkdir()

            with patch.object(Path, "cwd", return_value=nested):
                run_vib_init(Namespace(force=False))

            self.assertTrue((root / ".vibelign" / "project_map.json").exists())
            self.assertFalse((nested / ".vibelign" / "project_map.json").exists())

    def test_checkpoint_from_nested_directory_writes_to_parent_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            (root / ".vibelign").mkdir()
            (nested / "card.tsx").write_text(
                "export const card = 1\n", encoding="utf-8"
            )

            with patch.object(Path, "cwd", return_value=nested):
                run_vib_checkpoint(Namespace(message=["nested", "save"], json=True))

            checkpoints_dir = root / ".vibelign" / "checkpoints"
            self.assertTrue(checkpoints_dir.exists())
            self.assertFalse((nested / ".vibelign" / "checkpoints").exists())
            self.assertTrue(any(checkpoints_dir.iterdir()))

    def test_transfer_from_nested_directory_updates_parent_project_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            (root / ".vibelign").mkdir()
            (root / "README.md").write_text("# Root\n", encoding="utf-8")

            with patch.object(Path, "cwd", return_value=nested):
                run_transfer(
                    Namespace(
                        compact=False,
                        full=False,
                        handoff=False,
                        no_prompt=False,
                        print_mode=False,
                        dry_run=False,
                        out=None,
                    )
                )

            self.assertTrue((root / "PROJECT_CONTEXT.md").exists())
            self.assertFalse((nested / "PROJECT_CONTEXT.md").exists())

    def test_anchor_from_nested_directory_writes_root_anchor_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            (root / ".vibelign").mkdir()
            (nested / "card.tsx").write_text(
                "export const card = 1\n", encoding="utf-8"
            )

            with patch.object(Path, "cwd", return_value=nested):
                run_vib_anchor(
                    Namespace(
                        only_ext="",
                        set_intent=None,
                        intent="",
                        auto_intent=False,
                        list_intent=False,
                        validate=False,
                        json=True,
                        suggest=True,
                        dry_run=False,
                        auto=False,
                    )
                )

            self.assertTrue((root / ".vibelign" / "anchor_index.json").exists())
            self.assertFalse((nested / ".vibelign" / "anchor_index.json").exists())

    def test_doctor_from_nested_directory_writes_root_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            (root / ".vibelign").mkdir()
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")

            with patch.object(Path, "cwd", return_value=nested):
                run_vib_doctor(
                    Namespace(
                        strict=False,
                        json=True,
                        write_report=True,
                        fix=False,
                        detailed=False,
                        fix_hints=False,
                        plan=False,
                        patch=False,
                        apply=False,
                        force=False,
                    )
                )

            self.assertTrue(
                (root / ".vibelign" / "reports" / "doctor_latest.json").exists()
            )
            self.assertFalse(
                (nested / ".vibelign" / "reports" / "doctor_latest.json").exists()
            )

    def test_explain_from_nested_directory_resolves_file_from_cwd_and_writes_root_report(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            (root / ".vibelign").mkdir()
            (nested / "card.tsx").write_text(
                "export const card = 1\n", encoding="utf-8"
            )

            with patch.object(Path, "cwd", return_value=nested):
                run_vib_explain(self._ExplainArgs("card.tsx", 60, True, True, False))

            self.assertTrue(
                (root / ".vibelign" / "reports" / "explain_latest.json").exists()
            )
            self.assertFalse(
                (nested / ".vibelign" / "reports" / "explain_latest.json").exists()
            )

    def test_protect_from_nested_directory_keeps_relative_path_from_cwd_but_saves_at_root(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            target = nested / "card.tsx"
            target.write_text("export const card = 1\n", encoding="utf-8")
            (root / ".vibelign").mkdir()

            with patch.object(Path, "cwd", return_value=nested):
                run_protect(Namespace(file="card.tsx", list=False, remove=False))

            protected_file = root / ".vibelign_protected"
            self.assertTrue(protected_file.exists())
            self.assertIn(
                "vibelign-gui/card.tsx", protected_file.read_text(encoding="utf-8")
            )
            self.assertFalse((nested / ".vibelign_protected").exists())

    def test_watch_from_nested_directory_uses_parent_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "vibelign-gui"
            nested.mkdir()
            (root / ".vibelign").mkdir()

            captured: dict[str, object] = {}

            def fake_run_watch(config: dict[str, object]) -> None:
                captured.update(config)

            with patch(
                "vibelign.core.watch_engine.run_watch", side_effect=fake_run_watch
            ):
                with patch.object(Path, "cwd", return_value=nested):
                    run_watch_cmd(
                        Namespace(
                            strict=True,
                            write_log=True,
                            json=False,
                            debounce_ms=250,
                        )
                    )

            self.assertEqual(captured.get("root"), str(root.resolve()))


if __name__ == "__main__":
    unittest.main()
