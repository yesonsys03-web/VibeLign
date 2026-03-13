import os
import getpass
from pathlib import Path

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
        lines = profile.read_text(encoding="utf-8", errors="ignore").splitlines(keepends=True)
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


def run_config(args):
    print("=" * 50)
    print("  VibeGuard API 키 설정")
    print("=" * 50)
    print()

    # 현재 상태 표시
    print("현재 상태:")
    for p in _PROVIDERS:
        is_set = bool(os.environ.get(p["key_name"]))
        status = "✓ 설정됨" if is_set else "✗ 없음"
        print(f"  {p['key_name']:<22}: {status}")
    print()

    # 제공자 선택
    print("설정할 AI 서비스를 선택하세요:")
    for i, p in enumerate(_PROVIDERS, 1):
        print(f"  {i}. {p['label']:<22} ({p['url']})")
    print(f"  {len(_PROVIDERS) + 1}. 전체")
    print("  0. 취소")
    print()

    choice = input(f"선택 (0-{len(_PROVIDERS) + 1}): ").strip()

    if choice == "0" or not choice:
        print("취소했습니다.")
        return

    try:
        choice_num = int(choice)
    except ValueError:
        print("잘못된 선택입니다.")
        return

    if choice_num == len(_PROVIDERS) + 1:
        selected = _PROVIDERS
    elif 1 <= choice_num <= len(_PROVIDERS):
        selected = [_PROVIDERS[choice_num - 1]]
    else:
        print("잘못된 선택입니다.")
        return

    # API 키 입력
    print()
    collected = {}
    for p in selected:
        api_key = getpass.getpass(
            f"{p['label']} API 키를 입력하세요 (입력 내용은 표시되지 않습니다): "
        ).strip()
        if not api_key:
            print(f"  → {p['label']} 키 입력을 건너뜁니다.")
            continue
        collected[p["key_name"]] = api_key

    if not collected:
        print("설정할 키가 없습니다.")
        return

    # 영구/임시 선택
    profile = _get_shell_profile()
    print()
    print("저장 방식을 선택하세요:")
    print(f"  1. 영구 저장 ({profile} 에 저장, 새 터미널에서도 유지)")
    print("  2. 임시 저장 (현재 터미널 세션에서만 유효한 명령어 출력)")
    print()

    save_choice = input("선택 (1/2): ").strip()
    print()

    if save_choice == "1":
        for key_name, api_key in collected.items():
            _save_to_profile(profile, key_name, api_key)
            print(f"✓ {key_name} → {profile} 에 저장됨")
        print()
        print("적용하려면 새 터미널을 열거나 아래 명령어를 실행하세요:")
        print(f"  source {profile}")
    elif save_choice == "2":
        print("아래 명령어를 현재 터미널에 복사해서 실행하세요:")
        print()
        for key_name, api_key in collected.items():
            print(f"  export {key_name}=\"{api_key}\"")
        print()
        print("(새 터미널을 열면 다시 입력해야 합니다)")
    else:
        print("잘못된 선택입니다.")
        return

    print()
    print("✓ 설정 완료! 이제 'vibeguard ask 파일명' 을 실행하면 AI가 바로 설명합니다.")
