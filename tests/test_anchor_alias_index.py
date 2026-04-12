"""anchor_meta.json aliases/description 필드 테스트."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch as mock_patch
from vibelign.core.anchor_tools import (
    AnchorMetaEntry,
    load_anchor_meta,
    save_anchor_meta,
    set_anchor_intent,
)


def test_anchor_meta_entry_has_aliases_and_description():
    """AnchorMetaEntry에 aliases와 description 필드가 있어야 한다."""
    entry: AnchorMetaEntry = {
        "intent": "버튼 스타일 설정",
        "aliases": ["전체적용 버튼", "apply button", "변환 버튼"],
        "description": "전체적용/변환 실행 버튼의 색상과 스타일을 정의",
    }
    assert entry["aliases"] == ["전체적용 버튼", "apply button", "변환 버튼"]
    assert entry["description"] == "전체적용/변환 실행 버튼의 색상과 스타일을 정의"


def test_load_anchor_meta_parses_aliases(tmp_path):
    """anchor_meta.json에서 aliases/description을 파싱해야 한다."""
    meta_dir = tmp_path / ".vibelign"
    meta_dir.mkdir()
    data = {
        "MAIN_WINDOW__APPLY_BTN_STYLE": {
            "intent": "버튼 스타일",
            "aliases": ["전체적용 버튼", "apply button"],
            "description": "전체적용 버튼의 색상과 스타일",
        }
    }
    (meta_dir / "anchor_meta.json").write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )
    loaded = load_anchor_meta(tmp_path)
    entry = loaded["MAIN_WINDOW__APPLY_BTN_STYLE"]
    assert entry["aliases"] == ["전체적용 버튼", "apply button"]
    assert entry["description"] == "전체적용 버튼의 색상과 스타일"


def test_set_anchor_intent_with_aliases(tmp_path):
    """set_anchor_intent로 aliases/description을 저장할 수 있어야 한다."""
    meta_dir = tmp_path / ".vibelign"
    meta_dir.mkdir()
    (meta_dir / "anchor_meta.json").write_text("{}", encoding="utf-8")
    set_anchor_intent(
        tmp_path,
        "MY_ANCHOR",
        intent="버튼 렌더링",
        aliases=["적용 버튼", "apply btn"],
        description="적용 버튼 렌더링 로직",
    )
    loaded = load_anchor_meta(tmp_path)
    assert loaded["MY_ANCHOR"]["aliases"] == ["적용 버튼", "apply btn"]
    assert loaded["MY_ANCHOR"]["description"] == "적용 버튼 렌더링 로직"


def test_generate_anchor_intents_produces_aliases(tmp_path):
    """generate_anchor_intents_with_ai가 aliases/description도 생성해야 한다."""
    from vibelign.core.anchor_tools import generate_anchor_intents_with_ai

    src = tmp_path / "main_window.py"
    src.write_text(
        '# === ANCHOR: MAIN_WINDOW__APPLY_BTN_STYLE_START ===\n'
        'class ApplyButton:\n'
        '    def set_color(self, color): self.style = color\n'
        '# === ANCHOR: MAIN_WINDOW__APPLY_BTN_STYLE_END ===\n',
        encoding="utf-8",
    )
    meta_dir = tmp_path / ".vibelign"
    meta_dir.mkdir()
    (meta_dir / "anchor_meta.json").write_text("{}", encoding="utf-8")

    ai_response = json.dumps([
        {
            "anchor": "MAIN_WINDOW__APPLY_BTN_STYLE",
            "intent": "적용 버튼 색상 설정",
            "aliases": ["전체적용 버튼", "apply button", "적용 버튼 스타일"],
            "description": "전체적용/변환 실행 버튼의 색상과 스타일을 정의하는 구역",
        }
    ], ensure_ascii=False)

    with mock_patch(
        "vibelign.core.ai_explain.generate_text_with_ai",
        return_value=(ai_response, []),
    ), mock_patch(
        "vibelign.core.ai_explain.has_ai_provider",
        return_value=True,
    ):
        count = generate_anchor_intents_with_ai(tmp_path, [src])

    assert count >= 1
    meta = load_anchor_meta(tmp_path)
    entry = meta.get("MAIN_WINDOW__APPLY_BTN_STYLE", {})
    assert "aliases" in entry
    assert len(entry["aliases"]) >= 1
    assert "description" in entry


def test_choose_anchor_matches_korean_alias():
    """한국어 alias가 있으면 영어 앵커명과 한국어 요청이 매칭되어야 한다."""
    from vibelign.core.patch_suggester import choose_anchor, tokenize

    anchors = [
        "MAIN_WINDOW__SHOW_HELP_DIALOG",
        "MAIN_WINDOW__APPLY_BTN_STYLE",
        "MAIN_WINDOW__MENU_BAR",
    ]
    request_tokens = tokenize("전체적용 버튼 컬러 녹색으로 수정해줘")
    anchor_meta = {
        "MAIN_WINDOW__SHOW_HELP_DIALOG": {
            "intent": "도움말 대화상자 표시",
        },
        "MAIN_WINDOW__APPLY_BTN_STYLE": {
            "intent": "버튼 스타일",
            "aliases": ["전체적용 버튼", "apply button", "적용 버튼 스타일"],
            "description": "전체적용 버튼의 색상과 스타일",
        },
        "MAIN_WINDOW__MENU_BAR": {
            "intent": "메뉴바 구성",
        },
    }
    chosen, rationale = choose_anchor(anchors, request_tokens, anchor_meta)
    assert chosen == "MAIN_WINDOW__APPLY_BTN_STYLE"
    assert any("별칭" in r for r in rationale)


def test_choose_anchor_without_alias_falls_back():
    """alias 없으면 기존 intent 매칭 로직으로 폴백해야 한다."""
    from vibelign.core.patch_suggester import choose_anchor, tokenize

    anchors = ["SECTION_A", "SECTION_B"]
    request_tokens = tokenize("로그인 폼 수정")
    anchor_meta = {
        "SECTION_A": {"intent": "로그인 폼 렌더링"},
        "SECTION_B": {"intent": "회원가입 폼"},
    }
    chosen, _ = choose_anchor(anchors, request_tokens, anchor_meta)
    assert chosen == "SECTION_A"


def test_score_path_boosts_file_with_alias_match(tmp_path):
    """aliases가 있는 앵커를 포함한 파일의 점수가 올라야 한다."""
    from vibelign.core.patch_suggester import score_path, tokenize

    target = tmp_path / "gui" / "main_window.py"
    target.parent.mkdir(parents=True)
    target.write_text("# dummy", encoding="utf-8")

    request_tokens = tokenize("전체적용 버튼 컬러 수정")
    intent_meta = {
        "MAIN_WINDOW__APPLY_BTN_STYLE": {
            "intent": "버튼 스타일",
            "aliases": ["전체적용 버튼", "apply button"],
            "description": "전체적용 버튼의 색상과 스타일",
        },
        "MAIN_WINDOW__SHOW_HELP": {
            "intent": "도움말 표시",
        },
    }
    anchor_meta = {
        "anchors": ["MAIN_WINDOW__APPLY_BTN_STYLE", "MAIN_WINDOW__SHOW_HELP"],
        "suggested_anchors": [],
    }

    score_with_alias, _ = score_path(
        target,
        request_tokens,
        "gui/main_window.py",
        anchor_meta=anchor_meta,
        intent_meta=intent_meta,
    )

    intent_meta_no_alias = {
        "MAIN_WINDOW__APPLY_BTN_STYLE": {"intent": "버튼 스타일"},
        "MAIN_WINDOW__SHOW_HELP": {"intent": "도움말 표시"},
    }
    score_without_alias, _ = score_path(
        target,
        request_tokens,
        "gui/main_window.py",
        anchor_meta=anchor_meta,
        intent_meta=intent_meta_no_alias,
    )

    assert score_with_alias > score_without_alias


def test_execute_add_anchor_generates_aliases(tmp_path):
    """add_anchor 액션 실행 후 aliases/description이 자동 생성되어야 한다."""
    from vibelign.action_engine.executors.action_executor import _execute_add_anchor
    from vibelign.action_engine.models.action import Action

    src = tmp_path / "main_window.py"
    src.write_text(
        "class MainWindow:\n"
        "    def apply_btn_click(self):\n"
        "        self.color = 'blue'\n",
        encoding="utf-8",
    )
    meta_dir = tmp_path / ".vibelign"
    meta_dir.mkdir()
    (meta_dir / "anchor_meta.json").write_text("{}", encoding="utf-8")

    action = Action(
        action_type="add_anchor",
        description="앵커 추가",
        target_path="main_window.py",
        command=None,
        depends_on=[],
    )

    ai_response = json.dumps([
        {
            "anchor": "MAIN_WINDOW_APPLY_BTN_CLICK",
            "intent": "적용 버튼 클릭 처리",
            "aliases": ["적용 버튼", "apply button click"],
            "description": "적용 버튼 클릭 시 색상 변경",
        }
    ], ensure_ascii=False)

    with mock_patch(
        "vibelign.core.ai_explain.generate_text_with_ai",
        return_value=(ai_response, []),
    ), mock_patch(
        "vibelign.core.ai_explain.has_ai_provider",
        return_value=True,
    ):
        result = _execute_add_anchor(action, tmp_path)

    assert result.status == "done"
    meta = load_anchor_meta(tmp_path)
    has_aliases = any("aliases" in entry for entry in meta.values())
    assert has_aliases
