from __future__ import annotations

from pathlib import Path


def write_turn_transcript(
    root: Path,
    *,
    session_id: str,
    turn_index: int,
    adapter: str,
    response: str,
) -> Path:
    turns_dir = root / ".vibelign" / "planning" / session_id / "turns"
    turns_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = turns_dir / f"turn_{turn_index:03d}_{adapter}.md"
    transcript_path.write_text(response, encoding="utf-8")
    return transcript_path
