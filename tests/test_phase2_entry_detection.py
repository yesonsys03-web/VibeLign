import tempfile
import unittest
from pathlib import Path
from typing import TypedDict, cast

from vibelign.core.doctor_v2 import build_doctor_envelope
from vibelign.core.watch_rules import classify_event


class DoctorIssue(TypedDict, total=False):
    path: str | None
    category: str


class Phase2EntryDetectionTest(unittest.TestCase):
    def test_watch_rules_treats_vib_cli_as_entry_file(self) -> None:
        warnings = classify_event(
            Path("vib_cli.py"),
            "#\n" * 250,
            old_lines=50,
            new_lines=250,
            strict=False,
        )

        messages = " ".join(item["message"] for item in warnings)
        self.assertIn("vib_cli.py", messages)

    def test_watch_rules_treats_mcp_server_as_entry_file(self) -> None:
        warnings = classify_event(
            Path("mcp_server.py"),
            "#\n" * 250,
            old_lines=50,
            new_lines=250,
            strict=False,
        )

        messages = " ".join(item["message"] for item in warnings)
        self.assertIn("mcp_server.py", messages)

    def test_doctor_flags_real_entry_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _ = (root / "vib_cli.py").write_text(
                "import subprocess\n" * 250, encoding="utf-8"
            )
            _ = (root / "mcp_server.py").write_text(
                "import subprocess\n" * 250, encoding="utf-8"
            )

            envelope = build_doctor_envelope(root, strict=False)

        data = cast(dict[str, object], envelope["data"])
        issues_obj = cast(list[object], data["issues"])
        self.assertIsInstance(issues_obj, list)
        paths = {
            str(issue.get("path"))
            for item in issues_obj
            if isinstance(item, dict)
            for issue in [cast(DoctorIssue, cast(object, item))]
            if issue.get("category") == "structure"
        }
        self.assertIn("vib_cli.py", paths)
        self.assertIn("mcp_server.py", paths)


if __name__ == "__main__":
    _ = unittest.main()
