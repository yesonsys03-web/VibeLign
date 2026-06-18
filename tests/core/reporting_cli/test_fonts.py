from vibelign.core.reporting_cli.fonts import FONTS_DIR, REPORT_FONTS, font_def


def test_registry_has_five_fonts():
    assert set(REPORT_FONTS) == {
        "pretendard", "nanum-myeongjo", "gowun-batang", "gowun-dodum", "black-han-sans",
    }


def test_every_registered_face_file_exists_and_is_woff2():
    for fdef in REPORT_FONTS.values():
        for face in fdef.faces:
            path = FONTS_DIR / face.file
            assert path.exists(), f"missing {path}"
            assert path.read_bytes()[:4] == b"wOF2", f"not woff2: {path}"


def test_font_def_unknown_returns_none():
    assert font_def("nope") is None
    assert font_def("pretendard").office_name == "Pretendard"
