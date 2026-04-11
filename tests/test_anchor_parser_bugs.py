from pathlib import Path

from vibelign.core.anchor_tools import extract_anchors, extract_anchor_spans


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
