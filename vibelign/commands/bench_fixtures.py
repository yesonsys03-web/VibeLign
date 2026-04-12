# === ANCHOR: BENCH_FIXTURES_START ===
"""Shared fixtures for patch-accuracy measurement.

Moved here from tests/test_patch_accuracy_scenarios.py so that both the
test suite and `vib bench --patch` can share one canonical sandbox setup
path. Pinned intents make measurement hermetic (vib anchor --auto calls
an LLM, which drifts across runs).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

def _find_benchmark_dir() -> Path:
    """Locate `tests/benchmark/` across editable and uv-tool installs.

    When VibeLign is installed via `uv tool install`, `__file__` points into
    site-packages which has no sibling `tests/` tree — the __file__-based
    walk that works from a source checkout resolves to site-packages and
    returns a non-existent path. Fall back to walking up from cwd until we
    find `tests/benchmark/sample_project`. Callers run `vib bench` from
    inside the repo, so this is reliable.
    """
    candidate = Path(__file__).resolve().parents[2] / "tests" / "benchmark"
    if (candidate / "sample_project").exists():
        return candidate
    here = Path.cwd().resolve()
    for parent in (here, *here.parents):
        probe = parent / "tests" / "benchmark" / "sample_project"
        if probe.exists():
            return parent / "tests" / "benchmark"
    return candidate


BENCHMARK_DIR = _find_benchmark_dir()
SAMPLE_PROJECT = BENCHMARK_DIR / "sample_project"

PINNED_INTENTS: dict[str, str] = {
    "DATABASE_INIT_DB": "데이터를 저장할 빈 공간을 처음 준비합니다.",
    "DATABASE_CREATE_USER": "회원 정보를 새로 만들어 명부에 등록합니다.",
    "DATABASE_FIND_USER_BY_EMAIL": "이메일로 회원의 정보를 찾아 가져옵니다.",
    "DATABASE_FIND_USER_BY_ID": "고유 번호로 회원의 정보를 찾아 가져옵니다.",
    "DATABASE_UPDATE_USER": "회원의 등록 정보를 최신으로 수정합니다.",
    "DATABASE_UPDATE_LOGIN_ATTEMPTS": "로그인 시도 횟수를 기록하고 업데이트합니다.",
    "AUTH__HASH_PASSWORD": "비밀번호를 안전하게 암호로 바꿉니다.",
    "AUTH__GENERATE_TOKEN": "사용자 인증을 위한 암호 키를 만듭니다.",
    "AUTH_LOGIN_USER": "이메일과 비밀번호로 로그인을 처리합니다.",
    "AUTH_REGISTER_USER": "새로운 사용자의 회원가입을 처리합니다.",
    "APP_MAIN": "프로그램을 실행하고 서버를 시작합니다.",
    "USERS_GET_USER_PROFILE": "공개 가능한 사용자 정보를 가져옵니다.",
    "USERS_UPDATE_USER_PROFILE": "사용자의 이름과 소개글을 수정합니다.",
    "VALIDATORS_VALIDATE_EMAIL": "이메일 주소 형식이 올바른지 확인합니다.",
    "VALIDATORS_VALIDATE_EMAIL_DOMAIN": "허용된 이메일 도메인인지 확인합니다.",
    "VALIDATORS_VALIDATE_PASSWORD": "비밀번호가 조건에 맞는지 확인합니다.",
    "SIGNUP_RENDER_SIGNUP_FORM": "회원가입 화면을 보여줄 양식을 만듭니다.",
    "SIGNUP_HANDLE_SIGNUP": "입력한 회원가입 정보를 검사하고 처리합니다.",
    "LOGIN_RENDER_LOGIN_FORM": "로그인 화면을 보여줄 양식을 만듭니다.",
    "LOGIN_HANDLE_LOGIN": "입력한 로그인 정보를 검사하고 처리합니다.",
    "LOGIN_RENDER_LOGIN_ERROR": "로그인 실패 시 오류 메시지를 보여줍니다.",
    "PROFILE_RENDER_PROFILE": "사용자 프로필 화면을 보여줄 양식을 만듭니다.",
    "PROFILE_HANDLE_PROFILE_UPDATE": "수정된 프로필 정보를 받아 저장합니다.",
    "CONFIG": "프로그램 설정 값을 모아 놓은 곳입니다.",
}

PINNED_INTENTS_VERSION = "2026-04-12"


# === ANCHOR: BENCH_FIXTURES_PREPARE_PATCH_SANDBOX_START ===
def prepare_patch_sandbox(tmp: Path) -> Path:
    """Copy sample_project into `tmp`, insert anchors, pin intents.

    Returns the sandbox project root. Caller owns `tmp` lifecycle.
    Calls `vib start` and `vib anchor --auto` via subprocess — both are
    deterministic (marker insertion + anchor_index.json generation).
    Then overwrites anchor_meta.json with PINNED_INTENTS so the downstream
    patch-suggester scoring is reproducible across machines.
    """
    dst = tmp / "project"
    shutil.copytree(SAMPLE_PROJECT, dst)
    subprocess.run(
        ["vib", "start"],
        cwd=dst,
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["vib", "anchor", "--auto"],
        cwd=dst,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    meta_path = dst / ".vibelign" / "anchor_meta.json"
    meta_path.write_text(
        json.dumps(
            {name: {"intent": text} for name, text in PINNED_INTENTS.items()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return dst
# === ANCHOR: BENCH_FIXTURES_PREPARE_PATCH_SANDBOX_END ===
# === ANCHOR: BENCH_FIXTURES_END ===
