# === ANCHOR: VIB_DOCTOR_CMD_START ===
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vibelign.core.doctor_v2 import (
    DoctorV2Report,
    build_doctor_envelope,
    render_doctor_json,
    render_doctor_markdown,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import print_ai_response


from vibelign.terminal_render import cli_print

print = cli_print


def _update_doctor_state(meta: MetaPaths) -> None:
    if not meta.state_path.exists():
        return
    state = json.loads(meta.state_path.read_text(encoding="utf-8"))
    state["last_scan_at"] = datetime.now(timezone.utc).isoformat()
    _ = meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _run_fix(root: Path) -> None:
    """앵커 없는 파일에 자동으로 앵커 삽입."""
    from vibelign.core.anchor_tools import extract_anchors, insert_module_anchors
    from vibelign.core.project_scan import iter_source_files
    from vibelign.terminal_render import clack_info, clack_step, clack_success

    targets = [
        p for p in iter_source_files(root)
        if not extract_anchors(p)
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
        clack_success(f"앵커 {fixed}개 파일에 추가 완료! vib scan 으로 코드맵도 갱신하세요.")
    else:
        clack_info("앵커를 추가할 수 있는 파일이 없었어요.")


def run_vib_doctor(args: Any) -> None:
    root = Path.cwd()
    envelope = build_doctor_envelope(root, strict=args.strict)
    report = envelope["data"]
    meta = MetaPaths(root)
    _update_doctor_state(meta)

    if args.json:
        text = render_doctor_json(envelope)
        print(text)
        if args.write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("doctor", "json").write_text(
                text + "\n", encoding="utf-8"
            )
        if args.strict and report["status"] in {"Risky", "High Risk"}:
            raise SystemExit(1)
        return

    report_obj = DoctorV2Report(
        project_score=report["project_score"],
        status=report["status"],
        anchor_coverage=report["anchor_coverage"],
        stats=report["stats"],
        issues=report["issues"],
        recommended_actions=report["recommended_actions"],
    )
    markdown = render_doctor_markdown(
        report=report_obj,
        detailed=args.detailed,
        fix_hints=args.fix_hints,
    )
    print_ai_response(markdown)

    if getattr(args, "fix", False):
        _run_fix(root)

    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("doctor", "md").write_text(markdown, encoding="utf-8")
    if args.strict and report["status"] in {"Risky", "High Risk"}:
        raise SystemExit(1)


# === ANCHOR: VIB_DOCTOR_CMD_END ===
