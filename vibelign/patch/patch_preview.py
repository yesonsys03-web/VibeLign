# === ANCHOR: PATCH_PREVIEW_START ===
import re
from collections import deque
from pathlib import Path

from vibelign.core.context_chunk import fetch_anchor_context_window


# === ANCHOR: PATCH_PREVIEW_RENDER_PREVIEW_START ===
def render_preview(target_path: Path, target_anchor: str) -> str:
    preview_window_before = 2
    preview_window_after = 8
    fallback_limit = 10
    try:
        with target_path.open("r", encoding="utf-8", errors="ignore") as handle:
            if target_anchor and target_anchor not in {
                "[없음]",
                "[먼저 앵커를 추가하세요]",
            }:
                anchor_pattern = re.compile(
                    rf"ANCHOR:\s+{re.escape(target_anchor)}_START\b"
                )
                buffer: deque[str] = deque(maxlen=preview_window_before)
                snippet_lines: list[str] | None = None
                for line in handle:
                    stripped = line.rstrip("\n")
                    if snippet_lines is not None:
                        snippet_lines.append(stripped)
                        if (
                            len(snippet_lines)
                            >= preview_window_before + preview_window_after + 1
                        ):
                            return "\n".join(snippet_lines)
                        continue
                    if anchor_pattern.search(stripped):
                        snippet_lines = [*buffer, stripped]
                        continue
                    buffer.append(stripped)
                if snippet_lines is not None:
                    return "\n".join(snippet_lines)

        with target_path.open("r", encoding="utf-8", errors="ignore") as handle:
            lines: list[str] = []
            for idx, line in enumerate(handle):
                if idx >= fallback_limit:
                    break
                lines.append(line.rstrip("\n"))
            if lines:
                return "\n".join(lines)
    except Exception:
        return "[미리보기 불가] 파일 내용을 읽지 못했습니다."
    return "[미리보기 불가] 파일 내용을 읽지 못했습니다."
# === ANCHOR: PATCH_PREVIEW_RENDER_PREVIEW_END ===


# === ANCHOR: PATCH_PREVIEW_BUILD_STEP_CONTEXT_SNIPPET_START ===
def build_step_context_snippet(
    root: Path, target_file: str, target_anchor: str
# === ANCHOR: PATCH_PREVIEW_BUILD_STEP_CONTEXT_SNIPPET_END ===
) -> str | None:
    if not target_file or target_file == "[소스 파일 없음]":
        return None
    target_path = root / target_file
    if not target_path.exists():
        return None
    window = fetch_anchor_context_window(target_path, target_anchor)
    if window and window.strip():
        return window
    snippet = render_preview(target_path, target_anchor)
    return snippet if snippet.strip() else None


# === ANCHOR: PATCH_PREVIEW_BUILD_PREVIEW_PAYLOAD_START ===
def build_preview_payload(
    root: Path,
    target_file: str,
    target_anchor: str,
    confidence: object,
# === ANCHOR: PATCH_PREVIEW_BUILD_PREVIEW_PAYLOAD_END ===
) -> dict[str, object] | None:
    target_path = root / target_file
    if not target_path.exists():
        return None
    preview_text = render_preview(target_path, target_anchor)
    return {
        "schema_version": 1,
        "format": "ascii",
        "target_file": target_file,
        "target_anchor": target_anchor,
        "before_summary": "현재 파일 일부 미리보기입니다.",
        "after_summary": "AI 편집 전에 이 구역을 검토하세요.",
        "confidence": confidence,
        "before_text": preview_text,
    }
# === ANCHOR: PATCH_PREVIEW_END ===
