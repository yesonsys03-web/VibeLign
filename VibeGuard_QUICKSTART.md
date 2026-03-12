
# VibeGuard QUICKSTART (Beginner Guide)
# 바이브가드 빠른 시작 가이드

This guide shows exactly how to set up and use VibeGuard step‑by‑step.
이 가이드는 VibeGuard를 **1단계부터 순서대로** 설치하고 사용하는 방법을 설명합니다.

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

# 8. First-time setup (NEW)
# 8. 처음 세팅 (신규)

가장 빠른 세팅 방법 — 명령어 하나로 끝납니다:

vibeguard init

이 명령어 하나로:
- AI 규칙 파일 자동 생성
- 도구 템플릿 파일 내보내기
- .gitignore 생성
- git 저장소 초기화
- 첫 번째 세이브 포인트 자동 저장

까지 모두 완료됩니다.

---

# 9. Save & Restore (NEW)
# 9. 저장 & 되돌리기 (신규)

AI가 코드를 망쳤을 때를 대비해 세이브 포인트를 저장하세요.

작업 전에 저장:

vibeguard checkpoint "로그인 기능 추가 전"

저장 이력 보기:

vibeguard history

망쳤으면 되돌리기:

vibeguard undo

---

# 10. Protect important files (NEW)
# 10. 중요 파일 보호 (신규)

AI가 절대 건드리면 안 되는 파일을 잠글 수 있어요:

vibeguard protect main.py

보호 목록 보기:

vibeguard protect --list

보호 해제:

vibeguard protect --remove main.py

---

# 11. Ask AI to explain a file (NEW)
# 11. 파일 쉽게 설명받기 (신규)

코드가 뭘 하는지 모를 때, AI에게 물어볼 프롬프트를 만들어줍니다:

vibeguard ask login.py

파일로 저장해서 AI에게 붙여넣기:

vibeguard ask login.py --write

---

# 12. Test AI workflow commands
# 12. AI 워크플로우 테스트

vibeguard doctor

vibeguard anchor --dry-run

vibeguard patch "진행 표시바 추가해줘" --json

vibeguard explain --json

vibeguard guard --json

vibeguard export claude

---

# 13. Optional watch mode
# 13. 실시간 감시

pip install watchdog

vibeguard watch

---

# Success
# 성공 기준

If these run without errors:

vibeguard --help
vibeguard init
vibeguard checkpoint "test"
vibeguard history
vibeguard doctor
vibeguard patch "test" --json
vibeguard guard --json

Installation is correct.
설치 성공입니다.

---

# All Commands Summary
# 전체 명령어 요약

| 명령어 | 하는 일 |
|--------|---------|
| `vibeguard init` | 프로젝트 한 번에 세팅 |
| `vibeguard checkpoint "메시지"` | 세이브 포인트 저장 |
| `vibeguard undo` | 마지막 세이브 포인트로 되돌리기 |
| `vibeguard history` | 저장된 세이브 포인트 목록 보기 |
| `vibeguard protect <파일>` | 파일 AI 수정으로부터 보호 |
| `vibeguard protect --list` | 보호 목록 보기 |
| `vibeguard protect --remove <파일>` | 보호 해제 |
| `vibeguard ask <파일>` | 파일 설명 프롬프트 생성 |
| `vibeguard doctor` | 프로젝트 구조 진단 |
| `vibeguard anchor` | 안전 구역(앵커) 삽입 |
| `vibeguard patch "요청"` | AI 수정 요청서 생성 |
| `vibeguard explain` | 최근 변경사항 설명 |
| `vibeguard guard` | 종합 안전 체크 |
| `vibeguard export <도구>` | 도구별 템플릿 내보내기 |
| `vibeguard watch` | 실시간 감시 |
