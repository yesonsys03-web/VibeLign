# === ANCHOR: VIB_BENCH_CMD_START ===
"""vib bench — 앵커 효과 검증 벤치마크."""
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from vibelign.terminal_render import (
    clack_info,
    clack_intro,
    clack_outro,
    clack_step,
    clack_success,
    clack_warn,
)

BENCHMARK_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "benchmark"
SAMPLE_PROJECT = BENCHMARK_DIR / "sample_project"
SCENARIOS_PATH = BENCHMARK_DIR / "scenarios.json"


# === ANCHOR: VIB_BENCH_CMD__LOAD_SCENARIOS_START ===
def _load_scenarios() -> List[Dict[str, Any]]:
    return json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
# === ANCHOR: VIB_BENCH_CMD__LOAD_SCENARIOS_END ===


# === ANCHOR: VIB_BENCH_CMD__GENERATE_PLAIN_PROMPT_START ===
def _generate_plain_prompt(scenario: Dict[str, Any], project_files: List[str]) -> str:
    """A조건: 앵커/코드맵 없이 plain prompt 생성."""
    lines = [
        f"Request: {scenario['request']}",
        "",
        "Project files:",
    ]
    lines.extend(f"- {f}" for f in sorted(project_files))
    lines.extend([
        "",
        "Please modify the relevant file(s) to fulfill this request.",
        "Do not rewrite entire files. Make the smallest change necessary.",
    ])
    return "\n".join(lines)
# === ANCHOR: VIB_BENCH_CMD__GENERATE_PLAIN_PROMPT_END ===


# === ANCHOR: VIB_BENCH_CMD__GENERATE_ANCHOR_PROMPT_START ===
def _generate_anchor_prompt(
    scenario: Dict[str, Any], root: Path, project_files: List[str]
# === ANCHOR: VIB_BENCH_CMD__GENERATE_ANCHOR_PROMPT_END ===
) -> str:
    """B조건: 앵커+코드맵 포함 handoff prompt 생성."""
    from vibelign.core.anchor_tools import collect_anchor_index, extract_anchors
    from vibelign.core.meta_paths import MetaPaths

    meta = MetaPaths(root)

    # 코드맵 로드
    project_map = {}
    if meta.project_map_path.exists():
        project_map = json.loads(meta.project_map_path.read_text(encoding="utf-8"))

    # 앵커 인덱스
    anchor_index = collect_anchor_index(root)

    lines = [
        f"Request: {scenario['request']}",
        "",
        "Before making any changes:",
        "1. Read the project map below to understand the project structure",
        "2. Check the anchor list for the target file",
        "3. Only modify code within the specified anchor boundaries",
        "",
        "## Project Structure",
    ]
    if project_map.get("entry_files"):
        lines.append(f"Entry files: {', '.join(project_map['entry_files'])}")
    if project_map.get("ui_modules"):
        lines.append(f"UI modules: {', '.join(project_map['ui_modules'])}")
    if project_map.get("service_modules"):
        lines.append(f"Service modules: {', '.join(project_map['service_modules'])}")
    if project_map.get("core_modules"):
        lines.append(f"Core modules: {', '.join(project_map['core_modules'])}")

    lines.extend(["", "## Anchor Index"])
    for filepath, anchors in sorted(anchor_index.items()):
        if anchors:
            lines.append(f"- {filepath}: {', '.join(anchors)}")

    # 앵커 메타 (있으면)
    anchor_meta_path = meta.vibelign_dir / "anchor_meta.json"
    if anchor_meta_path.exists():
        try:
            anchor_meta = json.loads(anchor_meta_path.read_text(encoding="utf-8"))
            if anchor_meta:
                lines.extend(["", "## Anchor Details"])
                for name, meta_entry in sorted(anchor_meta.items()):
                    parts = [f"- {name}"]
                    if meta_entry.get("intent"):
                        parts.append(f"  intent: {meta_entry['intent']}")
                    if meta_entry.get("connects"):
                        parts.append(f"  connects: {', '.join(meta_entry['connects'])}")
                    lines.extend(parts)
        except (json.JSONDecodeError, OSError):
            pass

    lines.extend([
        "",
        "## Rules",
        "- Only modify files relevant to the request",
        "- Stay within anchor boundaries",
        "- Do not rewrite entire files",
        "- Do not remove ANCHOR markers",
        "",
        "Please modify the relevant file(s) to fulfill this request.",
    ])
    return "\n".join(lines)


# === ANCHOR: VIB_BENCH_CMD__RUN_GENERATE_START ===
def _run_generate(output_dir: Path) -> None:
    """A/B 조건별 프롬프트 생성."""
    from vibelign.core.anchor_tools import insert_module_anchors
    from vibelign.commands.vib_start_cmd import _build_project_map
    from vibelign.core.meta_paths import MetaPaths
    from vibelign.core.project_scan import iter_source_files, relpath_str

    scenarios = _load_scenarios()

    # sample_project는 tests/ 안에 있어서 iter_source_files가 무시함
    # 임시 디렉토리에 복사하여 양쪽 조건 모두에서 사용
    with tempfile.TemporaryDirectory() as tmp:
        tmp_root = Path(tmp)

        # A조건: 앵커 없이 프롬프트 생성
        shutil.copytree(SAMPLE_PROJECT, tmp_root / "project_a")
        proj_a = tmp_root / "project_a"
        project_files = [
            relpath_str(proj_a, p) for p in iter_source_files(proj_a)
        ]

        a_dir = output_dir / "condition_A_no_anchor"
        a_dir.mkdir(parents=True, exist_ok=True)

        clack_step("A조건: 앵커/코드맵 없는 프롬프트 생성 중...")
        for sc in scenarios:
            prompt = _generate_plain_prompt(sc, project_files)
            (a_dir / f"{sc['id']}.txt").write_text(prompt, encoding="utf-8")
            clack_info(f"  {sc['id']}: {sc['description']}")

        # B조건: 앵커+코드맵 포함 프롬프트 생성
        shutil.copytree(SAMPLE_PROJECT, tmp_root / "project_b")
        proj_b = tmp_root / "project_b"

        meta = MetaPaths(proj_b)
        meta.ensure_vibelign_dirs()

        for src_file in iter_source_files(proj_b):
            insert_module_anchors(src_file)

        project_map = _build_project_map(proj_b)
        meta.project_map_path.write_text(
            json.dumps(project_map, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        b_dir = output_dir / "condition_B_with_anchor"
        b_dir.mkdir(parents=True, exist_ok=True)

        b_project_files = [
            relpath_str(proj_b, p) for p in iter_source_files(proj_b)
        ]

        clack_step("B조건: 앵커+코드맵 포함 프롬프트 생성 중...")
        for sc in scenarios:
            prompt = _generate_anchor_prompt(sc, proj_b, b_project_files)
            (b_dir / f"{sc['id']}.txt").write_text(prompt, encoding="utf-8")
            clack_info(f"  {sc['id']}: {sc['description']}")
# === ANCHOR: VIB_BENCH_CMD__RUN_GENERATE_END ===


# === ANCHOR: VIB_BENCH_CMD__RUN_SCORE_START ===
def _run_score(results_dir: Path) -> Dict[str, Any]:
    """AI 수정 결과를 채점."""
    scenarios = _load_scenarios()
    scores = {"scenarios": []}

    for condition in ["condition_A_no_anchor", "condition_B_with_anchor"]:
        cond_dir = results_dir / condition
        if not cond_dir.exists():
            continue

        for sc in scenarios:
            sc_dir = cond_dir / sc["id"]
            if not sc_dir.exists():
                continue

            # 수정된 파일 목록 확인
            modified_files = []
            for f in sc_dir.iterdir():
                if f.suffix == ".py":
                    modified_files.append(f.name if "/" not in f.name else str(f.relative_to(sc_dir)))

            # 채점
            correct_files = set(sc["correct_files"])
            forbidden_files = set(sc.get("forbidden_files", []))
            modified_set = set(modified_files)

            file_accuracy = len(correct_files & modified_set) / max(len(correct_files), 1)
            safety = 1.0 if not (forbidden_files & modified_set) else 0.0
            extra_files = modified_set - correct_files
            precision = (
                len(correct_files & modified_set) / max(len(modified_set), 1)
            )

            # 앵커 경계 체크 (B조건에서만 의미 있음)
            anchor_respected = None
            if condition == "condition_B_with_anchor" and sc.get("correct_anchor"):
                anchor_respected = _check_anchor_boundary(sc_dir, sc["correct_anchor"])

            scores["scenarios"].append({
                "condition": condition,
                "scenario_id": sc["id"],
                "file_accuracy": round(file_accuracy, 2),
                "precision": round(precision, 2),
                "safety": round(safety, 2),
                "anchor_respected": anchor_respected,
                "modified_files": sorted(modified_files),
                "extra_files": sorted(extra_files),
            })

    return scores
# === ANCHOR: VIB_BENCH_CMD__RUN_SCORE_END ===


# === ANCHOR: VIB_BENCH_CMD__CHECK_ANCHOR_BOUNDARY_START ===
def _check_anchor_boundary(sc_dir: Path, expected_anchor: str) -> bool:
    """수정된 파일에서 앵커 경계 내에서만 수정되었는지 확인."""
    # 간단한 휴리스틱: 수정된 파일에 해당 앵커가 존재하는지만 확인
    for f in sc_dir.iterdir():
        if f.suffix == ".py":
            content = f.read_text(encoding="utf-8", errors="ignore")
            if expected_anchor in content:
                return True
    return False
# === ANCHOR: VIB_BENCH_CMD__CHECK_ANCHOR_BOUNDARY_END ===


# === ANCHOR: VIB_BENCH_CMD__RUN_REPORT_START ===
def _run_report(scores: Dict[str, Any]) -> str:
    """채점 결과를 마크다운 리포트로 변환."""
    lines = [
        "# VibeLign 앵커 효과 벤치마크 결과",
        "",
        "## 비교표: A(앵커 없음) vs B(앵커 있음)",
        "",
        "| 시나리오 | 조건 | 파일 정확도 | 정밀도 | 안전도 | 앵커 준수 |",
        "|----------|------|------------|--------|--------|----------|",
    ]
    for entry in scores.get("scenarios", []):
        cond_label = "A (없음)" if "no_anchor" in entry["condition"] else "B (있음)"
        anchor_str = (
            "O" if entry["anchor_respected"] is True
            else "X" if entry["anchor_respected"] is False
            else "-"
        )
        lines.append(
            f"| {entry['scenario_id']} | {cond_label} | "
            f"{entry['file_accuracy']:.0%} | {entry['precision']:.0%} | "
            f"{entry['safety']:.0%} | {anchor_str} |"
        )

    # 평균 요약
    a_scores = [e for e in scores.get("scenarios", []) if "no_anchor" in e["condition"]]
    b_scores = [e for e in scores.get("scenarios", []) if "with_anchor" in e["condition"]]

    if a_scores and b_scores:
        # === ANCHOR: VIB_BENCH_CMD_AVG_START ===
        def avg(entries, key):
            vals = [e[key] for e in entries]
            return sum(vals) / len(vals) if vals else 0
        # === ANCHOR: VIB_BENCH_CMD_AVG_END ===

        lines.extend([
            "",
            "## 평균 비교",
            "",
            "| 지표 | A (앵커 없음) | B (앵커 있음) | 차이 |",
            "|------|-------------|-------------|------|",
        ])
        for key, label in [
            ("file_accuracy", "파일 정확도"),
            ("precision", "정밀도"),
            ("safety", "안전도"),
        ]:
            a_avg = avg(a_scores, key)
            b_avg = avg(b_scores, key)
            diff = b_avg - a_avg
            sign = "+" if diff >= 0 else ""
            lines.append(
                f"| {label} | {a_avg:.0%} | {b_avg:.0%} | {sign}{diff:.0%} |"
            )
# === ANCHOR: VIB_BENCH_CMD__RUN_REPORT_END ===

    return "\n".join(lines)


# === ANCHOR: VIB_BENCH_CMD_RUN_VIB_BENCH_START ===
def run_vib_bench(args: Any) -> None:
    """앵커 효과 검증 벤치마크."""
    if not SAMPLE_PROJECT.exists():
        clack_warn("벤치마크 테스트 프로젝트를 찾을 수 없어요: tests/benchmark/sample_project/")
        raise SystemExit(1)

    output_dir = BENCHMARK_DIR / "output"
    results_dir = BENCHMARK_DIR / "results"

    do_generate = getattr(args, "generate", False)
    do_score = getattr(args, "score", False)
    do_report = getattr(args, "report", False)
    as_json = getattr(args, "json", False)

    if not any([do_generate, do_score, do_report]):
        do_generate = True  # 기본 동작

    if do_generate:
        clack_intro("VibeLign 벤치마크: 프롬프트 생성")
        _run_generate(output_dir)
        clack_success(f"프롬프트 생성 완료: {output_dir}")
        clack_info("")
        clack_info("다음 단계:")
        clack_info("1. output/condition_A_no_anchor/ 의 프롬프트를 AI에게 전달")
        clack_info("2. AI 수정 결과를 results/condition_A_no_anchor/{시나리오}/ 에 저장")
        clack_info("3. output/condition_B_with_anchor/ 도 동일하게 반복")
        clack_info("4. vib bench --score 로 채점")
        clack_outro("프롬프트가 준비되었어요!")

    if do_score:
        clack_intro("VibeLign 벤치마크: 채점")
        if not results_dir.exists():
            clack_warn(
                f"결과 디렉토리를 찾을 수 없어요: {results_dir}\n"
                "AI 수정 결과를 results/ 폴더에 먼저 저장하세요."
            )
            raise SystemExit(1)

        scores = _run_score(results_dir)
        if as_json:
            from vibelign.terminal_render import cli_print
            cli_print(json.dumps(scores, indent=2, ensure_ascii=False))
        else:
            for entry in scores.get("scenarios", []):
                clack_info(
                    f"{entry['scenario_id']} [{entry['condition']}]: "
                    f"파일={entry['file_accuracy']:.0%} "
                    f"정밀={entry['precision']:.0%} "
                    f"안전={entry['safety']:.0%}"
                )
            clack_outro("채점 완료!")

        if do_report:
            report = _run_report(scores)
            report_path = BENCHMARK_DIR / "BENCHMARK_REPORT.md"
            report_path.write_text(report, encoding="utf-8")
            clack_success(f"리포트 생성: {report_path}")
# === ANCHOR: VIB_BENCH_CMD_RUN_VIB_BENCH_END ===
# === ANCHOR: VIB_BENCH_CMD_END ===
