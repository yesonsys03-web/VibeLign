# === ANCHOR: VIB_SCAN_CMD_START ===
from pathlib import Path
from typing import Any

from vibelign.core.meta_paths import MetaPaths
from vibelign.terminal_render import clack_info, clack_intro, clack_outro, clack_step, clack_success, clack_warn


def _write_project_map(root: Path, meta: MetaPaths) -> dict:
    import json
    from vibelign.commands.vib_start_cmd import _build_project_map
    project_map = _build_project_map(root)
    meta.project_map_path.write_text(
        json.dumps(project_map, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return project_map


def run_vib_scan(args: Any) -> None:
    """앵커 스캔 + 코드맵 생성 + 앵커 인덱스 갱신을 한 번에 수행."""
    import json
    import types
    from vibelign.commands.vib_anchor_cmd import run_vib_anchor

    root = Path.cwd()
    meta = MetaPaths(root)

    clack_intro("VibeLign 스캔")

    # [1] 앵커 자동 삽입 (--auto 플래그 없으면 suggest만)
    clack_step("앵커 스캔 중...")
    anchor_args = types.SimpleNamespace(
        suggest=not getattr(args, "auto", False),
        auto=getattr(args, "auto", False),
        validate=False,
        dry_run=False,
        json=False,
        only_ext="",
    )
    run_vib_anchor(anchor_args)

    # [2] 앵커 무결성 검사 (+ --auto 시 자동 수정)
    clack_step("앵커 무결성 검사 중...")
    from vibelign.core.anchor_tools import insert_module_anchors, strip_anchors, validate_anchor_file
    from vibelign.core.project_scan import iter_source_files
    problems: list[str] = []
    problem_paths: list[Path] = []
    for path in iter_source_files(root):
        file_problems = [p for p in validate_anchor_file(path) if p != "앵커가 없습니다"]
        if file_problems:
            rel = str(path.relative_to(root))
            for p in file_problems:
                problems.append(f"{rel}: {p}")
            problem_paths.append(path)
    if problems:
        clack_warn(f"앵커 문제 {len(problems)}건 발견:")
        for p in problems:
            clack_warn(f"  {p}")
        if getattr(args, "auto", False) and problem_paths:
            clack_step("문제 파일 앵커 재삽입 중...")
            fixed: list[str] = []
            for p in problem_paths:
                strip_anchors(p)
                insert_module_anchors(p)
                fixed.append(str(p.relative_to(root)))
            clack_success(f"앵커 재삽입 완료: {', '.join(fixed)}")
        else:
            clack_info("vib anchor --validate 로 상세 확인, 또는 vib scan --auto 로 자동 수정하세요")
    else:
        clack_success("앵커 무결성 이상 없음")

    # [3] 코드맵 재생성 — 앵커 수정 후 최신 상태 반영
    clack_step("코드맵 재생성 중...")
    if meta.project_map_path.exists():
        meta.ensure_vibelign_dir()
        project_map = _write_project_map(root, meta)
        # anchor_index.json도 코드맵 데이터에서 추출해 저장 (중복 스캔 없음)
        anchor_index = project_map["anchor_index"]
        meta.anchor_index_path.write_text(
            json.dumps({"files": {k: {"anchors": v} for k, v in anchor_index.items()}},
                       indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        clack_success(
            f"코드맵 갱신 완료: {project_map['file_count']}개 파일, "
            f"앵커 {len(anchor_index)}개 파일 포함"
        )
    else:
        clack_info("project_map.json 없음 — vib init 또는 vib start를 먼저 실행하세요")

    clack_outro("스캔 완료. AI에게 project_map.json을 제공하면 전체 구조를 한 번에 파악해요.")


# === ANCHOR: VIB_SCAN_CMD_END ===
