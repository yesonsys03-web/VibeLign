import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import cast

import mcp.types as types

from vibelign.mcp_server import call_tool
from vibelign.core.local_checkpoints import list_checkpoints


class McpPatchApplyTest(unittest.TestCase):
    async def _call_tool_async(self, name: str, arguments: dict[str, object]) -> object:
        return await call_tool(name, arguments)

    def _call_tool(
        self, root: Path, name: str, arguments: dict[str, object]
    ) -> dict[str, object]:
        previous = Path.cwd()
        try:
            os.chdir(root)
            response = cast(
                list[types.TextContent],
                asyncio.run(self._call_tool_async(name, arguments)),
            )
        finally:
            os.chdir(previous)
        self.assertEqual(len(response), 1)
        return cast(dict[str, object], json.loads(response[0].text))

    def test_patch_apply_applies_filled_strict_patch_with_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "login_guard.py"
            target.write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            patch_payload = self._call_tool(
                root, "patch_get", {"request": "fix login guard"}
            )
            strict_patch = cast(dict[str, object], patch_payload["strict_patch"])
            operations = cast(list[dict[str, object]], strict_patch["operations"])
            operation = operations[0]
            operation["replace"] = str(operation["search"]).replace(
                "return True", "return False"
            )

            result = self._call_tool(
                root, "patch_apply", {"strict_patch": strict_patch}
            )

            self.assertTrue(result["ok"])
            self.assertIs(result.get("dry_run"), False)
            self.assertEqual(result["applied_operation_count"], 1)
            self.assertEqual(
                target.read_text(encoding="utf-8").count("return False"), 1
            )
            self.assertEqual(len(list_checkpoints(root)), 1)

    def test_patch_apply_dry_run_does_not_modify_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "login_guard.py"
            original = (
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n"
            )
            target.write_text(original, encoding="utf-8")

            patch_payload = self._call_tool(
                root, "patch_get", {"request": "fix login guard"}
            )
            strict_patch = cast(dict[str, object], patch_payload["strict_patch"])
            operations = cast(list[dict[str, object]], strict_patch["operations"])
            operation = operations[0]
            operation["replace"] = str(operation["search"]).replace(
                "return True", "return False"
            )

            result = self._call_tool(
                root,
                "patch_apply",
                {"strict_patch": strict_patch, "dry_run": True},
            )

            self.assertTrue(result["ok"])
            self.assertTrue(result.get("dry_run"))
            self.assertIsNone(result.get("checkpoint_id"))
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertEqual(len(list_checkpoints(root)), 0)

    def test_patch_apply_rejects_placeholder_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "login_guard.py"
            target.write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            patch_payload = self._call_tool(
                root, "patch_get", {"request": "fix login guard"}
            )
            strict_patch = cast(dict[str, object], patch_payload["strict_patch"])

            result = self._call_tool(
                root, "patch_apply", {"strict_patch": strict_patch}
            )

            self.assertFalse(result["ok"])
            self.assertIn("placeholder", cast(str, result["error"]))

    def test_patch_apply_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "login_guard.py"
            target.write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            patch_payload = self._call_tool(
                root, "patch_get", {"request": "fix login guard"}
            )
            strict_patch = cast(dict[str, object], patch_payload["strict_patch"])
            operations = cast(list[dict[str, object]], strict_patch["operations"])
            operation = operations[0]
            operation["target_file"] = "../outside.py"
            operation["replace"] = str(operation["search"]).replace(
                "return True", "return False"
            )

            result = self._call_tool(
                root, "patch_apply", {"strict_patch": strict_patch}
            )

            self.assertFalse(result["ok"])
            self.assertIn("허용되지 않은 대상 파일 경로", cast(str, result["error"]))

    def test_patch_apply_rejects_replace_without_anchor_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "login_guard.py"
            target.write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            patch_payload = self._call_tool(
                root, "patch_get", {"request": "fix login guard"}
            )
            strict_patch = cast(dict[str, object], patch_payload["strict_patch"])
            operations = cast(list[dict[str, object]], strict_patch["operations"])
            operations[0]["replace"] = "def login_guard():\n    return False\n"

            result = self._call_tool(
                root, "patch_apply", {"strict_patch": strict_patch}
            )

            self.assertFalse(result["ok"])
            self.assertIn("anchor START/END marker", cast(str, result["error"]))

    def test_patch_apply_rejects_search_anchor_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "login_guard.py"
            target.write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )

            patch_payload = self._call_tool(
                root, "patch_get", {"request": "fix login guard"}
            )
            strict_patch = cast(dict[str, object], patch_payload["strict_patch"])
            operations = cast(list[dict[str, object]], strict_patch["operations"])
            operation = operations[0]
            operation["search"] = str(operation["search"]).replace(
                "return True", "return Maybe"
            )
            operation["replace"] = str(operation["search"]).replace(
                "return Maybe", "return False"
            )

            result = self._call_tool(
                root, "patch_apply", {"strict_patch": strict_patch}
            )

            self.assertFalse(result["ok"])
            self.assertIn("현재 내용과 일치하지 않아요", cast(str, result["error"]))
