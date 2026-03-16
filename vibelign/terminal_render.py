import importlib
import os
import re
import sys
import builtins
from typing import Any, Optional, cast

_ONBOARDING_STYLE_ENV = "VIBELIGN_ONBOARDING_STYLE"

# ── 섹션 제목에 붙이는 이모지 매핑 ───────────────────────────────
_SECTION_EMOJI: list[tuple[str, str]] = [
    ("정체", "📄"),
    ("하는 일", "📄"),
    ("요약", "📋"),
    ("기능", "⚙️"),
    ("연결", "🔗"),
    ("주의", "⚠️"),
    ("수정", "✏️"),
    ("AI", "🤖"),
    ("문제", "🔴"),
    ("권장", "💡"),
    ("상태", "📊"),
    ("바뀐", "🔄"),
    ("설명", "💬"),
    ("다음", "➡️"),
    ("보면", "👀"),
    ("가드", "🛡️"),
    ("doctor", "🏥"),
    ("통과", "✅"),
    ("중지", "🚫"),
]


def _section_emoji(title: str) -> str:
    for keyword, emoji in _SECTION_EMOJI:
        if keyword in title:
            return emoji
    return "◆"


def _load_rich() -> Optional[dict[str, Any]]:
    try:
        return {
            "Console": importlib.import_module("rich.console").Console,
            "Group": importlib.import_module("rich.console").Group,
            "Columns": importlib.import_module("rich.columns").Columns,
            "Panel": importlib.import_module("rich.panel").Panel,
            "Rule": importlib.import_module("rich.rule").Rule,
            "Syntax": importlib.import_module("rich.syntax").Syntax,
            "Text": importlib.import_module("rich.text").Text,
            "Padding": importlib.import_module("rich.padding").Padding,
        }
    except ImportError:
        return None


def should_use_rich() -> bool:
    if os.environ.get("VIBELIGN_ASK_PLAIN") == "1":
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    if _load_rich() is None:
        return False
    return sys.stdout.isatty()


def normalize_ai_output(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    normalized = []
    in_fence = False
    blank_run = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            normalized.append(line.rstrip())
            blank_run = 0
            continue

        if in_fence:
            normalized.append(line)
            continue

        line = re.sub(r"^(\s*)[\u2022\u25cf\u25aa\u25e6\u2013\u2014]\s+", r"\1- ", line)
        line = re.sub(r"^(\s*)(\d+)\)\s+", r"\1\2. ", line)
        line = line.rstrip()

        if stripped:
            blank_run = 0
            normalized.append(line)
        else:
            blank_run += 1
            if blank_run <= 1:
                normalized.append("")

    return "\n".join(normalized).strip()


def _strip_inline_markdown(text: str) -> str:
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    cleaned = re.sub(r"__(.*?)__", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    return cleaned.strip()


def _flush_paragraph(blocks: list[tuple[str, object]], paragraph: list[str]) -> None:
    if not paragraph:
        return
    content = _strip_inline_markdown(
        " ".join(line.strip() for line in paragraph if line.strip())
    )
    if content:
        blocks.append(("paragraph", content))
    paragraph.clear()


def _flush_list(
    blocks: list[tuple[str, object]], items: list[str], ordered: bool
) -> None:
    if not items:
        return
    blocks.append(("ordered_list" if ordered else "bullet_list", items[:]))
    items.clear()


def _parse_blocks(text: str) -> list[tuple[str, object]]:
    blocks: list[tuple[str, object]] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_ordered = False
    code_lines: list[str] = []
    code_lang = "text"
    in_fence = False

    for raw_line in normalize_ai_output(text).splitlines():
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            _flush_paragraph(blocks, paragraph)
            _flush_list(blocks, list_items, list_ordered)
            if in_fence:
                blocks.append(("code", (code_lang, "\n".join(code_lines).rstrip())))
                code_lines = []
                code_lang = "text"
                in_fence = False
            else:
                in_fence = True
                code_lang = stripped[3:].strip() or "text"
            continue

        if in_fence:
            code_lines.append(raw_line)
            continue

        if not stripped:
            _flush_paragraph(blocks, paragraph)
            _flush_list(blocks, list_items, list_ordered)
            continue

        heading_match = re.match(r"^#{1,3}\s+(.+)$", stripped)
        if heading_match:
            _flush_paragraph(blocks, paragraph)
            _flush_list(blocks, list_items, list_ordered)
            blocks.append(("heading", _strip_inline_markdown(heading_match.group(1))))
            continue

        bare_heading = re.match(r"^([A-Za-z가-힣0-9 /_-]{2,40}):$", stripped)
        if bare_heading:
            _flush_paragraph(blocks, paragraph)
            _flush_list(blocks, list_items, list_ordered)
            blocks.append(("heading", _strip_inline_markdown(bare_heading.group(1))))
            continue

        if re.fullmatch(r"-{3,}", stripped):
            _flush_paragraph(blocks, paragraph)
            _flush_list(blocks, list_items, list_ordered)
            blocks.append(("rule", None))
            continue

        quote_match = re.match(r"^>\s?(.*)$", stripped)
        if quote_match:
            _flush_paragraph(blocks, paragraph)
            _flush_list(blocks, list_items, list_ordered)
            blocks.append(("quote", _strip_inline_markdown(quote_match.group(1))))
            continue

        bullet_match = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet_match:
            _flush_paragraph(blocks, paragraph)
            if list_items and list_ordered:
                _flush_list(blocks, list_items, list_ordered)
            list_ordered = False
            list_items.append(_strip_inline_markdown(bullet_match.group(1)))
            continue

        ordered_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if ordered_match:
            _flush_paragraph(blocks, paragraph)
            if list_items and not list_ordered:
                _flush_list(blocks, list_items, list_ordered)
            list_ordered = True
            list_items.append(_strip_inline_markdown(ordered_match.group(2)))
            continue

        paragraph.append(raw_line)

    _flush_paragraph(blocks, paragraph)
    _flush_list(blocks, list_items, list_ordered)
    if code_lines:
        blocks.append(("code", (code_lang, "\n".join(code_lines).rstrip())))
    return blocks


def _get_console(rich_mod: dict[str, Any], console: Optional[Any] = None) -> Any:
    """터미널 리사이즈 시 너비 자동 감지 — 고정 너비 사용 안 함"""
    if console is not None:
        return console
    return rich_mod["Console"](width=None, highlight=False)


def _severity_style(text: str) -> Optional[str]:
    normalized = text.strip().lower()
    if not normalized:
        return None

    danger_tokens = [
        "중지", "실패", "fail", "high risk", "risky",
        "문제", "보호된 파일", "건드리면 안 되는",
        "즉시 확인", "멈춰야", "blocked",
        "오류가 날 수 있", "위험이 높", "꼭 여러 파일",
    ]
    warning_tokens = [
        "주의", "warn", "warning", "caution", "조심",
        "확인하는 게 좋아요", "확인하세요", "먼저 보면",
        "헷갈릴 수 있", "실수할", "엉뚱한", "섞여 있",
    ]
    success_tokens = [
        "통과", "safe", "good", "완료", "안정적으로",
        "좋아요", "큰 위험이 없어", "안전",
        "문제는 없습니다", "걱정할 큰 구조 문제는 없습니다",
    ]

    if any(token in normalized for token in danger_tokens):
        return "bold red"
    if any(token in normalized for token in warning_tokens):
        return "bold yellow"
    if any(token in normalized for token in success_tokens):
        return "bold green"
    return None


def _severity_text(rich_mod: dict[str, Any], text: str) -> Any:
    style = _severity_style(text)
    if style:
        return rich_mod["Text"](text, style=style)
    return rich_mod["Text"](text)


def _clack_style(message: str, fallback_style: str) -> str:
    severity_style = _severity_style(message)
    if severity_style is not None and fallback_style in {
        "white", "cyan", "bold cyan", "bold magenta",
    }:
        return severity_style
    return fallback_style


# ── 섹션 헤딩: 제목 텍스트 + 아래 구분선 ────────────────────────
def _render_section_heading(rich_mod: dict[str, Any], title: str) -> Any:
    """섹션 제목 → 이모지 + 밝은 청록색 큰 제목 텍스트 + 구분선"""
    emoji = _section_emoji(title)
    # 제목 텍스트 (크고 눈에 띄게)
    title_text = rich_mod["Text"]()
    title_text.append(f" {emoji}  ", style="bold")
    title_text.append(title, style="bold bright_cyan")
    # 제목 아래 얇은 구분선
    rule = rich_mod["Rule"](style="dim cyan")
    return rich_mod["Group"](
        rich_mod["Text"](""),    # 섹션 위 여백
        rich_mod["Padding"](title_text, pad=(0, 0, 0, 0)),
        rule,
    )


def _render_bullet_list(rich_mod: dict[str, Any], items: list[str]) -> Any:
    """각 불릿 항목을 Padding으로 감싸 줄바꿈 시 들여쓰기 유지"""
    group_items = []
    for item in items:
        item_style = _severity_style(item)
        line = rich_mod["Text"]()
        line.append("▸ ", style=item_style or "bold cyan")
        line.append(item, style=item_style or "bright_white")
        group_items.append(rich_mod["Padding"](line, pad=(0, 0, 0, 2)))
    return rich_mod["Group"](*group_items)


def _render_ordered_list(rich_mod: dict[str, Any], items: list[str]) -> Any:
    """각 번호 항목을 Padding으로 감싸 줄바꿈 시 들여쓰기 유지"""
    group_items = []
    for index, item in enumerate(items, 1):
        item_style = _severity_style(item)
        line = rich_mod["Text"]()
        line.append(f"{index}. ", style=item_style or "bold magenta")
        line.append(item, style=item_style or "bright_white")
        group_items.append(rich_mod["Padding"](line, pad=(0, 0, 0, 2)))
    return rich_mod["Group"](*group_items)


def print_provider_status(
    provider: str,
    model: str,
    console: Optional[Any] = None,
    use_rich: Optional[bool] = None,
) -> None:
    if use_rich is None:
        use_rich = should_use_rich()
    rich_mod = _load_rich() if use_rich else None
    if not use_rich or rich_mod is None:
        builtins.print(f"현재 provider: {provider} / model: {model}")
        return

    rich_console = _get_console(rich_mod, console)
    label = rich_mod["Text"]()
    label.append(" 🤖 ", style="bold")
    label.append("Provider", style="bold cyan")
    label.append(": ")
    label.append(provider, style="bold bright_white")
    label.append("   │   ", style="bright_black")
    label.append("Model", style="bold green")
    label.append(": ")
    label.append(model, style="bold bright_white")
    label.append(" ")
    rich_console.print(
        rich_mod["Panel"].fit(label, border_style="bright_black", padding=(0, 1))
    )


def print_attempted_providers(
    attempted: list[str], console: Optional[Any] = None, use_rich: Optional[bool] = None
) -> None:
    if not attempted:
        return
    if use_rich is None:
        use_rich = should_use_rich()
    rich_mod = _load_rich() if use_rich else None
    if not use_rich or rich_mod is None:
        builtins.print("시도한 provider:")
        for item in attempted:
            builtins.print(f"  - {item}")
        builtins.print()
        return

    rich_console = _get_console(rich_mod, console)
    content = rich_mod["Text"]()
    for item in attempted:
        content.append("  ▸ ", style="bold yellow")
        content.append(item, style="bright_white")
        content.append("\n")
    rich_console.print(
        rich_mod["Panel"](
            content,
            title="⚠️  시도한 provider",
            border_style="yellow",
            padding=(0, 1),
        )
    )


def print_ai_response(
    text: str, console: Optional[Any] = None, use_rich: Optional[bool] = None
) -> None:
    if use_rich is None:
        use_rich = should_use_rich()
    rich_mod = _load_rich() if use_rich else None
    if not use_rich or rich_mod is None:
        builtins.print(text)
        return

    rich_console = _get_console(rich_mod, console)
    renderables: list[Any] = []
    current_section_items: list[Any] = []
    in_section = False

    def flush_section() -> None:
        nonlocal current_section_items, in_section
        for renderable in current_section_items:
            renderables.append(renderable)
        current_section_items = []
        in_section = False

    for block_type, payload in _parse_blocks(text):
        if block_type == "heading":
            flush_section()
            in_section = True
            renderables.append(_render_section_heading(rich_mod, str(payload)))
            continue

        if block_type == "paragraph":
            para_text = _severity_text(rich_mod, str(payload))
            if in_section:
                # 섹션 안 본문은 들여쓰기 + 아래 여백
                indented = rich_mod["Padding"](para_text, pad=(0, 0, 1, 4))
                current_section_items.append(indented)
            else:
                renderables.append(rich_mod["Padding"](para_text, pad=(0, 0, 1, 0)))

        elif block_type == "bullet_list":
            bullet = _render_bullet_list(rich_mod, cast(list[str], payload))
            if in_section:
                # 불릿 리스트 위아래 여백
                current_section_items.append(rich_mod["Padding"](bullet, pad=(0, 0, 1, 0)))
            else:
                renderables.append(rich_mod["Padding"](bullet, pad=(0, 0, 1, 0)))

        elif block_type == "ordered_list":
            ordered = _render_ordered_list(rich_mod, cast(list[str], payload))
            if in_section:
                current_section_items.append(rich_mod["Padding"](ordered, pad=(0, 0, 1, 0)))
            else:
                renderables.append(rich_mod["Padding"](ordered, pad=(0, 0, 1, 0)))

        elif block_type == "code":
            language, code = cast(tuple[str, str], payload)
            syntax = rich_mod["Syntax"](
                code or "", language or "text", word_wrap=True, line_numbers=False,
                theme="monokai",
            )
            boxed = rich_mod["Panel"](
                syntax, border_style="bright_black", padding=(0, 1)
            )
            if in_section:
                current_section_items.append(boxed)
            else:
                renderables.append(boxed)

        elif block_type == "quote":
            quote_text = _severity_text(rich_mod, str(payload))
            quote_panel = rich_mod["Panel"](
                quote_text, border_style="blue", padding=(0, 1)
            )
            if in_section:
                current_section_items.append(quote_panel)
            else:
                renderables.append(quote_panel)

        elif block_type == "rule":
            renderables.append(rich_mod["Rule"](style="bright_black"))

    flush_section()

    if not renderables:
        builtins.print(text)
        return

    rich_console.print(rich_mod["Group"](*renderables))


def cli_print(
    *args: object,
    sep: str = " ",
    end: str = "\n",
    file: Optional[Any] = None,
    flush: bool = False,
) -> None:
    plain_print = builtins.print
    text = sep.join(str(arg) for arg in args)

    if file not in (None, sys.stdout):
        plain_print(*args, sep=sep, end=end, file=file, flush=flush)
        return

    if end != "\n" or flush:
        plain_print(*args, sep=sep, end=end, file=file, flush=flush)
        return

    if should_use_rich():
        if "\n" in text:
            print_ai_response(text, use_rich=True)
            return
        rich_mod = _load_rich()
        if rich_mod is not None:
            rich_mod["Console"]().print(text, markup=False)
            return

    plain_print(text)


def _clack_line(
    symbol: str, message: str, style: str, console: Optional[Any] = None
) -> None:
    plain_print = builtins.print
    onboarding_style = (
        (os.environ.get(_ONBOARDING_STYLE_ENV) or "clack").strip().lower()
    )

    if onboarding_style != "clack":
        cli_print(message)
        return

    line = f"{symbol} {message}"
    use_rich = console is not None or should_use_rich()
    if not use_rich:
        plain_print(line)
        return
    rich_mod = _load_rich()
    if rich_mod is None:
        plain_print(line)
        return
    rich_console = _get_console(rich_mod, console)
    rich_console.print(rich_mod["Text"](line, style=_clack_style(message, style)))


def clack_intro(message: str, console: Optional[Any] = None) -> None:
    _clack_line("◆", message, "bold cyan", console)


def clack_step(message: str, console: Optional[Any] = None) -> None:
    _clack_line("◌", message, "cyan", console)


def clack_info(message: str, console: Optional[Any] = None) -> None:
    _clack_line("•", message, "white", console)


def clack_success(message: str, console: Optional[Any] = None) -> None:
    _clack_line("✔", message, "bold green", console)


def clack_warn(message: str, console: Optional[Any] = None) -> None:
    _clack_line("▲", message, "bold yellow", console)


def clack_error(message: str, console: Optional[Any] = None) -> None:
    _clack_line("✖", message, "bold red", console)


def clack_outro(message: str, console: Optional[Any] = None) -> None:
    _clack_line("◆", message, "bold magenta", console)


def print_cli_help(message: str, console: Optional[Any] = None) -> None:
    plain_print = builtins.print
    if not message:
        return

    if not should_use_rich():
        plain_print(message, end="")
        return

    rich_mod = _load_rich()
    if rich_mod is None:
        plain_print(message, end="")
        return

    rich_console = _get_console(rich_mod, console)

    lines = message.rstrip("\n").split("\n")
    section_titles = {
        "usage:": "Usage",
        "positional arguments:": "Positional Arguments",
        "optional arguments:": "Options",
        "options:": "Options",
    }

    intro: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    epilog_lines: list[str] = []
    current_title: Optional[str] = None
    current_lines: list[str] = []
    seen_section = False
    in_epilog = False

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_title is not None:
            sections.append((current_title, current_lines[:]))
        current_title = None
        current_lines = []

    for line in lines:
        normalized = line.strip().lower()
        if normalized in section_titles:
            flush()
            current_title = section_titles[normalized]
            current_lines = []
            seen_section = True
            in_epilog = False
            continue

        if in_epilog:
            epilog_lines.append(line)
            continue

        if current_title is None:
            if seen_section:
                in_epilog = True
                epilog_lines.append(line)
            else:
                intro.append(line)
        else:
            if seen_section and line.strip() and not line[0].isspace():
                flush()
                in_epilog = True
                epilog_lines.append(line)
            else:
                current_lines.append(line)

    flush()

    if intro:
        rich_console.print(
            rich_mod["Panel"](
                "\n".join(intro),
                title="🧬 VibeLign CLI",
                border_style="cyan",
                padding=(0, 1),
            )
        )

    border_map = {
        "Usage": "green",
        "Positional Arguments": "magenta",
        "Options": "yellow",
    }
    for title, body_lines in sections:
        body = "\n".join(body_lines).rstrip()
        if not body:
            continue
        if title == "Positional Arguments" and body.lstrip().startswith("{"):
            continue
        rich_console.print(
            rich_mod["Panel"](
                body,
                title=title,
                border_style=border_map.get(title, "cyan"),
                padding=(0, 1),
            )
        )

    epilog_text = "\n".join(epilog_lines).strip()
    if epilog_text:
        rich_console.print(
            rich_mod["Panel"](
                epilog_text,
                border_style="bright_blue",
                padding=(0, 1),
            )
        )
