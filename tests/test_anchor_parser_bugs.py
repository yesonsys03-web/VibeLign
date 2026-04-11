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
