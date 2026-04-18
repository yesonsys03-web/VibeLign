from pathlib import Path
from unittest.mock import MagicMock

from vibelign.core.anchor_tools import extract_anchors, extract_anchor_spans
from vibelign.core.patch_suggester import PatchSuggestion


def _write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


class TestBug2PhantomSpans:
    def test_inline_mention_in_docstring_is_not_an_anchor(self, tmp_path: Path) -> None:
        text = '''"""
        Respect anchor boundaries (`ANCHOR: NAME_START` / `ANCHOR: NAME_END`)
        """

        # === ANCHOR: REAL_ONE_START ===
        x = 1
        # === ANCHOR: REAL_ONE_END ===
        '''
        p = _write(tmp_path, "mod.py", text)
        assert extract_anchors(p) == ["REAL_ONE"]
        spans = extract_anchor_spans(p)
        assert [s["name"] for s in spans] == ["REAL_ONE"]

    def test_inline_mention_in_line_comment_is_not_an_anchor(self, tmp_path: Path) -> None:
        text = (
            "# format: /abs/path/file.py:ANCHOR: FOO_START\n"
            "# === ANCHOR: REAL_TWO_START ===\n"
            "y = 2\n"
            "# === ANCHOR: REAL_TWO_END ===\n"
        )
        p = _write(tmp_path, "mod2.py", text)
        assert extract_anchors(p) == ["REAL_TWO"]
        spans = extract_anchor_spans(p)
        assert [s["name"] for s in spans] == ["REAL_TWO"]


class TestBug4DunderPreserved:
    def test_extract_anchors_preserves_dunder_suffix(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: CLI_BASE___INIT___START ===\n"
            "pass\n"
            "# === ANCHOR: CLI_BASE___INIT___END ===\n"
        )
        p = _write(tmp_path, "cli_base.py", text)
        assert extract_anchors(p) == ["CLI_BASE___INIT__"]

    def test_extract_anchor_spans_preserves_dunder_suffix(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: CLI_BASE___INIT___START ===\n"
            "pass\n"
            "# === ANCHOR: CLI_BASE___INIT___END ===\n"
        )
        p = _write(tmp_path, "cli_base.py", text)
        spans = extract_anchor_spans(p)
        assert len(spans) == 1
        assert spans[0]["name"] == "CLI_BASE___INIT__"
        assert spans[0]["start"] == 1
        assert spans[0]["end"] == 3


class TestBug3DanglingStartDropped:
    def test_unterminated_start_is_not_returned(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: GOOD_START ===\n"
            "ok = 1\n"
            "# === ANCHOR: GOOD_END ===\n"
            "\n"
            "# === ANCHOR: DANGLING_START ===\n"
            "oops = 2\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        names = [s["name"] for s in spans]
        assert names == ["GOOD"]
        assert all(s["end"] is not None for s in spans)


class TestBug1DuplicateNamesSuffixed:
    def test_duplicate_spans_get_numeric_suffix(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: DUP_START ===\n"
            "first = 1\n"
            "# === ANCHOR: DUP_END ===\n"
            "\n"
            "# === ANCHOR: DUP_START ===\n"
            "second = 2\n"
            "# === ANCHOR: DUP_END ===\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        names = [s["name"] for s in spans]
        assert names == ["DUP", "DUP_2"]
        assert spans[0]["start"] == 1 and spans[0]["end"] == 3
        assert spans[1]["start"] == 5 and spans[1]["end"] == 7


class TestSignatureExtraction:
    def test_python_def_signature(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: MY_FUNC_START ===\n"
            "def my_func(a: int, b: str) -> bool:\n"
            "    return True\n"
            "# === ANCHOR: MY_FUNC_END ===\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        assert len(spans) == 1
        assert spans[0]["signature"] == "def my_func(a: int, b: str) -> bool:"

    def test_python_class_signature(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: MY_CLASS_START ===\n"
            "class MyClass(BaseModel):\n"
            "    pass\n"
            "# === ANCHOR: MY_CLASS_END ===\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        assert spans[0]["signature"] == "class MyClass(BaseModel):"

    def test_js_function_signature(self, tmp_path: Path) -> None:
        text = (
            "// === ANCHOR: HANDLER_START ===\n"
            "export async function handleRequest(req, res) {\n"
            "  return res.json({});\n"
            "}\n"
            "// === ANCHOR: HANDLER_END ===\n"
        )
        p = _write(tmp_path, "handler.ts", text)
        spans = extract_anchor_spans(p)
        assert spans[0]["signature"] == "export async function handleRequest(req, res) {"

    def test_const_arrow_signature(self, tmp_path: Path) -> None:
        text = (
            "// === ANCHOR: COMP_START ===\n"
            "const MyComponent = () => {\n"
            "  return <div/>;\n"
            "};\n"
            "// === ANCHOR: COMP_END ===\n"
        )
        p = _write(tmp_path, "comp.tsx", text)
        spans = extract_anchor_spans(p)
        assert spans[0]["signature"] == "const MyComponent = () => {"

    def test_no_signature_for_config_block(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: CONFIG_START ===\n"
            "MAX_RETRIES = 3\n"
            "TIMEOUT = 30\n"
            "# === ANCHOR: CONFIG_END ===\n"
        )
        p = _write(tmp_path, "config.py", text)
        spans = extract_anchor_spans(p)
        assert "signature" not in spans[0]

    def test_signature_within_5_lines(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: DELAYED_START ===\n"
            "# some comment\n"
            "# another comment\n"
            "# yet another\n"
            "def delayed_func():\n"
            "    pass\n"
            "# === ANCHOR: DELAYED_END ===\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        assert spans[0]["signature"] == "def delayed_func():"

    def test_signature_beyond_5_lines_not_found(self, tmp_path: Path) -> None:
        text = (
            "# === ANCHOR: FAR_START ===\n"
            "# 1\n"
            "# 2\n"
            "# 3\n"
            "# 4\n"
            "# 5\n"
            "def too_far():\n"
            "    pass\n"
            "# === ANCHOR: FAR_END ===\n"
        )
        p = _write(tmp_path, "mod.py", text)
        spans = extract_anchor_spans(p)
        assert "signature" not in spans[0]


class TestPatchSuggestionAnchorSpanFields:
    def test_default_fields_are_none(self) -> None:
        s = PatchSuggestion("req", "file.py", "ANCHOR", "high", ["reason"])
        assert s.anchor_start_line is None
        assert s.anchor_end_line is None
        assert s.anchor_signature is None

    def test_to_dict_includes_span_fields(self) -> None:
        s = PatchSuggestion(
            "req", "file.py", "ANCHOR", "high", ["reason"],
            anchor_start_line=10, anchor_end_line=20,
            anchor_signature="def foo():",
        )
        d = s.to_dict()
        assert d["anchor_start_line"] == 10
        assert d["anchor_end_line"] == 20
        assert d["anchor_signature"] == "def foo():"
