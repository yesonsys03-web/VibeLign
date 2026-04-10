# tests/test_import_resolver.py
import textwrap
from pathlib import Path
import pytest
from vibelign.core.import_resolver import parse_local_imports

@pytest.fixture
def tmp_project(tmp_path):
    return tmp_path

def test_tsx_relative_import_resolves(tmp_project):
    parent = tmp_project / "src" / "components" / "cards" / "GenericCommandCard.tsx"
    parent.parent.mkdir(parents=True)
    parent.write_text("// GenericCommandCard", encoding="utf-8")

    child = tmp_project / "src" / "components" / "cards" / "security" / "ClaudeHookCard.tsx"
    child.parent.mkdir(parents=True)
    child.write_text(
        textwrap.dedent('''
            import GenericCommandCard from "../GenericCommandCard";
            export default function ClaudeHookCard() {}
        '''),
        encoding="utf-8",
    )

    result = parse_local_imports(child, tmp_project)
    assert parent in result

def test_non_relative_import_ignored(tmp_project):
    f = tmp_project / "src" / "foo.tsx"
    f.parent.mkdir(parents=True)
    f.write_text('import React from "react";', encoding="utf-8")
    result = parse_local_imports(f, tmp_project)
    assert result == []

def test_import_outside_project_ignored(tmp_path):
    # 프로젝트 디렉토리와 분리된 외부 디렉토리 생성
    outside_dir = tmp_path / "outside_project"
    outside_dir.mkdir()
    outside_file = outside_dir / "leak.tsx"
    outside_file.write_text("// this is outside the project", encoding="utf-8")

    project = tmp_path / "my_project"
    project.mkdir()
    src = project / "src" / "foo.tsx"
    src.parent.mkdir(parents=True)

    # outside_file까지의 상대 경로 계산
    import os
    rel = os.path.relpath(outside_file, src.parent)
    src.write_text(f'import x from "{rel}";', encoding="utf-8")

    result = parse_local_imports(src, project)
    assert result == [], f"프로젝트 외부 파일이 결과에 포함되었음: {result}"


def test_re_export_from_resolves(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    target = project / "src" / "utils.ts"
    target.parent.mkdir(parents=True)
    target.write_text("export const foo = 1;", encoding="utf-8")

    src = project / "src" / "index.ts"
    src.write_text('export { foo } from "./utils";', encoding="utf-8")

    result = parse_local_imports(src, project)
    assert target in result

def test_python_relative_import_resolves(tmp_project):
    pkg = tmp_project / "vibelign" / "core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    target = pkg / "codespeak.py"
    target.write_text("# codespeak", encoding="utf-8")

    src = pkg / "patch_suggester.py"
    src.write_text(
        "from vibelign.core.codespeak import build_codespeak\n",
        encoding="utf-8",
    )
    result = parse_local_imports(src, tmp_project)
    assert target in result

def test_missing_file_extension_fallback(tmp_project):
    f_tsx = tmp_project / "src" / "Foo.tsx"
    f_tsx.parent.mkdir(parents=True)
    f_tsx.write_text("export default function Foo() {}", encoding="utf-8")

    src = tmp_project / "src" / "Bar.tsx"
    src.write_text('import Foo from "./Foo";', encoding="utf-8")

    result = parse_local_imports(src, tmp_project)
    assert f_tsx in result

def test_index_file_resolution(tmp_project):
    idx = tmp_project / "src" / "lib" / "index.ts"
    idx.parent.mkdir(parents=True)
    idx.write_text("export * from './commands';", encoding="utf-8")

    src = tmp_project / "src" / "App.tsx"
    src.write_text('import { foo } from "./lib";', encoding="utf-8")

    result = parse_local_imports(src, tmp_project)
    assert idx in result
