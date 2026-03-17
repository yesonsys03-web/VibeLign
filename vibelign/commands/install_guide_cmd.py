from vibelign.terminal_render import (
    clack_info,
    clack_intro,
    clack_outro,
    clack_step,
    clack_success,
    clack_warn,
    cli_print,
)


def run_install_guide(args) -> None:
    clack_intro("VibeLign 설치 방법")

    # ── 1단계 ──
    clack_step("1단계  터미널 열기  (어느 폴더든 상관없어요)")
    clack_info("Mac     →  ⌘+스페이스  →  '터미널' 검색 후 엔터")
    clack_info("Windows →  시작 버튼   →  'PowerShell' 검색 후 엔터")
    clack_info("Linux   →  Ctrl+Alt+T")

    cli_print("")

    # ── 2단계 ──
    clack_step("2단계  uv 설치  (더 빠르고 안정적이에요, 없으면 설치하세요)")
    clack_info("Mac / Linux:")
    clack_info("  curl -LsSf https://astral.sh/uv/install.sh | sh")
    clack_info("Windows (PowerShell):")
    clack_info('  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"')
    clack_warn("설치 후 터미널을 닫고 새로 열어주세요")

    cli_print("")

    # ── 3단계 ──
    clack_step("3단계  vibelign 설치")
    clack_info("uv 사용:   uv tool install vibelign")
    clack_info("pip 사용:  pip install vibelign")

    cli_print("")

    # ── 4단계 ──
    clack_step("4단계  설치 확인")
    clack_info("vib --help")

    cli_print("")

    # ── 5단계 (선택) ──
    clack_step("5단계  빠른 검색 도구 설치  (선택 — 없어도 잘 작동해요)")
    clack_info("파일이 많은 프로젝트라면 아래 도구를 설치하면 스캔이 훨씬 빨라져요.")
    clack_info("")
    clack_info("Mac (Homebrew):")
    clack_info("  brew install fd ripgrep")
    clack_info("")
    clack_info("Windows (winget):")
    clack_info("  winget install sharkdp.fd BurntSushi.ripgrep.MSVC")
    clack_info("")
    clack_info("Ubuntu / Debian:")
    clack_info("  sudo apt install fd-find ripgrep")
    clack_info("  (설치 후 fd 명령어가 fdfind 로 나올 수 있어요 → ln -s $(which fdfind) ~/.local/bin/fd)")
    clack_info("")
    clack_warn("설치 안 해도 VibeLign은 정상 작동해요. 파일이 수천 개일 때 체감 차이가 있어요.")

    cli_print("")

    # ── 에러 대처 ──
    clack_step("에러가 나면?")
    clack_info('"command not found"  →  python3 --version 먼저 확인')
    clack_info("                        python.org 에서 Python 3.9 이상 설치")
    clack_info('"permission denied"  →  Mac/Linux: sudo pip install vibelign')
    clack_info("                        Windows:   관리자 권한으로 PowerShell 열기")
    clack_info('"pip not found"      →  python3 -m pip install vibelign')
    clack_info("uv 설치 실패         →  https://docs.astral.sh/uv/getting-started/installation/")

    cli_print("")

    clack_outro("설치 후 시작:  vib start")
