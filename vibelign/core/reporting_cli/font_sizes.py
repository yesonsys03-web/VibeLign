# === ANCHOR: FONT_SIZES_START ===
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


MIN_REPORT_FONT_SIZE: Final = 8
MAX_REPORT_FONT_SIZE: Final = 72


@dataclass(frozen=True, slots=True)
class ReportFontSizes:
    title: int | None = None
    heading: int | None = None
    body: int | None = None

    def has_overrides(self) -> bool:
        return self.title is not None or self.heading is not None or self.body is not None


def normalize_report_font_sizes(
    *,
    title: int | None = None,
    heading: int | None = None,
    body: int | None = None,
) -> ReportFontSizes:
    _check_size("타이틀", title)
    _check_size("헤드라인", heading)
    _check_size("본문", body)
    return ReportFontSizes(title=title, heading=heading, body=body)


def font_size_override_css(font_sizes: ReportFontSizes) -> str:
    if not font_sizes.has_overrides():
        return ""
    rules: list[str] = []
    if font_sizes.title is not None:
        rules.append(f"h1 {{ font-size:{font_sizes.title}px; }}")
    if font_sizes.heading is not None:
        rules.append(f"h2 {{ font-size:{font_sizes.heading}px; }}")
    if font_sizes.body is not None:
        rules.append(
            f"body {{ font-size:{font_sizes.body}px; }} "
            f"p.summary {{ font-size:{font_sizes.body}px; }}"
        )
    return "\n".join(rules)


def _check_size(label: str, value: int | None) -> None:
    if value is None:
        return
    if MIN_REPORT_FONT_SIZE <= value <= MAX_REPORT_FONT_SIZE:
        return
    raise ValueError(
        f"{label} 폰트 크기는 {MIN_REPORT_FONT_SIZE}~{MAX_REPORT_FONT_SIZE} 사이여야 해요."
    )
# === ANCHOR: FONT_SIZES_END ===
