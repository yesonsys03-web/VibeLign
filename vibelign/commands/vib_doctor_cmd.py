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
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("doctor", "md").write_text(markdown, encoding="utf-8")
    if args.strict and report["status"] in {"Risky", "High Risk"}:
        raise SystemExit(1)


# === ANCHOR: VIB_DOCTOR_CMD_END ===
