import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import cast

import mcp.types as types

from vibelign.mcp_server import call_tool


class McpPatchSessionTest(unittest.TestCase):
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

    def test_lazy_fanout_persists_patch_session_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            login = root / "login_guard.py"
            login.write_text(
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_START ===\n"
                "def login_guard():\n    return True\n"
                "# === ANCHOR: LOGIN_GUARD_LOGIN_GUARD_END ===\n",
                encoding="utf-8",
            )
            progress = root / "progress_bar.py"
            progress.write_text(
                "# === ANCHOR: PROGRESS_BAR_PROGRESS_BAR_START ===\n"
                "def progress_bar():\n    return True\n"
                "# === ANCHOR: PROGRESS_BAR_PROGRESS_BAR_END ===\n",
                encoding="utf-8",
            )

            payload = self._call_tool(
                root,
                "patch_get",
                {
                    "request": "fix login guard 그리고 progress bar 추가해줘",
                    "lazy_fanout": True,
                },
            )

            session = cast(dict[str, object], payload.get("session"))
            self.assertTrue(session)
            self.assertEqual(session.get("needs_verification"), False)
            self.assertTrue(session.get("session_id"))
            self.assertTrue(session.get("pending_sub_intents"))
            state_path = root / ".vibelign/state.json"
            self.assertTrue(state_path.exists())
            state = cast(
                dict[str, object], json.loads(state_path.read_text(encoding="utf-8"))
            )
            stored = cast(dict[str, object], state["patch_session"])
            self.assertEqual(stored.get("session_id"), session.get("session_id"))
            self.assertEqual(
                stored.get("pending_sub_intents"), session.get("pending_sub_intents")
            )

    def test_patch_apply_sets_verification_gate_and_guard_clears_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            meta_dir = root / ".vibelign"
            meta_dir.mkdir(parents=True, exist_ok=True)
            state_path = meta_dir / "state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "patch_session": {
                            "session_id": "seed-session",
                            "active": True,
                            "needs_verification": False,
                            "pending_sub_intents": [],
                        }
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

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
            operation = cast(list[dict[str, object]], strict_patch["operations"])[0]
            operation["replace"] = str(operation["search"]).replace(
                "return True", "return False"
            )

            apply_result = self._call_tool(
                root, "patch_apply", {"strict_patch": strict_patch}
            )
            self.assertTrue(apply_result["ok"])
            state_after_apply = cast(
                dict[str, object], json.loads(state_path.read_text(encoding="utf-8"))
            )
            session_after_apply = cast(
                dict[str, object], state_after_apply["patch_session"]
            )
            self.assertTrue(session_after_apply.get("needs_verification"))
            self.assertIsNotNone(session_after_apply.get("last_applied_at"))

            guard_result = self._call_tool(root, "guard_check", {"strict": False})
            self.assertTrue(guard_result["ok"])
            state_after_guard = cast(
                dict[str, object], json.loads(state_path.read_text(encoding="utf-8"))
            )
            session_after_guard = cast(
                dict[str, object], state_after_guard["patch_session"]
            )
            self.assertFalse(session_after_guard.get("needs_verification"))
            self.assertIsNotNone(session_after_guard.get("verified_at"))


if __name__ == "__main__":
    unittest.main()
