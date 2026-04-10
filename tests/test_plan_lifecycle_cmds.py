import json
import importlib
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from collections.abc import Callable
from typing import cast

from vibelign.core.meta_paths import MetaPaths
from vibelign.mcp.mcp_state_store import load_planning_session

run_vib_plan_close = cast(
    Callable[[Namespace], None],
    importlib.import_module("vibelign.commands.vib_plan_close_cmd").run_vib_plan_close,
)
run_vib_plan_override = cast(
    Callable[[Namespace], None],
    importlib.import_module(
        "vibelign.commands.vib_plan_override_cmd"
    ).run_vib_plan_override,
)


class PlanLifecycleCommandsTest(unittest.TestCase):
    def test_plan_close_marks_active_plan_inactive_and_clears_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            meta.state_path.write_text(
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

            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_plan_close(Namespace())
            finally:
                os.chdir(previous)

            planning = load_planning_session(meta)
            self.assertIsNotNone(planning)
            assert planning is not None
            self.assertEqual(planning["active"], False)
            self.assertIsNone(planning["plan_id"])
            self.assertEqual(planning["override"], False)
            self.assertIsNone(planning["override_reason"])
            self.assertNotIn("override_count", planning)

    def test_plan_close_is_noop_without_active_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": False,
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

            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_plan_close(Namespace())
            finally:
                os.chdir(previous)

            planning = load_planning_session(meta)
            self.assertIsNotNone(planning)
            assert planning is not None
            self.assertEqual(planning["active"], False)
            self.assertIsNone(planning["plan_id"])

    def test_plan_close_clears_stale_override_even_when_inactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": False,
                            "plan_id": None,
                            "feature": "watch 수정",
                            "override": True,
                            "override_reason": "manual",
                            "overridden_at": "2026-04-09T01:00:00Z",
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T01:00:00Z",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_plan_close(Namespace())
            finally:
                os.chdir(previous)

            planning = load_planning_session(meta)
            self.assertIsNotNone(planning)
            assert planning is not None
            self.assertEqual(planning["override"], False)
            self.assertIsNone(planning["override_reason"])
            self.assertNotIn("overridden_at", planning)
            self.assertNotIn("override_count", planning)

    def test_plan_override_sets_override_fields_with_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            meta.state_path.write_text(
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

            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_plan_override(
                    Namespace(reason=["plan이", "현재", "구조와", "맞지", "않음"])
                )
            finally:
                os.chdir(previous)

            planning = load_planning_session(meta)
            self.assertIsNotNone(planning)
            assert planning is not None
            self.assertEqual(planning["override"], True)
            self.assertEqual(
                planning["override_reason"], "plan이 현재 구조와 맞지 않음"
            )
            self.assertIn("overridden_at", planning)
            self.assertEqual(planning["override_count"], 1)

    def test_plan_override_increments_override_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "plan_watch",
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "override_count": 1,
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

            previous = Path.cwd()
            try:
                os.chdir(root)
                run_vib_plan_override(Namespace(reason=["manual"]))
            finally:
                os.chdir(previous)

            planning = load_planning_session(meta)
            self.assertIsNotNone(planning)
            assert planning is not None
            self.assertEqual(planning["override_count"], 2)

    def test_plan_override_requires_non_empty_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()

            previous = Path.cwd()
            try:
                os.chdir(root)
                with self.assertRaises(SystemExit):
                    run_vib_plan_override(Namespace(reason=[]))
            finally:
                os.chdir(previous)

    def test_plan_override_requires_active_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = MetaPaths(root)
            meta.ensure_vibelign_dirs()
            meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": False,
                            "plan_id": None,
                            "feature": None,
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

            previous = Path.cwd()
            try:
                os.chdir(root)
                with self.assertRaises(SystemExit):
                    run_vib_plan_override(Namespace(reason=["manual"]))
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    _ = unittest.main()
