# === ANCHOR: VIB_PATCH_CMD_START ===
import json
from argparse import Namespace
from pathlib import Path
from collections.abc import Callable
from typing import Protocol, cast

from vibelign.core.codespeak import build_codespeak as build_codespeak
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_root import resolve_project_root
from vibelign.core.strict_patch import apply_strict_patch
from vibelign.patch.patch_builder import _build_patch_data as shared_build_patch_data
from vibelign.patch.patch_builder import (
    _build_patch_data_with_options as shared_build_patch_data_with_options,
)
from vibelign.patch.patch_builder import (
    _build_ready_handoff as shared_build_ready_handoff,
)
from vibelign.patch.patch_builder import _render_preview as shared_render_preview
from vibelign.patch.patch_builder import build_contract as shared_build_contract
from vibelign.patch.patch_builder import (
    build_patch_data as shared_build_patch_data_public,
)


from vibelign.terminal_render import cli_print
from vibelign.terminal_render import print_ai_response

print = cli_print

JsonObject = dict[str, object]


class OutputHelpersModule(Protocol):
    def emit_patch_result(
        self,
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
    ) -> None: ...


def _output_helpers() -> OutputHelpersModule:
    import importlib

    return cast(
        OutputHelpersModule,
        cast(object, importlib.import_module("vibelign.patch.patch_output")),
    )


def _build_ready_handoff(
    contract: dict[str, object],
    patch_plan: dict[str, object],
    strict_patch: dict[str, object] | None = None,
) -> dict[str, object]:
    return shared_build_ready_handoff(contract, patch_plan, strict_patch)


def _build_contract(patch_plan: dict[str, object]) -> dict[str, object]:
    return shared_build_contract(patch_plan)


def build_legacy_patch_suggestion(root: Path, request: str) -> JsonObject:
    data = _build_patch_data(
        root,
        request,
        use_ai=False,
        quiet_ai=True,
        preview=False,
        lazy_fanout=False,
    )
    patch_plan = cast(dict[str, object], data["patch_plan"])
    rationale_raw = cast(list[object], patch_plan.get("rationale", []))
    return {
        "request": request,
        "target_file": str(patch_plan["target_file"]),
        "target_anchor": str(patch_plan["target_anchor"]),
        "confidence": str(patch_plan["confidence"]),
        "rationale": [str(item) for item in rationale_raw],
    }


def _render_preview(target_path: Path, target_anchor: str) -> str:
    return shared_render_preview(target_path, target_anchor)


def _build_patch_data_with_options(
    root: Path,
    request: str,
    use_ai: bool,
    quiet_ai: bool,
    enable_step_fanout: bool = True,
    lazy_fanout: bool = False,
) -> dict[str, object]:
    return shared_build_patch_data_with_options(
        root,
        request,
        use_ai=use_ai,
        quiet_ai=quiet_ai,
        enable_step_fanout=enable_step_fanout,
        lazy_fanout=lazy_fanout,
    )


def _build_patch_data(
    root: Path,
    request: str,
    *,
    use_ai: bool = False,
    quiet_ai: bool = True,
    preview: bool = False,
    lazy_fanout: bool = False,
) -> dict[str, object]:
    return shared_build_patch_data(
        root,
        request,
        use_ai=use_ai,
        quiet_ai=quiet_ai,
        preview=preview,
        lazy_fanout=lazy_fanout,
    )


def build_patch_data(
    root: Path,
    request: str,
    *,
    use_ai: bool = False,
    quiet_ai: bool = True,
    preview: bool = False,
    lazy_fanout: bool = False,
) -> dict[str, object]:
    return shared_build_patch_data_public(
        root,
        request,
        use_ai=use_ai,
        quiet_ai=quiet_ai,
        preview=preview,
        lazy_fanout=lazy_fanout,
    )


def _render_markdown(data: dict[str, object], preview_text: str | None = None) -> str:
    import importlib

    render_helpers = cast(
        object, importlib.import_module("vibelign.patch.patch_render")
    )
    return cast(Callable[..., str], getattr(render_helpers, "render_markdown"))(
        data,
        build_contract=_build_contract,
        preview_text=preview_text,
    )


def run_vib_patch(args: Namespace | object) -> None:
    root = resolve_project_root(Path.cwd())
    apply_strict_raw = getattr(args, "apply_strict", None)
    apply_strict_text = (
        str(cast(object, apply_strict_raw)).strip()
        if apply_strict_raw is not None
        else ""
    )
    if apply_strict_text:
        strict_path = Path(apply_strict_text)
        if not strict_path.is_file():
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"strict_patch JSON 파일을 찾을 수 없어요: {strict_path}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        try:
            strict_patch = cast(
                dict[str, object],
                json.loads(strict_path.read_text(encoding="utf-8")),
            )
        except (OSError, json.JSONDecodeError) as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": f"strict_patch JSON을 읽을 수 없어요: {exc}",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        result = apply_strict_patch(
            root,
            strict_patch,
            dry_run=bool(getattr(args, "dry_run", False)),
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    request_value = getattr(args, "request", [])
    request_parts = (
        cast(list[object], request_value) if isinstance(request_value, list) else []
    )
    request = " ".join(str(part) for part in request_parts).strip()
    if not request:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "수정 요청 문장이 필요해요. (또는 --apply-strict FILE)",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    data = _build_patch_data(
        root,
        request,
        use_ai=bool(getattr(args, "ai", False)),
        quiet_ai=bool(getattr(args, "json", False)),
        preview=bool(getattr(args, "preview", False)),
        lazy_fanout=bool(getattr(args, "lazy_fanout", False)),
    )
    preview = cast(dict[str, object] | None, data.get("preview"))
    preview_text = str(preview["before_text"]) if preview is not None else None
    meta = MetaPaths(root)
    _output_helpers().emit_patch_result(
        data=data,
        preview_text=preview_text,
        as_json=bool(getattr(args, "json", False)),
        write_report=bool(getattr(args, "write_report", False)),
        copy_prompt=bool(getattr(args, "copy", False)),
        meta=meta,
        render_markdown=_render_markdown,
        print_text=print,
        print_rich=print_ai_response,
    )


# === ANCHOR: VIB_PATCH_CMD_END ===
