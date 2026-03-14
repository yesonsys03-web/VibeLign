import tempfile
import unittest
from pathlib import Path

from vibeguard.core.anchor_tools import (
    build_symbol_anchor_name,
    collect_anchor_index,
    insert_js_symbol_anchors,
    insert_module_anchors,
    insert_python_symbol_anchors,
    validate_anchor_file,
)


class AnchorToolsV2Test(unittest.TestCase):
    def test_validate_anchor_file_detects_missing_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("print('hello')\n", encoding="utf-8")
            problems = validate_anchor_file(path)
            self.assertIn("앵커가 없습니다", problems)

    def test_collect_anchor_index_after_insert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "sample.py"
            path.write_text("print('hello')\n", encoding="utf-8")
            self.assertTrue(insert_module_anchors(path))
            index = collect_anchor_index(root)
            self.assertIn("sample.py", index)
            self.assertTrue(index["sample.py"])

    def test_insert_module_anchors_preserves_shebang(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tool.py"
            path.write_text(
                "#!/usr/bin/env python3\nprint('hello')\n", encoding="utf-8"
            )
            self.assertTrue(insert_module_anchors(path))
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "#!/usr/bin/env python3")
            self.assertIn("ANCHOR:", "\n".join(lines[1:]))

    def test_build_anchor_name_normalizes_dots(self):
        from vibeguard.core.anchor_tools import build_anchor_name

        self.assertEqual(build_anchor_name(Path("foo.test.py")), "FOO_TEST")

    def test_insert_python_symbol_anchors_adds_function_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(
                "def render_progress_bar():\n    return True\n", encoding="utf-8"
            )
            self.assertTrue(insert_python_symbol_anchors(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("ANCHOR: SAMPLE_RENDER_PROGRESS_BAR_START", text)
            self.assertIn("ANCHOR: SAMPLE_RENDER_PROGRESS_BAR_END", text)

    def test_insert_module_anchors_keeps_symbol_anchor_and_module_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text("def login():\n    return True\n", encoding="utf-8")
            self.assertTrue(insert_module_anchors(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("ANCHOR: SAMPLE_START", text)
            self.assertIn("ANCHOR: SAMPLE_END", text)
            self.assertIn(
                f"ANCHOR: {build_symbol_anchor_name(path, 'login')}_START",
                text,
            )

    def test_extract_anchors_returns_base_names_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.py"
            path.write_text(
                "# === ANCHOR: SAMPLE_START ===\n# === ANCHOR: SAMPLE_LOGIN_START ===\n# === ANCHOR: SAMPLE_LOGIN_END ===\n# === ANCHOR: SAMPLE_END ===\n",
                encoding="utf-8",
            )
            from vibeguard.core.anchor_tools import extract_anchors

            anchors = extract_anchors(path)
            self.assertIn("SAMPLE", anchors)
            self.assertIn("SAMPLE_LOGIN", anchors)
            self.assertNotIn("SAMPLE_START", anchors)

    def test_insert_js_symbol_anchors_adds_function_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.ts"
            path.write_text(
                "export function renderProgressBar() {\n  return true;\n}\n",
                encoding="utf-8",
            )
            self.assertTrue(insert_js_symbol_anchors(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("ANCHOR: SAMPLE_RENDERPROGRESSBAR_START", text)
            self.assertIn("ANCHOR: SAMPLE_RENDERPROGRESSBAR_END", text)

    def test_insert_module_anchors_keeps_js_symbol_anchor_and_module_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.ts"
            path.write_text(
                "export class LoginPanel {\n  render() {\n    return true;\n  }\n}\n",
                encoding="utf-8",
            )
            self.assertTrue(insert_module_anchors(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("ANCHOR: SAMPLE_START", text)
            self.assertIn("ANCHOR: SAMPLE_END", text)
            self.assertIn(
                f"ANCHOR: {build_symbol_anchor_name(path, 'LoginPanel')}_START",
                text,
            )

    def test_insert_js_symbol_anchors_supports_brace_on_next_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.ts"
            path.write_text(
                "export function renderProgressBar()\n{\n  return true;\n}\n",
                encoding="utf-8",
            )
            self.assertTrue(insert_js_symbol_anchors(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("ANCHOR: SAMPLE_RENDERPROGRESSBAR_START", text)
            self.assertIn("ANCHOR: SAMPLE_RENDERPROGRESSBAR_END", text)

    def test_insert_js_symbol_anchors_handles_one_line_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.ts"
            path.write_text(
                "export function ping() { return true; }\nconst after = 1;\n",
                encoding="utf-8",
            )
            self.assertTrue(insert_js_symbol_anchors(path))
            text = path.read_text(encoding="utf-8")
            self.assertIn("ANCHOR: SAMPLE_PING_START", text)
            self.assertIn("ANCHOR: SAMPLE_PING_END", text)
            self.assertIn("const after = 1;", text)

    def test_insert_js_symbol_anchors_skips_braceless_expression_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.ts"
            path.write_text(
                "const ping = () => true;\nconst after = 1;\n",
                encoding="utf-8",
            )
            self.assertFalse(insert_js_symbol_anchors(path))


if __name__ == "__main__":
    unittest.main()
