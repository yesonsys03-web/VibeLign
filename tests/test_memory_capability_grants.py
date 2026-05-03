import json
import tempfile
import unittest
from pathlib import Path

from vibelign.core.memory.capability_grants import (
    add_capability_grant,
    capability_grants_path,
    is_capability_granted,
    load_capability_grants,
    revoke_capability_grant,
)


class MemoryCapabilityGrantsTest(unittest.TestCase):
    def test_missing_grant_store_defaults_to_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertFalse(is_capability_granted(root, "claude", "recovery_apply"))
            self.assertEqual(load_capability_grants(root), [])

    def test_matching_project_tool_and_capability_grant_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            grant_path = capability_grants_path(root)
            grant_path.parent.mkdir(parents=True)
            _ = grant_path.write_text(
                json.dumps(
                    {
                        "grants": [
                            {
                                "grant_id": "grant_test",
                                "tool": "claude",
                                "capability": "memory_full_read",
                                "status": "granted",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(is_capability_granted(root, "claude", "memory_full_read"))
            self.assertFalse(is_capability_granted(root, "cursor", "memory_full_read"))
            self.assertFalse(is_capability_granted(root, "claude", "recovery_apply"))

    def test_malformed_grant_store_defaults_to_denied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            grant_path = capability_grants_path(root)
            grant_path.parent.mkdir(parents=True)
            _ = grant_path.write_text("not-json", encoding="utf-8")

            self.assertEqual(load_capability_grants(root), [])
            self.assertFalse(is_capability_granted(root, "claude", "memory_write"))

    def test_non_granted_statuses_are_ignored_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            grant_path = capability_grants_path(root)
            grant_path.parent.mkdir(parents=True)
            _ = grant_path.write_text(
                json.dumps(
                    {
                        "grants": [
                            {
                                "grant_id": "grant_revoked",
                                "tool": "claude",
                                "capability": "memory_write",
                                "status": "revoked",
                            },
                            {
                                "grant_id": "grant_pending",
                                "tool": "claude",
                                "capability": "handoff_export",
                                "status": "pending",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(load_capability_grants(root), [])
            self.assertFalse(is_capability_granted(root, "claude", "memory_write"))
            self.assertFalse(is_capability_granted(root, "claude", "handoff_export"))

    def test_add_capability_grant_writes_single_stable_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            first = add_capability_grant(root, "claude", "recovery_apply")
            second = add_capability_grant(root, "claude", "recovery_apply")
            grants = load_capability_grants(root)

        self.assertEqual(first, second)
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0].tool, "claude")
        self.assertEqual(grants[0].capability, "recovery_apply")

    def test_revoke_capability_grant_removes_only_matching_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = add_capability_grant(root, "claude", "recovery_apply")
            _ = add_capability_grant(root, "cursor", "memory_full_read")

            removed = revoke_capability_grant(root, "claude", "recovery_apply")
            grants = load_capability_grants(root)

        self.assertTrue(removed)
        self.assertFalse(is_capability_granted(root, "claude", "recovery_apply"))
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0].tool, "cursor")
        self.assertEqual(grants[0].capability, "memory_full_read")

    def test_revoke_missing_capability_grant_is_safe_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            removed = revoke_capability_grant(root, "claude", "recovery_apply")
            grants = load_capability_grants(root)

        self.assertFalse(removed)
        self.assertEqual(grants, [])


if __name__ == "__main__":
    _ = unittest.main()
