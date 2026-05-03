import os
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from vibelign.commands.vib_mcp_cmd import run_vib_mcp_command
from vibelign.core.memory.capability_grants import (
    is_capability_granted,
    load_capability_grants,
)


class VibMcpGrantCommandTest(unittest.TestCase):
    def test_vib_mcp_grant_writes_future_capability_grant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                result = run_vib_mcp_command(
                    Namespace(mcp_action="grant", capability="recovery_apply", tool="claude")
                )
                root = Path(tmp)
                grants = load_capability_grants(root)
                granted = is_capability_granted(root, "claude", "recovery_apply")
            finally:
                os.chdir(previous)

        self.assertEqual(result, 0)
        self.assertEqual(len(grants), 1)
        self.assertTrue(granted)

    def test_vib_mcp_grant_rejects_default_allowed_capability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                result = run_vib_mcp_command(
                    Namespace(mcp_action="grant", capability="memory_summary_read", tool="claude")
                )
                grants = load_capability_grants(Path(tmp))
            finally:
                os.chdir(previous)

        self.assertEqual(result, 2)
        self.assertEqual(grants, [])

    def test_vib_mcp_grant_rejects_unknown_capability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                result = run_vib_mcp_command(
                    Namespace(mcp_action="grant", capability="unknown_capability", tool="claude")
                )
                grants = load_capability_grants(Path(tmp))
            finally:
                os.chdir(previous)

        self.assertEqual(result, 2)
        self.assertEqual(grants, [])

    def test_vib_mcp_grant_rejects_invalid_tool_label_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            output = StringIO()
            try:
                with redirect_stdout(output):
                    result = run_vib_mcp_command(
                        Namespace(mcp_action="grant", capability="recovery_apply", tool="///")
                    )
                grants = load_capability_grants(Path(tmp))
            finally:
                os.chdir(previous)

        self.assertEqual(result, 2)
        self.assertEqual(grants, [])
        self.assertIn("MCP tool name is required", output.getvalue())

    def test_vib_mcp_grants_prints_empty_state_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            output = StringIO()
            try:
                with redirect_stdout(output):
                    result = run_vib_mcp_command(Namespace(mcp_action="grants"))
                grant_path = Path(tmp) / ".vibelign" / "mcp_capability_grants.json"
            finally:
                os.chdir(previous)

        self.assertEqual(result, 0)
        self.assertIn("No MCP capability grants", output.getvalue())
        self.assertFalse(grant_path.exists())

    def test_vib_mcp_grants_prints_existing_grants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            output = StringIO()
            try:
                _ = run_vib_mcp_command(
                    Namespace(mcp_action="grant", capability="recovery_apply", tool="claude")
                )
                with redirect_stdout(output):
                    result = run_vib_mcp_command(Namespace(mcp_action="grants"))
            finally:
                os.chdir(previous)

        self.assertEqual(result, 0)
        self.assertIn("MCP capability grants", output.getvalue())
        self.assertIn("recovery_apply", output.getvalue())
        self.assertIn("claude", output.getvalue())

    def test_vib_mcp_revoke_removes_existing_grant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            output = StringIO()
            try:
                _ = run_vib_mcp_command(
                    Namespace(mcp_action="grant", capability="recovery_apply", tool="claude")
                )
                with redirect_stdout(output):
                    result = run_vib_mcp_command(
                        Namespace(mcp_action="revoke", capability="recovery_apply", tool="claude")
                    )
                grants = load_capability_grants(Path(tmp))
            finally:
                os.chdir(previous)

        self.assertEqual(result, 0)
        self.assertEqual(grants, [])
        self.assertIn("revoked", output.getvalue())

    def test_vib_mcp_revoke_missing_grant_is_safe_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            output = StringIO()
            try:
                with redirect_stdout(output):
                    result = run_vib_mcp_command(
                        Namespace(mcp_action="revoke", capability="recovery_apply", tool="claude")
                    )
                grants = load_capability_grants(Path(tmp))
            finally:
                os.chdir(previous)

        self.assertEqual(result, 0)
        self.assertEqual(grants, [])
        self.assertIn("No MCP capability grant matched", output.getvalue())


if __name__ == "__main__":
    _ = unittest.main()
