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
    def _init_repo(self, root: Path) -> MetaPaths:
        _git(root, "init")
        meta = MetaPaths(root)
        meta.ensure_vibelign_dirs()
        _ = meta.state_path.write_text(
            json.dumps({"schema_version": 1}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return meta

    def test_docs_only_change_is_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _meta = self._init_repo(root)
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

    def test_tests_only_change_is_planning_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _meta = self._init_repo(root)
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
            _meta = self._init_repo(root)
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
            _meta = self._init_repo(root)
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
            self.assertIn("소규모 단일 파일 수정", planning["summary"])

    def test_new_production_file_without_plan_requires_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _meta = self._init_repo(root)
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
            self.assertIn("vib plan-structure", planning["summary"])

    def test_new_source_file_without_anchor_warns_in_non_strict_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            _ = (core_dir / "base.py").write_text(
                "def base():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            target = core_dir / "oauth_provider.py"
            _ = target.write_text(
                "def oauth_provider():\n    return True\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertIn(
                "vibelign/core/oauth_provider.py",
                envelope["data"]["anchor_violations"],
            )
            self.assertEqual(envelope["data"]["status"], "warn")
            self.assertEqual(envelope["data"]["blocked"], False)
            self.assertIn(
                "신규 소스 파일에 앵커가 없습니다", envelope["data"]["summary"]
            )

    def test_new_source_file_without_anchor_fails_in_strict_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            _ = (core_dir / "base.py").write_text(
                "def base():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            target = core_dir / "oauth_provider.py"
            _ = target.write_text(
                "def oauth_provider():\n    return True\n", encoding="utf-8"
            )
            _git(root, "add", "vibelign/core/oauth_provider.py")

            envelope = build_guard_envelope(root, strict=True, since_minutes=120)

            self.assertIn(
                "vibelign/core/oauth_provider.py",
                envelope["data"]["anchor_violations"],
            )
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)

    def test_multi_file_production_edit_without_plan_requires_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _meta = self._init_repo(root)
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
            _meta = self._init_repo(root)
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

    def test_active_plan_passes_for_allowed_existing_and_new_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_oauth"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "OAuth 인증 추가",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": [
                                "new_production_file",
                                "multi_file_production_edit",
                            ]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/oauth_provider.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit", "import_wiring"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/oauth_provider.py",
                                "responsibility": "OAuth 공급자 로직",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "OAuth 인증 추가",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    import os\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = (core_dir / "oauth_provider.py").write_text(
                "# === ANCHOR: OAUTH_PROVIDER_START ===\n"
                "def oauth_provider():\n    return True\n"
                "# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=True, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "pass")
            self.assertEqual(planning["active_plan_id"], plan_id)

    def test_active_plan_allowed_paths_only_results_in_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_allowed_only"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/oauth_provider.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/oauth_provider.py",
                                "responsibility": "OAuth 공급자 로직",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    import os\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = (core_dir / "oauth_provider.py").write_text(
                "# === ANCHOR: OAUTH_PROVIDER_START ===\n"
                "def oauth_provider():\n    return True\n"
                "# === ANCHOR: OAUTH_PROVIDER_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "pass")
            self.assertEqual(envelope["data"]["status"], "pass")
            self.assertEqual(envelope["data"]["blocked"], False)

    def test_plan_deviation_detects_unexpected_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            other_path = core_dir / "other.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = other_path.write_text(
                "def other():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "plan_auth"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/oauth_provider.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/oauth_provider.py",
                                "responsibility": "OAuth 공급자 로직",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = other_path.write_text(
                "def other():\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn(
                "small_single_file_fix",
                cast(list[object], planning["exempt_reasons"]),
            )

    def test_active_plan_out_of_scope_change_results_in_plan_exists_but_deviated(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            other_path = core_dir / "other.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = other_path.write_text(
                "def other():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "plan_out_of_scope"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/oauth_provider.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/oauth_provider.py",
                                "responsibility": "OAuth 공급자 로직",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    import os\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = other_path.write_text(
                "def other():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(
                envelope["data"]["planning"]["status"], "plan_exists_but_deviated"
            )
            self.assertEqual(envelope["data"]["status"], "warn")
            self.assertEqual(envelope["data"]["blocked"], False)
            self.assertTrue(
                any(
                    "unexpected_change:vibelign/core/other.py" in str(item)
                    for item in cast(
                        list[object], envelope["data"]["planning"]["deviations"]
                    )
                )
            )

    def test_forbidden_violation_is_hard_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_forbidden"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/oauth_provider.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/oauth_provider.py",
                                "responsibility": "OAuth 공급자 로직",
                            }
                        ],
                        "forbidden": [
                            {
                                "type": "path_edit_outside_allowed_anchor",
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "reason": "anchor 밖 수정 금지",
                            }
                        ],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = auth_path.write_text(
                "outside = True\n"
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)
            self.assertTrue(
                any(
                    "forbidden:vibelign/core/auth.py" in str(item)
                    for item in cast(list[object], planning["deviations"])
                )
            )

    def test_anchor_outside_allowed_range_results_in_deviation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            _ = auth_path.write_text(
                "prefix = True\n"
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_anchor_range"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/auth_helper.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/auth_helper.py",
                                "responsibility": "helper",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = auth_path.write_text(
                "prefix = False\n"
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = (core_dir / "auth_helper.py").write_text(
                "def helper():\n    return True\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(
                envelope["data"]["planning"]["status"], "plan_exists_but_deviated"
            )
            self.assertEqual(
                envelope["data"]["planning"]["deviations"],
                ["anchor_outside_allowed_range:vibelign/core/auth.py"],
            )

    def test_max_lines_added_exceeded_results_in_deviation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_max_lines"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/auth_helper.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 1,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/auth_helper.py",
                                "responsibility": "helper",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    import os\n    import sys\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = (core_dir / "auth_helper.py").write_text(
                "def helper():\n    return True\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(
                envelope["data"]["planning"]["status"], "plan_exists_but_deviated"
            )
            self.assertEqual(
                envelope["data"]["planning"]["deviations"],
                ["max_lines_added_exceeded:vibelign/core/auth.py"],
            )

    def test_disallowed_change_type_results_in_deviation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            commands_dir = root / "vibelign" / "commands"
            commands_dir.mkdir(parents=True, exist_ok=True)
            cli_path = commands_dir / "demo_cmd.py"
            _ = cli_path.write_text(
                "# === ANCHOR: DEMO_CMD_START ===\n"
                "def register(parser):\n    parser.add_parser('demo')\n"
                "# === ANCHOR: DEMO_CMD_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_disallowed_change_type"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "command wiring",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/commands/demo_helper.py"],
                            "existing_file_paths": ["vibelign/commands/demo_cmd.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/commands/demo_cmd.py",
                                "anchor": "DEMO_CMD",
                                "max_lines_added": 100,
                                "allowed_change_types": ["registration"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/commands/demo_helper.py",
                                "responsibility": "demo helper",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "command wiring",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = cli_path.write_text(
                "# === ANCHOR: DEMO_CMD_START ===\n"
                "def register(parser):\n    value = 1\n    return value\n"
                "# === ANCHOR: DEMO_CMD_END ===\n",
                encoding="utf-8",
            )
            _ = (commands_dir / "demo_helper.py").write_text(
                "def helper():\n    return True\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(
                envelope["data"]["planning"]["status"], "plan_exists_but_deviated"
            )
            self.assertEqual(
                envelope["data"]["planning"]["deviations"],
                ["disallowed_change_type:edit:vibelign/commands/demo_cmd.py"],
            )

    def test_broken_plan_file_fails_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            _ = (core_dir / "auth.py").write_text(
                "def auth_handler():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "broken_plan"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                "{bad}\n", encoding="utf-8"
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = (core_dir / "auth.py").write_text(
                "def auth_handler():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "fail")
            self.assertTrue(
                any(
                    "broken_plan" in str(item)
                    for item in cast(list[object], planning["deviations"])
                )
            )

    def test_broken_plan_file_results_in_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            target = core_dir / "auth.py"
            _ = target.write_text(
                "def auth_handler():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "broken_plan_direct"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                "{bad}\n", encoding="utf-8"
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = target.write_text(
                "def auth_handler():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)

    def test_missing_plan_file_results_in_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            target = core_dir / "auth.py"
            _ = target.write_text(
                "def auth_handler():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": "missing_plan",
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = target.write_text(
                "def auth_handler():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)
            self.assertEqual(
                envelope["data"]["planning"]["deviations"],
                ["missing_plan_file"],
            )

    def test_invalid_plan_state_results_in_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            target = core_dir / "auth.py"
            _ = target.write_text(
                "def auth_handler():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": None,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = target.write_text(
                "def auth_handler():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)
            self.assertEqual(
                envelope["data"]["planning"]["deviations"],
                ["invalid_state"],
            )

    def test_key_complete_but_wrong_typed_plan_payload_fails_in_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            target = core_dir / "watch_engine.py"
            _ = target.write_text("def x():\n    return True\n", encoding="utf-8")
            _commit_all(root, "baseline")

            plan_id = "bad_shape_guard_plan"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "allowed_modifications": {},
                        "required_new_files": {},
                        "forbidden": [],
                        "messages": {},
                        "evidence": {},
                        "scope": {},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = target.write_text(
                "def x():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)
            self.assertTrue(
                any(
                    "broken_plan" in str(item)
                    for item in cast(
                        list[object], envelope["data"]["planning"]["deviations"]
                    )
                )
            )

    def test_plan_payload_with_non_dict_list_item_fails_in_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            target = core_dir / "watch_engine.py"
            _ = target.write_text("def x():\n    return True\n", encoding="utf-8")
            _commit_all(root, "baseline")

            plan_id = "bad_item_guard_plan"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "allowed_modifications": ["not-a-dict"],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {},
                        "evidence": {},
                        "scope": {},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = target.write_text(
                "def x():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)
            self.assertTrue(
                any(
                    "broken_plan" in str(item)
                    for item in cast(
                        list[object], envelope["data"]["planning"]["deviations"]
                    )
                )
            )

    def test_plan_payload_with_wrong_typed_forbidden_fails_in_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            target = core_dir / "watch_engine.py"
            _ = target.write_text("def x():\n    return True\n", encoding="utf-8")
            _commit_all(root, "baseline")

            plan_id = "bad_forbidden_guard_plan"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "allowed_modifications": [],
                        "required_new_files": [],
                        "forbidden": {},
                        "messages": {},
                        "evidence": {},
                        "scope": {},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = target.write_text(
                "def x():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)
            self.assertTrue(
                any(
                    "broken_plan" in str(item)
                    for item in cast(
                        list[object], envelope["data"]["planning"]["deviations"]
                    )
                )
            )

    def test_plan_payload_with_wrong_typed_required_new_files_fails_in_guard(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            target = core_dir / "watch_engine.py"
            _ = target.write_text("def x():\n    return True\n", encoding="utf-8")
            _commit_all(root, "baseline")

            plan_id = "bad_required_new_guard_plan"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "allowed_modifications": [],
                        "required_new_files": {},
                        "forbidden": [],
                        "messages": {},
                        "evidence": {},
                        "scope": {},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = target.write_text(
                "def x():\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(40))
                + "\n    return False\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "fail")
            self.assertEqual(envelope["data"]["status"], "fail")
            self.assertEqual(envelope["data"]["blocked"], True)
            self.assertTrue(
                any(
                    "broken_plan" in str(item)
                    for item in cast(
                        list[object], envelope["data"]["planning"]["deviations"]
                    )
                )
            )

    def test_staged_changes_take_priority_over_unstaged_working_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            watch_path = core_dir / "watch_engine.py"
            other_path = core_dir / "other.py"
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            _ = other_path.write_text(
                "def other():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "plan_watch"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "watch 기능 확장",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": [],
                            "existing_file_paths": ["vibelign/core/watch_engine.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/watch_engine.py",
                                "anchor": "WATCH_ENGINE",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 기능 확장",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    import os\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            _git(root, "add", "vibelign/core/watch_engine.py")
            _ = other_path.write_text(
                "def other():\n    return False\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertEqual(
                planning["changed_files"], ["vibelign/core/watch_engine.py"]
            )
            self.assertIn(
                "small_single_file_fix",
                cast(list[object], planning["exempt_reasons"]),
            )

    def test_disallowed_delete_on_allowed_path_is_deviation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_delete"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/oauth_provider.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/oauth_provider.py",
                                "responsibility": "OAuth 공급자 로직",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            auth_path.unlink()

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "plan_exists_but_deviated")
            self.assertTrue(
                any(
                    "unexpected_deleted" in str(item)
                    for item in cast(list[object], planning["deviations"])
                )
            )

    def test_import_wiring_allowed_type_can_pass_without_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                + "\n".join([f"from .dep_{i} import x_{i}" for i in range(35)])
                + "\n"
                "from pathlib import Path\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_import_wiring"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth wiring",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/core/oauth_provider.py"],
                            "existing_file_paths": ["vibelign/core/auth.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 100,
                                "allowed_change_types": ["import_wiring"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/core/oauth_provider.py",
                                "responsibility": "OAuth 공급자 로직",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth wiring",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                + "\n".join([f"from .dep_{i} import x_{i}" for i in range(35)])
                + "\n"
                "from pathlib import Path\n"
                "from typing import Any\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = (core_dir / "oauth_provider.py").write_text(
                "def oauth_provider():\n    return True\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "pass")

    def test_registration_allowed_type_can_pass_without_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            commands_dir = root / "vibelign" / "commands"
            commands_dir.mkdir(parents=True, exist_ok=True)
            cli_path = commands_dir / "demo_cmd.py"
            _ = cli_path.write_text(
                "# === ANCHOR: DEMO_CMD_START ===\n"
                + "\n".join([f"router.add_{i} = {i}" for i in range(40)])
                + "\n"
                "def register(parser):\n    parser.add_parser('demo')\n"
                "# === ANCHOR: DEMO_CMD_END ===\n",
                encoding="utf-8",
            )
            _commit_all(root, "baseline")

            plan_id = "plan_registration"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "command wiring",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": ["vibelign/commands/demo_helper.py"],
                            "existing_file_paths": ["vibelign/commands/demo_cmd.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/commands/demo_cmd.py",
                                "anchor": "DEMO_CMD",
                                "max_lines_added": 100,
                                "allowed_change_types": ["registration"],
                            }
                        ],
                        "required_new_files": [
                            {
                                "path": "vibelign/commands/demo_helper.py",
                                "responsibility": "demo helper",
                            }
                        ],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "command wiring",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = cli_path.write_text(
                "# === ANCHOR: DEMO_CMD_START ===\n"
                + "\n".join([f"router.add_{i} = {i}" for i in range(40)])
                + "\n"
                "def register(parser):\n    parser.add_parser('demo')\n    parser.set_defaults(func=run_demo)\n"
                "# === ANCHOR: DEMO_CMD_END ===\n",
                encoding="utf-8",
            )
            _ = (commands_dir / "demo_helper.py").write_text(
                "def helper():\n    return True\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "pass")

    def test_config_touch_allowed_type_can_pass_in_mixed_change_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            claude_dir = root / ".claude"
            core_dir.mkdir(parents=True, exist_ok=True)
            claude_dir.mkdir(parents=True, exist_ok=True)
            auth_path = core_dir / "auth.py"
            settings_path = claude_dir / "settings.json"
            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                "def auth_handler():\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = settings_path.write_text("{}\n", encoding="utf-8")
            _commit_all(root, "baseline")

            plan_id = "plan_config_touch"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "auth and config touch",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path", "config_path"],
                            "new_file_paths": [],
                            "existing_file_paths": [
                                "vibelign/core/auth.py",
                                ".claude/settings.json",
                            ],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/auth.py",
                                "anchor": "AUTH_HANDLER",
                                "max_lines_added": 100,
                                "allowed_change_types": ["edit"],
                            },
                            {
                                "path": ".claude/settings.json",
                                "anchor": "SETTINGS_JSON",
                                "max_lines_added": 100,
                                "allowed_change_types": ["config_touch"],
                            },
                        ],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "auth and config touch",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = auth_path.write_text(
                "# === ANCHOR: AUTH_HANDLER_START ===\n"
                + "\n".join(f"    value_{i} = {i}" for i in range(25))
                + "\n"
                "def auth_handler():\n    import os\n    return True\n"
                "# === ANCHOR: AUTH_HANDLER_END ===\n",
                encoding="utf-8",
            )
            _ = settings_path.write_text(
                "{\n"
                + "\n".join([f'  "key{i}": {i},' for i in range(35)])
                + '\n  "hooks": {}\n}\n',
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            self.assertEqual(envelope["data"]["planning"]["status"], "pass")

    def test_mixed_production_and_docs_change_under_active_plan_is_deviation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            docs_dir = root / "docs"
            core_dir.mkdir(parents=True, exist_ok=True)
            docs_dir.mkdir(parents=True, exist_ok=True)
            watch_path = core_dir / "watch_engine.py"
            readme_path = docs_dir / "README.md"
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            _ = readme_path.write_text("hello\n", encoding="utf-8")
            _commit_all(root, "baseline")

            plan_id = "plan_watch_only"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "watch 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": [],
                            "existing_file_paths": ["vibelign/core/watch_engine.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/watch_engine.py",
                                "anchor": "WATCH_ENGINE",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    import os\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            _ = readme_path.write_text("hello\nworld\n", encoding="utf-8")

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "plan_exists_but_deviated")
            self.assertTrue(
                any(
                    "unexpected_change:docs/README.md" in str(item)
                    for item in cast(list[object], planning["deviations"])
                )
            )

    def test_config_threshold_can_disable_small_fix_exemption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_repo(root)
            _ = (root / ".vibelign" / "config.yaml").write_text(
                "schema_version: 1\nsmall_fix_line_threshold: 2\n",
                encoding="utf-8",
            )
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
                "def watch_engine():\n    import os\n    import sys\n    import json\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertNotIn(
                "small_single_file_fix",
                cast(list[object], planning["exempt_reasons"]),
            )

    def test_broken_plan_does_not_override_docs_only_exemption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            docs_dir = root / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)
            _ = (docs_dir / "README.md").write_text("hello\n", encoding="utf-8")
            _commit_all(root, "baseline")

            plan_id = "broken_docs"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                "{bad}\n", encoding="utf-8"
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "docs 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = (docs_dir / "README.md").write_text("hello\nworld\n", encoding="utf-8")

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn("docs_only", cast(list[object], planning["exempt_reasons"]))

    def test_broken_plan_does_not_override_tests_only_exemption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            tests_dir = root / "tests"
            tests_dir.mkdir(parents=True, exist_ok=True)
            _ = (tests_dir / "test_example.py").write_text(
                "def test_ok():\n    assert True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "broken_tests"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                "{bad}\n", encoding="utf-8"
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "tests 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = (tests_dir / "test_example.py").write_text(
                "def test_ok():\n    assert 1 == 1\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn("tests_only", cast(list[object], planning["exempt_reasons"]))
            self.assertIn("테스트만 수정", planning["summary"])

    def test_broken_plan_does_not_override_config_only_exemption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            _ = (root / "pyproject.toml").write_text(
                "[project]\nname='demo'\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "broken_config"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                "{bad}\n", encoding="utf-8"
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "config 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = (root / "pyproject.toml").write_text(
                "[project]\nname='demo'\nversion='0.1.0'\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn("config_only", cast(list[object], planning["exempt_reasons"]))
            self.assertIn("config만 수정", planning["summary"])

    def test_broken_plan_does_not_override_small_single_file_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
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

            plan_id = "broken_small_fix"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                "{bad}\n", encoding="utf-8"
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    import os\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn(
                "small_single_file_fix",
                cast(list[object], planning["exempt_reasons"]),
            )
            self.assertIn("소규모 단일 파일 수정", planning["summary"])

    def test_broken_plan_does_not_override_small_fix_in_staged_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
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

            plan_id = "broken_small_fix_staged"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                "{bad}\n", encoding="utf-8"
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    import os\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            _git(root, "add", "vibelign/core/watch_engine.py")
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    import os\n    import sys\n    import json\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn(
                "small_single_file_fix",
                cast(list[object], planning["exempt_reasons"]),
            )
            self.assertIn("소규모 단일 파일 수정", planning["summary"])

    def test_valid_plan_small_fix_inside_plan_is_still_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
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

            plan_id = "valid_small_fix_inside"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "watch 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": [],
                            "existing_file_paths": ["vibelign/core/watch_engine.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/watch_engine.py",
                                "anchor": "WATCH_ENGINE",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    import os\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn(
                "small_single_file_fix",
                cast(list[object], planning["exempt_reasons"]),
            )

    def test_valid_plan_small_fix_outside_plan_is_still_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta = self._init_repo(root)
            core_dir = root / "vibelign" / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            watch_path = core_dir / "watch_engine.py"
            other_path = core_dir / "other.py"
            _ = watch_path.write_text(
                "# === ANCHOR: WATCH_ENGINE_START ===\n"
                "def watch_engine():\n    return True\n"
                "# === ANCHOR: WATCH_ENGINE_END ===\n",
                encoding="utf-8",
            )
            _ = other_path.write_text(
                "def other():\n    return True\n", encoding="utf-8"
            )
            _commit_all(root, "baseline")

            plan_id = "valid_small_fix_outside"
            _ = (meta.plans_dir / f"{plan_id}.json").write_text(
                json.dumps(
                    {
                        "id": plan_id,
                        "schema_version": 1,
                        "feature": "watch 수정",
                        "created_at": "2026-04-09T00:00:00Z",
                        "mode": "rules",
                        "evidence": {
                            "required_reasons": ["multi_file_production_edit"]
                        },
                        "scope": {
                            "changed_path_classes": ["production_path"],
                            "new_file_paths": [],
                            "existing_file_paths": ["vibelign/core/watch_engine.py"],
                        },
                        "allowed_modifications": [
                            {
                                "path": "vibelign/core/watch_engine.py",
                                "anchor": "WATCH_ENGINE",
                                "max_lines_added": 20,
                                "allowed_change_types": ["edit"],
                            }
                        ],
                        "required_new_files": [],
                        "forbidden": [],
                        "messages": {"summary": "ok"},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = meta.state_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "planning": {
                            "active": True,
                            "plan_id": plan_id,
                            "feature": "watch 수정",
                            "override": False,
                            "override_reason": None,
                            "created_at": "2026-04-09T00:00:00Z",
                            "updated_at": "2026-04-09T00:00:00Z",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            _ = other_path.write_text(
                "def other():\n    return False\n", encoding="utf-8"
            )

            envelope = build_guard_envelope(root, strict=False, since_minutes=120)

            planning = envelope["data"]["planning"]
            self.assertEqual(planning["status"], "planning_exempt")
            self.assertIn(
                "small_single_file_fix",
                cast(list[object], planning["exempt_reasons"]),
            )


if __name__ == "__main__":
    unittest.main()
