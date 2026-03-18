# === ANCHOR: VIB_ANCHOR_CMD_START ===
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

from vibelign.core.anchor_tools import (
    anchor_recommendation_details,
    collect_anchor_index,
    collect_anchor_metadata,
    generate_anchor_intents_with_ai,
    get_anchor_intent,
    insert_module_anchors,
    load_anchor_meta,
    preview_anchor_targets,
    recommend_anchor_targets,
    set_anchor_intent,
    suggest_anchor_names,
    validate_anchor_file,
)
from vibelign.core.meta_paths import MetaPaths
from vibelign.core.project_map import load_project_map


from vibelign.terminal_render import cli_print

print = cli_print


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
    project_map, _project_map_error = load_project_map(root)

    if args.set_intent:
        if not args.intent:
            print("오류: --intent 옵션으로 의도(intent) 텍스트를 입력하세요.")
            print("예시: vib anchor --set-intent ANCHOR_NAME --intent \"버튼/레이아웃 UI 구성\"")
            raise SystemExit(1)
        set_anchor_intent(root, args.set_intent, args.intent)
        print(f"✅ intent 저장 완료: [{args.set_intent}] → {args.intent}")
        return

    if args.auto_intent:
        from vibelign.core.project_scan import iter_source_files
        from vibelign.core.anchor_tools import extract_anchors
        anchored = [
            path for path in iter_source_files(root)
            if (allowed_exts is None or path.suffix.lower() in allowed_exts)
            and extract_anchors(path)
        ]
        if not anchored:
            print("앵커가 있는 파일이 없습니다. 먼저 vib anchor --auto 를 실행하세요.")
            return
        print(f"🤖 AI가 {len(anchored)}개 파일의 앵커 intent를 자동 생성 중...")
        count = generate_anchor_intents_with_ai(root, anchored)
        if count:
            print(f"✅ intent 등록 완료: {count}개")
        else:
            print("⚠️  intent 자동 생성 실패 (API 키 확인 또는 vib anchor --set-intent 로 직접 등록)")
        return

    if args.list_intent:
        data = load_anchor_meta(root)
        if not data:
            print("등록된 intent가 없습니다.")
            print("등록하려면: vib anchor --set-intent ANCHOR_NAME --intent \"설명\"")
            return
        for anchor, meta_info in sorted(data.items()):
            intent = meta_info.get("intent", "")
            warning = meta_info.get("warning", "")
            line = f"  {anchor}: {intent}"
            if warning:
                line += f"  ⚠️ {warning}"
            print(line)
        return

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

    recommendations = recommend_anchor_targets(
        root, allowed_exts=allowed_exts, project_map=project_map
    )
    targets = [root / str(item["path"]) for item in recommendations]
    if args.suggest or args.dry_run:
        suggestions = {
            str(item["path"]): item["suggested_anchors"] for item in recommendations
        }
        _ = _write_anchor_index(root, meta, allowed_exts)
        if args.json:
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
            for reason in list(item["reasons"])[:3]:
                print(f"  - 이유: {reason}")
            for name in list(suggestions.get(rel, []))[:5]:
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
        for item in recommendations:
            print(f"- {item['path']}")
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
        print("🤖 AI가 앵커 intent를 자동 생성 중...")
        count = generate_anchor_intents_with_ai(root, [root / rel for rel in changed])
        if count:
            print(f"✅ intent 등록 완료: {count}개")
        else:
            print("⚠️  intent 자동 생성 실패 (API 키 확인 또는 vib anchor --set-intent 로 직접 등록)")
    else:
        print("앵커가 필요한 파일이 없습니다.")
    print(f"Anchor index saved: {meta.anchor_index_path.relative_to(root)}")


# === ANCHOR: VIB_ANCHOR_CMD_END ===
