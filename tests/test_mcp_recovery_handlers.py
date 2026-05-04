import json
import importlib
import asyncio
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, cast
from unittest import mock

from vibelign.core.memory.capability_grants import add_capability_grant
from vibelign.core.recovery.models import (
    DriftCandidate,
    IntentZoneEntry,
    RecoveryOption,
    RecoveryPlan,
    RecoverySignalSet,
)
from vibelign.mcp.mcp_dispatch import call_tool_dispatch


@dataclass
class TextContent:
    type: str
    text: str


recovery_handlers = importlib.import_module("vibelign.mcp.mcp_recovery_handlers")
handle_recovery_preview = cast(
    Callable[[Path, dict[str, object], type[TextContent]], list[object]],
    recovery_handlers.handle_recovery_preview,
)


class McpRecoveryHandlersTest(unittest.TestCase):
    def test_recovery_preview_returns_read_only_plan_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = RecoveryPlan(
                plan_id="rec_test",
                mode="read_only",
                level=1,
                summary="Preview only",
                options=[RecoveryOption(option_id="opt_test", level=1, label="Explain only")],
                no_files_modified=True,
            )
            with mock.patch(
                "vibelign.mcp.mcp_recovery_handlers.collect_basic_signals",
                return_value=RecoverySignalSet(changed_paths=["src/app.py"]),
            ) as collect_mock:
                with mock.patch(
                    "vibelign.mcp.mcp_recovery_handlers.build_recovery_plan",
                    return_value=plan,
                ) as plan_mock:
                    result = handle_recovery_preview(root, {}, TextContent)
            payload = cast(dict[str, object], json.loads(cast(TextContent, result[0]).text))
            plan_payload = cast(dict[str, object], payload["plan"])
            options_payload = cast(list[dict[str, object]], plan_payload["options"])

        collect_mock.assert_called_once_with(root)
        plan_mock.assert_called_once()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["provenance"], "recovery_planner_preview")
        self.assertEqual(plan_payload["mode"], "read_only")
        self.assertTrue(plan_payload["no_files_modified"])
        self.assertEqual(options_payload[0]["option_id"], "opt_test")

    def test_recovery_preview_writes_audit_without_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = RecoveryPlan(
                plan_id="rec_test",
                mode="read_only",
                level=0,
                summary="No changes",
            )
            with mock.patch(
                "vibelign.mcp.mcp_recovery_handlers.collect_basic_signals",
                return_value=RecoverySignalSet(),
            ):
                with mock.patch(
                    "vibelign.mcp.mcp_recovery_handlers.build_recovery_plan",
                    return_value=plan,
                ):
                    _ = handle_recovery_preview(root, {}, TextContent)
            audit_text = (root / ".vibelign" / "memory_audit.jsonl").read_text(encoding="utf-8")

        self.assertIn("recovery_preview", audit_text)
        self.assertFalse((root / ".vibelign" / "state.json").exists())

    def test_recovery_preview_audit_records_path_counts_not_raw_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = RecoveryPlan(
                plan_id="rec_test",
                mode="read_only",
                level=1,
                summary="Preview paths",
                intent_zone=[
                    IntentZoneEntry(path="src/app.py", source="explicit", reason="explicit relevant file"),
                    IntentZoneEntry(path="src/ui.py", source="diff_fallback", reason="raw diff"),
                ],
                drift_candidates=[
                    DriftCandidate(path="src/auth.py", why_outside_zone="outside intent zone"),
                ],
            )
            with mock.patch(
                "vibelign.mcp.mcp_recovery_handlers.collect_basic_signals",
                return_value=RecoverySignalSet(),
            ):
                with mock.patch(
                    "vibelign.mcp.mcp_recovery_handlers.build_recovery_plan",
                    return_value=plan,
                ):
                    _ = handle_recovery_preview(root, {}, TextContent)
            audit_payload = cast(
                dict[str, object],
                json.loads((root / ".vibelign" / "memory_audit.jsonl").read_text(encoding="utf-8")),
            )

        self.assertEqual(audit_payload["paths_count"], {"in_zone": 2, "drift": 1, "total": 3})
        self.assertNotIn("src/app.py", json.dumps(audit_payload, sort_keys=True))
        self.assertNotIn("src/auth.py", json.dumps(audit_payload, sort_keys=True))

    def test_recovery_apply_executes_only_with_grant_and_feature_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "src").mkdir(parents=True)
            _ = (root / "src" / "app.py").write_text("broken\n", encoding="utf-8")
            _ = add_capability_grant(root, "claude", "recovery_apply")
            with mock.patch.dict("os.environ", {"VIBELIGN_RECOVERY_APPLY": "true"}, clear=False), mock.patch(
                "vibelign.core.recovery.apply._restore_files",
                return_value=1,
            ) as restore_mock:
                result = asyncio.run(
                    call_tool_dispatch(
                        "recovery_apply",
                        {
                            "tool": "claude",
                            "checkpoint_id": "ckpt_before",
                            "sandwich_checkpoint_id": "ckpt_safety",
                            "paths": ["src/app.py"],
                            "preview_paths": ["src/app.py"],
                            "confirmation": "APPLY ckpt_before",
                            "apply": True,
                        },
                        root=root,
                        text_content=TextContent,
                    )
                )
            payload = cast(dict[str, object], json.loads(cast(TextContent, result[0]).text))

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["capability"], "recovery_apply")
        self.assertEqual(payload["changed_files_count"], 1)
        self.assertEqual(payload["changed_files"], ["src/app.py"])
        self.assertEqual(payload["safety_checkpoint_id"], "ckpt_safety")
        self.assertTrue(payload["would_apply"])
        restore_mock.assert_called_once_with(root, "ckpt_before", ["src/app.py"])

    def test_recovery_apply_env_feature_gate_executes_without_raw_path_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "src").mkdir(parents=True)
            _ = (root / "src" / "app.py").write_text("broken\n", encoding="utf-8")
            _ = add_capability_grant(root, "claude", "recovery_apply")
            with mock.patch.dict("os.environ", {"VIBELIGN_RECOVERY_APPLY": "true"}, clear=False), mock.patch(
                "vibelign.core.recovery.apply._restore_files",
                return_value=1,
            ):
                result = asyncio.run(
                    call_tool_dispatch(
                        "recovery_apply",
                        {
                            "tool": "claude",
                            "checkpoint_id": "ckpt_before",
                            "sandwich_checkpoint_id": "ckpt_safety",
                            "paths": ["src/app.py"],
                            "preview_paths": ["src/app.py"],
                            "confirmation": "APPLY ckpt_before",
                            "apply": True,
                        },
                        root=root,
                        text_content=TextContent,
                    )
                )
            payload = cast(dict[str, object], json.loads(cast(TextContent, result[0]).text))
            audit_text = (root / ".vibelign" / "memory_audit.jsonl").read_text(encoding="utf-8")
            audit_payload = cast(dict[str, object], json.loads(audit_text))

        self.assertTrue(payload["ok"])
        self.assertEqual(audit_payload["event"], "recovery_apply")
        self.assertEqual(audit_payload["paths_count"], {"drift": 0, "in_zone": 1, "total": 1})
        self.assertNotIn("src/app.py", audit_text)

    def test_recovery_preview_payload_includes_live_p0_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_recovery_preview(root, {}, TextContent)
            payload = cast(dict[str, object], json.loads(cast(TextContent, result[0]).text))
            plan = cast(dict[str, object], payload["plan"])
            p0_summaries = cast(list[dict[str, object]], payload["p0_summaries"])

        self.assertEqual(plan["circuit_breaker_state"], "active")
        self.assertTrue(any(item["slo_id"] == "stale_intent" for item in p0_summaries))
        self.assertTrue(any(item["slo_id"] == "drift_label" for item in p0_summaries))

    def test_recovery_apply_with_grant_but_without_feature_stays_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = add_capability_grant(root, "claude", "recovery_apply")
            result = asyncio.run(
                call_tool_dispatch(
                    "recovery_apply",
                    {"tool": "claude"},
                    root=root,
                    text_content=TextContent,
                )
            )
            payload = cast(dict[str, object], json.loads(cast(TextContent, result[0]).text))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "permission_denied")
        self.assertEqual(payload["grant_status"], "granted_but_not_enabled")

    def test_recovery_apply_argument_cannot_bypass_env_feature_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = add_capability_grant(root, "claude", "recovery_apply")
            result = asyncio.run(
                call_tool_dispatch(
                    "recovery_apply",
                    {"tool": "claude", "feature_enabled": True},
                    root=root,
                    text_content=TextContent,
                )
            )
            payload = cast(dict[str, object], json.loads(cast(TextContent, result[0]).text))

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"], "permission_denied")
        self.assertEqual(payload["grant_status"], "granted_but_not_enabled")


if __name__ == "__main__":
    _ = unittest.main()
