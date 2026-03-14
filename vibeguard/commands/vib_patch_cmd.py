# === ANCHOR: VIB_PATCH_CMD_START ===
import json
import importlib
from pathlib import Path
from typing import Any, Dict, Optional

from vibeguard.core.codespeak import build_codespeak
from vibeguard.core.meta_paths import MetaPaths
from vibeguard.core.patch_suggester import suggest_patch
from vibeguard.core.project_scan import safe_read_text


def _render_preview(target_path: Path, target_anchor: str) -> str:
    text = safe_read_text(target_path)
    if not text:
        return "[미리보기 불가] 파일 내용을 읽지 못했습니다."
    lines = text.splitlines()
    if target_anchor and target_anchor not in {"[없음]", "[먼저 앵커를 추가하세요]"}:
        anchor_line = next(
            (idx for idx, line in enumerate(lines) if target_anchor in line), None
        )
        if anchor_line is not None:
            start = max(0, anchor_line - 2)
            end = min(len(lines), anchor_line + 8)
            snippet = lines[start:end]
            return "\n".join(snippet)
    return "\n".join(lines[:10])


def _build_patch_data(root: Path, request: str) -> Dict[str, Any]:
    suggestion = suggest_patch(root, request)
    codespeak = build_codespeak(request)
    confidence = suggestion.confidence
    if confidence == "high" and codespeak.confidence != "high":
        confidence = codespeak.confidence
    return {
        "patch_plan": {
            "schema_version": 1,
            "request": request,
            "interpretation": codespeak.interpretation,
            "target_file": suggestion.target_file,
            "target_anchor": suggestion.target_anchor,
            "codespeak": codespeak.codespeak,
            "constraints": [
                "patch only",
                "keep file structure",
                "no unrelated edits",
            ],
            "confidence": confidence,
            "preview_available": True,
            "clarifying_questions": codespeak.clarifying_questions,
            "rationale": suggestion.rationale,
        }
    }


def _build_patch_data_with_options(
    root: Path, request: str, use_ai: bool, quiet_ai: bool
) -> Dict[str, Any]:
    suggestion = suggest_patch(root, request)
    codespeak = build_codespeak(request)
    if use_ai:
        ai_codespeak = importlib.import_module("vibeguard.core.ai_codespeak")
        ai_explain = importlib.import_module("vibeguard.core.ai_explain")
        if ai_explain.has_ai_provider():
            try:
                enhanced = ai_codespeak.enhance_codespeak_with_ai(
                    request, codespeak, quiet=quiet_ai
                )
            except Exception:
                enhanced = None
            if enhanced is not None:
                codespeak = enhanced
    confidence = suggestion.confidence
    if confidence == "high" and codespeak.confidence != "high":
        confidence = codespeak.confidence
    return {
        "patch_plan": {
            "schema_version": 1,
            "request": request,
            "interpretation": codespeak.interpretation,
            "target_file": suggestion.target_file,
            "target_anchor": suggestion.target_anchor,
            "codespeak": codespeak.codespeak,
            "constraints": [
                "patch only",
                "keep file structure",
                "no unrelated edits",
            ],
            "confidence": confidence,
            "preview_available": True,
            "clarifying_questions": codespeak.clarifying_questions,
            "rationale": suggestion.rationale,
        }
    }


def _render_markdown(data: Dict[str, Any], preview_text: Optional[str] = None) -> str:
    patch_plan = data["patch_plan"]
    lines = [
        "# VibeLign Patch Plan",
        "",
        f"Interpretation: {patch_plan['interpretation']}",
        f"CodeSpeak: {patch_plan['codespeak']}",
        f"Confidence: {patch_plan['confidence']}",
        f"Target file: {patch_plan['target_file']}",
        f"Target anchor: {patch_plan['target_anchor']}",
        "",
        "Rationale:",
    ]
    lines.extend(f"- {item}" for item in patch_plan["rationale"])
    if patch_plan["clarifying_questions"]:
        lines.extend(["", "Clarifying questions:"])
        lines.extend(f"- {item}" for item in patch_plan["clarifying_questions"])
    if preview_text is not None:
        lines.extend(["", "Preview:", "```text", preview_text, "```"])
    lines.extend(
        [
            "",
            "Next step: AI 도구에 이 계획을 전달하거나, `vib patch --preview` 결과를 먼저 검토하세요.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_vib_patch(args: Any) -> None:
    root = Path.cwd()
    request = " ".join(args.request).strip()
    data = _build_patch_data_with_options(
        root, request, use_ai=args.ai, quiet_ai=args.json
    )
    patch_plan = data["patch_plan"]
    preview_text = None
    target_path = root / patch_plan["target_file"]
    if args.preview and target_path.exists():
        preview_text = _render_preview(target_path, patch_plan["target_anchor"])
        data["preview"] = {
            "schema_version": 1,
            "format": "ascii",
            "target_file": patch_plan["target_file"],
            "target_anchor": patch_plan["target_anchor"],
            "before_summary": "현재 파일 일부 미리보기입니다.",
            "after_summary": "AI 편집 전에 이 구역을 검토하세요.",
            "confidence": patch_plan["confidence"],
        }

    envelope = {"ok": True, "error": None, "data": data}
    meta = MetaPaths(root)

    if args.json:
        text = json.dumps(envelope, indent=2, ensure_ascii=False)
        print(text)
        if args.write_report:
            meta.ensure_vibelign_dirs()
            _ = meta.report_path("patch", "json").write_text(
                text + "\n", encoding="utf-8"
            )
        return

    markdown = _render_markdown(data, preview_text=preview_text)
    print(markdown, end="")
    if args.write_report:
        meta.ensure_vibelign_dirs()
        _ = meta.report_path("patch", "md").write_text(markdown, encoding="utf-8")


# === ANCHOR: VIB_PATCH_CMD_END ===
