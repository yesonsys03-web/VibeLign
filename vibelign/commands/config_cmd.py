import os
import json
import getpass
import urllib.request
from pathlib import Path
from typing import Optional


from vibelign.terminal_render import (
    clack_error,
    clack_info,
    clack_intro,
    clack_outro,
    clack_step,
    clack_success,
    clack_warn,
    cli_print,
)

print = cli_print

_DEFAULT_GEMINI_MODEL = "gemini-3-flash-preview"
_GEMINI_MODEL_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
]
_CLEAR_GEMINI_MODEL = "__CLEAR_GEMINI_MODEL__"

_PROVIDERS = [
    {
        "id": "anthropic",
        "label": "Anthropic (Claude)",
        "key_name": "ANTHROPIC_API_KEY",
        "url": "https://console.anthropic.com",
    },
    {
        "id": "openai",
        "label": "OpenAI (GPT)",
        "key_name": "OPENAI_API_KEY",
        "url": "https://platform.openai.com/api-keys",
    },
    {
        "id": "gemini",
        "label": "Gemini (Google)",
        "key_name": "GEMINI_API_KEY",
        "url": "https://aistudio.google.com",
    },
    {
        "id": "glm",
        "label": "GLM (Zhipu AI)",
        "key_name": "GLM_API_KEY",
        "url": "https://open.bigmodel.cn",
    },
    {
        "id": "kimi",
        "label": "Kimi (Moonshot AI)",
        "key_name": "MOONSHOT_API_KEY",
        "url": "https://platform.moonshot.cn",
    },
]


def _get_shell_profile() -> Path:
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return Path("~/.zshrc").expanduser()
    if "bash" in shell:
        profile = Path("~/.bash_profile").expanduser()
        return profile if profile.exists() else Path("~/.bashrc").expanduser()
    return Path("~/.zshrc").expanduser()


def _save_to_profile(profile: Path, key_name: str, api_key: str):
    """셸 프로파일에 export 라인 추가 (기존 항목 교체)"""
    export_line = f'export {key_name}="{api_key}"'

    if profile.exists():
        lines = profile.read_text(encoding="utf-8", errors="ignore").splitlines(
            keepends=True
        )
        new_lines = []
        replaced = False
        for line in lines:
            if line.startswith(f"export {key_name}="):
                new_lines.append(export_line + "\n")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(export_line + "\n")
        profile.write_text("".join(new_lines), encoding="utf-8")
    else:
        profile.write_text(export_line + "\n", encoding="utf-8")


def _fetch_gemini_models(api_key: str) -> list[str]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read())

    models = []
    for item in result.get("models", []):
        name = item.get("name", "")
        methods = item.get("supportedGenerationMethods", [])
        if not name.startswith("models/gemini-"):
            continue
        if "generateContent" not in methods:
            continue
        model = name.split("/", 1)[1]
        if any(
            token in model for token in ["image", "embedding", "tts", "aqa", "live"]
        ):
            continue
        models.append(model)

    ordered = []
    seen = set()
    for model in _GEMINI_MODEL_FALLBACKS + sorted(models):
        if model not in seen and model in models:
            ordered.append(model)
            seen.add(model)
    return ordered


def _select_gemini_model(api_key: Optional[str], current_model: str) -> Optional[str]:
    clack_step("Gemini 모델 설정 (선택사항)")
    if current_model:
        clack_info(f"현재 GEMINI_MODEL: {current_model}")
    else:
        clack_info(f"현재 GEMINI_MODEL: 기본값 사용 ({_DEFAULT_GEMINI_MODEL})")

    models = []
    source_label = "기본 추천 목록"
    if api_key:
        try:
            models = _fetch_gemini_models(api_key)
            if models:
                source_label = "Google AI Studio 공식 사용 가능 모델"
            else:
                clack_warn(
                    "Google AI Studio 모델 목록이 비어 있어 기본 추천 목록을 보여줍니다."
                )
        except Exception:
            models = []
            clack_warn(
                "Google AI Studio 모델 목록을 가져오지 못해 기본 추천 목록을 보여줍니다."
            )

    if not models:
        models = list(_GEMINI_MODEL_FALLBACKS)

    clack_info(f"모델 목록: {source_label}")
    for i, model in enumerate(models, 1):
        note = ""
        if model == _DEFAULT_GEMINI_MODEL:
            note = " (기본값)"
        elif model == current_model:
            note = " (현재값)"
        print(f"  {i}. {model}{note}")
    print(f"  {len(models) + 1}. 직접 입력")
    clear_choice = None
    if current_model:
        clear_choice = len(models) + 2
        print(f"  {clear_choice}. 설정 해제 (기본값 사용)")
    print("  0. 변경 안 함")
    print()

    max_choice = clear_choice or (len(models) + 1)
    choice = input(f"선택 (0-{max_choice}): ").strip()
    if choice == "0" or not choice:
        return None
    if choice.isdigit():
        choice_num = int(choice)
        if 1 <= choice_num <= len(models):
            return models[choice_num - 1]
        if choice_num == len(models) + 1:
            custom_model = input("Gemini 모델 ID를 입력하세요: ").strip()
            return custom_model or None
        if clear_choice and choice_num == clear_choice:
            return _CLEAR_GEMINI_MODEL

    clack_warn("잘못된 선택입니다. Gemini 모델 설정을 건너뜁니다.")
    return None


def run_config(args):
    clack_intro("VibeLign API 키 설정")

    # 무료 API 안내
    if not any(os.environ.get(p["key_name"]) for p in _PROVIDERS):
        clack_info("AI 기능을 쓰려면 API 키가 하나 이상 필요해요.")
        clack_info("무료로 시작하려면 Google AI Studio에서 Gemini 키를 받으세요:")
        clack_info("  https://aistudio.google.com/apikey")
        clack_info("  (Google 계정만 있으면 무료로 바로 발급돼요)")
        print()

    # 현재 상태 표시
    clack_step("현재 상태")
    for p in _PROVIDERS:
        is_set = bool(os.environ.get(p["key_name"]))
        status = "✓ 설정됨" if is_set else "✗ 없음"
        clack_info(f"{p['key_name']:<22}: {status}")
    gemini_model = (os.environ.get("GEMINI_MODEL") or "").strip()
    if gemini_model:
        model_status = f"✓ 사용자 설정 ({gemini_model})"
    else:
        model_status = f"기본값 사용 ({_DEFAULT_GEMINI_MODEL})"
    clack_info(f"{'GEMINI_MODEL':<22}: {model_status}")

    # 제공자 선택
    clack_step("설정할 AI 서비스를 선택하세요")
    for i, p in enumerate(_PROVIDERS, 1):
        print(f"  {i}. {p['label']:<22} ({p['url']})")
    print(f"  {len(_PROVIDERS) + 1}. 전체")
    print("  0. 취소")
    print()

    choice = input(f"선택 (0-{len(_PROVIDERS) + 1}): ").strip()

    if choice == "0" or not choice:
        clack_warn("취소했습니다.")
        return

    try:
        choice_num = int(choice)
    except ValueError:
        clack_error("잘못된 선택입니다.")
        return

    if choice_num == len(_PROVIDERS) + 1:
        selected = _PROVIDERS
    elif 1 <= choice_num <= len(_PROVIDERS):
        selected = [_PROVIDERS[choice_num - 1]]
    else:
        clack_error("잘못된 선택입니다.")
        return

    includes_gemini = any(p["id"] == "gemini" for p in selected)

    # API 키 입력
    print()
    collected = {}
    for p in selected:
        api_key = getpass.getpass(
            f"{p['label']} API 키를 입력하세요 (입력 내용은 표시되지 않습니다): "
        ).strip()
        if not api_key:
            clack_warn(f"{p['label']} 키 입력을 건너뜁니다.")
            continue
        collected[p["key_name"]] = api_key

    if includes_gemini:
        print()
        gemini_api_key = (
            collected.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
        ).strip()
        gemini_model = _select_gemini_model(gemini_api_key, gemini_model)
        if gemini_model == _CLEAR_GEMINI_MODEL:
            collected["GEMINI_MODEL"] = ""
        elif gemini_model is not None:
            collected["GEMINI_MODEL"] = gemini_model

    if not collected:
        clack_warn("설정할 값이 없습니다.")
        return

    # 영구/임시 선택
    profile = _get_shell_profile()
    print()
    clack_step("저장 방식을 선택하세요")
    print(f"  1. 영구 저장 ({profile} 에 저장, 새 터미널에서도 유지)")
    print("  2. 임시 저장 (현재 터미널 세션에서만 유효한 명령어 출력)")
    print()

    save_choice = input("선택 (1/2): ").strip()
    print()

    if save_choice == "1":
        for key_name, api_key in collected.items():
            _save_to_profile(profile, key_name, api_key)
            clack_success(f"{key_name} → {profile} 에 저장됨")
        print()
        clack_info("적용하려면 새 터미널을 열거나 아래 명령어를 실행하세요:")
        clack_info(f"source {profile}")
    elif save_choice == "2":
        clack_info("아래 명령어를 현재 터미널에 복사해서 실행하세요:")
        print()
        for key_name, api_key in collected.items():
            print(f'  export {key_name}="{api_key}"')
        print()
        clack_warn("새 터미널을 열면 다시 입력해야 합니다")
    else:
        clack_error("잘못된 선택입니다.")
        return

    clack_outro("설정 완료")
    clack_info("이제 'vib ask 파일명'을 실행하면 AI가 바로 설명합니다.")
