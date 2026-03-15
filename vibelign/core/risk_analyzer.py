from dataclasses import dataclass, field, asdict
import re
from pathlib import Path
from vibelign.core.project_scan import iter_project_files, iter_source_files, line_count, safe_read_text, relpath_str

ENTRY_FILES = {"main.py","app.py","cli.py","index.js","app.js","main.ts","index.ts","main.rs","main.go","main.cpp","Program.cs"}
CATCH_ALL = {"utils.py","helpers.py","misc.py","all_utils.py","utils.js","helpers.js","misc.js","utils.ts","helpers.ts","misc.ts"}
UI_HINTS = ["qwidget","mainwindow","react","component","render(","button","layout","window","dialog","route","router"]
BIZ_HINTS = ["hashlib","threading","copy2(","requests","sqlite3","fetch(","axios","express(","flask(","fastapi","django","subprocess","os.walk","shutil"]
FUNCTION_PATTERNS = [r"^def\s+", r"^class\s+", r"^function\s+", r"^export\s+function\s+", r"^[A-Za-z_][\w<>:,\s*&]+\("]

@dataclass
class RiskReport:
    level: str = "GOOD"
    score: int = 0
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    def to_dict(self):
        return asdict(self)

def count_matches(text, patterns):
    return sum(len(re.findall(p, text, flags=re.MULTILINE)) for p in patterns)

def contains_any(text, needles):
    low = text.lower()
    return any(n in low for n in needles)

def add_issue(report, issue, suggestion, score):
    report.issues.append(issue)
    report.suggestions.append(suggestion)
    report.score += score

def analyze_project(root: Path, strict=False):
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
            add_issue(report, f"{rel} 파일이 너무 큽니다 ({lines}줄)", f"{name}은 시작 코드만 유지하고 나머지 로직은 모듈로 분리하세요", 3)
        if name in CATCH_ALL:
            add_issue(report, f"{rel}은 모든 걸 담는 파일처럼 보입니다", f"{name}을 역할별로 분리하세요", 2)
        if lines >= 800:
            add_issue(report, f"{rel} 파일이 위험할 정도로 큽니다 ({lines}줄, critical)", f"{name}을 반드시 더 작은 모듈로 분리하세요", 5)
        elif lines >= 500:
            add_issue(report, f"{rel} 파일이 매우 큽니다 ({lines}줄, strong warning)", f"{name}을 더 작은 모듈로 분리하는 것을 강력히 권장합니다", 3)
        elif lines >= 300:
            add_issue(report, f"{rel} 파일이 큽니다 ({lines}줄, warning)", f"{name}을 더 작은 모듈로 분리하는 것을 고려하세요", 2)
        if lines > anchor_limit and "ANCHOR:" not in text:
            missing_anchor_files += 1
            add_issue(report, f"{rel}에 앵커가 없습니다", f"{name}에 앵커를 추가하면 AI가 안전하게 부분 수정할 수 있습니다", 2)
        if fn_count >= (18 if strict else 25):
            add_issue(report, f"{rel}에 정의가 너무 많습니다 ({fn_count}개)", f"{name}을 기능별 모듈로 분리하는 것을 고려하세요", 2)
        if name in ENTRY_FILES and lines > 60 and contains_any(text, BIZ_HINTS):
            add_issue(report, f"{rel}에 비즈니스 로직이 섞여 있을 수 있습니다", f"{name}에서 시작 코드 외의 로직을 별도 모듈로 옮기세요", 3)
        if contains_any(text, UI_HINTS) and contains_any(text, BIZ_HINTS) and lines > 100:
            add_issue(report, f"{rel}에 UI와 비즈니스 로직이 혼재할 수 있습니다", f"{name}에서 UI 코드와 처리/서비스 로직을 분리하세요", 3)

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
    report.level = "HIGH" if report.score >= 12 else "WARNING" if report.score >= 4 else "GOOD"
    return report


_IMPORT_RE = re.compile(
    r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
)


def _extract_internal_imports(root: Path, path: Path):
    """Extract internal (project-local) import targets from a Python file."""
    text = safe_read_text(path)
    results = []
    for m in _IMPORT_RE.finditer(text):
        mod = m.group(1) or m.group(2)
        top = mod.split(".")[0]
        candidate = root / top
        if candidate.is_dir() or (root / f"{top}.py").exists():
            results.append(mod)
    return results


def _check_dependency_risks(root: Path):
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
            if mod not in module_names and not any(mod.startswith(m + ".") for m in module_names):
                issues.append(
                    (f"{rel}이 존재하지 않는 내부 모듈 '{mod}'을 참조합니다",
                     f"import 대상 '{mod}'이 프로젝트에 존재하는지 확인하세요", 2)
                )

    seen_cycles: set[frozenset[str]] = set()
    for src, imports in import_graph.items():
        src_mod = src.replace("/", ".").removesuffix(".py")
        for target in imports:
            for other_src, other_imports in import_graph.items():
                other_mod = other_src.replace("/", ".").removesuffix(".py")
                if target.startswith(other_mod) or other_mod.startswith(target):
                    if any(i.startswith(src_mod) or src_mod.startswith(i) for i in other_imports):
                        pair = frozenset([src, other_src])
                        if src != other_src and pair not in seen_cycles:
                            seen_cycles.add(pair)
                            issues.append(
                                (f"{src}와 {other_src} 사이에 순환 import가 의심됩니다",
                                 "순환 의존성을 제거하거나 공통 모듈로 분리하세요", 3)
                            )

    return issues
