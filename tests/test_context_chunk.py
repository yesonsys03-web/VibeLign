import tempfile
import unittest
from pathlib import Path

from vibelign.core.context_chunk import fetch_anchor_context_window


class ContextChunkTest(unittest.TestCase):
    def test_python_prepends_module_preamble_when_anchor_far_below(self) -> None:
        filler = "\n".join([f"# filler line {i}" for i in range(80)])
        content = (
            '"""Module doc."""\n'
            "import os\n"
            "import sys\n"
            "\n"
            "X = 1\n"
            "\n"
            "def shallow():\n"
            "    return 0\n"
            "\n"
            f"{filler}\n"
            "\n"
            "# === ANCHOR: DEEP_START ===\n"
            "def deep():\n"
            "    return 1\n"
            "# === ANCHOR: DEEP_END ===\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mod.py"
            path.write_text(content, encoding="utf-8")
            out = fetch_anchor_context_window(path, "DEEP", pad_before=5, pad_after=3)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertIn("import os", out)
        self.assertIn("def deep():", out)
        self.assertIn("vibelign: module preamble", out)

    def test_python_ast_ignores_fake_def_inside_docstring(self) -> None:
        filler = "\n".join([f"# filler line {i}" for i in range(70)])
        content = (
            '"""Docstring with a fake def line.\n'
            "def fake_helper():\n"
            "    return 'not real code'\n"
            '"""\n'
            "import os\n"
            "VALUE = 1\n"
            "\n"
            f"{filler}\n"
            "\n"
            "# === ANCHOR: REAL_START ===\n"
            "def real_helper():\n"
            "    return os.name\n"
            "# === ANCHOR: REAL_END ===\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ast_docstring.py"
            path.write_text(content, encoding="utf-8")
            out = fetch_anchor_context_window(path, "REAL", pad_before=4, pad_after=3)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertIn("import os", out)
        self.assertIn("VALUE = 1", out)
        self.assertIn("def real_helper()", out)

    def test_python_no_duplicate_preamble_when_window_starts_at_top(self) -> None:
        content = (
            "# === ANCHOR: TOP_START ===\n"
            "def top():\n"
            "    return 0\n"
            "# === ANCHOR: TOP_END ===\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "top.py"
            path.write_text(content, encoding="utf-8")
            out = fetch_anchor_context_window(path, "TOP", pad_before=20, pad_after=5)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out.count("vibelign: module preamble"), 0)

    def test_py_prefix_max_lines_zero_skips_preamble(self) -> None:
        filler = "\n".join([f"# row {i}" for i in range(60)])
        content = (
            "import json\n"
            f"{filler}\n"
            "# === ANCHOR: FAR_START ===\n"
            "y = 2\n"
            "# === ANCHOR: FAR_END ===\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "far.py"
            path.write_text(content, encoding="utf-8")
            out = fetch_anchor_context_window(
                path, "FAR", pad_before=3, pad_after=2, py_prefix_max_lines=0
            )
        self.assertIsNotNone(out)
        assert out is not None
        self.assertNotIn("import json", out)
        self.assertIn("y = 2", out)

    def test_tsx_prepends_import_preamble_when_anchor_far_below(self) -> None:
        filler = "\n".join([f"// filler {i}" for i in range(80)])
        content = (
            'import React from "react";\n'
            "\n"
            "export function Shallow() {\n"
            "  return null;\n"
            "}\n"
            "\n"
            f"{filler}\n"
            "\n"
            "// === ANCHOR: DEEP_START ===\n"
            "export function Deep() {\n"
            "  return null;\n"
            "}\n"
            "// === ANCHOR: DEEP_END ===\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Mod.tsx"
            path.write_text(content, encoding="utf-8")
            out = fetch_anchor_context_window(path, "DEEP", pad_before=5, pad_after=4)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertIn('import React from "react"', out)
        self.assertIn("export function Deep()", out)
        self.assertIn("vibelign: module preamble", out)

    def test_tsx_no_preamble_when_window_covers_file_top(self) -> None:
        content = (
            "// === ANCHOR: TOP_START ===\n"
            "export function Top() { return null; }\n"
            "// === ANCHOR: TOP_END ===\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Top.tsx"
            path.write_text(content, encoding="utf-8")
            out = fetch_anchor_context_window(path, "TOP", pad_before=15, pad_after=6)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out.count("vibelign: module preamble"), 0)

    def test_js_ts_prefix_max_lines_zero_skips_preamble(self) -> None:
        filler = "\n".join([f"// x{i}" for i in range(50)])
        content = (
            "import fs from 'fs';\n"
            f"{filler}\n"
            "// === ANCHOR: FAR_START ===\n"
            "export const y = 2;\n"
            "// === ANCHOR: FAR_END ===\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "far.ts"
            path.write_text(content, encoding="utf-8")
            out = fetch_anchor_context_window(
                path, "FAR", pad_before=2, pad_after=2, js_ts_prefix_max_lines=0
            )
        self.assertIsNotNone(out)
        assert out is not None
        self.assertNotIn("import fs", out)
        self.assertIn("export const y", out)


if __name__ == "__main__":
    unittest.main()
