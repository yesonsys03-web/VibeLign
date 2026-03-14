import tempfile
import unittest
from pathlib import Path

from vibeguard.core.doctor_v2 import build_doctor_envelope


class VibDoctorV2Test(unittest.TestCase):
    def test_doctor_envelope_contains_score_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.py").write_text("print('hello')\n" * 90, encoding="utf-8")
            (root / "ui_panel.py").write_text(
                "def render():\n    return 'ui'\n", encoding="utf-8"
            )

            envelope = build_doctor_envelope(root, strict=False)

            self.assertTrue(envelope["ok"])
            data = envelope["data"]
            self.assertIn("project_score", data)
            self.assertIn("anchor_coverage", data)
            self.assertTrue(0 <= data["project_score"] <= 100)
            self.assertIn(
                data["status"], {"Safe", "Good", "Caution", "Risky", "High Risk"}
            )


if __name__ == "__main__":
    unittest.main()
