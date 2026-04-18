import json
import tempfile
import unittest
from pathlib import Path

from vibelign.core.hook_setup import (
    ensure_claude_pretooluse_hook,
    get_claude_hook_status,
    set_claude_hook_enabled,
)


class HookSetupTest(unittest.TestCase):
    def test_install_merges_pretooluse_and_preserves_foreign_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_path = root / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            _ = settings_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Edit",
                                    "hooks": [
                                        {"type": "command", "command": "custom-hook"}
                                    ],
                                }
                            ]
                        }
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            result = ensure_claude_pretooluse_hook(root)

            self.assertEqual(result.status, "installed")
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            entries = payload["hooks"]["PreToolUse"]
            self.assertEqual(len(entries), 2)
            self.assertTrue(any(entry.get("matcher") == "Edit" for entry in entries))
            self.assertTrue(
                any(
                    hook.get("marker") == "vibelign-claude-pretooluse-v1"
                    for entry in entries
                    for hook in entry.get("hooks", [])
                )
            )

    def test_install_updates_existing_managed_entry_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_path = root / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            _ = settings_path.write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Write",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "old-command",
                                            "marker": "vibelign-claude-pretooluse-v1",
                                        }
                                    ],
                                }
                            ]
                        }
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            result = ensure_claude_pretooluse_hook(root)

            self.assertEqual(result.status, "updated")
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            entries = payload["hooks"]["PreToolUse"]
            self.assertEqual(len(entries), 1)
            self.assertNotEqual(entries[0]["hooks"][0]["command"], "old-command")

    def test_enable_disable_status_roundtrip_uses_config_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            set_claude_hook_enabled(root, False)
            disabled = get_claude_hook_status(root)
            self.assertEqual(disabled["enabled"], False)

            set_claude_hook_enabled(root, True)
            enabled = get_claude_hook_status(root)
            self.assertEqual(enabled["enabled"], True)

    def test_install_rejects_wrong_shaped_hooks_or_pretooluse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_path = root / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)

            _ = settings_path.write_text(
                json.dumps({"hooks": []}, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            result = ensure_claude_pretooluse_hook(root)
            self.assertEqual(result.status, "malformed-settings")
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["hooks"], [])

            _ = settings_path.write_text(
                json.dumps(
                    {"hooks": {"PreToolUse": {"matcher": "Write"}}},
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            result = ensure_claude_pretooluse_hook(root)
            self.assertEqual(result.status, "malformed-settings")
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            self.assertIsInstance(payload["hooks"]["PreToolUse"], dict)

    def test_install_collapses_duplicate_managed_entries_to_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            settings_path = root / ".claude" / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            managed = {
                "matcher": "Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": "old-command",
                        "marker": "vibelign-claude-pretooluse-v1",
                    }
                ],
            }
            foreign = {
                "matcher": "Edit",
                "hooks": [{"type": "command", "command": "custom-hook"}],
            }
            _ = settings_path.write_text(
                json.dumps(
                    {"hooks": {"PreToolUse": [managed, foreign, managed]}},
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            result = ensure_claude_pretooluse_hook(root)

            self.assertEqual(result.status, "updated")
            payload = json.loads(settings_path.read_text(encoding="utf-8"))
            entries = payload["hooks"]["PreToolUse"]
            managed_entries = [
                entry
                for entry in entries
                if any(
                    hook.get("marker") == "vibelign-claude-pretooluse-v1"
                    for hook in entry.get("hooks", [])
                )
            ]
            self.assertEqual(len(managed_entries), 1)
            self.assertTrue(any(entry.get("matcher") == "Edit" for entry in entries))


if __name__ == "__main__":
    unittest.main()
