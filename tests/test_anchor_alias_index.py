"""anchor_meta.json aliases/description 필드 테스트."""
import json
import sys
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


def test_generate_code_based_aliases():
    """코드 기반으로 aliases/description이 생성되어야 한다."""
    from vibelign.core.anchor_tools import generate_code_based_aliases

    aliases, description = generate_code_based_aliases(
        "MAIN_WINDOW__APPLY_BTN_STYLE",
        "class ApplyButton:\n    def set_color(self, color): pass\n",
    )
    # 앵커 이름에서 토큰 추출
    assert any("apply" in a for a in aliases)
    # btn → button 약어 확장
    assert any("button" in a for a in aliases)
    assert description  # 빈 문자열이 아니어야


def test_reverse_aliases_do_not_import_patch_suggester():
    from vibelign.core.anchor_tools import _get_reverse_aliases

    sys.modules.pop("vibelign.core.patch_suggester", None)
    reverse_aliases = _get_reverse_aliases()

    assert "홈" in reverse_aliases["home"]
    assert "vibelign.core.patch_suggester" not in sys.modules


def test_token_alias_module_exposes_only_anchor_alias_api():
    import vibelign.core.token_aliases as token_aliases

    assert token_aliases.reverse_token_aliases()["home"] == ["홈", "홈화면", "메인화면"]
    assert not hasattr(token_aliases, "tokenize")
    assert not hasattr(token_aliases, "path_tokens")
    assert not hasattr(token_aliases, "intent_tokens")


def test_generate_code_based_intents_updates_existing(tmp_path):
    """코드 기반 생성은 기존 앵커도 갱신해야 한다."""
    from vibelign.core.anchor_tools import generate_code_based_intents

    src = tmp_path / "widget.py"
    src.write_text(
        '# === ANCHOR: WIDGET_RENDER_START ===\n'
        'def render_button(self): pass\n'
        '# === ANCHOR: WIDGET_RENDER_END ===\n',
        encoding="utf-8",
    )
    meta_dir = tmp_path / ".vibelign"
    meta_dir.mkdir()
    # 기존 intent만 있는 상태
    save_anchor_meta(tmp_path, {"WIDGET_RENDER": {"intent": "위젯 렌더링"}})

    count = generate_code_based_intents(tmp_path, [src])
    assert count >= 1
    meta = load_anchor_meta(tmp_path)
    entry = meta["WIDGET_RENDER"]
    assert "aliases" in entry
    # 기존 intent는 유지
    assert entry["intent"] == "위젯 렌더링"


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
