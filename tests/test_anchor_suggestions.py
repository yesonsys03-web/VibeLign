import tempfile
import unittest
from pathlib import Path

from vibeguard.core.anchor_tools import suggest_anchor_names


class AnchorSuggestionsTest(unittest.TestCase):
    def test_python_symbols_become_suggested_anchor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(
                "class LoginService:\n    pass\n\ndef render_progress_bar():\n    return True\n",
                encoding="utf-8",
            )
            names = suggest_anchor_names(path)
            self.assertIn("LOGINSERVICE", names)
            self.assertIn("RENDER_PROGRESS_BAR", names)


if __name__ == "__main__":
    unittest.main()
