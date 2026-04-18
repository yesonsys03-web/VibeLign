# Anchor Alias Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** anchor_meta.json에 aliases/description 필드를 추가하여 한국어 요청 ↔ 영어 앵커명 매핑 정확도를 높인다.

**Architecture:** 기존 `anchor_meta.json`의 `AnchorMetaEntry`에 `aliases`(list[str])와 `description`(str) 필드를 추가한다. `vib anchor --auto-intent` 실행 시 AI가 코드 스니펫을 보고 aliases/description을 자동 생성한다. `doctor --apply`의 `add_anchor` 액션 실행 후에도 삽입된 앵커에 대해 자동 생성한다. `choose_anchor`와 `score_path`에서 aliases를 키워드 매칭 풀에 포함시켜 앵커 선택 정확도를 높인다.

**Tech Stack:** Python 3.12, TypedDict, AI prompt (generate_text_with_ai)

---

## File Structure

| 파일 | 역할 | 변경 종류 |
|------|------|-----------|
| `vibelign/core/anchor_tools.py` | AnchorMetaEntry 타입 확장, AI 생성 함수 수정 | Modify |
| `vibelign/core/patch_suggester.py` | choose_anchor/score_path에서 aliases 활용 | Modify |
| `vibelign/action_engine/executors/action_executor.py` | add_anchor 후 aliases 자동 생성 | Modify |
| `tests/test_anchor_alias_index.py` | aliases/description 생성·저장·매칭 테스트 | Create |

---

### Task 1: AnchorMetaEntry 타입 확장 + 저장/로드

**Files:**
- Modify: `vibelign/core/anchor_tools.py:33-36` (AnchorMetaEntry TypedDict)
- Modify: `vibelign/core/anchor_tools.py:575-591` (load_anchor_meta 파싱)
- Modify: `vibelign/core/anchor_tools.py:613-630` (set_anchor_intent에 aliases/description 파라미터)
- Test: `tests/test_anchor_alias_index.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_anchor_alias_index.py
"""anchor_meta.json aliases/description 필드 테스트."""
import json
import pytest
from pathlib import Path
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py -v`
Expected: FAIL — `aliases` not in AnchorMetaEntry, `set_anchor_intent` doesn't accept aliases/description params

- [ ] **Step 3: Extend AnchorMetaEntry TypedDict**

`vibelign/core/anchor_tools.py:33-36`에서:

```python
class AnchorMetaEntry(TypedDict, total=False):
    intent: str
    connects: list[str]
    warning: str
    aliases: list[str]
    description: str
```

- [ ] **Step 4: Update load_anchor_meta to parse aliases/description**

`vibelign/core/anchor_tools.py` — `load_anchor_meta` 함수의 정규화 루프 안에 추가:

```python
        # 기존 intent, connects, warning 파싱 뒤에 추가
        aliases = _normalize_string_list(entry.get("aliases"))
        if aliases:
            meta_entry["aliases"] = aliases
        description = entry.get("description")
        if isinstance(description, str):
            meta_entry["description"] = description
```

- [ ] **Step 5: Update set_anchor_intent to accept aliases/description**

`vibelign/core/anchor_tools.py` — `set_anchor_intent` 시그니처에 파라미터 추가:

```python
def set_anchor_intent(
    root: Path,
    anchor_name: str,
    intent: str,
    connects: list[str] | None = None,
    warning: str | None = None,
    aliases: list[str] | None = None,
    description: str | None = None,
) -> None:
    """특정 앵커에 의도(intent) 정보를 저장한다."""
    data = load_anchor_meta(root)
    entry = data.get(anchor_name, {})
    entry["intent"] = intent
    if connects is not None:
        entry["connects"] = connects
    if warning is not None:
        entry["warning"] = warning
    if aliases is not None:
        entry["aliases"] = aliases
    if description is not None:
        entry["description"] = description
    data[anchor_name] = entry
    save_anchor_meta(root, data)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py -v`
Expected: 3 PASSED

- [ ] **Step 7: Commit**

```bash
git add vibelign/core/anchor_tools.py tests/test_anchor_alias_index.py
git commit -m "feat(anchor): add aliases/description fields to AnchorMetaEntry"
```

---

### Task 2: AI 자동 생성 — aliases/description 포함

**Files:**
- Modify: `vibelign/core/anchor_tools.py:697-738` (generate_anchor_intents_with_ai)
- Test: `tests/test_anchor_alias_index.py` (추가 테스트)

- [ ] **Step 1: Write the failing test**

`tests/test_anchor_alias_index.py`에 추가:

```python
from unittest.mock import patch


def test_generate_anchor_intents_produces_aliases(tmp_path):
    """generate_anchor_intents_with_ai가 aliases/description도 생성해야 한다."""
    from vibelign.core.anchor_tools import (
        generate_anchor_intents_with_ai,
        insert_module_anchors,
        load_anchor_meta,
    )

    # 앵커가 있는 파일 생성
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

    # AI 응답을 모킹: intent + aliases + description을 JSON으로 반환
    ai_response = json.dumps([
        {
            "anchor": "MAIN_WINDOW__APPLY_BTN_STYLE",
            "intent": "적용 버튼 색상 설정",
            "aliases": ["전체적용 버튼", "apply button", "적용 버튼 스타일"],
            "description": "전체적용/변환 실행 버튼의 색상과 스타일을 정의하는 구역",
        }
    ], ensure_ascii=False)

    with patch(
        "vibelign.core.anchor_tools.generate_text_with_ai",
        return_value=(ai_response, []),
    ), patch(
        "vibelign.core.anchor_tools.has_ai_provider",
        return_value=True,
    ):
        count = generate_anchor_intents_with_ai(tmp_path, [src])

    assert count >= 1
    meta = load_anchor_meta(tmp_path)
    entry = meta.get("MAIN_WINDOW__APPLY_BTN_STYLE", {})
    assert "aliases" in entry
    assert len(entry["aliases"]) >= 1
    assert "description" in entry
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py::test_generate_anchor_intents_produces_aliases -v`
Expected: FAIL — 현재 generate_anchor_intents_with_ai는 intent만 파싱

- [ ] **Step 3: Rewrite generate_anchor_intents_with_ai**

`vibelign/core/anchor_tools.py`의 `generate_anchor_intents_with_ai` 함수를 수정. AI 프롬프트를 JSON 배열 출력으로 변경하고, aliases/description도 파싱:

```python
def generate_anchor_intents_with_ai(root: Path, paths: list[Path]) -> int:
    """AI를 사용해 anchor intent/aliases/description을 자동 생성하고 저장. 반환: 등록된 intent 수"""
    from vibelign.core.ai_explain import generate_text_with_ai, has_ai_provider

    if not has_ai_provider():
        return 0
    existing = load_anchor_meta(root)
    all_blocks: dict[str, str] = {}
    for path in paths:
        for anchor, code in extract_anchor_blocks(path).items():
            if anchor not in existing:
                all_blocks[anchor] = code[:400]
    if not all_blocks:
        return 0
    numbered = "\n\n".join(
        f"[{i + 1}] {name}\n{code}" for i, (name, code) in enumerate(all_blocks.items())
    )
    prompt = (
        "다음은 코드 파일의 각 구역(앵커)입니다.\n"
        "각 구역에 대해 JSON 배열로 출력하세요. 다른 말은 하지 마세요.\n\n"
        "각 항목 형식:\n"
        '{"anchor": "앵커이름", "intent": "한 줄 설명(10~20자)", '
        '"aliases": ["한국어 별칭1", "영어 별칭", ...], '
        '"description": "이 구역이 하는 일을 한 문장으로"}\n\n'
        "aliases 규칙:\n"
        "- 사용자가 이 구역을 수정하고 싶을 때 쓸 법한 한국어/영어 표현 2~5개\n"
        "- 코드 속 변수명, 클래스명, UI 요소명을 자연어로 풀어서 포함\n"
        "- 예: APPLY_BTN_STYLE → ['전체적용 버튼', 'apply button', '적용 버튼 스타일']\n\n"
        + numbered
    )
    text, _ = generate_text_with_ai(prompt, quiet=True)
    if not text:
        return 0
    # JSON 배열 파싱 시도
    anchor_list = list(all_blocks.keys())
    count = 0
    try:
        # JSON 블록 추출 (```json ... ``` 또는 bare JSON)
        json_text = text.strip()
        if "```" in json_text:
            start = json_text.find("[")
            end = json_text.rfind("]") + 1
            if start >= 0 and end > start:
                json_text = json_text[start:end]
        items = json.loads(json_text)
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                anchor_name = item.get("anchor", "")
                if anchor_name not in all_blocks:
                    continue
                intent = item.get("intent", "")
                aliases = item.get("aliases")
                description = item.get("description")
                if not intent:
                    continue
                set_anchor_intent(
                    root,
                    anchor_name,
                    intent,
                    aliases=aliases if isinstance(aliases, list) else None,
                    description=description if isinstance(description, str) else None,
                )
                count += 1
    except (json.JSONDecodeError, ValueError):
        # JSON 파싱 실패 시 기존 [번호] 형식 폴백
        parsed: dict[str, str] = {}
        parts = re.split(r"\[(\d+)\]", text)
        i = 1
        while i + 1 < len(parts):
            idx = int(parts[i]) - 1
            val = parts[i + 1].strip().splitlines()[0].strip()
            if 0 <= idx < len(anchor_list) and val:
                parsed[anchor_list[idx]] = val
            i += 2
        for anchor, intent in parsed.items():
            set_anchor_intent(root, anchor, intent)
            count += 1
    return count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py -v`
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/anchor_tools.py tests/test_anchor_alias_index.py
git commit -m "feat(anchor): AI generates aliases/description for anchor intents"
```

---

### Task 3: choose_anchor에서 aliases 활용

**Files:**
- Modify: `vibelign/core/patch_suggester.py:978-1062` (choose_anchor 함수)
- Test: `tests/test_anchor_alias_index.py` (추가 테스트)

- [ ] **Step 1: Write the failing test**

`tests/test_anchor_alias_index.py`에 추가:

```python
from vibelign.core.patch_suggester import choose_anchor, tokenize


def test_choose_anchor_matches_korean_alias():
    """한국어 alias가 있으면 영어 앵커명과 한국어 요청이 매칭되어야 한다."""
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
    assert any("alias" in r or "별칭" in r for r in rationale)


def test_choose_anchor_without_alias_falls_back():
    """alias 없으면 기존 intent 매칭 로직으로 폴백해야 한다."""
    anchors = ["SECTION_A", "SECTION_B"]
    request_tokens = tokenize("로그인 폼 수정")
    anchor_meta = {
        "SECTION_A": {"intent": "로그인 폼 렌더링"},
        "SECTION_B": {"intent": "회원가입 폼"},
    }
    chosen, _ = choose_anchor(anchors, request_tokens, anchor_meta)
    assert chosen == "SECTION_A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py::test_choose_anchor_matches_korean_alias -v`
Expected: FAIL — choose_anchor가 aliases를 보지 않아서 APPLY_BTN_STYLE을 선택하지 못함

- [ ] **Step 3: Add alias scoring to choose_anchor**

`vibelign/core/patch_suggester.py`의 `choose_anchor` 함수, intent 매칭 블록 뒤에 (약 1046행 뒤) aliases 매칭 추가:

```python
        # intent 정보가 있으면 자연어 매칭 점수 추가
        if anchor_meta and anchor in anchor_meta:
            meta = anchor_meta[anchor]
            intent = meta.get("intent", "").lower()
            if intent:
                # ... 기존 intent 매칭 로직 ...
                pass
            # aliases 매칭 — 한국어 요청 ↔ 영어 앵커 격차 보완
            anchor_aliases = meta.get("aliases")
            if isinstance(anchor_aliases, list):
                for alias in anchor_aliases:
                    if not isinstance(alias, str):
                        continue
                    alias_tokens = _intent_tokens(alias)
                    alias_matches = _meaningful_overlap(request_tokens, alias_tokens)
                    for token in alias_matches:
                        score += 5
                        rationale.append(f"앵커 별칭('{alias}')에 키워드 '{token}'이 포함됨")
            # description 매칭
            desc = meta.get("description", "")
            if isinstance(desc, str) and desc:
                desc_tokens = _intent_tokens(desc)
                desc_matches = _meaningful_overlap(request_tokens, desc_tokens)
                for token in desc_matches:
                    score += 3
                    rationale.append(f"앵커 설명에 키워드 '{token}'이 포함됨")
            warning = meta.get("warning")
            # ... 기존 warning 로직 ...
```

구체적으로, `choose_anchor` 함수의 기존 `if anchor_meta and anchor in anchor_meta:` 블록 안에서 `warning = meta.get("warning")` 줄 **바로 위에** aliases/description 매칭 코드를 삽입:

```python
            # aliases 매칭 — 한국어 요청 ↔ 영어 앵커 격차 보완
            anchor_aliases = meta.get("aliases")
            if isinstance(anchor_aliases, list):
                for alias in anchor_aliases:
                    if not isinstance(alias, str):
                        continue
                    alias_tokens = _intent_tokens(alias)
                    alias_matches = _meaningful_overlap(request_tokens, alias_tokens)
                    for token in alias_matches:
                        score += 5
                        rationale.append(f"앵커 별칭('{alias}')에 키워드 '{token}'이 포함됨")
            # description 매칭
            desc = meta.get("description", "")
            if isinstance(desc, str) and desc:
                desc_tokens = _intent_tokens(desc)
                desc_matches = _meaningful_overlap(request_tokens, desc_tokens)
                for token in desc_matches:
                    score += 3
                    rationale.append(f"앵커 설명에 키워드 '{token}'이 포함됨")
```

alias 매칭 점수는 **5점** (intent의 4점보다 높음) — aliases는 사용자가 쓸 법한 정확한 표현이므로 신뢰도가 높기 때문.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py -v`
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/patch_suggester.py tests/test_anchor_alias_index.py
git commit -m "feat(patch): use anchor aliases for keyword matching in choose_anchor"
```

---

### Task 4: score_path에서 aliases 활용 (파일 선택 개선)

**Files:**
- Modify: `vibelign/core/patch_suggester.py:672-727` (score_path의 intent_meta 매칭)
- Test: `tests/test_anchor_alias_index.py` (추가 테스트)

- [ ] **Step 1: Write the failing test**

`tests/test_anchor_alias_index.py`에 추가:

```python
from vibelign.core.patch_suggester import score_path


def test_score_path_boosts_file_with_alias_match(tmp_path):
    """aliases가 있는 앵커를 포함한 파일의 점수가 올라야 한다."""
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

    score_with_alias, rationale = score_path(
        target,
        request_tokens,
        "gui/main_window.py",
        anchor_meta=anchor_meta,
        intent_meta=intent_meta,
    )

    # aliases 없는 버전과 비교
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py::test_score_path_boosts_file_with_alias_match -v`
Expected: FAIL — score_path가 aliases를 읽지 않음

- [ ] **Step 3: Add alias scoring to score_path**

`vibelign/core/patch_suggester.py`의 `score_path` 함수, `intent_meta` 매칭 블록(약 685-727행) 안에서 `intent` 매칭 뒤에 aliases/description 매칭을 추가:

기존 `if best_anchor_name is not None:` 블록 뒤, `return score, rationale` 전에:

```python
    # aliases/description에서 추가 매칭 (파일 레벨)
    if isinstance(intent_meta, dict):
        file_anchors = (
            set(anchor_meta.get("anchors", []))
            if isinstance(anchor_meta, dict)
            else set()
        )
        best_alias_delta = 0
        best_alias_rationale: list[str] = []
        for anchor_name, meta_entry in intent_meta.items():
            if file_anchors and anchor_name not in file_anchors:
                continue
            # aliases 매칭
            aliases = meta_entry.get("aliases")
            if isinstance(aliases, list):
                for alias in aliases:
                    if not isinstance(alias, str):
                        continue
                    alias_tokens = _intent_tokens(alias)
                    matched = _meaningful_overlap(request_tokens, alias_tokens)
                    delta = len(matched) * 4
                    if delta > best_alias_delta:
                        best_alias_delta = delta
                        best_alias_rationale = [
                            f"앵커 별칭('{alias}')에 키워드 '{', '.join(matched)}'이 포함됨"
                        ]
            # description 매칭
            desc = meta_entry.get("description", "")
            if isinstance(desc, str) and desc:
                desc_tokens = _intent_tokens(desc)
                matched = _meaningful_overlap(request_tokens, desc_tokens)
                delta = len(matched) * 2
                if delta > best_alias_delta:
                    best_alias_delta = delta
                    best_alias_rationale = [
                        f"앵커 설명에 키워드 '{', '.join(matched)}'이 포함됨"
                    ]
        if best_alias_delta > 0:
            score += best_alias_delta
            rationale.extend(best_alias_rationale)
```

주의: 기존 intent 매칭 블록과 중복 실행되지 않도록, aliases/description 매칭은 별도 루프에서 best-delta를 구해 한 번만 score에 더한다.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py -v`
Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add vibelign/core/patch_suggester.py tests/test_anchor_alias_index.py
git commit -m "feat(patch): use anchor aliases in score_path for file selection"
```

---

### Task 5: doctor APPLY에서 앵커 삽입 후 aliases 자동 생성

**Files:**
- Modify: `vibelign/action_engine/executors/action_executor.py:63-78` (_execute_add_anchor)
- Test: `tests/test_anchor_alias_index.py` (추가 테스트)

- [ ] **Step 1: Write the failing test**

`tests/test_anchor_alias_index.py`에 추가:

```python
def test_execute_add_anchor_generates_aliases(tmp_path):
    """add_anchor 액션 실행 후 aliases/description이 자동 생성되어야 한다."""
    from vibelign.action_engine.executors.action_executor import _execute_add_anchor
    from vibelign.action_engine.models.action import Action
    from vibelign.core.anchor_tools import load_anchor_meta

    # 앵커 없는 소스 파일
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
            "anchor": "MAIN_WINDOW",
            "intent": "메인 윈도우 UI",
            "aliases": ["메인 창", "main window"],
            "description": "메인 윈도우 클래스 정의",
        }
    ], ensure_ascii=False)

    with patch(
        "vibelign.core.anchor_tools.generate_text_with_ai",
        return_value=(ai_response, []),
    ), patch(
        "vibelign.core.anchor_tools.has_ai_provider",
        return_value=True,
    ):
        result = _execute_add_anchor(action, tmp_path)

    assert result.status == "done"
    meta = load_anchor_meta(tmp_path)
    # 최소 하나의 앵커에 aliases가 있어야 함
    has_aliases = any("aliases" in entry for entry in meta.values())
    assert has_aliases
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py::test_execute_add_anchor_generates_aliases -v`
Expected: FAIL — 현재 _execute_add_anchor는 앵커 삽입만 하고 aliases 생성 안 함

- [ ] **Step 3: Add aliases generation to _execute_add_anchor**

`vibelign/action_engine/executors/action_executor.py`의 `_execute_add_anchor` 함수에서 앵커 삽입 성공 후 aliases 생성 추가:

```python
def _execute_add_anchor(action: Action, root: Path) -> ExecutionResult:
    """앵커 없는 파일에 앵커 삽입 + aliases/description 자동 생성."""
    if not action.target_path:
        return ExecutionResult(action, "skipped", "파일 경로 없음")
    path = root / action.target_path
    if not path.exists():
        return ExecutionResult(action, "skipped", f"파일 없음: {action.target_path}")
    try:
        from vibelign.core.anchor_tools import extract_anchors, insert_module_anchors
        if extract_anchors(path):
            return ExecutionResult(action, "skipped", "이미 앵커 있음")
        if insert_module_anchors(path):
            # 삽입 성공 → aliases/description 자동 생성
            try:
                from vibelign.core.anchor_tools import generate_anchor_intents_with_ai
                generate_anchor_intents_with_ai(root, [path])
            except Exception:
                pass  # aliases 생성 실패해도 앵커 삽입은 성공
            return ExecutionResult(action, "done", f"앵커 추가: {action.target_path}")
        return ExecutionResult(action, "failed", "앵커 삽입 실패")
    except Exception as e:
        return ExecutionResult(action, "failed", str(e))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_anchor_alias_index.py -v`
Expected: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add vibelign/action_engine/executors/action_executor.py tests/test_anchor_alias_index.py
git commit -m "feat(action): auto-generate aliases after add_anchor in doctor APPLY"
```

---

### Task 6: 기존 테스트 회귀 확인

**Files:**
- 없음 (기존 테스트만 실행)

- [ ] **Step 1: 전체 테스트 실행**

Run: `.venv/bin/python -m pytest tests/ -v --timeout=30 -x`
Expected: 모든 기존 테스트 PASS

- [ ] **Step 2: 회귀 확인 후 최종 커밋**

문제가 있으면 수정 후 커밋. 없으면 이 step 생략.
