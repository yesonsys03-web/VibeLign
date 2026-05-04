# === ANCHOR: CHANGE_EXPLAINER_START ===
from dataclasses import dataclass, asdict, field
from datetime import datetime
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from vibelign.core.project_map import enrich_change_kind, load_project_map
from vibelign.core.project_scan import iter_project_files, relpath_str
from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS

FileSummary = dict[str, str]


@dataclass
# === ANCHOR: CHANGE_EXPLAINER_CHANGEITEM_START ===
class ChangeItem:
    path: str
    status: str
    kind: str
    modified_at: str = ""


# === ANCHOR: CHANGE_EXPLAINER_CHANGEITEM_END ===


@dataclass
# === ANCHOR: CHANGE_EXPLAINER_EXPLAINREPORT_START ===
class ExplainReport:
    source: str
    summary: str
    what_changed: list[str] = field(default_factory=list)
    why_it_might_matter: list[str] = field(default_factory=list)
    risk_level: str = "LOW"
    rollback_hint: str = ""
    files: list[FileSummary] = field(default_factory=list)

    # === ANCHOR: CHANGE_EXPLAINER_TO_DICT_START ===
    def to_dict(self) -> dict[str, object]:
        # === ANCHOR: CHANGE_EXPLAINER_EXPLAINREPORT_END ===
        return asdict(self)

    # === ANCHOR: CHANGE_EXPLAINER_TO_DICT_END ===


# === ANCHOR: CHANGE_EXPLAINER__RISK_LABEL_START ===
def _risk_label(level: str) -> str:
    return {
        "LOW": "낮음",
        "MEDIUM": "보통",
        "HIGH": "높음",
    }.get(level, level)


# === ANCHOR: CHANGE_EXPLAINER__RISK_LABEL_END ===


# === ANCHOR: CHANGE_EXPLAINER_CLASSIFY_PATH_START ===
def classify_path(rel: str) -> str:
    low = rel.lower()
    if any(
        low.endswith(name)
        for name in [
            "main.py",
            "index.js",
            "app.js",
            "main.ts",
            "main.rs",
            "main.go",
            "main.cpp",
            "program.cs",
        ]
    ):
        return "entry file"
    if "/ui/" in low or "window" in low or "dialog" in low or "widget" in low:
        return "ui"
    if "test" in low:
        return "test"
    if any(
        tok in low
        for tok in [
            "worker",
            "backup",
            "service",
            "core",
            "api",
            "config",
            "scheduler",
            "hash",
        ]
    ):
        return "logic"
    if low.endswith(".md"):
        return "docs"
    return "general"


# === ANCHOR: CHANGE_EXPLAINER_CLASSIFY_PATH_END ===


# === ANCHOR: CHANGE_EXPLAINER_RISK_FROM_ITEMS_START ===
def risk_from_items(items: Sequence[ChangeItem]) -> str:
    if not items:
        return "LOW"
    score = 0
    for item in items:
        score += (
            3
            if item.kind == "entry file"
            else 2
            if item.kind == "logic"
            else 1
            if item.kind == "ui"
            else 0
        )
        if item.status in {"deleted", "renamed"}:
            score += 3
    if len(items) >= 8:
        score += 3
    return "HIGH" if score >= 8 else "MEDIUM" if score >= 4 else "LOW"


# === ANCHOR: CHANGE_EXPLAINER_RISK_FROM_ITEMS_END ===


# === ANCHOR: CHANGE_EXPLAINER__DECODE_GIT_PATH_START ===
def _decode_git_path(path: str) -> str:
    """git 옥탈(octal) 인코딩된 경로를 UTF-8 NFC 문자열로 디코딩.
    macOS는 NFD, git 출력은 NFC — 비교 시 통일이 필요하므로 NFC로 반환."""
    import unicodedata

    if not (path.startswith('"') and path.endswith('"')):
        return unicodedata.normalize("NFC", path)
    path = path[1:-1]
    buf = bytearray()
    i = 0
    while i < len(path):
        if path[i] == "\\" and i + 3 < len(path) and path[i + 1 : i + 4].isdigit():
            buf.append(int(path[i + 1 : i + 4], 8))
            i += 4
        else:
            buf.extend(path[i].encode("utf-8"))
            i += 1
    try:
        return unicodedata.normalize("NFC", buf.decode("utf-8"))
    except UnicodeDecodeError:
        return path


# === ANCHOR: CHANGE_EXPLAINER__DECODE_GIT_PATH_END ===


# === ANCHOR: CHANGE_EXPLAINER__RUN_GIT_START ===
def _run_git(root: Path, args: Sequence[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=WINDOWS_SUBPROCESS_FLAGS,
        )
        return proc.returncode == 0, proc.stdout if proc.returncode == 0 else (
            proc.stderr or proc.stdout
        )
    except Exception as e:
        return False, str(e)


# === ANCHOR: CHANGE_EXPLAINER__RUN_GIT_END ===


# === ANCHOR: CHANGE_EXPLAINER__FILE_MODIFIED_AT_START ===


def _file_modified_at(root: Path, rel_path: str) -> str:
    try:
        return datetime.fromtimestamp((root / rel_path).stat().st_mtime).strftime(
            "%Y-%m-%d %H:%M"
        )
    except OSError:
        return ""


# === ANCHOR: CHANGE_EXPLAINER__FILE_MODIFIED_AT_END ===


# === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FROM_GIT_START ===
def explain_from_git(root: Path) -> ExplainReport | None:
    ok, out = _run_git(root, ["status", "--porcelain", "--", "."])
    if not ok:
        return None
    project_map, _project_map_error = load_project_map(root)
    # 상위 git 저장소에서 현재 폴더 자체가 untracked으로 표시될 수 있음 — 필터용
    # macOS 경로는 NFD이므로 NFC로 정규화해서 git 출력과 비교
    import unicodedata

    cwd_dir_entry = unicodedata.normalize("NFC", root.name + "/")
    items: list[ChangeItem] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status_code = line[:2].strip()
        rel = line[3:].strip()
        if "->" in rel:
            rel = rel.split("->", 1)[1].strip()
        # 현재 디렉토리 자체가 untracked으로 잡히는 경우 건너뜀
        if status_code == "??" and _decode_git_path(rel) == cwd_dir_entry:
            continue
        status = {
            "M": "modified",
            "A": "added",
            "D": "deleted",
            "R": "renamed",
            "??": "untracked",
        }.get(status_code, "changed")
        items.append(
            ChangeItem(
                rel,
                status,
                enrich_change_kind(project_map, rel, classify_path(rel)),
                _file_modified_at(root, rel),
            )
        )
    risk = risk_from_items(items)
    if not items:
        return ExplainReport(
            "git",
            "Git 저장소가 깨끗합니다. 현재 변경된 파일이 없습니다.",
            risk_level="LOW",
            rollback_hint="지금 당장 롤백할 필요가 없습니다.",
            files=[],
        )
    return ExplainReport(
        "git",
        f"{len(items)}개의 파일이 바뀐 것을 확인했어요. 지금 위험도는 {_risk_label(risk)} 정도로 보여요.",
        ["최근 파일이 변경되었습니다."],
        ["AI에게 계속 수정을 요청하기 전에 변경된 파일을 확인하세요."],
        risk,
        "되돌리려면 vib undo 를 쓰거나, vib checkpoint 로 저장해둔 지점이 있다면 그곳으로 돌아갈 수 있어요.",
        [asdict(i) for i in items],
    )


# === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FROM_GIT_END ===


# === ANCHOR: CHANGE_EXPLAINER__PARSE_UNIFIED_DIFF_START ===
def _parse_unified_diff(diff_text: str) -> dict[str, list[str]]:
    """유니파이드 diff 텍스트를 파싱해 추가/삭제 줄과 섹션 컨텍스트를 반환."""
    added: list[str] = []
    removed: list[str] = []
    sections: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("@@"):
            parts = line.split("@@", 2)
            if len(parts) >= 3:
                ctx = parts[2].strip()
                if ctx:
                    sections.append(ctx)
        elif line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    return {"added": added, "removed": removed, "sections": sections}


# === ANCHOR: CHANGE_EXPLAINER__PARSE_UNIFIED_DIFF_END ===


# === ANCHOR: CHANGE_EXPLAINER__EXTRACT_DEF_NAME_START ===
def _extract_def_name(line: str) -> str:
    """'def foo(...)' → 'foo', 'class Bar:' → 'Bar'"""
    tokens = line.split("(")[0].strip().split()
    return tokens[-1] if len(tokens) >= 2 else line[:20]


# === ANCHOR: CHANGE_EXPLAINER__EXTRACT_DEF_NAME_END ===


# === ANCHOR: CHANGE_EXPLAINER__KOREAN_DIFF_EXPLANATION_START ===
def _korean_diff_explanation(
    parsed: dict[str, list[str]],
    # === ANCHOR: CHANGE_EXPLAINER__KOREAN_DIFF_EXPLANATION_END ===
) -> tuple[str, list[str], list[str], str]:
    """파싱된 diff 정보로 한국어 설명을 생성. (요약, 변경사항, 중요성, 위험등급) 반환."""
    added = parsed["added"]
    removed = parsed["removed"]
    sections = parsed["sections"]
    n_add = len(added)
    n_del = len(removed)
    what: list[str] = []
    why: list[str] = []

    if not n_add and not n_del:
        return "변경된 내용이 없어요.", [], [], "LOW"

    # ── Import 변경
    kw_import = ("import ", "from ")
    import_add = [l for l in added if l.lstrip().startswith(kw_import)]
    import_del = [l for l in removed if l.lstrip().startswith(kw_import)]
    if import_add or import_del:
        if import_add and import_del:
            what.append(
                f"사용하는 외부 도구(import)가 바뀌었어요 — {len(import_del)}개 제거, {len(import_add)}개 추가"
            )
        elif import_add:
            what.append(f"새 외부 도구(import)가 {len(import_add)}개 추가됐어요")
        else:
            what.append(
                f"기존 외부 도구(import) {len(import_del)}개를 더 이상 쓰지 않아요"
            )
        why.append("다른 파일이나 라이브러리와의 연결 방식이 달라질 수 있어요")

    # ── 함수 / 클래스 정의 변경
    kw_def = ("def ", "async def ", "class ")
    def_add = [
        l.strip() for l in added if any(l.lstrip().startswith(k) for k in kw_def)
    ]
    def_del = [
        l.strip() for l in removed if any(l.lstrip().startswith(k) for k in kw_def)
    ]

    if def_add:
        names = [f"`{_extract_def_name(l)}`" for l in def_add[:3]]
        suffix = " 등" if len(def_add) > 3 else ""
        what.append(f"새 기능이 추가됐어요: {', '.join(names)}{suffix}")
        why.append("새 기능이 생겼어요. 다른 파일과 잘 연결됐는지 확인해보세요")

    if def_del:
        names = [f"`{_extract_def_name(l)}`" for l in def_del[:3]]
        suffix = " 등" if len(def_del) > 3 else ""
        what.append(f"기존 기능이 삭제됐어요: {', '.join(names)}{suffix}")
        why.append("삭제된 기능을 다른 곳에서 쓰고 있다면 오류가 생길 수 있어요")

    # ── 섹션 컨텍스트 (변경이 일어난 함수/클래스 이름)
    unique_ctx = list(dict.fromkeys(sections))[:3]
    if unique_ctx and not def_add and not def_del:
        what.append(f"수정된 위치: {', '.join(f'`{c}`' for c in unique_ctx)}")

    # ── 전체 줄 수 요약
    if n_add == 0:
        what.append(f"코드 {n_del}줄이 삭제됐어요")
    elif n_del == 0:
        what.append(f"코드 {n_add}줄이 새로 추가됐어요")
    else:
        what.append(f"코드 {n_add}줄 추가, {n_del}줄 삭제됐어요")

    if not why:
        why.append("`vib checkpoint` 로 저장해두면 언제든 되돌릴 수 있어요")

    # ── 위험도 계산
    score = (3 if (def_del or import_del) else 0) + (
        3 if n_del > 30 else 1 if n_del > 10 else 0
    )
    risk = "HIGH" if score >= 5 else "MEDIUM" if score >= 2 else "LOW"
    summary = f"코드 {n_add}줄 추가, {n_del}줄 삭제됐어요."
    return summary, what, why, risk


# === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FILE_FROM_GIT_START ===
def explain_file_from_git(root: Path, rel_path: str) -> ExplainReport | None:
    """특정 파일의 git diff 를 분석해 ExplainReport 반환. git 없으면 None."""
    project_map, _project_map_error = load_project_map(root)
    item_kind = enrich_change_kind(project_map, rel_path, classify_path(rel_path))

    # HEAD 대비 변경 (staged + unstaged 모두 포함)
    ok, diff = _run_git(root, ["diff", "HEAD", "--", rel_path])
    if not ok:
        # 커밋이 아직 없는 새 저장소 → staged 변경만 확인
        ok, diff = _run_git(root, ["diff", "--cached", "--", rel_path])
        if not ok:
            return None

    if not diff.strip():
        # diff 가 없을 때: 새 파일(untracked)인지 확인
        ok2, st = _run_git(root, ["status", "--porcelain", "--", rel_path])
        if ok2 and "??" in st:
            try:
                content = (root / rel_path).read_text(encoding="utf-8", errors="ignore")
                n = len(content.splitlines())
            except OSError:
                n = 0
            risk = "MEDIUM" if item_kind in {"entry file", "logic"} else "LOW"
            return ExplainReport(
                "git",
                f"`{rel_path}` 는 처음 추가된 파일이에요. 총 {n}줄로 이루어져 있어요.",
                [f"처음 생성된 파일이에요 (총 {n}줄)"],
                [
                    "이 파일이 어떤 역할을 하는지, 다른 파일과 어떻게 연결되는지 확인해보세요"
                ],
                risk,
                "vib checkpoint 로 지금 상태를 저장해두면 나중에 vib undo 로 되돌릴 수 있어요.",
                [
                    {
                        "path": rel_path,
                        "status": "added",
                        "kind": item_kind,
                        "modified_at": _file_modified_at(root, rel_path),
                    }
                ],
            )
        return ExplainReport(
            "git",
            f"`{rel_path}` 는 마지막 저장 이후 바뀐 내용이 없어요.",
            ["변경된 내용이 없어요"],
            [],
            "LOW",
            "되돌릴 필요가 없어요.",
            [],
        )

    parsed = _parse_unified_diff(diff)
    summary, what_changed, why_matters, risk = _korean_diff_explanation(parsed)
    return ExplainReport(
        "git",
        summary,
        what_changed,
        why_matters,
        risk,
        "vib undo 로 되돌릴 수 있어요. 또는 vib checkpoint 로 저장해두면 언제든 그 시점으로 돌아갈 수 있어요.",
        [
            {
                "path": rel_path,
                "status": "modified",
                "kind": item_kind,
                "modified_at": _file_modified_at(root, rel_path),
            }
        ],
    )


# === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FILE_FROM_GIT_END ===


# === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FILE_FROM_MTIME_START ===
def explain_file_from_mtime(
    root: Path,
    rel_path: str,
    since_minutes: int = 120,
    # === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FILE_FROM_MTIME_END ===
) -> "ExplainReport":
    """git 없이 수정 시각만으로 특정 파일의 변경 여부를 설명."""
    path = root / rel_path
    project_map, _project_map_error = load_project_map(root)
    item_kind = enrich_change_kind(project_map, rel_path, classify_path(rel_path))

    try:
        mtime = path.stat().st_mtime
    except OSError:
        return ExplainReport(
            "mtime",
            f"`{rel_path}` 파일을 찾을 수 없어요.",
            ["파일이 존재하지 않아요"],
            ["파일이 삭제됐거나 경로가 잘못됐을 수 있어요"],
            "MEDIUM",
            "백업에서 복원하거나 AI 에게 재생성을 요청해보세요",
            [],
        )

    cutoff = time.time() - since_minutes * 60
    recently = mtime >= cutoff

    try:
        n_lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    except OSError:
        n_lines = 0

    if recently:
        mins_ago = max(0, int((time.time() - mtime) / 60))
        when = f"{mins_ago}분 전" if mins_ago > 0 else "방금"
        risk = "MEDIUM" if item_kind in {"entry file", "logic"} else "LOW"
        return ExplainReport(
            "mtime",
            f"`{rel_path}` 가 {when}에 수정됐어요 (현재 {n_lines}줄).",
            [f"{when}에 파일이 수정됐어요 (총 {n_lines}줄)"],
            ["무엇이 바뀌었는지 보려면 vib history 로 checkpoint 기록을 확인해보세요"],
            risk,
            "vib undo 로 되돌릴 수 있어요. 먼저 vib checkpoint 로 현재 상태를 저장해두는 걸 추천해요.",
            [
                {
                    "path": rel_path,
                    "status": "recently_modified",
                    "kind": item_kind,
                    "modified_at": _file_modified_at(root, rel_path),
                }
            ],
        )

    return ExplainReport(
        "mtime",
        f"`{rel_path}` 는 최근 {since_minutes}분 동안 수정되지 않았어요.",
        ["최근에 수정된 내용이 없어요"],
        [],
        "LOW",
        "롤백이 필요하지 않아요.",
        [],
    )


# === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FROM_MTIME_START ===
def explain_from_mtime(root: Path, since_minutes: int = 120) -> ExplainReport:
    cutoff = time.time() - since_minutes * 60
    project_map, _project_map_error = load_project_map(root)
    items: list[ChangeItem] = []
    for path in iter_project_files(root):
        try:
            if path.stat().st_mtime >= cutoff and path.suffix.lower() in {
                ".py",
                ".js",
                ".ts",
                ".rs",
                ".go",
                ".java",
                ".cs",
                ".cpp",
                ".c",
                ".hpp",
                ".h",
            }:
                rel = relpath_str(root, path)
                items.append(
                    ChangeItem(
                        rel,
                        "recently_modified",
                        enrich_change_kind(project_map, rel, classify_path(rel)),
                        _file_modified_at(root, rel),
                    )
                )
        except Exception:
            pass

    # calm fallback on freshly created repos
    items = sorted(items, key=lambda i: i.path)[:5]
    risk = risk_from_items(items)
    if not items:
        return ExplainReport(
            "mtime",
            f"최근 {since_minutes}분 동안 수정된 파일이 없습니다.",
            risk_level="LOW",
            rollback_hint="수정 시간 기준으로 최근 변경된 파일이 없습니다.",
            files=[],
        )

    if len(items) <= 2 and all(i.kind in {"general", "docs", "test"} for i in items):
        risk = "LOW"
    elif (
        len(items) <= 3
        and all(i.kind != "entry file" for i in items)
        and risk == "HIGH"
    ):
        risk = "MEDIUM"

    return ExplainReport(
        "mtime",
        f"최근 {since_minutes}분 동안 {len(items)}개의 소스 파일이 바뀌었습니다. 지금 위험도는 {_risk_label(risk)} 정도로 보여요.",
        ["최근 소스 파일 변경이 감지되었습니다."],
        ["AI 수정을 계속하기 전에 이 파일들을 확인하세요."],
        risk,
        "다음 AI 수정 전에 vib checkpoint 로 지금 상태를 저장해두는 게 좋아요. 나중에 vib undo 로 되돌릴 수 있어요.",
        [asdict(i) for i in items],
    )


# === ANCHOR: CHANGE_EXPLAINER_EXPLAIN_FROM_MTIME_END ===
# === ANCHOR: CHANGE_EXPLAINER_END ===
