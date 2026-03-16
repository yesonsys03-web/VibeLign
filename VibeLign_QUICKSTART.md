
# VibeLign QUICKSTART (Beginner Guide)
# VibeLign 빠른 시작 가이드

This guide shows exactly how to set up and use VibeLign step‑by‑step.
이 가이드는 VibeLign을 **1단계부터 순서대로** 설치하고 사용하는 방법을 설명합니다.

---

# 1. Download
# 1. 다운로드

Download:

VibeLign_final_release.zip

압축을 풉니다.

---

# 2. Open Terminal
# 2. 터미널 열기

Mac → Terminal.app 실행

---

# 3. Move to folder
# 3. 폴더 이동

Example:

cd ~/Downloads/VibeLign_final_release

---

# 4. Check files
# 4. 파일 확인

Run:

ls

You should see:

README.md
pyproject.toml
vibelign
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

설치 후 `vib` 과 `vibelign` 두 명령어 모두 사용 가능합니다.

---

# 7. Verify
# 7. 설치 확인

vib --help

---

# 8. First-time setup (NEW)
# 8. 처음 세팅 (신규)

가장 빠른 세팅 방법 — 명령어 하나로 시작합니다:

vib start

이 명령어로:
- AI 규칙 파일 확인 및 생성
- AI 도구 훅 설정 (Claude Code 등)
- 프로젝트 건강 점수 확인
- 다음 할 일 안내

VibeLign 메타데이터를 초기화/재설치하려면:

vib init

---

# 9. Save & Restore (NEW)
# 9. 저장 & 되돌리기 (신규)

AI가 코드를 망쳤을 때를 대비해 세이브 포인트를 저장하세요.

작업 전에 저장:

vib checkpoint "로그인 기능 추가 전"

저장 이력 보기:

vib history

망쳤으면 되돌리기:

vib undo

---

# 10. Protect important files (NEW)
# 10. 중요 파일 보호 (신규)

AI가 절대 건드리면 안 되는 파일을 잠글 수 있어요:

vib protect main.py

보호 목록 보기:

vib protect --list

보호 해제:

vib protect --remove main.py

---

# 11. Ask AI to explain a file (NEW)
# 11. 파일 쉽게 설명받기 (신규)

코드가 뭘 하는지 모를 때, AI에게 물어볼 프롬프트를 만들어줍니다:

vib ask login.py

파일로 저장해서 AI에게 붙여넣기:

vib ask login.py --write

---

# 12. Test AI workflow commands
# 12. AI 워크플로우 테스트

vib doctor

vib anchor --dry-run

vib scan

vib patch "진행 표시바 추가해줘" --json

vib patch "로그인 버튼 추가해줘" --json

vib explain --json

vib guard --json

vib export claude

---

# 13. Optional watch mode (실시간 감시) — 선택 사항
# 13. watchdog 설치 후 실시간 감시 사용 가능

> **watchdog이 뭔가요?**
> VibeLign이 파일 변화를 **실시간으로** 감지할 수 있게 해주는 도우미 프로그램이에요.
> VibeLign을 설치할 때 기본으로 포함되지 않아서, 따로 설치해야 해요.
> `vib watch` 명령어를 쓰지 않는다면 **설치 안 해도 됩니다.**

**설치 방법 (둘 중 하나만 실행하세요)**

uv로 설치한 경우:

```
uv add watchdog
```

pip으로 설치한 경우:

```
pip install watchdog
```

> **어떤 걸 써야 하나요?**
> 6단계에서 `uv tool install .` 로 설치했으면 → `uv add watchdog`
> `pip install -e .` 로 설치했으면 → `pip install watchdog`

**설치 확인**

```
python3 -c "import watchdog; print('watchdog 설치 완료!')"
```

위 명령어 실행 후 `watchdog 설치 완료!` 가 출력되면 성공이에요.

**실행**

```
vib watch
```

파일이 바뀔 때마다 터미널에 알림이 나와요. 종료하려면 `Ctrl + C` 를 누르세요.

---

# Success
# 성공 기준

If these run without errors:

vib --help
vib start
vib checkpoint "test"
vib history
vib doctor
vib patch "test" --json
vib guard --json

Installation is correct.
설치 성공입니다.

---

# All Commands Summary
# 전체 명령어 요약

| 명령어 | 하는 일 |
|--------|---------|
| `vib init` | VibeLign 메타데이터 초기화/재설치 |
| `vib start` | 처음 쓰는 사람용 가이드 온보딩 |
| `vib checkpoint "메시지"` | 세이브 포인트 저장 |
| `vib undo` | 마지막 세이브 포인트로 되돌리기 |
| `vib history` | 저장된 세이브 포인트 목록 보기 |
| `vib protect <파일>` | 파일 AI 수정으로부터 보호 |
| `vib protect --list` | 보호 목록 보기 |
| `vib protect --remove <파일>` | 보호 해제 |
| `vib ask <파일>` | 파일 설명 프롬프트 생성 |
| `vib doctor` | 프로젝트 구조 진단 |
| `vib anchor` | 안전 구역(앵커) 삽입 |
| `vib scan` | 앵커 스캔 + 코드맵 갱신 한 번에 |
| `vib patch "요청"` | AI 수정 요청서 생성 (한국어 지원) |
| `vib explain` | 최근 변경사항 설명 |
| `vib guard` | 종합 안전 체크 |
| `vib export <도구>` | 도구별 템플릿 내보내기 |
| `vib watch` | 실시간 감시 |

기존 `vibelign` 명령어도 하위 호환 래퍼로 계속 지원됩니다.
