# === ANCHOR: ACTION_EXECUTOR_START ===
"""Action Executor — Plan의 Action을 실제로 실행한다.

원칙:
  - add_anchor: 자동 실행 (anchor_tools 사용)
  - fix_mcp / fix_project_map: 명령어 안내만 (자동 실행 안전하지 않음)
  - split_file / review: 건너뜀 (수동 작업 필요)
  - checkpoint는 사용자가 직접 관리 (자동 생성 안 함)
  - 파일 변경 감지 시 경고 출력
"""
from __future__ import annotations

import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from vibelign.action_engine.models.action import Action
from vibelign.action_engine.models.plan import Plan


@dataclass
class ExecutionResult:
    action: Action
    status: str        # "done" | "skipped" | "manual" | "failed"
    detail: str = ""


@dataclass
class ApplyResult:
    checkpoint_id: Optional[str]
    results: List[ExecutionResult] = field(default_factory=list)
    aborted: bool = False

    @property
    def done_count(self) -> int:
        return sum(1 for r in self.results if r.status == "done")

    @property
    def manual_count(self) -> int:
        return sum(1 for r in self.results if r.status == "manual")


def _check_plan_staleness(plan: Plan, root: Path) -> bool:
    """plan 생성 후 파일이 변경됐으면 True 반환."""
    from vibelign.core.analysis_cache import _project_mtime_hash
    from vibelign.core.meta_paths import MetaPaths
    import json

    meta = MetaPaths(root)
    cache_path = meta.analysis_cache_path
    if not cache_path.exists():
        return False
    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        cached_hash = payload.get("project_mtime_hash", "")
        current_hash = _project_mtime_hash(root)
        return cached_hash != current_hash
    except Exception:
        return False


def _execute_add_anchor(action: Action, root: Path) -> ExecutionResult:
    """앵커 없는 파일에 앵커 삽입."""
    if not action.target_path:
        return ExecutionResult(action, "skipped", "파일 경로 없음")
    path = root / action.target_path
    if not path.exists():
        return ExecutionResult(action, "skipped", f"파일 없음: {action.target_path}")
    try:
        from vibelign.core.anchor_tools import extract_anchors, insert_module_anchors
        if extract_anchors(path):
            return ExecutionResult(action, "skipped", "이미 앵커 있음")
        if insert_module_anchors(path):
            try:
                from vibelign.core.anchor_tools import generate_code_based_intents
                generate_code_based_intents(root, [path])
            except Exception:
                pass
            # AI 보강은 vib anchor --auto-intent 로 별도 실행 (APPLY 블로킹 방지)
            return ExecutionResult(action, "done", f"앵커 추가: {action.target_path}")
        return ExecutionResult(action, "failed", "앵커 삽입 실패")
    except Exception as e:
        return ExecutionResult(action, "failed", str(e))


def _execute_action(action: Action, root: Path) -> ExecutionResult:
    if action.action_type == "add_anchor":
        return _execute_add_anchor(action, root)
    elif action.action_type in ("fix_mcp", "fix_project_map"):
        cmd = action.command or "(명령어 없음)"
        return ExecutionResult(action, "manual", f"수동 실행 필요: {cmd}")
    else:
        return ExecutionResult(action, "skipped", f"{action.action_type} — 수동 작업 필요")


def execute_plan(plan: Plan, root: Path, force: bool = False, quiet: bool = False) -> ApplyResult:
    """Plan을 실행한다.

    Args:
        plan: generate_plan()이 반환한 Plan
        root: 프로젝트 루트
        force: True면 확인 프롬프트 생략

    Returns:
        ApplyResult
    """
    from vibelign.terminal_render import clack_step, clack_info, clack_warn

    def _q_step(msg: str) -> None:
        if not quiet:
            clack_step(msg)

    def _q_info(msg: str) -> None:
        if not quiet:
            clack_info(msg)

    def _q_warn(msg: str) -> None:
        if not quiet:
            clack_warn(msg)

    # plan 이후 파일 변경 확인
    if _check_plan_staleness(plan, root):
        _q_warn(
            "⚠️  분석 이후 파일이 변경됐습니다. "
            "vib doctor --plan 을 다시 실행해 최신 계획을 확인하세요."
        )
        if not force:
            try:
                ans = input("  그래도 계속할까요? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                return ApplyResult(checkpoint_id=None, aborted=True)
            if ans not in ("y", "yes"):
                return ApplyResult(checkpoint_id=None, aborted=True)

    # 확인 프롬프트 (--force 없으면)
    if not force:
        print(f"\n  자동 적용 대상: {len(plan.actions)}개 항목")
        try:
            ans = input("\n  실행할까요? [y/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ApplyResult(checkpoint_id=None, aborted=True)
        if ans not in ("y", "yes"):
            return ApplyResult(checkpoint_id=None, aborted=True)

    # 액션 실행
    results: List[ExecutionResult] = []
    for action in plan.actions:
        result = _execute_action(action, root)
        results.append(result)

    # aliases 없는 앵커가 있으면 코드 기반 즉시 생성 + AI 백그라운드 보강
    try:
        from vibelign.core.anchor_tools import load_anchor_meta, extract_anchors
        from vibelign.core.project_scan import iter_source_files
        meta = load_anchor_meta(root)
        needs_aliases = any(
            not entry.get("aliases") for entry in meta.values()
        ) if meta else True
        if needs_aliases:
            anchored = [p for p in iter_source_files(root) if extract_anchors(p)]
            if anchored:
                from vibelign.core.anchor_tools import generate_code_based_intents
                generate_code_based_intents(root, anchored)
                def _ai_enhance() -> None:
                    try:
                        from vibelign.core.anchor_tools import generate_anchor_intents_with_ai
                        generate_anchor_intents_with_ai(root, anchored)
                    except Exception:
                        pass
                threading.Thread(target=_ai_enhance, daemon=True).start()
    except Exception:
        pass

    # 분석 캐시 무효화 (파일이 변경됐으므로)
    try:
        from vibelign.core.meta_paths import MetaPaths
        cache_path = MetaPaths(root).analysis_cache_path
        if cache_path.exists():
            cache_path.unlink()
    except Exception:
        pass

    return ApplyResult(checkpoint_id=None, results=results)
# === ANCHOR: ACTION_EXECUTOR_END ===
