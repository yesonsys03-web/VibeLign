from pathlib import Path
import re
from dataclasses import dataclass, asdict
from vibeguard.core.project_scan import iter_source_files, relpath_str
from vibeguard.core.anchor_tools import extract_anchors

KEYWORD_HINTS = {
    "progress":["progress","worker","backup","copy","ui","status"],
    "backup":["backup","worker","copy","hash","verify"],
    "ui":["ui","window","dialog","widget","layout","button"],
    "button":["button","ui","window","dialog","layout"],
    "log":["log","logger","logging","status"],
    "schedule":["schedule","scheduler","cron","timer"],
    "config":["config","settings","json","yaml","toml"],
}

LOW_PRIORITY_NAMES = {"__init__.py", "__init__.js", "__init__.ts"}

@dataclass
class PatchSuggestion:
    request: str
    target_file: str
    target_anchor: str
    confidence: str
    rationale: list[str]
    def to_dict(self):
        return asdict(self)

def tokenize(text):
    return re.findall(r"[a-zA-Z_]+", text.lower())

def score_path(path: Path, request_tokens):
    score = 0
    rationale = []
    pt = str(path).lower()
    stem = path.stem.lower()

    if path.name in LOW_PRIORITY_NAMES:
        score -= 6
        rationale.append("init 스타일 파일이라 우선순위 낮음")
    if "/tests/" in pt or pt.startswith("tests/") or "/docs/" in pt or pt.startswith("docs/"):
        score -= 5
        rationale.append("docs/test 경로라 우선순위 낮음")

    for token in request_tokens:
        if token and token in pt:
            score += 3
            rationale.append(f"경로에 키워드 '{token}'이 포함됨")
    for key, hints in KEYWORD_HINTS.items():
        if key in request_tokens:
            for hint in hints:
                if hint in pt:
                    score += 2
                    rationale.append(f"'{key}' 키워드 계열인 '{hint}'와 경로가 일치")
    if stem in request_tokens:
        score += 4
        rationale.append(f"파일명 '{stem}'이 요청과 직접 일치")
    if any(tok in stem for tok in ["worker", "service", "window", "config", "scheduler", "backup"]):
        score += 1
    return score, rationale

def choose_anchor(anchors, request_tokens):
    if not anchors:
        return "[먼저 앵커를 추가하세요]", ["이 파일에는 아직 앵커가 없습니다"]
    best_anchor = anchors[0]
    best_score = -1
    best_rationale = [f"첫 번째 앵커 '{best_anchor}'를 기본값으로 선택"]
    for anchor in anchors:
        score = 0
        rationale = []
        al = anchor.lower()
        for token in request_tokens:
            if token in al:
                score += 3
                rationale.append(f"앵커에 키워드 '{token}'이 포함됨")
        if "core" in al or "logic" in al or "worker" in al:
            score += 1
        if score > best_score:
            best_score = score
            best_anchor = anchor
            best_rationale = rationale or [f"사용 가능한 앵커 중 '{anchor}'를 최선으로 선택"]
    return best_anchor, best_rationale

def suggest_patch(root: Path, request: str):
    request_tokens = tokenize(request)
    scored = []
    for path in iter_source_files(root):
        score, rationale = score_path(path, request_tokens)
        scored.append((score, path, rationale))

    if not scored:
        return PatchSuggestion(request, "[소스 파일 없음]", "[없음]", "low", ["프로젝트에 아직 소스 파일이 없습니다"])

    scored.sort(key=lambda x: (-x[0], str(x[1])))
    best_score, best_path, reasons = scored[0]
    anchors = extract_anchors(best_path)
    anchor, ar = choose_anchor(anchors, request_tokens)
    confidence = "high" if best_score >= 8 else "medium" if best_score >= 4 else "low"
    return PatchSuggestion(request, relpath_str(root, best_path), anchor, confidence, reasons[:5] + ar[:3])
