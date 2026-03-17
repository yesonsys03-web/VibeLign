# === ANCHOR: VIB_SCAN_CMD_START ===
from pathlib import Path
from typing import Any

from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import clack_info, clack_intro, clack_outro, clack_step, clack_success, clack_warn


def run_vib_scan(args: Any) -> None:
    """앵커 스캔 + 코드맵 생성 + 앵커 인덱스 갱신을 한 번에 수행."""
    import json
    from datetime import datetime, timezone
    from vibelign.core.anchor_tools import collect_anchor_index
    from vibelign.commands.vib_anchor_cmd import run_vib_anchor
    from vibelign.commands.vib_start_cmd import _build_project_map

    root = Path.cwd()
    meta = MetaPaths(root)

    clack_intro("VibeLign 스캔")

    # [1] 앵커 자동 삽입 (--auto 플래그 없으면 suggest만)
    clack_step("앵커 스캔 중...")
    import types
    anchor_args = types.SimpleNamespace(
        suggest=not getattr(args, "auto", False),
        auto=getattr(args, "auto", False),
        validate=False,
        dry_run=False,
        json=False,
        only_ext="",
    )
    run_vib_anchor(anchor_args)

    # [2] 앵커 인덱스 수집
    clack_step("앵커 인덱스 갱신 중...")
    anchor_index = collect_anchor_index(root)
    meta.ensure_vibelign_dir()
    meta.anchor_index_path.write_text(
        json.dumps({"files": {k: {"anchors": v} for k, v in anchor_index.items()}},
                   indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    clack_success(f"앵커 인덱스 갱신 완료: {len(anchor_index)}개 파일")

    # [3] 코드맵 재생성 (앵커 인덱스 포함)
    clack_step("코드맵 재생성 중...")
    if meta.project_map_path.exists():
        project_map = _build_project_map(root)
        meta.project_map_path.write_text(
            json.dumps(project_map, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        clack_success(
            f"코드맵 갱신 완료: {project_map['file_count']}개 파일, "
            f"앵커 {len(project_map['anchor_index'])}개 파일 포함"
        )
    else:
        clack_info("project_map.json 없음 — vib init 또는 vib start를 먼저 실행하세요")

    # [4] 앵커 무결성 검사
    clack_step("앵커 무결성 검사 중...")
    from vibelign.core.anchor_tools import validate_anchor_file
    from vibelign.core.project_scan import iter_source_files
    problems: list[str] = []
    for path in iter_source_files(root):
        for problem in validate_anchor_file(path):
            if problem != "앵커가 없습니다":
                rel = str(path.relative_to(root))
                problems.append(f"{rel}: {problem}")
    if problems:
        clack_warn(f"앵커 문제 {len(problems)}건 발견:")
        for p in problems:
            clack_warn(f"  {p}")
        clack_info("vib anchor --validate 로 상세 확인, 문제 파일을 에디터로 열어 수정하세요")
    else:
        clack_success("앵커 무결성 이상 없음")

    clack_outro("스캔 완료. AI에게 project_map.json을 제공하면 전체 구조를 한 번에 파악해요.")


# === ANCHOR: VIB_SCAN_CMD_END ===
