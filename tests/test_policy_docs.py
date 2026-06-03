from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_DOCS = (
    ROOT / "plans" / "VibeLign-멀티AI-기획CLI-설계안.md",
    ROOT / "plans" / "VibeLign-코알못UX-통합기획안.md",
    ROOT / "plans" / "spec-pr4-first-cli-persona-spike.md",
    ROOT / "plans" / "spec-pr5-multi-persona-routing.md",
)


def _policy_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in POLICY_DOCS)


def test_policy_docs_pin_official_cli_contract() -> None:
    text = _policy_text()

    assert "codex exec" in text
    assert "claude -p" in text
    assert "agy -p" in text
    assert "공식 CLI" in text
    assert "토큰/세션 파일" in text
    assert "--save-transcript" in text
    assert "앞선 페르소나 응답" in text
    assert "경쟁 모델 학습" in text


def test_policy_docs_remove_stale_antigravity_grey_area_language() -> None:
    text = _policy_text()
    stale_phrases = (
        "headless/print 계열",
        "<headless-or-print-flag>",
        "제3자 relay 회색지대",
        "선례 없는 회색지대",
        "이미 추가된 \"Third-Party AI CLI 고지\"",
    )

    for phrase in stale_phrases:
        assert phrase not in text
