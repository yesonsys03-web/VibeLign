# === ANCHOR: VIB_DOCTOR_CMD_START ===
import json
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from vibelign.action_engine.action_planner import generate_plan
from vibelign.action_engine.executors.action_executor import execute_plan
from vibelign.action_engine.generators.patch_generator import generate_patch_preview
from vibelign.core.risk_analyzer import RiskReport, analyze_project
from vibelign.core.doctor_v2 import (
    DoctorV2Report,
    analyze_project_v2,
    build_doctor_envelope,
    render_doctor_json,
    render_doctor_markdown,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


def build_legacy_doctor_output(
    root: Path, *, strict: bool, as_json: bool
) -> tuple[str, bool]:
    report = analyze_project(root, strict=strict)
    if as_json:
        return json.dumps(report.to_dict(), indent=2), True

    return _render_legacy_doctor_markdown(report), False


def _render_legacy_doctor_markdown(report: RiskReport) -> str:
    lines = [
        "# VibeLign Doctor Report",
        "",
        f"## 1. 지금 상태\n지금 프로젝트 상태는 `{report.level}`이고, 점수는 `{report.score}`입니다.",
        "",
        "## 2. 한눈에 보는 숫자",
        f"- 전체 파일 수: {report.stats.get('files_scanned', 0)}",
        f"- 소스 파일 수: {report.stats.get('source_files_scanned', 0)}",
        f"- 처음부터 중요한 역할을 하는 큰 파일 수: {report.stats.get('oversized_entry_files', 0)}",
        f"- 안전 구역 표시가 없는 파일 수: {report.stats.get('missing_anchor_files', 0)}",
        "",
    ]
    if not report.issues:
        lines.extend(
            ["## 3. 확인된 점", "- 지금 바로 걱정할 큰 구조 문제는 보이지 않습니다."]
        )
        return "\n".join(lines) + "\n"

    lines.extend(["## 3. 먼저 보면 좋은 문제"])
    for index, issue in enumerate(report.issues, 1):
        lines.append(f"{index}. {issue.get('found', '')}")
    lines.extend(["", "## 4. 다음에 하면 좋은 일"])
    for index, suggestion in enumerate(report.suggestions, 1):
        lines.append(f"{index}. {suggestion}")
    return "\n".join(lines) + "\n"


def _update_doctor_state(meta: MetaPaths) -> None:
    if not meta.state_path.exists():
        return
    loaded = cast(object, json.loads(meta.state_path.read_text(encoding="utf-8")))
    if not isinstance(loaded, dict):
        return
    state = cast(dict[str, object], loaded)
    state["last_scan_at"] = datetime.now(timezone.utc).isoformat()
    _ = meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _run_fix(root: Path) -> None:
    """앵커 없는 파일에 자동으로 앵커 삽입."""
    from vibelign.core.anchor_tools import extract_anchors, insert_module_anchors
    from vibelign.core.project_scan import iter_source_files
    from vibelign.core.project_scan import safe_read_text
    from vibelign.core.structure_policy import is_trivial_package_init
    from vibelign.terminal_render import clack_info, clack_step, clack_success

    targets = [
        p
        for p in iter_source_files(root)
        if not extract_anchors(p) and not is_trivial_package_init(p, safe_read_text(p))
    ]
    if not targets:
        clack_info("앵커가 없는 파일이 없어요. 이미 다 표시되어 있어요!")
        return

    clack_step(f"앵커 없는 파일 {len(targets)}개에 자동으로 앵커를 추가할게요...")
    fixed = 0
    for p in targets:
        if insert_module_anchors(p):
            rel = p.relative_to(root)
            clack_info(f"  + {rel}")
            fixed += 1
    if fixed:
        clack_success(
            f"앵커 {fixed}개 파일에 추가 완료! vib scan 으로 코드맵도 갱신하세요."
        )
    else:
        clack_info("앵커를 추가할 수 있는 파일이 없었어요.")


def _run_plan(root: Path, strict: bool, as_json: bool) -> None:
    """실행 계획 출력 — 파일 수정 없음."""
    from vibelign.terminal_render import clack_step

    if not as_json:
        clack_step("프로젝트 분석 중...")
    report = analyze_project_v2(root, strict=strict)
    plan = generate_plan(report)

    if as_json:
        import json as _json

        print(_json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "VibeLign 실행 계획 (--plan)",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"현재 점수: {plan.source_score} / 100",
        f"실행 단계: {len(plan.actions)}개",
        "",
    ]
    if not plan.actions:
        lines.append("✓ 지금 당장 할 일이 없어요. 프로젝트 상태가 좋아요!")
    else:
        for i, action in enumerate(plan.actions, 1):
            cmd_hint = f"  → {action.command}" if action.command else ""
            path_hint = f" ({action.target_path})" if action.target_path else ""
            lines.append(f"{i}. [{action.action_type}]{path_hint}")
            lines.append(f"   {action.description[:80]}")
            if cmd_hint:
                lines.append(cmd_hint)
    if plan.warnings:
        lines.extend(["", "⚠️  주의:"])
        for w in plan.warnings:
            lines.append(f"  - {w}")
    lines.extend(
        [
            "",
            "※ 이 계획은 파일을 수정하지 않아요. 적용하려면 vib doctor --apply 를 사용하세요.",
        ]
    )
    print_ai_response("\n".join(lines) + "\n")


def _run_patch(root: Path, strict: bool, as_json: bool) -> None:
    """변경 예정 미리보기 출력 — 파일 수정 없음."""
    from vibelign.terminal_render import clack_step

    if not as_json:
        clack_step("프로젝트 분석 중...")
    report = analyze_project_v2(root, strict=strict)
    plan = generate_plan(report)

    if as_json:
        import json as _json

        preview_lines: list[object] = []
        for action in plan.actions:
            preview_lines.append(action.to_dict())
        print(
            _json.dumps(
                {"ok": True, "plan": plan.to_dict()}, indent=2, ensure_ascii=False
            )
        )
        return

    preview = generate_patch_preview(plan, root)
    print_ai_response(preview)


def _run_apply(root: Path, strict: bool, as_json: bool, force: bool = False) -> None:
    """자동 리팩토링 실행 — checkpoint 생성 후 적용."""
    import json as _json
    from vibelign.terminal_render import (
        clack_step,
        clack_success,
        clack_info,
        clack_warn,
    )

    def _step(msg: str) -> None:
        if not as_json:
            clack_step(msg)

    _step("프로젝트 분석 중...")
    report = analyze_project_v2(root, strict=strict)
    plan = generate_plan(report)

    if not plan.actions:
        msg = "실행할 항목이 없습니다. 프로젝트 상태가 좋아요!"
        if as_json:
            print(_json.dumps({"ok": True, "message": msg}, ensure_ascii=False))
        else:
            clack_success(msg)
        return

    result = execute_plan(plan, root, force=force, quiet=as_json)

    if result.aborted:
        if as_json:
            print(_json.dumps({"ok": False, "error": "aborted"}, ensure_ascii=False))
        else:
            clack_warn("취소됐습니다.")
        return

    if as_json:
        print(
            _json.dumps(
                {
                    "ok": True,
                    "checkpoint_id": result.checkpoint_id,
                    "done": result.done_count,
                    "manual": result.manual_count,
                    "results": [
                        {
                            "action_type": r.action.action_type,
                            "status": r.status,
                            "detail": r.detail,
                        }
                        for r in result.results
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    print()
    clack_success(
        f"완료: {result.done_count}개 자동 적용, {result.manual_count}개 수동 필요"
    )
    if result.checkpoint_id:
        clack_info(
            f"복원하려면: vib undo --checkpoint-id {result.checkpoint_id} --force"
        )

    manual_items = [r for r in result.results if r.status == "manual"]
    if manual_items:
        print("\n수동으로 실행하세요:")
        for r in manual_items:
            print(f"  {r.detail}")


def run_vib_doctor(args: Namespace) -> None:
    root = resolve_project_root(Path.cwd())
    strict = bool(getattr(args, "strict", False))
    as_json = bool(getattr(args, "json", False))
    write_report = bool(getattr(args, "write_report", False))
    fix = bool(getattr(args, "fix", False))
    detailed = bool(getattr(args, "detailed", False))
    fix_hints = bool(getattr(args, "fix_hints", False))
    plan_mode = bool(getattr(args, "plan", False))
    patch_mode = bool(getattr(args, "patch", False))
    apply_mode = bool(getattr(args, "apply", False))
    force = bool(getattr(args, "force", False))

    if plan_mode:
        _run_plan(root, strict=strict, as_json=as_json)
        return

    if patch_mode:
        _run_patch(root, strict=strict, as_json=as_json)
        return

    if apply_mode:
        _run_apply(root, strict=strict, as_json=as_json, force=force)
        return

    envelope = build_doctor_envelope(root, strict=strict)
    report = cast(dict[str, object], envelope["data"])
    meta = MetaPaths(root)
    _update_doctor_state(meta)

    if as_json:
        text = render_doctor_json(envelope)
        print(text)
        if write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("doctor", "json").write_text(
                text + "\n", encoding="utf-8"
            )
        if strict and report["status"] in {"Risky", "High Risk"}:
            raise SystemExit(1)
        return

    report_obj = DoctorV2Report(
        project_score=cast(int, report["project_score"]),
        status=cast(str, report["status"]),
        anchor_coverage=cast(int, report["anchor_coverage"]),
        stats=cast(dict[str, object], report["stats"]),
        issues=cast(list[dict[str, object]], report["issues"]),
        recommended_actions=cast(list[str], report["recommended_actions"]),
    )
    markdown = render_doctor_markdown(
        report=report_obj,
        detailed=detailed,
        fix_hints=fix_hints,
    )
    print_ai_response(markdown)

    if fix:
        _run_fix(root)

    if write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("doctor", "md").write_text(markdown, encoding="utf-8")
    if strict and report["status"] in {"Risky", "High Risk"}:
        raise SystemExit(1)


# === ANCHOR: VIB_DOCTOR_CMD_END ===
