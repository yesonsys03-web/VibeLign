import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vibelign.core.anchor_tools import (
    build_symbol_anchor_name,
    collect_anchor_index,
    insert_js_symbol_anchors,
    insert_module_anchors,
    insert_python_symbol_anchors,
    preview_anchor_targets,
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

    def test_preview_anchor_targets_uses_opt_in_rust_project_scan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "sample.py"
            path.write_text("print('hello')\n", encoding="utf-8")

            with patch.dict("os.environ", {"VIBELIGN_PROJECT_SCAN_RUST": "1"}, clear=False), patch(
                "vibelign.core.project_scan.scan_project_with_rust",
                return_value=(
                    {
                        "result": "project_scan",
                        "files": [
                            {"path": "sample.py", "category": "other", "imports": []},
                        ],
                    },
                    None,
                ),
            ) as rust_scan:
                targets = preview_anchor_targets(root)

        self.assertEqual(targets, [path])
        rust_scan.assert_called_once_with(root)

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
        from vibelign.core.anchor_tools import build_anchor_name

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
            from vibelign.core.anchor_tools import extract_anchors

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

    def test_insert_js_symbol_anchors_ignores_braces_in_strings(self):
        # 문자열 안의 '}' 가 naive 카운터를 속여 END 앵커가 본문 중간에 박히던 버그.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.tsx"
            path.write_text(
                'export function Foo() {\n'
                '  const msg = "close brace: }";\n'
                '  return msg;\n'
                '}\n',
                encoding="utf-8",
            )
            self.assertTrue(insert_js_symbol_anchors(path))
            out = path.read_text(encoding="utf-8").splitlines()
            end_idx = next(i for i, ln in enumerate(out) if "FOO_END" in ln)
            # END 앵커 바로 위 줄은 함수 닫는 '}' 여야 한다(본문 중간 금지).
            self.assertEqual(out[end_idx - 1].strip(), "}")
            body_idx = next(i for i, ln in enumerate(out) if "return msg;" in ln)
            self.assertLess(body_idx, end_idx)

    def test_insert_js_symbol_anchors_jsx_end_after_close_brace(self):
        # JSX 반환 컴포넌트(템플릿 리터럴 포함)의 END 앵커는 } 뒤에 와야 한다.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Modal.tsx"
            path.write_text(
                "export function Modal() {\n"
                "  const label = `n=${count}`;\n"
                "  return (\n"
                "    <div>\n"
                "      <button>{label}</button>\n"
                "      닫기\n"
                "    </div>\n"
                "  );\n"
                "}\n",
                encoding="utf-8",
            )
            self.assertTrue(insert_js_symbol_anchors(path))
            out = path.read_text(encoding="utf-8").splitlines()
            end_idx = next(i for i, ln in enumerate(out) if "MODAL_END" in ln)
            self.assertEqual(out[end_idx - 1].strip(), "}")
            # '닫기' JSX 텍스트는 END 앵커보다 위에 있어야 한다(텍스트 안에 박히면 안 됨).
            close_idx = next(i for i, ln in enumerate(out) if "닫기" in ln)
            self.assertLess(close_idx, end_idx)

    def test_insert_js_symbol_anchors_nested_arrow_keeps_outer_end_after_brace(self):
        # 함수 본문 안의 const 화살표(핸들러) 마커가 바깥 함수의 END 위치를 밀면 안 된다.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Panel.tsx"
            path.write_text(
                "export function Panel() {\n"
                "  const onClick = () => {\n"
                "    doThing();\n"
                "  };\n"
                "  return <button onClick={onClick}>닫기</button>;\n"
                "}\n",
                encoding="utf-8",
            )
            self.assertTrue(insert_js_symbol_anchors(path))
            out = path.read_text(encoding="utf-8").splitlines()
            outer_end = next(
                i for i, ln in enumerate(out) if "PANEL_PANEL_END" in ln
            )
            # 바깥 함수 END 앵커 바로 위는 함수 닫는 '}'.
            self.assertEqual(out[outer_end - 1].strip(), "}")
            # 안쪽 화살표 END 앵커도 존재하고 바깥 END 보다 위에 있어야 한다.
            inner_end = next(i for i, ln in enumerate(out) if "PANEL_ONCLICK_END" in ln)
            self.assertLess(inner_end, outer_end)


if __name__ == "__main__":
    unittest.main()
