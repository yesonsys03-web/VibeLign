# === ANCHOR: INSTALL_GUIDE_CMD_START ===
from vibelign.terminal_render import (
    clack_info,
    clack_intro,
    clack_outro,
    clack_step,
    clack_warn,
    cli_print,
)


# === ANCHOR: INSTALL_GUIDE_CMD_RUN_INSTALL_GUIDE_START ===
def run_install_guide(_args: object) -> None:
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
    clack_info(
        '  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'
    )
    clack_warn("설치 후 터미널을 닫고 새로 열어주세요")

    cli_print("")

    # ── 3단계 ──
    clack_step("3단계  vibelign 설치")
    clack_info("── Mac / Linux ──────────────────────────────────")
    clack_info("  pip install vibelign")
    clack_info("")
    clack_info("── Windows (권장) ───────────────────────────────")
    clack_info("  uv tool install vibelign")
    clack_info("  → vib 명령어 바로 사용 가능, 경고 없음")
    clack_info("")
    clack_info("── Windows (uv 없이 쓰는 대안) ──────────────────")
    clack_info("  py -m pip install vibelign --no-warn-script-location")
    clack_info("  → 실행 시 vib 대신:  py -m vibelign start / checkpoint ...")

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
    clack_info(
        '"pip not found"      →  Windows: py -m pip install vibelign --no-warn-script-location'
    )
    clack_info("                        Mac/Linux: python3 -m pip install vibelign")
    clack_info(
        '"vib not found"      →  Windows 권장: uv tool install vibelign  (vib 바로 사용)'
    )
    clack_info(
        "                        Windows 대안: py -m vibelign [명령어]  (PATH 불필요)"
    )
    clack_info("")
    clack_info("  pip으로 설치했는데 vib가 안 되면 — 수동 PATH 설정:")
    clack_info("  1. Win+R  →  sysdm.cpl  →  엔터")
    clack_info("  2. 고급 탭  →  환경 변수")
    clack_info("  3. 시스템 변수의 Path  →  편집")
    clack_info("  4. 설치 경고 메시지에 표시된 Scripts 경로를 추가")
    clack_info(
        "     예: C:\\Users\\사용자이름\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\"
    )
    clack_warn(
        "     Scripts 경로는 pip 설치 시 뜨는 WARNING 메시지에 정확히 나와 있어요!"
    )
    clack_info("  5. 터미널을 완전히 껐다 다시 켜기")
    clack_info('"스크립트 경고 뜸"   →  --no-warn-script-location 옵션 추가')
    clack_info('"uv tool install 후 vib 안 됨"')
    clack_info("                     →  uv tool update-shell  실행 후 터미널 재시작")
    clack_info(
        "                        bash에서 안 되면: bash 안에서 uv tool update-shell 재실행"
    )
    clack_info(
        "                        또는: echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.bashrc"
    )
    clack_info(
        "uv 설치 실패         →  https://docs.astral.sh/uv/getting-started/installation/"
    )

    cli_print("")

    clack_outro("설치 후 시작:  vib start")


# === ANCHOR: INSTALL_GUIDE_CMD_RUN_INSTALL_GUIDE_END ===
# === ANCHOR: INSTALL_GUIDE_CMD_END ===
