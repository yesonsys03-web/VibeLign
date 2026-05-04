# === ANCHOR: RECOVERY_RENDER_START ===
from __future__ import annotations

from .models import RecoveryPlan


# === ANCHOR: RECOVERY_RENDER__RENDER_TEXT_PLAN_START ===
def render_text_plan(plan: RecoveryPlan) -> str:
    lines = [
        "VibeLign 복구 도우미 (읽기 전용)",
        "파일은 수정하지 않았습니다.",
        f"요약: {plan.summary}",
        "",
        "사용 방법: `vib explain`로 전체 변경을 보고, 낯선 파일은 `vib explain <파일경로>`로 확인한 뒤, 되돌릴 파일은 `vib recover --file <파일경로>`로 미리보세요.",
    ]
    changed_paths = _changed_paths(plan)
    if changed_paths:
        lines.extend(["", "변경 파일 요약:", *_category_summary_lines(changed_paths)])
        priority_paths = _priority_paths(plan)
        if priority_paths:
            lines.extend(["", "먼저 확인할 파일:", *priority_paths])
    lines.extend(["", "복구 옵션:"])
    for index, option in enumerate(plan.options, start=1):
        suffix = f" (확인 필요: {option.blocked_reason})" if option.blocked_reason else ""
        lines.append(_option_label(index, option.label, suffix))
    if plan.drift_candidates:
        lines.extend(
            [
                "",
                "검토가 필요한 파일:",
                "아래 파일은 이번 작업 의도와 연결되지 않았습니다. `vib explain <파일경로>` 또는 에디터로 열어 확인하세요.",
            ]
        )
        for candidate in plan.drift_candidates:
            lines.append(f"- {candidate.path} — {_path_role_label(candidate.path)}")
    if plan.safe_checkpoint_candidate is not None:
        lines.extend(
            [
                "",
                "안전 체크포인트:",
                f"- {plan.safe_checkpoint_candidate.checkpoint_id}: {plan.safe_checkpoint_candidate.message or '(no message)'}",
                f"  정보 완성: {_bool_label(plan.safe_checkpoint_candidate.metadata_complete)}; 미리보기 가능: {_bool_label(plan.safe_checkpoint_candidate.preview_available)}; 변경 전 생성됨: {_bool_label(plan.safe_checkpoint_candidate.predates_change)}",
            ]
        )
    return "\n".join(lines)
# === ANCHOR: RECOVERY_RENDER__RENDER_TEXT_PLAN_END ===


def _bool_label(value: bool) -> str:
    return "예" if value else "아니오"


def _option_label(index: int, label: str, suffix: str) -> str:
    stripped = label.strip()
    if stripped.startswith(("1단계", "2단계", "3단계")):
        return f"{stripped}{suffix}"
    return f"{index}. {stripped}{suffix}"


def _changed_paths(plan: RecoveryPlan) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for option in plan.options:
        for path in option.affected_paths:
            if path and path not in seen:
                seen.add(path)
                result.append(path)
    return result


def _category_summary_lines(paths: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    for path in paths:
        label = _path_kind_label(path)
        counts[label] = counts.get(label, 0) + 1
    order = ["문서", "테스트", "핵심 코드", "화면", "명령/설정", "일반 파일"]
    return [f"- {label} {counts[label]}개 — {_kind_description(label)}" for label in order if counts.get(label, 0)]


def _priority_paths(plan: RecoveryPlan) -> list[str]:
    source = [candidate.path for candidate in plan.drift_candidates] or _changed_paths(plan)
    return [f"- {path} — {_path_role_label(path)}" for path in source[:5]]


def _path_role_label(path: str) -> str:
    return f"{_path_kind_label(path)}: {_path_role_description(path)}"


def _path_kind_label(path: str) -> str:
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    if normalized.startswith("docs/") or "/docs/" in normalized or name.endswith((".md", ".mdx", ".rst")):
        return "문서"
    if normalized.startswith("tests/") or "/tests/" in normalized or name.startswith("test_"):
        return "테스트"
    if normalized.startswith("vibelign-gui/") or name.endswith((".tsx", ".jsx", ".css")):
        return "화면"
    if normalized.startswith("vibelign/core/") or normalized.startswith("src/"):
        return "핵심 코드"
    if name in {"pyproject.toml", "vib.spec"} or normalized.startswith("vibelign/commands/") or normalized.startswith("vibelign/cli/"):
        return "명령/설정"
    return "일반 파일"


def _path_role_description(path: str) -> str:
    normalized = path.replace("\\", "/").lower()
    name = normalized.rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0]
    if normalized.startswith("docs/") or "/docs/" in normalized or name.endswith((".md", ".mdx", ".rst")):
        return "작업 계획이나 기능 설명을 담은 문서입니다"
    if normalized.startswith("tests/") or "/tests/" in normalized or name.startswith("test_"):
        target = _human_readable_stem(stem.removeprefix("test_"))
        return f"{target} 기능이 맞게 동작하는지 확인하는 테스트입니다"
    if "recovery" in normalized or "recover" in normalized:
        return "되돌리기와 복구 안내 흐름을 담당합니다"
    if "memory" in normalized:
        return "세션 메모리와 작업 기록을 관리합니다"
    if normalized.startswith("vibelign-gui/") or name.endswith((".tsx", ".jsx", ".css")):
        return "사용자 화면에 보이는 표시와 조작을 담당합니다"
    if normalized.startswith("vibelign/commands/") or normalized.startswith("vibelign/cli/"):
        return "사용자가 입력하는 vib 명령을 처리합니다"
    if name in {"pyproject.toml", "vib.spec"}:
        return "설치, 빌드, 패키징 설정을 담고 있습니다"
    if normalized.startswith("vibelign/core/") or normalized.startswith("src/"):
        return "제품의 핵심 동작 로직을 담당합니다"
    return "프로젝트 동작에 필요한 보조 파일입니다"


def _human_readable_stem(stem: str) -> str:
    words = [word for word in stem.replace("-", "_").split("_") if word]
    if not words:
        return "관련"
    translations = {
        "aggregator": "집계",
        "apply": "적용",
        "audit": "감사 기록",
        "capabilities": "권한",
        "candidate": "후보",
        "candidates": "후보",
        "cli": "명령",
        "contracts": "연동 규칙",
        "denied": "거부",
        "distribution": "배포",
        "execution": "실행",
        "gui": "화면",
        "handlers": "처리기",
        "mcp": "AI 연결",
        "memory": "메모리",
        "metadata": "정보",
        "patch": "수정",
        "path": "경로",
        "planner": "계획",
        "readiness": "준비 상태",
        "recover": "복구",
        "recovery": "복구",
        "retention": "보존",
        "safety": "안전",
        "scaffold": "기초 구조",
        "schema": "데이터 형식",
        "schemas": "데이터 형식",
        "score": "점수",
        "suggester": "추천",
        "vib": "vib",
    }
    return " ".join(translations.get(word, word) for word in words)


def _kind_description(label: str) -> str:
    return {
        "문서": "기획이나 설명 문서가 바뀌었습니다.",
        "테스트": "기능이 맞게 동작하는지 확인하는 코드가 바뀌었습니다.",
        "핵심 코드": "실제 기능 로직이 바뀌었습니다.",
        "화면": "GUI 화면이나 표시 코드가 바뀌었습니다.",
        "명령/설정": "CLI 명령, 패키징, 설정 파일이 바뀌었습니다.",
        "일반 파일": "기타 프로젝트 파일이 바뀌었습니다.",
    }.get(label, "프로젝트 파일이 바뀌었습니다.")

# === ANCHOR: RECOVERY_RENDER_END ===
