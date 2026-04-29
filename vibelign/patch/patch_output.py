# === ANCHOR: PATCH_OUTPUT_START ===
import json
from collections.abc import Callable
from typing import cast

from vibelign.core.meta_paths import MetaPaths
from vibelign.core.structure_policy import WINDOWS_SUBPROCESS_FLAGS
from vibelign.terminal_render import clack_success, clack_warn


# === ANCHOR: PATCH_OUTPUT_COPY_TO_CLIPBOARD_START ===
def copy_to_clipboard(text: str) -> None:
    import subprocess
    import sys

    try:
        if sys.platform == "darwin":
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            _ = proc.communicate(text.encode("utf-8"))
        elif sys.platform.startswith("linux"):
            proc = subprocess.Popen(
                ["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE
            )
            _ = proc.communicate(text.encode("utf-8"))
        elif sys.platform == "win32":
            proc = subprocess.Popen(
                ["clip"],
                stdin=subprocess.PIPE,
                creationflags=WINDOWS_SUBPROCESS_FLAGS,
            )
            _ = proc.communicate(text.encode("utf-16le"))
        else:
            clack_warn("이 OS에서는 클립보드 복사를 지원하지 않아요.")
            return

        clack_success(
            "AI 전달용 프롬프트가 클립보드에 복사되었어요! 바로 붙여넣기하세요."
        )
    except FileNotFoundError:
        clack_warn("클립보드 도구를 찾을 수 없어요. (macOS: pbcopy, Linux: xclip)")
# === ANCHOR: PATCH_OUTPUT_COPY_TO_CLIPBOARD_END ===


# === ANCHOR: PATCH_OUTPUT__WRITE_PATCH_REPORT_START ===
def _write_patch_report(meta: MetaPaths, *, text: str, suffix: str) -> None:
    meta.ensure_vibelign_dirs()
    _ = meta.report_path("patch", suffix).write_text(text, encoding="utf-8")
# === ANCHOR: PATCH_OUTPUT__WRITE_PATCH_REPORT_END ===


# === ANCHOR: PATCH_OUTPUT_EMIT_PATCH_RESULT_START ===
def emit_patch_result(
    *,
    data: dict[str, object],
    preview_text: str | None,
    as_json: bool,
    write_report: bool,
    copy_prompt: bool,
    meta: MetaPaths,
    render_markdown: Callable[[dict[str, object], str | None], str],
    print_text: Callable[[str], None],
    print_rich: Callable[[str], None],
# === ANCHOR: PATCH_OUTPUT_EMIT_PATCH_RESULT_END ===
) -> None:
    envelope = {"ok": True, "error": None, "data": data}
    if as_json:
        text = json.dumps(envelope, indent=2, ensure_ascii=False)
        print_text(text)
        if write_report:
            _write_patch_report(meta, text=text + "\n", suffix="json")
        return

    markdown = render_markdown(data, preview_text)
    print_rich(markdown)
    if write_report:
        _write_patch_report(meta, text=markdown, suffix="md")

    if not copy_prompt:
        return

    handoff = data.get("handoff")
    if isinstance(handoff, dict):
        handoff_data = cast(dict[str, object], handoff)
        prompt = handoff_data.get("prompt")
        if prompt:
            copy_to_clipboard(str(prompt))
            return
    clack_warn("아직 AI에게 전달할 프롬프트가 없어요. 요청을 더 구체적으로 써주세요.")
# === ANCHOR: PATCH_OUTPUT_END ===
