# === ANCHOR: VIB_ANCHOR_CMD_START ===
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from vibeguard.core.anchor_tools import (
    collect_anchor_index,
    collect_anchor_metadata,
    insert_module_anchors,
    preview_anchor_targets,
    suggest_anchor_names,
    validate_anchor_file,
)
from vibeguard.core.meta_paths import MetaPaths


def _allowed_exts(value: str) -> Optional[Set[str]]:
    if not value.strip():
        return None
    normalized = set()
    for ext in value.split(","):
        token = ext.strip().lower()
        if not token:
            continue
        normalized.add(token if token.startswith(".") else f".{token}")
    return normalized


def _update_anchor_state(root: Path, meta: MetaPaths) -> None:
    if not meta.state_path.exists():
        return
    state = json.loads(meta.state_path.read_text(encoding="utf-8"))
    state["last_anchor_run_at"] = datetime.now(timezone.utc).isoformat()
    _ = meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _write_anchor_index(
    root: Path, meta: MetaPaths, allowed_exts: Optional[Set[str]]
) -> Dict[str, list[str]]:
    meta.ensure_vibelign_dirs()
    index = collect_anchor_index(root, allowed_exts=allowed_exts)
    metadata = collect_anchor_metadata(root, allowed_exts=allowed_exts)
    payload = {"schema_version": 1, "anchors": index, "files": metadata}
    _ = meta.anchor_index_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return index


def run_vib_anchor(args: Any) -> None:
    root = Path.cwd()
    meta = MetaPaths(root)
    allowed_exts = _allowed_exts(args.only_ext)

    if args.validate:
        index = _write_anchor_index(root, meta, allowed_exts)
        problems = []
        for rel in sorted(index):
            path = root / rel
            for problem in validate_anchor_file(path):
                problems.append(f"{rel}: {problem}")
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": not problems,
                        "error": None,
                        "data": {"problems": problems, "anchor_index": index},
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            if problems:
                raise SystemExit(1)
            return
        if problems:
            print("Anchor validation problems:")
            for item in problems:
                print(f"- {item}")
            raise SystemExit(1)
        print("Anchor validation passed.")
        print(f"Anchor index saved: {meta.anchor_index_path.relative_to(root)}")
        return

    targets = preview_anchor_targets(root, allowed_exts=allowed_exts)
    if args.suggest or args.dry_run:
        suggestions = {
            str(path.relative_to(root)): suggest_anchor_names(path) for path in targets
        }
        _ = _write_anchor_index(root, meta, allowed_exts)
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "error": None,
                        "data": {
                            "targets": [
                                str(path.relative_to(root)) for path in targets
                            ],
                            "suggested_anchors": suggestions,
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        if not targets:
            print("앵커를 추천할 파일이 없습니다.")
            return
        print("추천 앵커 대상 파일:")
        for path in targets:
            rel = str(path.relative_to(root))
            print(f"- {rel}")
            for name in suggestions.get(rel, [])[:5]:
                print(f"  - {name}")
        return

    if not args.auto:
        if args.json:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "error": None,
                        "data": {
                            "targets": [
                                str(path.relative_to(root)) for path in targets
                            ],
                            "mode": "suggest",
                        },
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        if not targets:
            print("앵커를 추천할 파일이 없습니다.")
            return
        print(
            "기본 동작은 suggest 모드입니다. 실제 삽입은 `vib anchor --auto`를 사용하세요."
        )
        for path in targets:
            print(f"- {path.relative_to(root)}")
        return

    changed = []
    for path in targets:
        if insert_module_anchors(path):
            changed.append(str(path.relative_to(root)))
    index = _write_anchor_index(root, meta, allowed_exts)
    _update_anchor_state(root, meta)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": True,
                    "error": None,
                    "data": {"changed": changed, "anchor_index": index},
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return
    if changed:
        print("앵커를 추가했습니다:")
        for rel in changed:
            print(f"- {rel}")
    else:
        print("앵커가 필요한 파일이 없습니다.")
    print(f"Anchor index saved: {meta.anchor_index_path.relative_to(root)}")


# === ANCHOR: VIB_ANCHOR_CMD_END ===
