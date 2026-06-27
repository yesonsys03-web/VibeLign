# === ANCHOR: VIB_REPORT_CARD_NEWS_CMD_START ===
from __future__ import annotations

import json
from pathlib import Path
from typing import NoReturn, Protocol

from vibelign.core.reporting_cli.report_card_news_export import export_card_news


class ReportCardNewsArgs(Protocol):
    @property
    def payload(self) -> str:
        ...

    @property
    def json(self) -> bool:
        ...


def run_vib_report_card_news(raw: ReportCardNewsArgs) -> None:
    want_json = bool(raw.json)
    try:
        result = export_card_news(Path(raw.payload).expanduser())
    except (OSError, ValueError) as exc:
        _fail(want_json, str(exc))
    payload = {
        "ok": True,
        "json_path": str(result.json_path),
        "html_path": str(result.html_path),
        "storyboard_path": str(result.storyboard_path),
        "prompt_dir": str(result.prompt_dir),
        "prompt_paths": [str(path) for path in result.prompt_paths],
        "card_count": result.card_count,
    }
    if want_json:
        print(json.dumps(payload, ensure_ascii=False))
        return
    from vibelign.terminal_render import clack_intro, clack_success

    clack_intro("VibeLign 카드뉴스")
    clack_success(f"카드뉴스 결과물: {result.html_path}")


def _fail(want_json: bool, message: str) -> NoReturn:
    if want_json:
        print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    else:
        print(message)
    raise SystemExit(1)


# === ANCHOR: VIB_REPORT_CARD_NEWS_CMD_END ===
