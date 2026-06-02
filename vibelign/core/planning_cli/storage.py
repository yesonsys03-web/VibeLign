from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from vibelign.core.docs_visualizer import _slugify
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.planning_cli.markdown_writer import build_template_markdown
from vibelign.core.planning_cli.models import PlanningInput, PlanningResult

WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}


def safe_plan_slug(idea: str) -> str:
    has_filename_text = bool(re.search(r"[a-zA-Z0-9가-힣]", idea))
    slug = _slugify(idea).strip(" .-")
    slug = re.sub(r'[<>:"/\\|?*]+', "-", slug)
    slug = re.sub(r"-+", "-", slug).strip(" .-")
    if not has_filename_text or not slug or slug.lower() in WINDOWS_RESERVED_NAMES:
        return "plan"
    return slug


def _relative_output_path(output: str | None, slug: str) -> Path:
    if not output:
        return Path("plans") / f"{slug}.md"
    output_path = Path(output)
    if output_path.is_absolute() or any(part == ".." for part in output_path.parts):
        raise ValueError("output must be a project-relative path")
    return output_path


def _unique_output_path(root: Path, relative: Path) -> Path:
    candidate = root / relative
    if not candidate.exists():
        return relative
    stem = relative.stem
    suffix = relative.suffix or ".md"
    parent = relative.parent
    index = 2
    while True:
        next_relative = parent / f"{stem}-{index}{suffix}"
        if not (root / next_relative).exists():
            return next_relative
        index += 1


def create_planning_template(root: Path, planning_input: PlanningInput) -> PlanningResult:
    root = root.resolve()
    idea = planning_input.idea.strip()
    if not idea:
        raise ValueError("idea is required")

    slug = safe_plan_slug(idea)
    requested_relative = _relative_output_path(planning_input.output, slug)
    relative_path = requested_relative
    output_path = root / relative_path
    if planning_input.output and output_path.exists() and not planning_input.force:
        raise FileExistsError(f"output already exists: {relative_path}")
    if not planning_input.output:
        relative_path = _unique_output_path(root, requested_relative)
        output_path = root / relative_path

    markdown = build_template_markdown(idea, language=planning_input.language)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    session_id = f"plan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:6]}"
    meta = MetaPaths(root)
    session_dir = meta.vibelign_dir / "planning" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session = {
        "schema_version": 1,
        "session_id": session_id,
        "idea": idea,
        "language": planning_input.language,
        "output_path": relative_path.as_posix(),
        "fallback_reason": "template_only",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (session_dir / "session.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return PlanningResult(
        output_path=relative_path.as_posix(),
        absolute_output_path=str(output_path),
        markdown=markdown,
        fallback_reason="template_only",
        session_id=session_id,
    )
