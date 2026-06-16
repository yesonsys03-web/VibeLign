from __future__ import annotations

from hashlib import sha1
from pathlib import Path, PurePosixPath, PureWindowsPath

from vibelign.core.planning_cli.storage import safe_plan_slug
from vibelign.core.reporting_cli.models import ReportModel

_MAX_REPORT_SLUG_CHARS = 80


def _relative_output_path(output: str) -> Path:
    # is_absolute() 는 호스트 OS 규칙을 따른다: Windows 에서 "/tmp/x" 는 드라이브가
    # 없어 절대경로로 인정되지 않아 가드를 통과하고 드라이브 루트에 써진다.
    # POSIX·Windows 양쪽 규칙으로 절대성/드라이브/루트를 모두 검사해 OS 무관하게 막는다.
    posix = PurePosixPath(output)
    win = PureWindowsPath(output)
    if (
        posix.is_absolute()  # 선행 "/"
        or win.is_absolute()  # "C:\\..."
        or bool(win.drive)  # "C:foo" (드라이브 상대)
        or bool(win.root)  # "\\foo" (드라이브 루트 상대)
        or any(part == ".." for part in posix.parts)
        or any(part == ".." for part in win.parts)
    ):
        raise ValueError("output must be a project-relative path")
    return Path(output)


def _report_slug(slug_source: str) -> str:
    slug = safe_plan_slug(slug_source)
    if len(slug) <= _MAX_REPORT_SLUG_CHARS:
        return slug
    digest = sha1(slug.encode("utf-8")).hexdigest()[:8]
    prefix = slug[: _MAX_REPORT_SLUG_CHARS - len(digest) - 1].strip(" .-")
    return f"{prefix}-{digest}" if prefix else f"report-{digest}"


def _unique_output_path(root: Path, relative: Path) -> Path:
    candidate = root / relative
    if not candidate.exists():
        return relative
    stem = relative.stem
    suffix = relative.suffix or ".html"
    parent = relative.parent
    index = 2
    while True:
        next_relative = parent / f"{stem}-{index}{suffix}"
        if not (root / next_relative).exists():
            return next_relative
        index += 1


def write_report(
    root: Path,
    model: ReportModel,
    html: str,
    *,
    slug_source: str,
    output: str | None = None,
    force: bool = False,
) -> Path:
    """보고서 HTML 을 디스크에 쓰고 최종 경로를 반환한다.

    output 이 주어지면 프로젝트 상대 경로만 허용한다. explicit output 은
    force=True 없이는 기존 파일을 덮어쓰지 않는다. output 이 없으면
    .vibelign/reports/{slug}-{report_type}.html 로 저장하되
    기존 파일은 덮어쓰지 않는다.
    """
    root = root.resolve()
    if output:
        relative = _relative_output_path(output)
        # explicit output 은 _unique_output_path 를 거치지 않는다:
        # 덮어쓰기는 --force 계약으로 제어하고, 자동 suffix 는 하지 않는다.
    else:
        slug = _report_slug(slug_source)
        relative = _unique_output_path(
            root,
            Path(".vibelign") / "reports" / f"{slug}-{model.report_type}.html",
        )
    dest = root / relative

    # 어휘적 검사(_relative_output_path)는 심볼릭 링크를 추적하지 않는다.
    # resolve() 로 실제 경로를 구해 root 밖으로 탈출하는지 확인한다.
    resolved = dest.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("output must be a project-relative path")

    if output and dest.exists() and not force:
        raise FileExistsError(f"output already exists: {relative}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return dest
