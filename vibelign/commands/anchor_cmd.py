# === ANCHOR: ANCHOR_CMD_START ===
from pathlib import Path
from typing import Protocol
from vibelign.core.anchor_tools import preview_anchor_targets, insert_module_anchors


from vibelign.terminal_render import cli_print

print = cli_print


class AnchorArgs(Protocol):
    only_ext: str | None
    dry_run: bool


# === ANCHOR: ANCHOR_CMD_RUN_ANCHOR_START ===
def run_anchor(args: AnchorArgs) -> None:
    root = Path.cwd()
    only_ext = (args.only_ext or "").strip()
    allowed_exts = (
        {ext.strip().lower() for ext in only_ext.split(",") if ext.strip()}
        if only_ext
        else None
    )
    targets = preview_anchor_targets(root, allowed_exts=allowed_exts)
    if args.dry_run:
        if not targets:
            print("앵커가 필요한 파일이 없습니다.")
            return
        print("앵커가 추가될 파일 목록:")
        for path in targets:
            print(path.relative_to(root))
        return
    changed = 0
    for path in targets:
        if insert_module_anchors(path):
            changed += 1
            print(f"앵커 삽입: {path.relative_to(root)}")
    print(
        f"{changed}개 파일에 앵커를 삽입했습니다."
        if changed
        else "앵커가 필요한 파일이 없습니다."
    )


# === ANCHOR: ANCHOR_CMD_RUN_ANCHOR_END ===
# === ANCHOR: ANCHOR_CMD_END ===
