import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import cast

from vibelign.commands.vib_guard_cmd import build_guard_envelope
from vibelign.core.meta_paths import MetaPaths


def _git(root: Path, *args: str) -> None:
    _ = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )


def _commit_all(root: Path, message: str) -> None:
    _git(root, "add", ".")
    _git(
        root,
        "-c",
        "user.name=VibeLign Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )


class GuardPlanningTest(unittest.TestCase):
    def _init_repo(self, root: Path, threshold: int = 2) -> MetaPaths:
        _git(root, "init")
        meta = MetaPaths(root)
        meta.ensure_vibelign_dirs()
        _ = meta.state_path.write_text(
            json.dumps({"schema_version": 1}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _ = meta.config_path.write_text(
            f"schema_version: 1\nsmall_fix_line_threshold: {threshold}\n",
            encoding="utf-8",
        )
        return meta

    def test_docs_only_change_is_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = self._init_repo(root)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            _ = (docs_dir / "README.md").write_text("hello\n", encoding="utf-8")
            _commit_all(root, "baseline")

            _ = (docs_dir / "README.md").write_text("hello\nworld\n", encoding="utf-8")

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            exempt_reasons = cast(list[object], planning["exempt_reasons"])
            self.assertIn("docs_only", exempt_reasons)
            self.assertIn("문서만 수정", planning["summary"])
            self.assertNotIn("plan-structure", planning["summary"])

    def test_tests_only_change_is_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = self._init_repo(root)
            tests_dir = root / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            test_path = tests_dir / "test_watch_engine.py"
            _ = test_path.write_text(
                "def test_ok():\n    assert True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            _ = test_path.write_text(
                "def test_ok():\n    assert 1 == 1\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            exempt_reasons = cast(list[object], planning["exempt_reasons"])
            self.assertIn("tests_only", exempt_reasons)
            self.assertIn("테스트만 수정", planning["summary"])

    def test_config_only_change_is_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = self._init_repo(root)
            claude_dir = root / ".claude"
            claude_dir.mkdir(parents=True, exist_ok=True)
            settings_path = claude_dir / "settings.json"
            _ = settings_path.write_text("{}\n", encoding="utf-8")
            _commit_all(root, "baseline")

            _ = settings_path.write_text('{"hooks": {}}\n', encoding="utf-8")

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            exempt_reasons = cast(list[object], planning["exempt_reasons"])
            self.assertIn("config_only", exempt_reasons)
            self.assertIn("config만 수정", planning["summary"])

    def test_small_single_file_production_edit_is_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = self._init_repo(root, threshold=10)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            watch_path = core_dir / "watch_engine.py"
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    import os\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            exempt_reasons = cast(list[object], planning["exempt_reasons"])
            self.assertIn("small_single_file_fix", exempt_reasons)

    def test_new_production_file_requires_vib_plan_guidance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            _ = (core_dir / "base.py").write_text(
                "def base():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            _ = (core_dir / "oauth_provider.py").write_text(
                "# === ANCHOR: OAUTH_PROVIDER_START ===\n"
                "def oauth_provider():\n    return True\n"
                "# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_required")
            required_reasons = cast(list[object], planning["required_reasons"])
            self.assertIn("new_production_file", required_reasons)
            self.assertEqual(envelope["data"]["status"], "warn")
            self.assertIn("vib plan", planning["summary"])
            self.assertNotIn("plan-structure", planning["summary"])

    def test_multi_file_production_edit_requires_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            first = core_dir / "first.py"
            second = core_dir / "second.py"
            _ = first.write_text("def first():\n    return True\n", encoding="utf-8")
            _ = second.write_text("def second():\n    return True\n", encoding="utf-8")
            _commit_all(root, "baseline")

            _ = first.write_text("def first():\n    return False\n", encoding="utf-8")
            _ = second.write_text("def second():\n    return False\n", encoding="utf-8")

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_required")
            required_reasons = cast(list[object], planning["required_reasons"])
            self.assertIn("multi_file_production_edit", required_reasons)

    def test_strict_mode_upgrades_planning_required_to_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            _ = (core_dir / "base.py").write_text(
                "def base():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            _ = (core_dir / "oauth_provider.py").write_text(
                "# === ANCHOR: OAUTH_PROVIDER_START ===\n"
                "def oauth_provider():\n    return True\n"
                "# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=True, since_minutes=120)

            self.assertEqual(
                envelope["data"]["planning"]["status"], "planning_required"
            )
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)

    def test_stale_plan_json_does_not_allow_structural_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            _ = (meta.plans_dir / "plan_oauth.json").write_text(
                json.dumps(
                    {
                        "id": "plan_oauth",
                        "allowed_modifications": [],
                        "required_new_files": ["vibelign/core/oauth_provider.py"],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {"schema_version": 1, "planning": {"active": True, "plan_id": "plan_oauth"}},
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            _ = (core_dir / "base.py").write_text(
                "def base():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            _ = (core_dir / "oauth_provider.py").write_text(
                "# === ANCHOR: OAUTH_PROVIDER_START ===\n"
                "def oauth_provider():\n    return True\n"
                "# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_required")
            self.assertIsNone(planning["active_plan_id"])


if __name__ == "__main__":
    _ = unittest.main()
