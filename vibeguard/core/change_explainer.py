from dataclasses import dataclass, asdict, field
import subprocess, time
from pathlib import Path
from vibeguard.core.project_scan import iter_project_files, relpath_str

@dataclass
class ChangeItem:
    path: str
    status: str
    kind: str

@dataclass
class ExplainReport:
    source: str
    summary: str
    what_changed: list[str] = field(default_factory=list)
    why_it_might_matter: list[str] = field(default_factory=list)
    risk_level: str = "LOW"
    rollback_hint: str = ""
    files: list[dict] = field(default_factory=list)
    def to_dict(self):
        return asdict(self)

def classify_path(rel: str):
    low = rel.lower()
    if any(low.endswith(name) for name in ["main.py","index.js","app.js","main.ts","main.rs","main.go","main.cpp","program.cs"]):
        return "entry file"
    if "/ui/" in low or "window" in low or "dialog" in low or "widget" in low:
        return "ui"
    if "test" in low:
        return "test"
    if any(tok in low for tok in ["worker","backup","service","core","api","config","scheduler","hash"]):
        return "logic"
    if low.endswith(".md"):
        return "docs"
    return "general"

def risk_from_items(items):
    if not items:
        return "LOW"
    score = 0
    for item in items:
        score += 3 if item.kind == "entry file" else 2 if item.kind == "logic" else 1 if item.kind == "ui" else 0
        if item.status in {"deleted","renamed"}:
            score += 3
    if len(items) >= 8:
        score += 3
    return "HIGH" if score >= 8 else "MEDIUM" if score >= 4 else "LOW"

def _run_git(root: Path, args):
    try:
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
        return proc.returncode == 0, proc.stdout if proc.returncode == 0 else (proc.stderr or proc.stdout)
    except Exception as e:
        return False, str(e)

def explain_from_git(root: Path):
    ok, out = _run_git(root, ["status","--porcelain"])
    if not ok:
        return None
    items = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status_code = line[:2].strip()
        rel = line[3:].strip()
        if "->" in rel:
            rel = rel.split("->",1)[1].strip()
        status = {"M":"modified","A":"added","D":"deleted","R":"renamed","??":"untracked"}.get(status_code,"changed")
        items.append(ChangeItem(rel, status, classify_path(rel)))
    risk = risk_from_items(items)
    if not items:
        return ExplainReport("git", "Git 저장소가 깨끗합니다. 현재 변경된 파일이 없습니다.", risk_level="LOW", rollback_hint="지금 당장 롤백할 필요가 없습니다.", files=[])
    return ExplainReport("git", f"Git 상태에서 {len(items)}개의 변경된 파일을 감지했습니다. 위험 수준은 {risk}로 보입니다.", ["최근 파일이 변경되었습니다."], ["AI에게 계속 수정을 요청하기 전에 변경된 파일을 확인하세요."], risk, "롤백이 필요하면 git diff와 git restore를 사용하세요.", [asdict(i) for i in items])

def explain_from_mtime(root: Path, since_minutes=120):
    cutoff = time.time() - since_minutes * 60
    items = []
    for path in iter_project_files(root):
        try:
            if path.stat().st_mtime >= cutoff and path.suffix.lower() in {".py",".js",".ts",".rs",".go",".java",".cs",".cpp",".c",".hpp",".h"}:
                rel = relpath_str(root, path)
                items.append(ChangeItem(rel, "recently_modified", classify_path(rel)))
        except Exception:
            pass

    # calm fallback on freshly created repos
    items = sorted(items, key=lambda i: i.path)[:5]
    risk = risk_from_items(items)
    if not items:
        return ExplainReport("mtime", f"최근 {since_minutes}분 동안 수정된 파일이 없습니다.", risk_level="LOW", rollback_hint="수정 시간 기준으로 최근 변경된 파일이 없습니다.", files=[])

    if len(items) <= 2 and all(i.kind in {"general", "docs", "test"} for i in items):
        risk = "LOW"
    elif len(items) <= 3 and all(i.kind != "entry file" for i in items) and risk == "HIGH":
        risk = "MEDIUM"

    return ExplainReport(
        "mtime",
        f"최근 {since_minutes}분 동안 {len(items)}개의 소스 파일이 수정되었습니다. 위험 수준은 {risk}로 보입니다.",
        ["최근 소스 파일 변경이 감지되었습니다."],
        ["AI 수정을 계속하기 전에 이 파일들을 확인하세요."],
        risk,
        "Git을 사용 중이라면 다음 AI 수정 전에 커밋하세요. Git이 없다면 수동으로 복사하거나 버전 백업을 사용하세요.",
        [asdict(i) for i in items],
    )
