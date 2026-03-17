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
    clack_info("fd 와 ripgrep 은 파일을 빠르게 찾아주는 도구예요.")
    clack_info("vib start 실행 시 ⚡ 메시지가 보이면 설치를 권장해요.")
    clack_info("파일이 수백 개 이상인 프로젝트에서 스캔 속도 차이가 체감돼요.")
    clack_info("")
    clack_info("── Mac ──────────────────────────────────────────")
    clack_info("Homebrew(패키지 관리자)로 설치해요.")
    clack_info("Homebrew가 없다면 먼저 설치하세요: https://brew.sh")
    clack_info("  brew install fd ripgrep")
    clack_info("")
    clack_info("── Windows ──────────────────────────────────────")
    clack_info("winget 으로 설치해요. (Windows 10/11 기본 탑재)")
    clack_info("  winget install sharkdp.fd BurntSushi.ripgrep.MSVC")
    clack_info("")
    clack_info("── Ubuntu / Debian (Linux) ───────────────────────")
    clack_info("  sudo apt install fd-find ripgrep")
    clack_info("Ubuntu에서는 fd 대신 fdfind 라는 이름으로 설치되지만,")
    clack_info("VibeLign이 자동으로 인식해요. 추가 설정 없이 바로 사용 가능해요.")
    clack_info("")
    clack_warn("설치 안 해도 VibeLign은 정상 작동해요. 속도 차이만 있어요.")

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
