# tests/test_patch_import_expansion.py
"""
patch_suggester가 wrapper 컴포넌트를 찾았을 때
그 파일의 import도 AI 후보 풀에 포함되는지 검증.
"""
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch as mock_patch
import pytest
from vibelign.core.patch_suggester import _ai_select_file, _build_import_pool_expansion


def _make_project(tmp_path: Path) -> tuple[Path, Path, Path]:
    """ClaudeHookCard → GenericCommandCard 구조 생성."""
    security = tmp_path / "src" / "components" / "cards" / "security"
    security.mkdir(parents=True)
    cards = tmp_path / "src" / "components" / "cards"

    wrapper = security / "ClaudeHookCard.tsx"
    wrapper.write_text(
        textwrap.dedent('''
            // === ANCHOR: CLAUDE_HOOK_CARD_START ===
            import GenericCommandCard from "../GenericCommandCard";
            export default function ClaudeHookCard(props) {
              return <GenericCommandCard {...props} />;
            }
            // === ANCHOR: CLAUDE_HOOK_CARD_END ===
        '''),
        encoding="utf-8",
    )

    parent = cards / "GenericCommandCard.tsx"
    parent.write_text(
        textwrap.dedent('''
            // === ANCHOR: GENERIC_COMMAND_CARD_START ===
            import { useState } from "react";
            export default function GenericCommandCard({ cmd }) {
              const [flagValues, setFlagValues] = useState({});
              return <div />;
            }
            // === ANCHOR: GENERIC_COMMAND_CARD_END ===
        '''),
        encoding="utf-8",
    )
    return tmp_path, wrapper, parent


def test_import_pool_expansion_includes_imported_file(tmp_path):
    root, wrapper, parent = _make_project(tmp_path)
    expanded = _build_import_pool_expansion(wrapper, root, max_hops=1)
    assert parent in expanded


def test_import_pool_expansion_empty_for_no_imports(tmp_path):
    f = tmp_path / "src" / "Leaf.tsx"
    f.parent.mkdir(parents=True)
    f.write_text("export default function Leaf() {}", encoding="utf-8")
    result = _build_import_pool_expansion(f, tmp_path, max_hops=1)
    assert result == []


def test_import_pool_expansion_does_not_include_node_modules(tmp_path):
    f = tmp_path / "src" / "Foo.tsx"
    f.parent.mkdir(parents=True)
    f.write_text('import React from "react";\nexport default function Foo() {}', encoding="utf-8")
    result = _build_import_pool_expansion(f, tmp_path, max_hops=1)
    assert result == []


def test_suggest_patch_prefers_stateful_parent_over_wrapper(tmp_path):
    """ClaudeHookCard(wrapper) 가 아닌 GenericCommandCard(state owner)를 찾는지 검증."""
    root, wrapper, parent = _make_project(tmp_path)
    from vibelign.core.patch_suggester import _build_import_pool_expansion

    # _build_import_pool_expansion이 wrapper의 import로 parent를 반환해야 함
    expanded = _build_import_pool_expansion(wrapper, root, max_hops=1)
    assert parent in expanded, "GenericCommandCard가 1-hop import 탐색에 포함돼야 함"


def test_import_pool_expansion_multi_hop(tmp_path):
    """max_hops=2 일 때 A→B→C 체인을 모두 반환한다."""
    src = tmp_path / "src"
    src.mkdir()

    a = src / "A.tsx"
    b = src / "B.tsx"
    c = src / "C.tsx"

    c.write_text("export default function C() {}", encoding="utf-8")
    b.write_text('import C from "./C";\nexport default function B() {}', encoding="utf-8")
    a.write_text('import B from "./B";\nexport default function A() {}', encoding="utf-8")

    result = _build_import_pool_expansion(a, tmp_path, max_hops=2)
    assert b in result
    assert c in result
