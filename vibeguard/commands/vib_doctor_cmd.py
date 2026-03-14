# === ANCHOR: VIB_DOCTOR_CMD_START ===
from pathlib import Path
from typing import Any

from vibeguard.core.doctor_v2 import (
    DoctorV2Report,
    build_doctor_envelope,
    render_doctor_json,
    render_doctor_markdown,
)
from vibeguard.core.meta_paths import MetaPaths


def run_vib_doctor(args: Any) -> None:
    root = Path.cwd()
    envelope = build_doctor_envelope(root, strict=args.strict)
    report = envelope["data"]
    meta = MetaPaths(root)

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
    print(markdown, end="")
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("doctor", "md").write_text(markdown, encoding="utf-8")
    if args.strict and report["status"] in {"Risky", "High Risk"}:
        raise SystemExit(1)
# === ANCHOR: VIB_DOCTOR_CMD_END ===
