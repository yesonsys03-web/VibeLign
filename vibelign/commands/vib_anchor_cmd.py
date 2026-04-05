# === ANCHOR: VIB_ANCHOR_CMD_START ===
import json
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Iterable
from typing import Callable, cast

from vibelign.core import anchor_tools as anchor_tools_mod
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import ProjectMapSnapshot, load_project_map
from vibelign.core.project_root import resolve_project_root


from vibelign.terminal_render import cli_print

print = cli_print

AnchorIndex = dict[str, list[str]]
AnchorMetaMap = dict[str, dict[str, object]]
Recommendation = dict[str, object]


def _collect_anchor_index(root: Path, allowed_exts: set[str] | None) -> AnchorIndex:
    collect = cast(
        Callable[[Path, set[str] | None], AnchorIndex],
        cast(object, anchor_tools_mod.collect_anchor_index),
    )
    return collect(root, allowed_exts)


def _collect_anchor_metadata(
    root: Path, allowed_exts: set[str] | None
) -> dict[str, dict[str, list[str]]]:
    collect = cast(
        Callable[[Path, set[str] | None], dict[str, dict[str, list[str]]]],
        cast(object, anchor_tools_mod.collect_anchor_metadata),
    )
    return collect(root, allowed_exts)


def _generate_anchor_intents_with_ai(root: Path, anchored: list[Path]) -> int:
    return anchor_tools_mod.generate_anchor_intents_with_ai(root, anchored)


def _insert_module_anchors(path: Path) -> bool:
    return anchor_tools_mod.insert_module_anchors(path)


def _load_anchor_meta(root: Path) -> AnchorMetaMap:
    load = cast(
        Callable[[Path], AnchorMetaMap], cast(object, anchor_tools_mod.load_anchor_meta)
    )
    return load(root)


def _recommend_anchor_targets(
    root: Path, allowed_exts: set[str] | None, project_map: ProjectMapSnapshot | None
) -> list[Recommendation]:
    recommend = cast(
        Callable[
            [Path, set[str] | None, ProjectMapSnapshot | None], list[Recommendation]
        ],
        cast(object, anchor_tools_mod.recommend_anchor_targets),
    )
    return recommend(root, allowed_exts, project_map)


def _set_anchor_intent(root: Path, anchor_name: str, intent: str) -> None:
    _ = anchor_tools_mod.set_anchor_intent(root, anchor_name, intent)


def _validate_anchor_file(path: Path) -> Iterable[str]:
    return cast(Iterable[str], anchor_tools_mod.validate_anchor_file(path))


def _allowed_exts(value: str) -> set[str] | None:
    if not value.strip():
        return None
    normalized: set[str] = set()
    for ext in value.split(","):
        token = ext.strip().lower()
        if not token:
            continue
        normalized.add(token if token.startswith(".") else f".{token}")
    return normalized


def _update_anchor_state(_root: Path, meta: MetaPaths) -> None:
    if not meta.state_path.exists():
        return
    loaded = cast(object, json.loads(meta.state_path.read_text(encoding="utf-8")))
    if not isinstance(loaded, dict):
        return
    state = cast(dict[str, object], loaded)
    state["last_anchor_run_at"] = datetime.now(timezone.utc).isoformat()
    _ = meta.state_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _write_anchor_index(
    root: Path, meta: MetaPaths, allowed_exts: set[str] | None
) -> AnchorIndex:
    meta.ensure_vibelign_dirs()
    index = _collect_anchor_index(root, allowed_exts)
    metadata = _collect_anchor_metadata(root, allowed_exts)
    payload = {"schema_version": 1, "anchors": index, "files": metadata}
    _ = meta.anchor_index_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return index


def run_vib_anchor(args: object) -> None:
    root = resolve_project_root(Path.cwd())
    meta = MetaPaths(root)
    only_ext_value = getattr(args, "only_ext", "")
    only_ext = only_ext_value if isinstance(only_ext_value, str) else ""
    allowed_exts = _allowed_exts(only_ext)
    project_map, _project_map_error = load_project_map(root)
    set_intent = getattr(args, "set_intent", None)
    intent_value = getattr(args, "intent", None)
    intent = intent_value if isinstance(intent_value, str) else ""
    auto_intent = bool(getattr(args, "auto_intent", False))
    list_intent = bool(getattr(args, "list_intent", False))
    validate = bool(getattr(args, "validate", False))
    json_mode = bool(getattr(args, "json", False))
    suggest_mode = bool(getattr(args, "suggest", False))
    dry_run = bool(getattr(args, "dry_run", False))
    auto_mode = bool(getattr(args, "auto", False))

    if isinstance(set_intent, str) and set_intent:
        if not intent:
            print("오류: --intent 옵션으로 의도(intent) 텍스트를 입력하세요.")
            print(
                '예시: vib anchor --set-intent ANCHOR_NAME --intent "버튼/레이아웃 UI 구성"'
            )
            raise SystemExit(1)
        _set_anchor_intent(root, set_intent, intent)
        print(f"✅ intent 저장 완료: [{set_intent}] → {intent}")
        return

    if auto_intent:
        from vibelign.core.project_scan import iter_source_files
        from vibelign.core.anchor_tools import extract_anchors

        anchored = [
            path
            for path in iter_source_files(root)
            if (allowed_exts is None or path.suffix.lower() in allowed_exts)
            and extract_anchors(path)
        ]
        if not anchored:
            print("앵커가 있는 파일이 없습니다. 먼저 vib anchor --auto 를 실행하세요.")
            return
        print(f"🤖 AI가 {len(anchored)}개 파일의 앵커 intent를 자동 생성 중...")
        count = _generate_anchor_intents_with_ai(root, anchored)
        if count:
            print(f"✅ intent 등록 완료: {count}개")
        else:
            print(
                "⚠️  intent 자동 생성 실패 (API 키 확인 또는 vib anchor --set-intent 로 직접 등록)"
            )
        return

    if list_intent:
        data = _load_anchor_meta(root)
        if not data:
            print("등록된 intent가 없습니다.")
            print('등록하려면: vib anchor --set-intent ANCHOR_NAME --intent "설명"')
            return
        for anchor, meta_info in sorted(data.items()):
            intent = meta_info.get("intent", "")
            warning = meta_info.get("warning", "")
            line = f"  {anchor}: {intent}"
            if warning:
                line += f"  ⚠️ {warning}"
            print(line)
        return

    if validate:
        index = _write_anchor_index(root, meta, allowed_exts)
        problems: list[str] = []
        for rel in sorted(index):
            path = root / rel
            for problem in _validate_anchor_file(path):
                problems.append(f"{rel}: {problem}")
        if json_mode:
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

    recommendations = _recommend_anchor_targets(
        root, allowed_exts=allowed_exts, project_map=project_map
    )
    targets = [root / str(item["path"]) for item in recommendations]
    if suggest_mode or dry_run:
        suggestions = {
            str(item["path"]): cast(list[str], item["suggested_anchors"])
            for item in recommendations
        }
        _ = _write_anchor_index(root, meta, allowed_exts)
        if json_mode:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "error": None,
                        "data": {
                            "targets": [str(item["path"]) for item in recommendations],
                            "recommendations": recommendations,
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
        for item in recommendations:
            rel = str(item["path"])
            print(f"- {rel}")
            reasons = cast(list[str], item.get("reasons", []))
            for reason in reasons[:3]:
                print(f"  - 이유: {reason}")
            for name in list(suggestions.get(rel, []))[:5]:
                print(f"  - {name}")
        return

    if not auto_mode:
        if json_mode:
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
        for item in recommendations:
            print(f"- {item['path']}")
        return

    changed: list[str] = []
    for path in targets:
        if _insert_module_anchors(path):
            changed.append(str(path.relative_to(root)))
    index = _write_anchor_index(root, meta, allowed_exts)
    _update_anchor_state(root, meta)

    if json_mode:
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
        print("🤖 AI가 앵커 intent를 자동 생성 중...")
        count = _generate_anchor_intents_with_ai(root, [root / rel for rel in changed])
        if count:
            print(f"✅ intent 등록 완료: {count}개")
        else:
            print(
                "⚠️  intent 자동 생성 실패 (API 키 확인 또는 vib anchor --set-intent 로 직접 등록)"
            )
    else:
        print("앵커가 필요한 파일이 없습니다.")
    print(f"Anchor index saved: {meta.anchor_index_path.relative_to(root)}")


# === ANCHOR: VIB_ANCHOR_CMD_END ===
