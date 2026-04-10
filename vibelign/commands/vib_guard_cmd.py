# === ANCHOR: VIB_GUARD_CMD_START ===
import json
import re
import subprocess
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, TypedDict, cast

from vibelign.core.change_explainer import (
    ChangeItem,
    ExplainReport,
    FileSummary,
    classify_path,
    explain_from_git,
    explain_from_mtime,
    risk_from_items,
)
from vibelign.core.doctor_v2 import analyze_project_v2
from vibelign.core.guard_report import GuardReport
from vibelign.core.guard_report import combine_guard
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import enrich_change_kind, load_project_map
from vibelign.core.project_root import resolve_project_root
from vibelign.core.protected_files import get_protected, is_protected
from vibelign.core.risk_analyzer import analyze_project
from vibelign.mcp.mcp_state_store import load_planning_session
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print
_WINDOWS_FLAGS = (
    subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
)


class GuardDoctorData(TypedDict):
    project_score: int
    status: str
    issues: list[object]
    recommended_actions: list[str]


class GuardExplainData(TypedDict):
    source: str
    risk_level: str
    files: list[FileSummary]
    summary: str


class GuardData(TypedDict):
    status: str
    strict: bool
    blocked: bool
    project_score: int
    project_status: str
    change_risk_level: str
    summary: str
    recommendations: list[str]
    protected_violations: list[str]
    doctor: dict[str, object] | GuardDoctorData
    explain: GuardExplainData
    planning: "PlanningData"


class PlanningData(TypedDict):
    status: str
    strict: bool
    active_plan_id: str | None
    summary: str
    changed_files: list[str]
    required_reasons: list[str]
    deviations: list[str]
    exempt_reasons: list[str]


class FileChangeDetails(TypedDict):
    added_lines: int
    ranges: list[tuple[int, int]]


class GuardError(TypedDict):
    code: str
    message: str
    hint: str


class GuardEnvelope(TypedDict):
    ok: bool
    error: GuardError | None
    data: GuardData


class GuardArgs(Protocol):
    strict: bool
    since_minutes: int
    json: bool
    write_report: bool


_SMALL_FIX_LINE_THRESHOLD = 30
_PLAN_REQUIRED_RECOMMENDATION = (
    "구조 영향 가능성이 높다면 먼저 `vib plan-structure`를 실행하세요."
)


def _planning_message(status: str) -> str:
    return {
        "planning_exempt": "현재 변경은 plan-structure 없이 진행 가능한 범위입니다.",
        "planning_required": "구조 영향 가능성이 높은 변경이 감지되었습니다. 먼저 `vib plan-structure`를 실행하세요.",
        "plan_exists_but_deviated": "활성 구조 계획은 존재하지만 실제 변경이 허용 범위를 벗어났습니다.",
        "fail": "구조 계획 검증에 실패했습니다. 금지 규칙 위반 또는 plan 상태 이상을 확인하세요.",
        "pass": "활성 구조 계획과 실제 변경이 일치합니다.",
    }.get(status, "구조 계획 상태를 확인하세요.")


def _planning_exempt_summary(reasons: Sequence[str]) -> str:
    if "docs_only" in reasons:
        return (
            "현재 변경은 문서만 수정하므로 plan-structure 없이 진행 가능한 범위입니다."
        )
    if "tests_only" in reasons:
        return "현재 변경은 테스트만 수정하므로 plan-structure 없이 진행 가능한 범위입니다."
    if "config_only" in reasons:
        return "현재 변경은 config만 수정하므로 plan-structure 없이 진행 가능한 범위입니다."
    if "small_single_file_fix" in reasons:
        return "현재 변경은 소규모 단일 파일 수정이므로 plan-structure 없이 진행 가능한 범위입니다."
    if "override" in reasons:
        return "planning override가 활성화되어 있어 현재 변경은 plan-structure 없이 진행 가능한 범위입니다."
    if "no_changed_files" in reasons:
        return "현재 변경 파일이 없어 plan-structure 없이 진행 가능한 상태입니다."
    return "현재 변경은 plan-structure 없이 진행 가능한 범위입니다."


def _planning_guard_level(status: str, strict: bool) -> str:
    if status in {"fail"}:
        return "fail"
    if status in {"planning_required", "plan_exists_but_deviated"}:
        return "fail" if strict else "warn"
    return "pass"


def _merge_status(current: str, planning_level: str) -> str:
    rank = {"pass": 0, "warn": 1, "fail": 2}
    return (
        planning_level
        if rank.get(planning_level, 0) > rank.get(current, 0)
        else current
    )


def _classify_guard_path(rel_path: str) -> str:
    low = rel_path.lower()
    if low.startswith(".vibelign/"):
        return "meta"
    if low.startswith("docs/") or low.endswith(".md"):
        return "docs"
    if low.startswith("tests/") or "/tests/" in low or low.startswith("test_"):
        return "tests"
    if low in {"pyproject.toml", "package.json", "package-lock.json", "uv.lock"}:
        return "config"
    if (
        low.startswith(".claude/")
        or low.startswith(".github/")
        or low.endswith(".yaml")
        or low.endswith(".yml")
        or low.endswith(".toml")
    ):
        return "config"
    if low.startswith("vibelign/") or low.endswith(".py"):
        return "production"
    return "support"


def _load_plan_payload(
    meta: MetaPaths,
) -> tuple[dict[str, object] | None, str | None, str | None]:
    planning = load_planning_session(meta)
    if not planning:
        return None, None, None
    if planning.get("override") is True:
        plan_id = planning.get("plan_id")
        return None, str(plan_id) if isinstance(plan_id, str) else None, "override"
    if planning.get("active") is not True:
        return None, None, None
    plan_id = planning.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        return None, None, "invalid_state"
    plan_path = meta.plans_dir / f"{plan_id}.json"
    if not plan_path.exists():
        return None, plan_id, "missing_plan_file"
    try:
        loaded = cast(object, json.loads(plan_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None, plan_id, "broken_plan"
    if not isinstance(loaded, dict):
        return None, plan_id, "broken_plan"
    payload = cast(dict[str, object], loaded)
    required_keys = {
        "id",
        "schema_version",
        "allowed_modifications",
        "required_new_files",
        "forbidden",
        "messages",
        "evidence",
        "scope",
    }
    if not required_keys.issubset(payload.keys()):
        return None, plan_id, "broken_plan"
    allowed_modifications = payload.get("allowed_modifications")
    required_new_files = payload.get("required_new_files")
    forbidden = payload.get("forbidden")
    if not isinstance(allowed_modifications, list):
        return None, plan_id, "broken_plan"
    if not isinstance(required_new_files, list):
        return None, plan_id, "broken_plan"
    if not isinstance(forbidden, list):
        return None, plan_id, "broken_plan"
    for item in cast(list[object], allowed_modifications):
        if not isinstance(item, dict):
            return None, plan_id, "broken_plan"
    for item in cast(list[object], required_new_files):
        if not isinstance(item, dict):
            return None, plan_id, "broken_plan"
    for item in cast(list[object], forbidden):
        if not isinstance(item, dict):
            return None, plan_id, "broken_plan"
    return payload, plan_id, None


def _planning_threshold(meta: MetaPaths) -> int:
    if not meta.config_path.exists():
        return _SMALL_FIX_LINE_THRESHOLD
    try:
        content = meta.config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return _SMALL_FIX_LINE_THRESHOLD
    match = re.search(r"^small_fix_line_threshold:\s*(\d+)\s*$", content, re.MULTILINE)
    if not match:
        return _SMALL_FIX_LINE_THRESHOLD
    return int(match.group(1))


def _run_guard_git(root: Path, args: Sequence[str]) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=_WINDOWS_FLAGS,
        )
        return proc.returncode == 0, proc.stdout if proc.returncode == 0 else (
            proc.stderr or proc.stdout
        )
    except Exception as exc:
        return False, str(exc)


def _decode_guard_git_path(path: str) -> str:
    import unicodedata

    if not (path.startswith('"') and path.endswith('"')):
        return unicodedata.normalize("NFC", path)
    path = path[1:-1]
    buf = bytearray()
    index = 0
    while index < len(path):
        if (
            path[index] == "\\"
            and index + 3 < len(path)
            and path[index + 1 : index + 4].isdigit()
        ):
            buf.append(int(path[index + 1 : index + 4], 8))
            index += 4
        else:
            buf.extend(path[index].encode("utf-8"))
            index += 1
    try:
        return unicodedata.normalize("NFC", buf.decode("utf-8"))
    except UnicodeDecodeError:
        return path


def _status_to_change(status_code: str) -> str:
    return {
        "M": "modified",
        "A": "added",
        "D": "deleted",
        "R": "renamed",
        "??": "untracked",
    }.get(status_code, "changed")


def _guard_explain_report(root: Path, since_minutes: int) -> ExplainReport:
    staged_ok, staged_out = _run_guard_git(
        root, ["diff", "--cached", "--name-status", "--", "."]
    )
    if staged_ok and staged_out.strip():
        project_map, _project_map_error = load_project_map(root)
        items: list[ChangeItem] = []
        for line in staged_out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            status_code = parts[0].strip()[:1]
            rel = parts[-1].strip()
            decoded = _decode_guard_git_path(rel)
            items.append(
                ChangeItem(
                    decoded,
                    _status_to_change(status_code),
                    enrich_change_kind(project_map, decoded, classify_path(decoded)),
                )
            )
        return ExplainReport(
            "git-staged",
            f"staged 변경 {len(items)}개를 기준으로 검사했어요.",
            ["staged 변경을 우선 검사했습니다."],
            ["working tree 변경이 있어도 staged 기준으로 planning을 계산합니다."],
            risk_from_items(items),
            "staged 변경을 먼저 정리하거나 새 plan을 생성하세요.",
            [
                {"path": item.path, "status": item.status, "kind": item.kind}
                for item in items
            ],
        )
    explain_report = explain_from_git(root)
    if explain_report is not None:
        return explain_report
    return explain_from_mtime(root, since_minutes=since_minutes)


def _parse_diff_line_ranges(diff_text: str) -> tuple[int, list[tuple[int, int]]]:
    added_lines = 0
    ranges: list[tuple[int, int]] = []
    hunk_pattern = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
    for line in diff_text.splitlines():
        match = hunk_pattern.match(line)
        if not match:
            continue
        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count > 0:
            ranges.append((start, start + count - 1))
            added_lines += count
    return added_lines, ranges


def _anchor_ranges(path: Path) -> dict[str, tuple[int, int]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    starts: dict[str, int] = {}
    ranges: dict[str, tuple[int, int]] = {}
    for index, line in enumerate(lines, start=1):
        start_match = re.search(r"ANCHOR:\s*([A-Z0-9_]+)_START", line)
        if start_match:
            starts[start_match.group(1)] = index
        end_match = re.search(r"ANCHOR:\s*([A-Z0-9_]+)_END", line)
        if end_match:
            name = end_match.group(1)
            start = starts.get(name)
            if start is not None:
                ranges[name] = (start, index)
    return ranges


def _change_ranges_within_anchor(
    path: Path, anchor: str, ranges: list[tuple[int, int]]
) -> bool:
    anchor_ranges = _anchor_ranges(path)
    anchor_range = anchor_ranges.get(anchor)
    if anchor_range is None:
        return False
    anchor_start, anchor_end = anchor_range
    for start, end in ranges:
        if start < anchor_start or end > anchor_end:
            return False
    return True


def _file_change_details(
    root: Path, item: FileSummary, *, staged_only: bool
) -> FileChangeDetails:
    rel_path = str(item["path"])
    status = str(item["status"])
    path = root / rel_path
    if status in {"added", "untracked"}:
        if staged_only:
            ok, staged_content = _run_guard_git(root, ["show", f":{rel_path}"])
            if ok:
                line_count = len(staged_content.splitlines())
                return {
                    "added_lines": line_count,
                    "ranges": [(1, line_count)] if line_count else [],
                }
        try:
            line_count = len(path.read_text(encoding="utf-8").splitlines())
        except OSError:
            line_count = 0
        return {
            "added_lines": line_count,
            "ranges": [(1, line_count)] if line_count else [],
        }
    diff_args = ["diff", "--unified=0"]
    if staged_only:
        diff_args.append("--cached")
    else:
        diff_args.append("HEAD")
    diff_args.extend(["--", rel_path])
    ok, diff = _run_guard_git(root, diff_args)
    if not ok:
        return {"added_lines": 0, "ranges": []}
    added_lines, ranges = _parse_diff_line_ranges(diff)
    return {"added_lines": added_lines, "ranges": ranges}


def _is_import_wiring_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("import ") or stripped.startswith("from ")


def _is_registration_line(line: str) -> bool:
    stripped = line.strip()
    registration_tokens = (
        "register(",
        ".register(",
        "add_parser(",
        ".add_parser(",
        "set_defaults(",
        ".set_defaults(",
        "router.add_",
        "app.add_",
    )
    return any(token in stripped for token in registration_tokens)


def _modified_change_types(root: Path, rel_path: str, *, staged_only: bool) -> set[str]:
    diff_args = ["diff", "--unified=0"]
    if staged_only:
        diff_args.append("--cached")
    else:
        diff_args.append("HEAD")
    diff_args.extend(["--", rel_path])
    ok, diff = _run_guard_git(root, diff_args)
    if not ok:
        return {"edit"}
    added: list[str] = []
    removed: list[str] = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
    parsed = {"added": added, "removed": removed}
    changed_lines = [
        str(line) for line in parsed["added"] + parsed["removed"] if str(line).strip()
    ]
    if not changed_lines:
        return {"edit"}
    detected: set[str] = {"edit"}
    if all(_is_import_wiring_line(line) for line in changed_lines):
        detected.add("import_wiring")
    if all(_is_registration_line(line) for line in changed_lines):
        detected.add("registration")
    if _classify_guard_path(rel_path) == "config":
        detected.add("config_touch")
    return detected


def _planning_data(
    root: Path,
    meta: MetaPaths,
    strict: bool,
    explain_files: Sequence[FileSummary],
    explain_source: str,
) -> PlanningData:
    threshold = _planning_threshold(meta)
    staged_only = explain_source == "git-staged"
    changed_files = [str(item["path"]) for item in explain_files]
    if not changed_files:
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": None,
            "summary": _planning_exempt_summary(["no_changed_files"]),
            "changed_files": [],
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": ["no_changed_files"],
        }

    plan_payload, active_plan_id, plan_error = _load_plan_payload(meta)
    if plan_error == "override":
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": active_plan_id,
            "summary": _planning_exempt_summary(["override"]),
            "changed_files": changed_files,
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": ["override"],
        }

    production_items = [
        item
        for item in explain_files
        if _classify_guard_path(str(item["path"])) == "production"
    ]
    relevant_items = [
        item
        for item in explain_files
        if _classify_guard_path(str(item["path"])) != "meta"
    ]
    new_production_items = [
        item
        for item in production_items
        if str(item["status"]) in {"added", "untracked"}
    ]
    docs_only = (
        all(
            _classify_guard_path(str(item["path"])) == "docs" for item in relevant_items
        )
        if relevant_items
        else False
    )
    tests_only = (
        all(
            _classify_guard_path(str(item["path"])) == "tests"
            for item in relevant_items
        )
        if relevant_items
        else False
    )
    config_only = (
        all(
            _classify_guard_path(str(item["path"])) == "config"
            for item in relevant_items
        )
        if relevant_items
        else False
    )
    small_fix_candidate = False
    if len(production_items) == 1 and len(relevant_items) == 1:
        item = production_items[0]
        if str(item["status"]) not in {"added", "untracked", "deleted", "renamed"}:
            details = _file_change_details(root, item, staged_only=staged_only)
            small_fix_candidate = details["added_lines"] <= threshold

    exempt_reasons: list[str] = []
    if docs_only:
        exempt_reasons.append("docs_only")
    if tests_only:
        exempt_reasons.append("tests_only")
    if config_only:
        exempt_reasons.append("config_only")
    if exempt_reasons:
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": active_plan_id,
            "summary": _planning_exempt_summary(exempt_reasons),
            "changed_files": changed_files,
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": exempt_reasons,
        }

    forbidden_paths: set[str] = set()
    if isinstance(plan_payload, dict):
        forbidden_obj = plan_payload.get("forbidden", [])
        if isinstance(forbidden_obj, list):
            forbidden_items = cast(list[object], forbidden_obj)
            for item in forbidden_items:
                if isinstance(item, dict):
                    item_dict = cast(dict[str, object], item)
                    path = item_dict.get("path")
                    if isinstance(path, str):
                        forbidden_paths.add(path)

    if small_fix_candidate and not any(
        str(item["path"]) in forbidden_paths for item in relevant_items
    ):
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": active_plan_id,
            "summary": _planning_exempt_summary(["small_single_file_fix"]),
            "changed_files": changed_files,
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": ["small_single_file_fix"],
        }

    required_reasons: list[str] = []
    if new_production_items:
        required_reasons.append("new_production_file")
    if len(production_items) >= 2:
        required_reasons.append("multi_file_production_edit")

    if plan_error in {"missing_plan_file", "broken_plan", "invalid_state"}:
        reason_text = {
            "missing_plan_file": "plan 파일이 없습니다.",
            "broken_plan": "plan 파일이 파손되었습니다.",
            "invalid_state": "planning state가 올바르지 않습니다.",
        }[plan_error]
        return {
            "status": "fail",
            "strict": strict,
            "active_plan_id": active_plan_id,
            "summary": f"{_planning_message('fail')} {reason_text}",
            "changed_files": changed_files,
            "required_reasons": required_reasons,
            "deviations": [plan_error],
            "exempt_reasons": [],
        }

    if not required_reasons and (
        not production_items or (plan_payload is None and plan_error is None)
    ):
        return {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": active_plan_id,
            "summary": _planning_exempt_summary(exempt_reasons or ["default_exempt"]),
            "changed_files": changed_files,
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": exempt_reasons or ["default_exempt"],
        }

    if plan_payload is None:
        return {
            "status": "planning_required",
            "strict": strict,
            "active_plan_id": None,
            "summary": f"{_planning_message('planning_required')} 이유: {', '.join(required_reasons)}",
            "changed_files": changed_files,
            "required_reasons": required_reasons,
            "deviations": [],
            "exempt_reasons": exempt_reasons,
        }

    allowed_modifications = cast(
        list[dict[str, object]], plan_payload.get("allowed_modifications", [])
    )
    required_new_files = cast(
        list[dict[str, object]], plan_payload.get("required_new_files", [])
    )
    forbidden_rules = cast(list[dict[str, object]], plan_payload.get("forbidden", []))

    allowed_by_path = {
        str(item["path"]): item
        for item in allowed_modifications
        if isinstance(item.get("path"), str)
    }
    required_new_paths = {
        str(item["path"])
        for item in required_new_files
        if isinstance(item.get("path"), str)
    }

    deviations: list[str] = []
    hard_fail = False
    for item in relevant_items:
        rel_path = str(item["path"])
        status = str(item["status"])
        details = _file_change_details(root, item, staged_only=staged_only)
        for rule in forbidden_rules:
            rule_path = rule.get("path")
            if rule_path == rel_path:
                anchor = rule.get("anchor")
                if isinstance(anchor, str):
                    if not _change_ranges_within_anchor(
                        root / rel_path,
                        anchor,
                        details["ranges"],
                    ):
                        hard_fail = True
                        deviations.append(f"forbidden:{rel_path}")
                else:
                    hard_fail = True
                    deviations.append(f"forbidden:{rel_path}")
        if status in {"added", "untracked"}:
            if rel_path not in required_new_paths:
                deviations.append(f"unexpected_new_file:{rel_path}")
            continue
        if status in {"deleted", "renamed"}:
            allowed = allowed_by_path.get(rel_path)
            if allowed is None or status not in cast(
                list[object], allowed.get("allowed_change_types", [])
            ):
                deviations.append(f"unexpected_{status}:{rel_path}")
                continue
            continue
        allowed = allowed_by_path.get(rel_path)
        if allowed is None:
            deviations.append(f"unexpected_change:{rel_path}")
            continue
        allowed_change_types = cast(
            list[object], allowed.get("allowed_change_types", [])
        )
        if allowed_change_types:
            detected_change_types = _modified_change_types(
                root, rel_path, staged_only=staged_only
            )
            allowed_change_type_names = {str(item) for item in allowed_change_types}
            if detected_change_types.isdisjoint(allowed_change_type_names):
                deviations.append(
                    f"disallowed_change_type:{'/'.join(sorted(detected_change_types))}:{rel_path}"
                )
                continue
        anchor = allowed.get("anchor")
        if isinstance(anchor, str) and not _change_ranges_within_anchor(
            root / rel_path, anchor, details["ranges"]
        ):
            deviations.append(f"anchor_outside_allowed_range:{rel_path}")
        max_lines_added = allowed.get("max_lines_added")
        if (
            isinstance(max_lines_added, int)
            and details["added_lines"] > max_lines_added
        ):
            deviations.append(f"max_lines_added_exceeded:{rel_path}")

    if hard_fail:
        return {
            "status": "fail",
            "strict": strict,
            "active_plan_id": active_plan_id,
            "summary": f"{_planning_message('fail')} 이유: {', '.join(deviations)}",
            "changed_files": changed_files,
            "required_reasons": required_reasons,
            "deviations": deviations,
            "exempt_reasons": exempt_reasons,
        }
    if deviations:
        return {
            "status": "plan_exists_but_deviated",
            "strict": strict,
            "active_plan_id": active_plan_id,
            "summary": f"{_planning_message('plan_exists_but_deviated')} 이유: {', '.join(deviations)}",
            "changed_files": changed_files,
            "required_reasons": required_reasons,
            "deviations": deviations,
            "exempt_reasons": exempt_reasons,
        }
    return {
        "status": "pass",
        "strict": strict,
        "active_plan_id": active_plan_id,
        "summary": _planning_message("pass"),
        "changed_files": changed_files,
        "required_reasons": required_reasons,
        "deviations": [],
        "exempt_reasons": exempt_reasons,
    }


# === ANCHOR: VIB_GUARD_CMD__GUARD_STATUS_START ===
def _guard_status(report: GuardReport) -> str:
    if report.blocked:
        return "fail"
    if report.overall_level == "WARNING":
        return "warn"
    return "pass"


# === ANCHOR: VIB_GUARD_CMD__GUARD_STATUS_END ===


# === ANCHOR: VIB_GUARD_CMD__REWRITE_RECOMMENDATIONS_START ===
def _rewrite_recommendations(recommendations: list[str]) -> list[str]:
    rewritten: list[str] = []
    for item in recommendations:
        rewritten.append(
            item.replace("`vibelign anchor`", "`vib anchor --suggest`")
            .replace("vibelign undo", "vib undo")
            .replace("vibelign", "vib")
        )
    return rewritten


# === ANCHOR: VIB_GUARD_CMD__REWRITE_RECOMMENDATIONS_END ===


# === ANCHOR: VIB_GUARD_CMD__PROTECTED_VIOLATIONS_START ===
def _protected_violations(
    root: Path, explain_files: Sequence[FileSummary]
) -> list[str]:
    protected = get_protected(root)
    if not protected:
        return []
    violations: list[str] = []
    for item in explain_files:
        path = item["path"]
        if is_protected(path, protected):
            violations.append(path)
    return violations


# === ANCHOR: VIB_GUARD_CMD__PROTECTED_VIOLATIONS_END ===


# === ANCHOR: VIB_GUARD_CMD__BUILD_GUARD_ENVELOPE_START ===
def _build_guard_envelope(
    root: Path,
    strict: bool,
    since_minutes: int,
    # === ANCHOR: VIB_GUARD_CMD__BUILD_GUARD_ENVELOPE_END ===
) -> GuardEnvelope:
    legacy_doctor = analyze_project(root, strict=strict)
    explain_report_obj = _guard_explain_report(root, since_minutes)
    explain_report = (
        explain_report_obj
        if hasattr(explain_report_obj, "files")
        else explain_from_mtime(root, since_minutes=since_minutes)
    )
    legacy_guard = combine_guard(legacy_doctor, explain_report)
    doctor_v2 = analyze_project_v2(root, strict=strict)
    violations = _protected_violations(root, explain_report.files)
    status = _guard_status(legacy_guard)
    if strict and status == "warn":
        status = "fail"
    explain_data: GuardExplainData = {
        "source": explain_report.source,
        "risk_level": explain_report.risk_level,
        "files": explain_report.files,
        "summary": explain_report.summary,
    }
    data: GuardData = {
        "status": status,
        "strict": strict,
        "blocked": legacy_guard.blocked or (strict and status == "fail"),
        "project_score": doctor_v2.project_score,
        "project_status": doctor_v2.status,
        "change_risk_level": legacy_guard.change_risk_level,
        "summary": legacy_guard.summary,
        "recommendations": _rewrite_recommendations(legacy_guard.recommendations),
        "protected_violations": violations,
        "doctor": doctor_v2.to_dict(),
        "explain": explain_data,
        "planning": {
            "status": "planning_exempt",
            "strict": strict,
            "active_plan_id": None,
            "summary": _planning_message("planning_exempt"),
            "changed_files": [],
            "required_reasons": [],
            "deviations": [],
            "exempt_reasons": ["default_exempt"],
        },
    }
    planning = _planning_data(
        root,
        MetaPaths(root),
        strict,
        explain_report.files,
        explain_report.source,
    )
    data["planning"] = planning
    planning_level = _planning_guard_level(planning["status"], strict)
    data["status"] = _merge_status(status, planning_level)
    data["blocked"] = bool(data["blocked"] or data["status"] == "fail")
    if planning_level != "pass":
        data["summary"] = f"{data['summary']}\n\n구조 계획: {planning['summary']}"
        recommendations = list(data["recommendations"])
        if _PLAN_REQUIRED_RECOMMENDATION not in recommendations:
            recommendations.append(_PLAN_REQUIRED_RECOMMENDATION)
        data["recommendations"] = recommendations
    return {"ok": True, "error": None, "data": data}


def build_guard_envelope(root: Path, strict: bool, since_minutes: int) -> GuardEnvelope:
    return _build_guard_envelope(root, strict=strict, since_minutes=since_minutes)


# === ANCHOR: VIB_GUARD_CMD__RENDER_MARKDOWN_START ===
def _render_markdown(data: GuardData) -> str:
    status_label = {
        "pass": "통과",
        "warn": "주의",
        "fail": "중지",
    }.get(str(data["status"]), str(data["status"]))
    status_hint = {
        "pass": "지금은 큰 위험이 없어 보여요. 다음 단계로 넘어가도 됩니다.",
        "warn": "바로 멈출 정도는 아니지만, 먼저 한 번 더 확인하는 게 좋아요.",
        "fail": "지금은 다음 작업으로 넘어가기보다, 먼저 문제를 해결하는 게 좋아요.",
    }.get(str(data["status"]), "현재 상태를 먼저 확인해보세요.")
    lines = [
        "# VibeLign 가드 리포트",
        "",
        f"전체 상태: {status_label}",
        status_hint,
        f"엄격 모드: {'예' if data['strict'] else '아니오'}",
        f"프로젝트 점수: {data['project_score']} / 100",
        f"프로젝트 기본 상태: {data['project_status']}",
        f"최근 바뀐 내용의 위험도: {data['change_risk_level']}",
        "",
        "## 요약",
        str(data["summary"]),
        "",
    ]
    planning = data.get("planning")
    if planning:
        lines.extend(
            [
                "## 구조 계획 판정",
                f"- 상태: {planning.get('status')}",
                f"- 활성 plan: {planning.get('active_plan_id') or '없음'}",
                f"- 요약: {planning.get('summary')}",
            ]
        )
        changed_files = cast(list[object], planning.get("changed_files", []))
        if changed_files:
            lines.append("- 변경 파일:")
            lines.extend([f"  - `{item}`" for item in changed_files])
        required_reasons = cast(list[object], planning.get("required_reasons", []))
        if required_reasons:
            lines.append("- 필요 이유:")
            lines.extend([f"  - {item}" for item in required_reasons])
        deviations = cast(list[object], planning.get("deviations", []))
        if deviations:
            lines.append("- 이탈 항목:")
            lines.extend([f"  - {item}" for item in deviations])
        lines.append("")
    if data["protected_violations"]:
        lines.extend(["## 보호된 파일에서 바뀐 점"])
        lines.extend([f"- `{item}`" for item in data["protected_violations"]])
        lines.append("")
    lines.extend(["## 다음에 하면 좋은 일"])
    lines.extend([f"- {item}" for item in data["recommendations"]])
    lines.extend(["", "## 최근 바뀐 파일"])
    files = data["explain"]["files"]
    if files:
        lines.extend(
            [f"- `{item['path']}` ({item['status']}, {item['kind']})" for item in files]
        )
    else:
        lines.append("- 최근에 바뀐 파일이 없습니다.")
    return "\n".join(lines) + "\n"


# === ANCHOR: VIB_GUARD_CMD__RENDER_MARKDOWN_END ===


# === ANCHOR: VIB_GUARD_CMD__UPDATE_GUARD_STATE_START ===
def _update_guard_state(meta: MetaPaths, quiet: bool = False) -> None:
    if not meta.state_path.exists():
        return
    try:
        raw_state_obj = cast(
            object, json.loads(meta.state_path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        if not quiet:
            print("가드 상태 파일을 읽지 못해 마지막 실행 시간 기록은 건너뜁니다.")
        return
    if not isinstance(raw_state_obj, dict):
        return
    raw_state = cast(dict[object, object], raw_state_obj)
    state = {str(key): value for key, value in raw_state.items()}
    state["last_guard_run_at"] = datetime.now(timezone.utc).isoformat()
    try:
        _ = meta.state_path.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError:
        if not quiet:
            print("가드 상태 파일을 저장하지 못해 마지막 실행 시간 기록은 건너뜁니다.")


# === ANCHOR: VIB_GUARD_CMD__UPDATE_GUARD_STATE_END ===


# === ANCHOR: VIB_GUARD_CMD_RUN_VIB_GUARD_START ===
def run_vib_guard(args: GuardArgs) -> None:
    root = resolve_project_root(Path.cwd())
    meta = MetaPaths(root)
    envelope = _build_guard_envelope(
        root, strict=args.strict, since_minutes=args.since_minutes
    )
    _update_guard_state(meta, quiet=args.json)
    if args.json:
        text = json.dumps(envelope, indent=2, ensure_ascii=False)
        print(text)
        if args.write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("guard", "json").write_text(
                text + "\n", encoding="utf-8"
            )
        if envelope["data"]["status"] == "fail":
            raise SystemExit(1)
        return
    markdown = _render_markdown(envelope["data"])
    print_ai_response(markdown)
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("guard", "md").write_text(markdown, encoding="utf-8")
    if envelope["data"]["status"] == "fail":
        raise SystemExit(1)


# === ANCHOR: VIB_GUARD_CMD_RUN_VIB_GUARD_END ===
# === ANCHOR: VIB_GUARD_CMD_END ===
