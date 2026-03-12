
# VibeGuard QUICKSTART (Beginner Guide)
# 바이브가드 빠른 시작 가이드

This guide shows exactly how to test VibeGuard step‑by‑step.
이 가이드는 VibeGuard를 **1단계부터 순서대로 테스트하는 방법**을 설명합니다.

---

# 1. Download
# 1. 다운로드

Download:

VibeGuard_final_release.zip

압축을 풉니다.

---

# 2. Open Terminal
# 2. 터미널 열기

Mac → Terminal.app 실행

---

# 3. Move to folder
# 3. 폴더 이동

Example:

cd ~/Downloads/VibeGuard_final_release

---

# 4. Check files
# 4. 파일 확인

Run:

ls

You should see:

README.md
pyproject.toml
vibeguard
docs

---

# 5. Check Python
# 5. Python 확인

python3 --version

Python 3.10 이상 필요

---

# 6. Install
# 6. 설치

Recommended:

uv tool install .

Alternative:

pip install -e .

---

# 7. Verify
# 7. 설치 확인

vibeguard --help

---

# 8. Test commands
# 8. 테스트

vibeguard doctor

vibeguard anchor --dry-run

vibeguard patch add progress bar --json

vibeguard explain --json

vibeguard guard --json

vibeguard export claude

---

# 9. Optional watch mode
# 9. 실시간 감시

pip install watchdog

vibeguard watch

---

# Success
# 성공 기준

If these run:

vibeguard --help
vibeguard doctor
vibeguard patch
vibeguard guard

Installation is correct.
설치 성공입니다.
