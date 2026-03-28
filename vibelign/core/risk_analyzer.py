from dataclasses import dataclass, field, asdict
import re
from pathlib import Path
from vibelign.core.project_scan import (
    iter_project_files,
    iter_source_files,
    line_count,
    safe_read_text,
    relpath_str,
)

ENTRY_FILES = {
    "main.py",
    "app.py",
    "cli.py",
    "index.js",
    "app.js",
    "main.ts",
    "index.ts",
    "main.rs",
    "main.go",
    "main.cpp",
    "Program.cs",
}
CATCH_ALL = {
    "utils.py",
    "helpers.py",
    "misc.py",
    "all_utils.py",
    "utils.js",
    "helpers.js",
    "misc.js",
    "utils.ts",
    "helpers.ts",
    "misc.ts",
}
UI_HINTS = [
    "qwidget",
    "mainwindow",
    "react",
    "component",
    "render(",
    "button",
    "layout",
    "window",
    "dialog",
    "route",
    "router",
]
BIZ_HINTS = [
    "hashlib",
    "threading",
    "copy2(",
    "requests",
    "sqlite3",
    "fetch(",
    "axios",
    "express(",
    "flask(",
    "fastapi",
    "django",
    "subprocess",
    "os.walk",
    "shutil",
]
FUNCTION_PATTERNS = [
    r"^def\s+",
    r"^class\s+",
    r"^function\s+",
    r"^export\s+function\s+",
    r"^[A-Za-z_][\w<>:,\s*&]+\(",
]


@dataclass
class RiskReport:
    level: str = "GOOD"
    score: int = 0
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def count_matches(text: str, patterns: list[str]) -> int:
    return sum(len(re.findall(p, text, flags=re.MULTILINE)) for p in patterns)


def contains_any(text: str, needles: list[str] | set[str]) -> bool:
    low = text.lower()
    return any(n in low for n in needles)


def add_issue(report: RiskReport, issue: str, suggestion: str, score: int) -> None:
    report.issues.append(issue)
    report.suggestions.append(suggestion)
    report.score += score


def analyze_project(root: Path, strict: bool = False) -> RiskReport:
    report = RiskReport()
    files_scanned = sum(1 for _ in iter_project_files(root))
    source_files_scanned = 0
    oversized_entry_files = 0
    missing_anchor_files = 0
    for path in iter_source_files(root):
        source_files_scanned += 1
        rel = relpath_str(root, path)
        name = path.name
        lines = line_count(path)
        text = safe_read_text(path)
        fn_count = count_matches(text, FUNCTION_PATTERNS)
        entry_limit = 120 if strict else 200
        anchor_limit = 40 if strict else 80

        if name in ENTRY_FILES and lines > entry_limit:
            oversized_entry_files += 1
            add_issue(
                report,
                f"{rel} 파일이 너무 깁니다 ({lines}줄) — AI가 어디를 고쳐야 할지 헷갈릴 수 있어요",
                f"{name}은 시작 코드만 두고 나머지는 다른 파일로 옮기는 게 좋아요",
                3,
            )
        if name in CATCH_ALL:
            add_issue(
                report,
                f"{rel}은 여러 기능이 한 파일에 몰려 있어요",
                f"{name}을 기능별로 파일을 나눠보세요",
                2,
            )
        if lines >= 1000:
            add_issue(
                report,
                f"{rel} 파일이 너무 깁니다 ({lines}줄) — AI가 실수할 위험이 높아요",
                f"{name}은 꼭 여러 파일로 나눠야 해요",
                5,
            )
        elif lines >= 800:
            add_issue(
                report,
                f"{rel} 파일이 많이 깁니다 ({lines}줄) — AI가 엉뚱한 곳을 고칠 수 있어요",
                f"{name}을 여러 파일로 나누는 걸 강력히 권장해요",
                3,
            )
        elif lines >= 500:
            add_issue(
                report,
                f"{rel} 파일이 조금 깁니다 ({lines}줄)",
                f"{name}을 여러 파일로 나누는 걸 고려해보세요",
                2,
            )
        if lines > anchor_limit and "=== ANCHOR:" not in text:
            missing_anchor_files += 1
            add_issue(
                report,
                f"{rel}에 안전 구역 표시(앵커)가 없어요",
                f"{name}에 앵커를 추가하면 AI가 딱 그 부분만 안전하게 고칠 수 있어요 — vib anchor --suggest",
                2,
            )
        if fn_count >= (18 if strict else 25):
            add_issue(
                report,
                f"{rel}에 기능이 너무 많이 들어 있어요 ({fn_count}개) — AI가 어디를 건드려야 할지 헷갈릴 수 있어요",
                f"{name}을 기능별로 파일을 나눠보세요",
                2,
            )
        if name in ENTRY_FILES and lines > 60 and contains_any(text, BIZ_HINTS):
            add_issue(
                report,
                f"{rel}에 실행 코드 말고 다른 기능도 섞여 있는 것 같아요",
                f"{name}에서 시작 코드 외의 기능은 다른 파일로 옮기세요",
                3,
            )
        if (
            contains_any(text, UI_HINTS)
            and contains_any(text, BIZ_HINTS)
            and lines > 100
        ):
            add_issue(
                report,
                f"{rel}에 화면 코드와 처리 코드가 한 파일에 섞여 있어요",
                f"{name}에서 화면 코드와 처리 코드를 파일로 나눠보세요",
                3,
            )

    dep_issues = _check_dependency_risks(root)
    for issue, suggestion, sc in dep_issues:
        add_issue(report, issue, suggestion, sc)

    report.issues = list(dict.fromkeys(report.issues))
    report.suggestions = list(dict.fromkeys(report.suggestions))
    report.stats = {
        "files_scanned": files_scanned,
        "source_files_scanned": source_files_scanned,
        "oversized_entry_files": oversized_entry_files,
        "missing_anchor_files": missing_anchor_files,
    }
    report.level = (
        "HIGH" if report.score >= 12 else "WARNING" if report.score >= 4 else "GOOD"
    )
    return report


_IMPORT_RE = re.compile(
    r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
)


def _resolve_relative_import(mod: str, path: Path, root: Path) -> str | None:
    """Resolve a relative import like '.commands.foo' to 'pkg.commands.foo'."""
    if not mod.startswith("."):
        return None
    # Count leading dots
    dots = len(mod) - len(mod.lstrip("."))
    remainder = mod.lstrip(".")
    # Determine the importing file's package parts
    try:
        rel = path.relative_to(root)
    except ValueError:
        return None
    parts = list(rel.with_suffix("").parts)
    # Single dot → same package (drop file name), two dots → parent, etc.
    pkg_parts = parts[:-1]  # drop the file name to get package
    levels_up = dots - 1
    if levels_up > len(pkg_parts):
        return None
    if levels_up > 0:
        pkg_parts = pkg_parts[:-levels_up]
    base = ".".join(pkg_parts)
    if remainder:
        return f"{base}.{remainder}" if base else remainder
    return base or None


def _extract_internal_imports(root: Path, path: Path) -> list[str]:
    """Extract internal (project-local) import targets from a Python file."""
    text = safe_read_text(path)
    results: list[str] = []
    for m in _IMPORT_RE.finditer(text):
        mod = m.group(1) or m.group(2)
        # Resolve relative imports to absolute module names
        if mod.startswith("."):
            resolved = _resolve_relative_import(mod, path, root)
            if resolved is None:
                continue
            mod = resolved
        top = mod.split(".")[0]
        candidate = root / top
        if candidate.is_dir() or (root / f"{top}.py").exists():
            results.append(mod)
    return results


def _check_dependency_risks(root: Path) -> list[tuple[str, str, int]]:
    """Lightweight dependency-risk checks: circular imports, missing targets, suspicious chains."""
    issues: list[tuple[str, str, int]] = []
    import_graph: dict[str, list[str]] = {}

    py_files = [p for p in iter_source_files(root) if p.suffix == ".py"]
    module_names: set[str] = set()
    for p in py_files:
        rel = p.relative_to(root)
        parts = list(rel.with_suffix("").parts)
        module_names.add(".".join(parts))
        if parts[-1] == "__init__":
            module_names.add(".".join(parts[:-1]))

    for p in py_files:
        rel = relpath_str(root, p)
        imports = _extract_internal_imports(root, p)
        import_graph[rel] = imports

        for mod in imports:
            if mod not in module_names and not any(
                mod.startswith(m + ".") for m in module_names
            ):
                issues.append(
                    (
                        f"{rel}이 '{mod}' 파일을 불러오려 하는데 그 파일이 없어요",
                        f"'{mod}' 파일이 프로젝트 안에 있는지 확인해보세요",
                        2,
                    )
                )

    seen_cycles: set[frozenset[str]] = set()
    for src, imports in import_graph.items():
        src_mod = src.replace("/", ".").removesuffix(".py")
        for target in imports:
            for other_src, other_imports in import_graph.items():
                other_mod = other_src.replace("/", ".").removesuffix(".py")
                if target.startswith(other_mod) or other_mod.startswith(target):
                    if any(
                        i.startswith(src_mod) or src_mod.startswith(i)
                        for i in other_imports
                    ):
                        pair = frozenset([src, other_src])
                        if src != other_src and pair not in seen_cycles:
                            seen_cycles.add(pair)
                            issues.append(
                                (
                                    f"{src}와 {other_src}가 서로를 불러오고 있어요 — 이러면 오류가 날 수 있어요",
                                    "두 파일이 서로를 부르지 않도록 공통 내용을 별도 파일로 분리해보세요",
                                    3,
                                )
                            )

    return issues
