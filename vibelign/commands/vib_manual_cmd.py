# === ANCHOR: VIB_MANUAL_CMD_START ===
"""vib manual - 코알못을 위한 VibeLign 상세 매뉴얼."""

from __future__ import annotations

from typing import TypedDict

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


class ManualEntry(TypedDict):
    emoji: str
    title: str
    one_line: str
    what: str
    when: list[str]
    examples: list[tuple[str, str]]
    options: list[tuple[str, str]]


# ──────────────────────────────────────────────
# 매뉴얼 데이터
# ──────────────────────────────────────────────

MANUAL: dict[str, ManualEntry] = {
    "start": {
        "emoji": "🚀",
        "title": "vib start",
        "one_line": "처음 시작할 때 딱 한 번만 실행해요",
        "what": (
            "새 프로젝트에서 VibeLign을 처음 쓸 때 필요한 파일을 자동으로 만들어줘요.\n"
            "AGENTS.md, AI_DEV_SYSTEM_SINGLE_FILE.md 같은 파일이 생기는데,\n"
            "이게 있어야 AI가 내 프로젝트를 제대로 이해하고 작업해요.\n\n"
            "Git을 쓰는 프로젝트라면 커밋 전에 비밀정보를 막아주는 보호도 같이 켜줘요.\n"
            "그래서 API 키, 토큰, .env 같은 걸 실수로 올리려 하면 커밋 단계에서 한 번 더 잡아줘요.\n\n"
            "`vib start --all-tools`를 쓰면 Claude, Antigravity, OpenCode, Cursor, Codex 준비도 한 번에 해줘요.\n"
            "기본값은 기존 설정을 최대한 보존하면서 없는 것만 추가해요.\n"
            "정말 다시 깔듯이 새로 만들고 싶을 때만 `--force`를 써요."
        ),
        "when": [
            "새 프로젝트 폴더에서 VibeLign을 처음 쓸 때",
            "AI한테 코딩을 맡기기 전에 한 번만 세팅할 때",
            "설치 직후 처음 설정할 때",
            "여러 AI 도구를 한 번에 준비하고 싶을 때",
        ],
        "examples": [
            ("vib start", "기본 세팅 (가장 많이 씀)"),
            (
                "vib start --all-tools",
                "Claude, Antigravity, OpenCode, Cursor, Codex를 한 번에 준비",
            ),
            ("vib start --all-tools --force", "기존 VibeLign 설정도 다시 생성"),
            ("vib start --quickstart", "세팅 + 앵커 자동 삽입까지 한 번에"),
        ],
        "options": [
            (
                "--all-tools",
                "Claude, Antigravity, OpenCode, Cursor, Codex 설정을 한 번에 준비해요.\n기존 설정은 최대한 보존하면서 없는 것만 추가해요.",
            ),
            (
                "--tools",
                "원하는 도구만 골라서 준비해요.\n예: claude,opencode,cursor,antigravity,codex",
            ),
            (
                "--force",
                "기존 VibeLign 설정 파일도 다시 만들거나 덮어써요.\n기본값은 안전 모드라서 기존 설정을 최대한 유지해요.",
            ),
            (
                "--quickstart",
                "start 실행 후 anchor --auto 까지 자동으로 실행해요.\n한 번에 다 끝내고 싶을 때 써요.",
            ),
            (
                "준비 상태 안내",
                "start가 끝나면 도구별로 '바로 사용 가능' / '거의 끝남'을 알려줘요.\n현재는 Claude, Antigravity, OpenCode는 바로 사용 가능으로 보여줘요.",
            ),
            (
                "비밀정보 커밋 보호",
                "Git 저장소라면 pre-commit 보호도 같이 설치해요.\n커밋 전에 API 키, 토큰, 개인키, .env 같은 걸 검사해줘요.",
            ),
        ],
    },
    "checkpoint": {
        "emoji": "💾",
        "title": "vib checkpoint",
        "one_line": "게임 세이브처럼 지금 상태를 저장해요",
        "what": (
            "AI한테 코드를 맡기기 전에 현재 상태를 저장해두는 기능이에요.\n"
            "뭔가 잘못되면 이 시점으로 되돌릴 수 있어요.\n"
            "게임에서 '세이브' 버튼 누르는 것과 똑같아요.\n\n"
            "메시지 없이 실행하면 메모를 입력할 수 있는 화면이 나와요.\n"
            "git commit 메시지처럼 '이 시점에 뭘 했는지' 적어두면\n"
            "나중에 vib undo 에서 어떤 걸 골라야 할지 쉽게 알 수 있어요.\n\n"
            "체크포인트 저장 시 PROJECT_CONTEXT.md도 자동으로 갱신돼요.\n"
            "AI 툴을 바꿀 때 별도로 vib transfer를 실행하지 않아도 됩니다."
        ),
        "when": [
            "AI한테 수정을 시키기 바로 직전",
            "기능이 완성됐을 때 기록을 남기고 싶을 때",
            "큰 작업을 시작하기 전에 안전망을 만들 때",
        ],
        "examples": [
            ("vib checkpoint", "실행 → 메시지 입력 화면이 나와요"),
            ('vib checkpoint "로그인 완성"', "메시지를 바로 지정해서 저장"),
            ('vib checkpoint "버그 수정 전"', "작업 전 백업"),
        ],
        "options": [
            (
                "message",
                '저장할 때 메모를 남길 수 있어요.\n메시지 없이 실행하면 입력 화면이 나와요.\n엔터만 누르면 메시지 없이 저장돼요.\n예: vib checkpoint "회원가입 버튼 추가"',
            ),
        ],
    },
    "undo": {
        "emoji": "⏪",
        "title": "vib undo",
        "one_line": "저장한 곳으로 되돌려요",
        "what": (
            "AI가 코드를 이상하게 바꿨을 때 저장한 시점으로 되돌려요.\n"
            "게임에서 '불러오기' 버튼 누르는 것과 똑같아요.\n"
            "checkpoint로 저장해뒀어야 쓸 수 있어요.\n\n"
            "실행하면 저장된 목록이 번호와 함께 나와요:\n"
            "  [1] 오늘 16:52:47   로그인 기능 추가 전  ← 가장 최근\n"
            "  [2] 오늘 14:30:05   시작\n"
            "  [0] 취소\n\n"
            "번호를 입력하면 그 시점으로 되돌아가요.\n"
            "엔터만 누르면 가장 최근 저장으로 되돌려요.\n"
            "0을 누르면 아무것도 안 하고 취소돼요."
        ),
        "when": [
            "AI가 코드를 망가뜨렸을 때",
            "수정 결과가 마음에 들지 않을 때",
            "실수로 파일을 지웠을 때",
            "특정 시점으로 골라서 되돌리고 싶을 때",
        ],
        "examples": [
            ("vib undo", "목록 보고 번호 선택 → 되돌리기"),
        ],
        "options": [
            (
                "번호 입력",
                "목록에서 원하는 시점의 번호를 입력해요.\n엔터 = 가장 최근 / 0 또는 q = 취소",
            ),
        ],
    },
    "history": {
        "emoji": "📋",
        "title": "vib history",
        "one_line": "저장 목록을 봐요",
        "what": (
            "지금까지 checkpoint로 저장한 기록을 전부 보여줘요.\n"
            "언제 저장했는지, 어떤 메시지를 남겼는지 확인할 수 있어요.\n\n"
            "시간은 '오늘 16:52:34' / '어제 09:00:11' 처럼 읽기 쉽게 나와요.\n"
            "되돌리려면 vib undo 를 쓰세요."
        ),
        "when": [
            "내가 언제 저장했는지 확인하고 싶을 때",
            "어떤 버전으로 되돌릴지 결정하기 전에 목록을 먼저 볼 때",
            "저장이 제대로 됐는지 확인하고 싶을 때",
        ],
        "examples": [
            ("vib history", "저장 기록 전체 보기"),
        ],
        "options": [],
    },
    "doctor": {
        "emoji": "🩺",
        "title": "vib doctor",
        "one_line": "프로젝트 건강 상태를 확인해요",
        "what": (
            "내 프로젝트가 AI 작업을 받기에 괜찮은 상태인지 점검해요.\n"
            "점수로 보여주고, 문제가 있으면 뭐가 문제인지 알려줘요.\n"
            "마치 의사가 건강검진 해주는 것처럼요."
        ),
        "when": [
            "AI한테 코딩을 시키기 전에 준비됐는지 확인할 때",
            "프로젝트 상태가 좋은지 수시로 확인할 때",
            "뭔가 이상한 것 같을 때 진단받고 싶을 때",
        ],
        "examples": [
            ("vib doctor", "기본 점검 (점수 + 문제 목록)"),
            ("vib doctor --strict", "더 꼼꼼하게 점검"),
            ("vib doctor --detailed", "문제마다 자세한 설명 포함"),
            ("vib doctor --fix", "앵커 없는 파일에 자동으로 앵커 추가"),
            ("vib doctor --write-report", "결과를 파일로 저장"),
        ],
        "options": [
            (
                "--strict",
                "기본 점검보다 더 꼼꼼하게 검사해요.\n작은 문제도 놓치지 않아요.",
            ),
            ("--detailed", "각 문제마다 왜 문제인지 설명을 추가로 보여줘요."),
            ("--fix-hints", "각 문제를 어떻게 고치면 되는지 힌트를 줘요."),
            (
                "--fix",
                "앵커가 없는 파일에 자동으로 앵커를 달아줘요.\n직접 하기 귀찮을 때 편해요.",
            ),
            (
                "--write-report",
                "점검 결과를 파일로 저장해요.\n나중에 다시 볼 수 있어요.",
            ),
            ("--json", "결과를 JSON 형식으로 출력해요. (개발자용)"),
        ],
    },
    "anchor": {
        "emoji": "⚓",
        "title": "vib anchor",
        "one_line": "AI가 정확한 위치를 찾을 수 있도록 표식을 달아요",
        "what": (
            "코드 파일에 '여기서부터 여기까지가 이 기능이야'라는 표식(앵커)을 달아요.\n"
            "이 표식이 있으면 AI가 수정할 때 정확한 위치를 찾을 수 있어요.\n"
            "지도에 핀 꽂는 것처럼요."
        ),
        "when": [
            "AI한테 처음으로 코딩을 시키기 전에 (한 번만 하면 돼요)",
            "새 파일을 추가했을 때",
            "앵커가 제대로 있는지 확인하고 싶을 때",
        ],
        "examples": [
            ("vib anchor --auto", "모든 파일에 자동으로 앵커 달기 (가장 많이 씀)"),
            (
                "vib anchor --suggest",
                "어떻게 달면 좋을지 추천만 보기 (실제로 바꾸지 않음)",
            ),
            ("vib anchor --validate", "앵커가 제대로 달려있는지 검사"),
            ("vib anchor --dry-run", "실제로 바꾸지 않고 어떻게 바뀔지 미리 보기"),
            ("vib anchor --only-ext .py", "Python 파일만 처리"),
        ],
        "options": [
            (
                "--auto",
                "모든 파일에 자동으로 앵커를 달아줘요.\n처음 설정할 때 이걸 써요.",
            ),
            (
                "--suggest",
                "앵커를 어떻게 달면 좋을지 추천만 보여줘요.\n실제로 파일을 바꾸지는 않아요.",
            ),
            (
                "--validate",
                "앵커가 올바르게 달려있는지 검사해요.\n짝이 안 맞는 앵커를 찾아줘요.",
            ),
            ("--dry-run", "실제로 바꾸지 않고 어떻게 바뀔지만 미리 보여줘요."),
            (
                "--only-ext .py",
                "특정 확장자의 파일만 처리해요.\n예: --only-ext .py (파이썬만), --only-ext .js (자바스크립트만)",
            ),
            ("--json", "결과를 JSON 형식으로 출력해요. (개발자용)"),
        ],
    },
    "scan": {
        "emoji": "🔍",
        "title": "vib scan",
        "one_line": "앵커 스캔 + 코드맵 갱신을 한 번에 해요",
        "what": (
            "앵커 검사, 앵커 인덱스 갱신, 코드맵 재생성을 한 번에 실행해요.\n"
            "anchor 와 start 를 따로 실행하지 않아도 돼요.\n"
            "뭔가 꼬인 것 같을 때 이걸 실행하면 대부분 해결돼요."
        ),
        "when": [
            "파일을 많이 추가하거나 삭제했을 때",
            "앵커가 꼬인 것 같을 때 한 번에 정리하고 싶을 때",
            "코드맵을 최신 상태로 갱신하고 싶을 때",
        ],
        "examples": [
            ("vib scan", "앵커 스캔 + 코드맵 갱신"),
            ("vib scan --auto", "문제 있는 앵커 자동 수정 + 코드맵 갱신"),
        ],
        "options": [
            (
                "--auto",
                "문제 있는 앵커를 자동으로 고쳐줘요.\n앵커를 지웠다가 다시 달아서 깨끗하게 만들어요.",
            ),
        ],
    },
    "patch": {
        "emoji": "🛠️",
        "title": "vib patch",
        "one_line": "말로 요청하면 안전한 수정 계획을 만들어요",
        "what": (
            '"로그인 버튼 추가해줘" 같이 말로 요청하면,\n'
            "어떤 파일의 어느 부분을 어떻게 수정할지 계획을 세워줘요.\n"
            "이 계획을 복사해서 AI (Claude, ChatGPT 등)에 붙여넣으면 돼요."
        ),
        "when": [
            "AI한테 코드 수정을 요청할 때 더 정확하게 전달하고 싶을 때",
            "어떤 파일을 수정해야 할지 모를 때 도움받고 싶을 때",
            "수정 전에 계획을 먼저 확인하고 싶을 때",
        ],
        "examples": [
            ('vib patch "로그인 버튼 추가"', "수정 계획 만들기"),
            ('vib patch "버그 수정" --ai', "AI가 더 정확하게 분석"),
            ('vib patch "사이드바 제거" --preview', "미리 보기"),
            ('vib patch "기능 추가" --copy', "결과를 클립보드에 복사"),
        ],
        "options": [
            ("request", '수정 요청을 말로 써요.\n예: vib patch "다크모드 추가해줘"'),
            (
                "--ai",
                "AI가 코드를 더 자세히 분석해서 정확한 계획을 세워요.\n조금 더 시간이 걸려요.",
            ),
            ("--preview", "수정 계획을 미리 보기로 확인해요."),
            (
                "--copy",
                "AI에 전달할 프롬프트를 클립보드에 복사해요.\n바로 붙여넣기할 수 있어요.",
            ),
            ("--write-report", "수정 계획을 파일로 저장해요."),
            ("--json", "결과를 JSON 형식으로 출력해요. (개발자용)"),
        ],
    },
    "guard": {
        "emoji": "🛡️",
        "title": "vib guard",
        "one_line": "AI가 코드를 망가뜨리지 않았는지 검사해요",
        "what": (
            "AI가 코드를 수정한 후, 구조가 망가지지 않았는지 종합 검사해요.\n"
            "doctor (건강 점검) + explain (변경 설명)을 합친 거예요.\n"
            "AI 작업 후 항상 한 번 실행해보세요."
        ),
        "when": [
            "AI가 코드를 수정한 직후",
            "뭔가 이상한 것 같을 때 종합 검진을 받고 싶을 때",
            "AI 작업 결과를 확인하고 싶을 때",
        ],
        "examples": [
            ("vib guard", "기본 검사"),
            ("vib guard --strict", "더 꼼꼼하게 검사"),
            ("vib guard --write-report", "결과를 파일로 저장"),
        ],
        "options": [
            ("--strict", "더 꼼꼼하게 검사해요. 작은 문제도 잡아줘요."),
            (
                "--since-minutes 60",
                "최근 몇 분 동안의 변경만 확인해요.\n기본값은 120분이에요.",
            ),
            ("--write-report", "검사 결과를 파일로 저장해요."),
            ("--json", "결과를 JSON 형식으로 출력해요. (개발자용)"),
        ],
    },
    "explain": {
        "emoji": "📖",
        "title": "vib explain",
        "one_line": "뭐가 바뀌었는지 쉽게 알려줘요",
        "what": (
            "최근에 코드가 어떻게 바뀌었는지 쉬운 말로 설명해줘요.\n"
            "AI가 수정한 내용을 이해하기 어려울 때 쓰세요.\n"
            '개발 경험 없어도 "이 파일에서 이런 게 바뀌었어요" 수준으로 알려줘요.'
        ),
        "when": [
            "AI가 수정한 내용이 뭔지 이해하고 싶을 때",
            "어떤 파일이 바뀌었는지 확인하고 싶을 때",
            "변경 내역을 누군가한테 설명해야 할 때",
        ],
        "examples": [
            ("vib explain", "전체 변경 설명"),
            ("vib explain main.py", "특정 파일만 설명"),
            ("vib explain --ai", "AI가 더 자세하게 분석"),
            ("vib explain --since-minutes 30", "최근 30분 변경만 보기"),
        ],
        "options": [
            ("file", "특정 파일의 변경만 설명해요.\n예: vib explain login.py"),
            ("--ai", "AI가 변경 내용을 더 자세하게 분석해서 설명해줘요."),
            (
                "--since-minutes 숫자",
                "최근 몇 분 동안의 변경만 보여줘요.\n기본값은 120분이에요.",
            ),
            ("--write-report", "설명 결과를 파일로 저장해요."),
            ("--json", "결과를 JSON 형식으로 출력해요. (개발자용)"),
        ],
    },
    "protect": {
        "emoji": "🔒",
        "title": "vib protect",
        "one_line": "중요한 파일을 AI가 건드리지 못하게 잠가요",
        "what": (
            "절대 바뀌면 안 되는 파일을 보호해요.\n"
            "보호된 파일은 AI가 수정 대상으로 포함시키지 않아요.\n"
            "설정 파일, 환경 변수 파일 등에 쓰면 좋아요."
        ),
        "when": [
            ".env 같은 설정 파일을 AI가 건드리지 않았으면 할 때",
            "중요한 파일을 실수로 수정하는 걸 막고 싶을 때",
            "보호 목록을 관리하고 싶을 때",
        ],
        "examples": [
            ("vib protect main.py", "main.py 보호"),
            ("vib protect .env", ".env 파일 보호"),
            ("vib protect --list", "보호된 파일 목록 보기"),
            ("vib protect main.py --remove", "main.py 보호 해제"),
        ],
        "options": [
            ("file", "보호할 파일 이름을 써요.\n예: vib protect settings.py"),
            ("--list", "현재 보호되어 있는 파일 목록을 보여줘요."),
            ("--remove", "보호를 해제해요.\n예: vib protect main.py --remove"),
        ],
    },
    "watch": {
        "emoji": "👁️",
        "title": "vib watch",
        "one_line": "파일이 바뀔 때마다 자동으로 코드맵을 갱신해요",
        "what": (
            "파일이 저장될 때마다 자동으로 코드맵을 최신 상태로 유지해요.\n"
            "AI가 작업하는 동안 켜두면 항상 최신 정보로 작업할 수 있어요.\n"
            "watchdog 패키지가 설치되어 있어야 해요. (vib start 에서 자동 설치 제안)"
        ),
        "when": [
            "AI가 코딩하는 동안 백그라운드로 켜두고 싶을 때",
            "파일이 자주 바뀌는 작업 중에",
            "코드맵을 항상 최신 상태로 유지하고 싶을 때",
        ],
        "examples": [
            ("vib watch", "실시간 감시 시작 (Ctrl+C 로 종료)"),
            ("vib watch --strict", "더 꼼꼼한 감시 모드"),
            ("vib watch --write-log", "감시 로그를 파일로 저장"),
        ],
        "options": [
            ("--strict", "더 꼼꼼하게 감시해요. 작은 변화도 잡아줘요."),
            ("--write-log", "감시 중 발생한 일을 파일로 기록해요."),
            (
                "--debounce-ms 숫자",
                "파일이 바뀐 후 몇 밀리초 후에 처리할지 설정해요.\n기본값은 800ms예요. 너무 자주 갱신되면 늘려요.",
            ),
            ("--json", "결과를 JSON 형식으로 출력해요. (개발자용)"),
        ],
    },
    "ask": {
        "emoji": "💬",
        "title": "vib ask",
        "one_line": "파일이 뭘 하는지 쉬운 말로 설명해줘요",
        "what": (
            "코드 파일을 AI가 분석해서 쉬운 말로 설명해줘요.\n"
            "코드를 모르는 사람도 이 파일이 뭘 하는 건지 알 수 있어요.\n"
            "특정 질문도 할 수 있어요."
        ),
        "when": [
            "이 파일이 뭘 하는 건지 궁금할 때",
            "AI가 만든 코드를 이해하고 싶을 때",
            "특정 파일에 대해 질문하고 싶을 때",
        ],
        "examples": [
            ("vib ask main.py", "main.py가 뭘 하는지 설명"),
            ('vib ask login.py "비밀번호는 어디서 확인해?"', "특정 질문하기"),
            ("vib ask app.py --write", "설명을 파일로 저장"),
        ],
        "options": [
            ("file", "설명할 파일 이름이에요.\n예: vib ask login.py"),
            (
                "question",
                '파일에 대해 궁금한 걸 물어볼 수 있어요.\n예: vib ask login.py "이 함수는 뭐야?"',
            ),
            ("--write", "설명 결과를 VIBELIGN_ASK.md 파일로 저장해요."),
        ],
    },
    "config": {
        "emoji": "🔑",
        "title": "vib config",
        "one_line": "AI 기능을 쓰기 위한 API 키를 설정해요",
        "what": (
            "AI 기능(ask, patch --ai 등)을 사용하려면 API 키가 필요해요.\n"
            "이 명령어로 Anthropic(Claude) 또는 Gemini API 키를 설정할 수 있어요."
        ),
        "when": [
            "처음 설치하고 AI 기능을 쓰려고 할 때",
            "API 키를 바꾸고 싶을 때",
        ],
        "examples": [
            ("vib config", "API 키 설정 시작"),
        ],
        "options": [],
    },
    "secrets": {
        "emoji": "🚫",
        "title": "vib secrets",
        "one_line": "API 키 같은 비밀정보가 Git에 올라가기 전에 막아요",
        "what": (
            "커밋하기 전에 staged 된 변경사항을 검사해서\n"
            "API 키, 토큰, 개인키, .env 같은 비밀정보가 들어갔는지 확인해줘요.\n"
            "쉽게 말하면 '실수로 중요한 비밀번호를 인터넷에 올리기 전에 막아주는 문지기'예요.\n\n"
            "보통은 `vib start`를 하면 자동으로 연결돼서 따로 신경 쓸 일이 거의 없어요.\n"
            "직접 확인하고 싶을 때만 `vib secrets --staged`를 실행하면 돼요."
        ),
        "when": [
            "API 키나 .env를 실수로 git add 한 것 같을 때",
            "커밋 전에 한 번 더 확인하고 싶을 때",
            "왜 커밋이 막혔는지 이해하고 싶을 때",
        ],
        "examples": [
            ("vib secrets --staged", "지금 커밋하려는 내용에 비밀정보가 있는지 검사"),
            ("vib secrets --install-hook", "자동 검사 훅 설치"),
            ("vib secrets --uninstall-hook", "VibeLign이 설치한 자동 검사 훅 제거"),
        ],
        "options": [
            (
                "--staged",
                "지금 git add 해둔 내용만 검사해요.\n커밋 직전에 보는 검사라고 생각하면 쉬워요.",
            ),
            (
                "--install-hook",
                "커밋할 때마다 자동 검사되게 연결해요.\n보통은 vib start가 자동으로 해줘요.",
            ),
            (
                "--uninstall-hook",
                "VibeLign이 설치한 자동 검사 연결을 제거해요.",
            ),
            (
                "오탐 예외 처리",
                "진짜 비밀정보가 아닌데도 막히면 그 줄 끝에 `vibelign: allow-secret`를 붙여서 예외 처리할 수 있어요.",
            ),
        ],
    },
    "export": {
        "emoji": "📤",
        "title": "vib export",
        "one_line": "Claude, Cursor 등 AI 도구에 맞는 설정 파일을 만들어요",
        "what": (
            "Claude Code, Cursor, OpenCode 같은 AI 도구에서\n"
            "VibeLign을 연동해서 쓸 수 있도록 설정 파일을 만들어줘요."
        ),
        "when": [
            "Claude Code를 쓰면서 VibeLign도 같이 쓰고 싶을 때",
            "Cursor에서 VibeLign 설정을 적용하고 싶을 때",
        ],
        "examples": [
            ("vib export claude", "Claude Code용 설정 파일 생성"),
            ("vib export cursor", "Cursor용 설정 파일 생성"),
            ("vib export opencode", "OpenCode용 설정 파일 생성"),
        ],
        "options": [
            (
                "tool",
                "어떤 AI 도구용인지 선택해요.\n선택지: claude / opencode / cursor / antigravity",
            ),
        ],
    },
    "transfer": {
        "emoji": "🔄",
        "title": "vib transfer",
        "one_line": "AI 툴 전환 시 맥락 파일을 만들어요",
        "what": (
            "Claude Code → Cursor → Windsurf 등 AI 툴을 바꿀 때\n"
            "프로젝트 맥락을 즉시 전달해줘요.\n"
            "PROJECT_CONTEXT.md 파일 하나만 있으면 어떤 AI든 바로 이어서 작업 가능해요."
        ),
        "when": [
            "AI 툴을 바꾸기 직전에",
            "다른 사람에게 프로젝트를 넘길 때",
            "새 AI 채팅에 프로젝트 맥락을 전달하고 싶을 때",
        ],
        "examples": [
            ("vib transfer", "기본 생성 (PROJECT_CONTEXT.md)"),
            ("vib transfer --compact", "경량 버전 (토큰 절약)"),
            ("vib transfer --full", "핵심 파일 전체 포함"),
            ("vib transfer --out ctx.md", "파일명 지정"),
        ],
        "options": [
            (
                "--compact",
                "토큰을 최소화한 경량 버전을 만들어요.\n무료 플랜에서 쓸 때 좋아요.",
            ),
            (
                "--full",
                "핵심 파일을 더 깊이 포함해요.\n더 자세한 맥락이 필요할 때 써요.",
            ),
            (
                "--out 파일명",
                "출력 파일명을 지정해요.\n기본값은 PROJECT_CONTEXT.md예요.",
            ),
        ],
    },
    "completion": {
        "emoji": "⌨️",
        "title": "vib completion",
        "one_line": "탭키로 명령어를 자동완성해요",
        "what": (
            "vib + 탭키를 누르면 명령어 목록이 뜨게 해줘요.\n"
            '"vib pr" 치고 탭 누르면 "vib protect"가 자동완성돼요.\n'
            "macOS/Linux (zsh/bash)와 Windows (PowerShell) 모두 지원해요."
        ),
        "when": [
            "처음 설치하고 탭 자동완성을 설정하고 싶을 때 (딱 한 번만 하면 돼요)",
            "명령어 이름이 기억 안 날 때",
        ],
        "examples": [
            ("vib completion --install", "자동완성 자동 설정 (추천!)"),
            ("vib completion", "설정 방법 안내 보기"),
        ],
        "options": [
            (
                "--install",
                "자동완성을 자동으로 설정해줘요.\nzsh/bash/PowerShell을 자동으로 감지해요.\n새 터미널을 열면 바로 사용할 수 있어요.",
            ),
        ],
    },
    "init": {
        "emoji": "🔄",
        "title": "vib init",
        "one_line": "VibeLign을 최신 버전으로 다시 설치해요",
        "what": (
            "VibeLign을 최신 버전으로 재설치해요.\n"
            "업데이트가 있을 때, 또는 뭔가 이상할 때 쓰세요.\n"
            "uv 또는 pip을 자동으로 감지해서 설치해요."
        ),
        "when": [
            "VibeLign 업데이트를 하고 싶을 때",
            "설치가 꼬인 것 같을 때 다시 설치하고 싶을 때",
        ],
        "examples": [
            ("vib init", "최신 버전으로 재설치"),
            ("vib init --force", "강제로 다시 설치"),
        ],
        "options": [
            ("--force", "이미 최신 버전이어도 강제로 다시 설치해요."),
        ],
    },
    "install": {
        "emoji": "📦",
        "title": "vib install",
        "one_line": "단계별 설치 방법을 안내해줘요",
        "what": (
            "VibeLign을 처음 설치하는 방법을 단계별로 안내해줘요.\n"
            "터미널 여는 법부터 uv 설치, vibelign 설치까지 모두 설명해요."
        ),
        "when": [
            "처음 설치하는데 어떻게 해야 할지 모를 때",
            "설치 방법을 다시 확인하고 싶을 때",
        ],
        "examples": [
            ("vib install", "설치 방법 안내 보기"),
        ],
        "options": [],
    },
    "rules": {
        "emoji": "📋",
        "title": "VibeLign AI 개발 규칙",
        "one_line": "AI가 코드를 작성할 때 반드시 지켜야 할 규칙들이에요",
        "what": (
            "vib start를 실행하면 프로젝트에 AI_DEV_SYSTEM_SINGLE_FILE.md 파일이 생겨요.\n"
            "이 파일이 AI한테 '이렇게 코딩해야 해'를 알려주는 규칙서예요.\n"
            "Claude Code, OpenCode, Cursor 등 어떤 AI를 써도 이 규칙을 읽고 따라요.\n\n"
            "━━ 핵심 원칙 ━━\n\n"
            "🔹 패치 우선 원칙\n"
            "  AI는 파일 전체를 다시 쓰지 않아요.\n"
            "  꼭 필요한 부분만 최소한으로 수정해요.\n"
            "  관련 없는 파일은 절대 건드리지 않아요.\n\n"
            "━━ 두 가지 수정 방식 ━━\n\n"
            "방식 1 — 일반 수정 (기본)\n"
            "  평소처럼 말하면 AI가 알아서 수정해요.\n"
            "  예: '로그인 버튼 색 파란색으로 바꿔줘'\n\n"
            "방식 2 — 바이브라인 안전 수정 ('바이브라인으로' 또는 'vibelign')\n"
            "  요청에 '바이브라인으로'를 붙이면 전체 안전 워크플로우 자동 실행:\n"
            "  patch_get → 정확한 위치 확인 → 수정 → guard_check → checkpoint 저장\n"
            "  예: '바이브라인으로 로그인 버튼 색 파란색으로 바꿔줘'\n\n"
            "  ⚠️  '바이브라인으로' 없으면 → AI가 직접 수정 (VibeLign 툴 사용 안 함)\n\n"
            "━━ 파일 구조 규칙 ━━\n\n"
            "🔹 진입 파일 보호 (main.py, index.js 등)\n"
            "  진입 파일은 작게 유지해요. 실제 로직은 별도 파일로 분리해요.\n\n"
            "🔹 UI와 비즈니스 로직 분리\n"
            "  UI 파일: 화면 레이아웃, 버튼, 입력창만\n"
            "  로직 파일: 실제 처리, 파일 읽기/쓰기, 네트워크\n"
            "  두 가지를 한 파일에 섞으면 안 돼요.\n\n"
            "🔹 파일 크기 관리\n"
            "  파일이 커지면 역할별로 나눠요.\n"
            "  utils.py, helpers.py, misc.py 같은 모호한 이름 금지.\n"
            "  대신: backup_worker.py, translation_pipeline.py처럼 구체적으로 지어요.\n\n"
            "━━ 함수 설계 규칙 ━━\n\n"
            "🔹 함수 길이\n"
            "  함수가 40줄 넘으면 → 분리 고려\n"
            "  함수가 80줄 넘으면 → 반드시 분리\n"
            "  한 함수는 딱 한 가지 일만 해요.\n\n"
            "🔹 함수 이름\n"
            "  좋은 예: load_config(), parse_excel_row(), validate_input_path()\n"
            "  나쁜 예: do_stuff(), process(), handle(), run_all()\n\n"
            "🔹 파일 간 연결\n"
            "  순환 import 금지 (A가 B를 부르고, B가 다시 A를 부르는 구조)\n"
            "  공통 로직은 별도 파일로 분리해서 양쪽에서 가져다 써요.\n\n"
            "━━ 유지보수 규칙 (코알못도 관리할 수 있게) ━━\n\n"
            "🔹 매직 넘버 금지\n"
            "  나쁜 예: if retry > 3\n"
            "  좋은 예: MAX_RETRY = 3 / if retry > MAX_RETRY\n\n"
            "🔹 에러 메시지는 사람이 읽을 수 있게\n"
            "  나쁜 예: raise Exception('NoneType')\n"
            "  좋은 예: raise Exception('파일을 찾을 수 없어요. 경로를 확인하세요')\n\n"
            "🔹 조용한 실패 금지\n"
            "  except: pass 절대 금지\n"
            "  에러가 나면 반드시 화면에 표시해요.\n\n"
            "🔹 죽은 코드 제거\n"
            "  주석 처리된 코드 덩어리 남기지 않아요.\n"
            "  쓰지 않는 import, 변수, 함수 삭제해요.\n\n"
            "🔹 의존성 동기화\n"
            "  새 패키지를 추가하면 pyproject.toml도 함께 업데이트해요.\n\n"
            "🔹 주석도 함께 업데이트\n"
            "  코드를 바꾸면 위에 있는 설명 주석도 같이 바꿔요.\n"
            "  오래된 주석은 없는 것보다 더 혼란스러워요.\n\n"
            "━━ 앵커 규칙 ━━\n\n"
            "🔹 앵커(ANCHOR)가 있으면 그 안에서만 수정\n"
            "  앵커를 무시하고 파일 전체를 바꾸면 안 돼요.\n"
            "  앵커가 없는 큰 파일은 먼저 앵커를 달고 작업해요.\n\n"
            "🔹 앵커를 허락 없이 지우면 안 돼요"
        ),
        "when": [
            "AI가 내 규칙을 제대로 따르고 있는지 확인하고 싶을 때",
            "'바이브라인으로' 키워드를 언제 써야 하는지 헷갈릴 때",
            "AI가 이상하게 코딩할 때 어떤 규칙이 있는지 확인할 때",
            "내 프로젝트 규칙을 처음부터 다시 보고 싶을 때",
        ],
        "examples": [
            ("vib manual rules", "전체 규칙 보기"),
            ("vib start", "프로젝트에 규칙 파일(AI_DEV_SYSTEM_SINGLE_FILE.md) 생성"),
            ("cat AI_DEV_SYSTEM_SINGLE_FILE.md", "규칙 파일 직접 보기"),
        ],
        "options": [
            (
                "규칙 파일 위치",
                "AI_DEV_SYSTEM_SINGLE_FILE.md — 프로젝트 루트에 생성돼요",
            ),
            (
                "규칙 업데이트",
                "vib start 재실행하면 최신 규칙으로 덮어써요 (기존 파일은 .md~ 백업)",
            ),
            (
                "어떤 AI든 적용",
                "AGENTS.md를 읽는 Claude Code, OpenCode, Cursor 모두 자동 적용",
            ),
        ],
    },
    "mcp": {
        "emoji": "🤖",
        "title": "MCP (AI 자동 연동)",
        "one_line": "AI가 VibeLign 기능을 자동으로 써요",
        "what": (
            "보통은 AI한테 '체크포인트 저장해줘'라고 말하면\n"
            "AI가 명령어를 알려주고, 여러분이 직접 터미널에서 쳐야 해요.\n\n"
            "MCP가 연결되면 달라져요.\n"
            "AI한테 말하면 AI가 직접 VibeLign을 실행해요.\n"
            "터미널을 따로 열 필요가 없어요.\n\n"
            "설정: vib start 실행 → Claude Code 재시작 (딱 한 번만)\n\n"
            "추가로 `vib start --all-tools`를 쓰면 여러 도구를 한 번에 준비할 수 있어요.\n"
            "현재 안내 기준으로는 Claude, Antigravity, OpenCode는 바로 사용 가능으로 보여주고,\n"
            "Cursor, Codex는 마지막 연결 확인이 한 번 더 필요할 수 있어요.\n\n"
            "쉽게 생각하면:\n"
            "  Claude        → 거의 바로 됨\n"
            "  Antigravity   → 사용자 경험상 바로 되는 경우가 많음\n"
            "  OpenCode      → 프로젝트 설정 파일까지 함께 준비 가능\n"
            "  Cursor/Codex  → 규칙 파일은 준비되지만 마지막 연결 확인이 필요할 수 있음\n\n"
            "━━ 두 가지 수정 방식 ━━\n\n"
            "방식 1 — 일반 수정 (기본)\n"
            "  평소처럼 말하면 AI가 알아서 수정해요.\n"
            "  예: '로그인 버튼 색 파란색으로 바꿔줘'\n\n"
            "방식 2 — 바이브라인 안전 수정 (키워드: '바이브라인으로')\n"
            "  요청 앞에 '바이브라인으로'를 붙이면 전체 안전 워크플로우 자동 실행:\n"
            "  patch_get → 정확한 위치 확인 → 수정 → guard_check → checkpoint 저장\n"
            "  예: '바이브라인으로 로그인 버튼 색 파란색으로 바꿔줘'\n\n"
            "━━ 사용 가능한 MCP 도구 ━━\n"
            "  checkpoint_create   — 체크포인트 저장   (vib checkpoint 와 같아요)\n"
            "  checkpoint_list     — 저장 목록 보기    (vib history 와 같아요)\n"
            "  checkpoint_restore  — 특정 시점 복원    (vib undo 와 같아요)\n"
            "\n"
            "  ⚠️  복원할 때는 '바이브라인 언두해줘'라고 말하면 돼요.\n"
            "     AI가 목록을 먼저 보여주고 → 번호를 고르면 → 자동으로 복원해요.\n"
            "     ('vib undo'를 직접 실행하면 MCP 환경에서 멈춰요. AI한테 맡기세요!)\n\n"
            "  project_context_get — AI 전환 시 컨텍스트 전달 (vib transfer 와 같아요)\n"
            "  doctor_run          — 건강 진단         (vib doctor 와 같아요)\n"
            "  guard_check         — AI 작업 후 확인   (vib guard 와 같아요)\n"
            "  protect_add         — 파일 보호 등록    (vib protect 와 같아요)\n"
            "  patch_get           — 자연어→CodeSpeak 번역 + 수정 위치 특정 (vib patch 와 같아요)\n"
            "  anchor_run          — 앵커 자동 삽입    (vib anchor --auto 와 같아요)\n"
            "  anchor_list         — 앵커 목록 보기\n"
            "  explain_get         — 변경 내역 분석    (vib explain 와 같아요)\n"
            "  config_get          — 현재 설정 확인"
        ),
        "when": [
            "Claude Code와 VibeLign을 함께 쓸 때",
            "Antigravity나 OpenCode도 같이 준비하고 싶을 때",
            "매번 터미널에서 명령어 치기 귀찮을 때",
            "AI가 작업 전후를 자동으로 관리해주길 원할 때",
            "어느 파일을 건드려야 할지 애매한 수정을 안전하게 하고 싶을 때",
        ],
        "examples": [
            ("vib start --all-tools", "여러 AI 도구를 한 번에 준비"),
            ('"저장해줘"', "checkpoint_create 호출"),
            ('"저장된 목록 보여줘"', "checkpoint_list 호출"),
            (
                '"바이브라인 언두해줘"',
                "목록 보여줌 → 번호 선택 → checkpoint_restore 자동 호출",
            ),
            ('"3번으로 복원해줘"', "checkpoint_restore 바로 호출"),
            (
                '"바이브라인으로 로그인 버튼 크기 키워줘"',
                "patch_get → 수정 → guard_check → checkpoint 자동 실행",
            ),
            (
                '"바이브라인으로 다크모드 배경색 바꿔줘"',
                "안전 수정 전체 워크플로우 자동 실행",
            ),
            ('"프로젝트 상태 진단해줘"', "doctor_run 호출"),
            ('"방금 수정한 거 문제없는지 확인해줘"', "guard_check 호출"),
            ('"앵커 없는 파일에 앵커 삽입해줘"', "anchor_run 호출"),
        ],
        "options": [
            ("설정 방법", "vib start 한 번 실행 → Claude Code 재시작"),
            (
                "여러 도구 한 번에 준비",
                "vib start --all-tools\nClaude, Antigravity, OpenCode, Cursor, Codex 준비를 한 번에 시도해요.",
            ),
            (
                "바로 사용 가능",
                "현재 start 안내 기준으로 Claude, Antigravity, OpenCode는 바로 사용 가능으로 보여줘요.",
            ),
            (
                "마지막 확인 필요",
                "Cursor, Codex는 설정 화면이나 설정 파일에서 VibeLign 연결을 한 번 더 확인해야 할 수 있어요.",
            ),
            (
                "'바이브라인으로' 키워드",
                "요청 앞에 붙이면 안전 수정 모드. 로직·기능 변경 시 권장",
            ),
            ("일반 수정", "단순 텍스트 변경, 오타 수정은 그냥 말해도 돼요"),
            (
                "복원은 시점 지정 필수",
                "'되돌려줘'만 하면 AI가 목록을 먼저 보여줘요. 번호나 메시지를 함께 말하세요",
            ),
            (
                "한 번에 여러 요청 가능",
                "'저장하고, 앵커 확인하고, 작업 시작해줘' → AI가 순서대로 자동 처리",
            ),
        ],
    },
}

# 그룹 순서
GROUPS = [
    ("🏁 처음 시작", ["start", "init", "install"]),
    ("💾 세이브 & 되돌리기", ["checkpoint", "undo", "history"]),
    ("🔬 점검 & 확인", ["doctor", "guard", "explain"]),
    ("✏️ AI 수정 요청", ["patch", "anchor", "scan"]),
    (
        "🗂️ 파일 & 설정",
        [
            "protect",
            "transfer",
            "ask",
            "config",
            "secrets",
            "export",
            "watch",
            "completion",
        ],
    ),
    ("🤖 MCP (AI 자동 연동)", ["mcp"]),
    ("📋 AI 개발 규칙", ["rules"]),
]


# ──────────────────────────────────────────────
# 렌더링
# ──────────────────────────────────────────────


def _render_command(key: str) -> None:
    """단일 커맨드 상세 매뉴얼 출력."""
    m = MANUAL.get(key)
    if not m:
        console.print(f"[red]'{key}' 커맨드를 찾을 수 없어요.[/red]")
        console.print("사용 가능한 커맨드: " + ", ".join(MANUAL.keys()))
        return

    emoji = m["emoji"]
    title = m["title"]
    one_line = m["one_line"]

    # 헤더 패널
    header = Text()
    header.append(f"{emoji}  ", style="bold")
    header.append(title, style="bold cyan")
    header.append(f"  —  {one_line}", style="dim white")
    console.print(Panel(header, border_style="cyan", padding=(0, 2)))

    # 이게 뭐야?
    console.print()
    console.print("  [bold yellow]💡 이게 뭐야?[/bold yellow]")
    for line in m["what"].splitlines():
        console.print(f"     [white]{line}[/white]")

    # 언제 써?
    if m["when"]:
        console.print()
        console.print("  [bold green]🕐 언제 써?[/bold green]")
        for w in m["when"]:
            console.print(f"     [dim]•[/dim]  {w}")

    # 이렇게 쳐봐 (MCP는 AI한테 말하는 방식)
    if m["examples"]:
        console.print()
        label = "💬  AI한테 이렇게 말해봐" if key == "mcp" else "✏️  이렇게 쳐봐"
        console.print(f"  [bold magenta]{label}[/bold magenta]")
        tbl = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        tbl.add_column(style="bold cyan", no_wrap=True)
        tbl.add_column(style="dim white")
        for cmd, desc in m["examples"]:
            tbl.add_row(cmd, f"→  {desc}")
        console.print(tbl)

    # 옵션 설명
    if m["options"]:
        console.print()
        console.print("  [bold blue]⚙️  옵션 설명[/bold blue]")
        tbl = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        tbl.add_column(style="bold cyan", no_wrap=True, width=24)
        tbl.add_column(style="white")
        for opt, desc in m["options"]:
            tbl.add_row(opt, desc)
        console.print(tbl)

    console.print()


def _render_overview() -> None:
    """전체 커맨드 목록 개요 출력."""
    console.print()
    console.print(
        Panel(
            Text("VibeLign 전체 명령어 매뉴얼", style="bold white", justify="center"),
            subtitle="[dim]vib manual <커맨드명>  →  상세 보기[/dim]",
            border_style="bright_blue",
            padding=(0, 4),
        )
    )
    console.print()

    for group_name, keys in GROUPS:
        tbl = Table(
            title=group_name,
            box=box.ROUNDED,
            border_style="dim",
            title_style="bold white",
            show_header=False,
            padding=(0, 2),
            expand=False,
        )
        tbl.add_column(style="bold cyan", no_wrap=True, width=14)
        tbl.add_column(style="dim white", width=10)
        tbl.add_column(style="white")
        for k in keys:
            m = MANUAL[k]
            tbl.add_row(
                k,
                m["emoji"],
                m["one_line"],
            )
        console.print(tbl)
        console.print()

    console.print("[dim]  상세 보기:  vib manual checkpoint[/dim]")
    console.print("[dim]  파일 저장:  vib manual --save[/dim]")
    console.print()


def _render_all() -> None:
    """모든 커맨드 상세 출력 (--save용 또는 전체 보기)."""
    _render_overview()
    console.print()
    for group_name, keys in GROUPS:
        console.rule(f"[bold dim]{group_name}[/bold dim]")
        console.print()
        for k in keys:
            _render_command(k)


def _save_markdown() -> str:
    """마크다운 매뉴얼 생성 후 파일 저장."""
    lines = [
        "# VibeLign 사용 설명서\n",
        "> AI한테 코딩 시켜도 안전하게 지켜주는 도구 — 코알못을 위한 매뉴얼\n\n",
        "---\n\n",
        "## 목차\n\n",
    ]
    for group_name, keys in GROUPS:
        lines.append(f"### {group_name}\n")
        for k in keys:
            m = MANUAL[k]
            lines.append(f"- [{m['emoji']} `vib {k}`](#{k}) — {m['one_line']}\n")
        lines.append("\n")

    lines.append("---\n\n")

    for group_name, keys in GROUPS:
        lines.append(f"## {group_name}\n\n")
        for k in keys:
            m = MANUAL[k]
            emoji = m["emoji"]
            lines.append(f"### {emoji} `{m['title']}`\n\n")
            lines.append(f"> {m['one_line']}\n\n")
            lines.append(f"**💡 이게 뭐야?**\n\n{m['what']}\n\n")
            if m["when"]:
                lines.append("**🕐 언제 써?**\n\n")
                for w in m["when"]:
                    lines.append(f"- {w}\n")
                lines.append("\n")
            if m["examples"]:
                lines.append("**✏️ 이렇게 쳐봐**\n\n```\n")
                for cmd, desc in m["examples"]:
                    lines.append(f"{cmd}   # {desc}\n")
                lines.append("```\n\n")
            if m["options"]:
                lines.append("**⚙️ 옵션 설명**\n\n")
                lines.append("| 옵션 | 설명 |\n|------|------|\n")
                for opt, desc in m["options"]:
                    desc_inline = desc.replace("\n", " ")
                    lines.append(f"| `{opt}` | {desc_inline} |\n")
                lines.append("\n")
            lines.append("---\n\n")

    content = "".join(lines)
    save_path = "VIBELIGN_MANUAL.md"
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(content)
    return save_path


# ──────────────────────────────────────────────
# 진입점
# ──────────────────────────────────────────────


def run_vib_manual(args) -> None:
    command = getattr(args, "command_name", None)
    save = getattr(args, "save", False)
    all_flag = getattr(args, "all", False)

    if save:
        path = _save_markdown()
        console.print(
            f"\n[bold green]✅ 매뉴얼을 저장했어요![/bold green]  →  [cyan]{path}[/cyan]"
        )
        console.print(
            "[dim]이 파일을 AI한테 보여주면 VibeLign에 대해 더 잘 도와줄 수 있어요.[/dim]\n"
        )
        return

    if command:
        _render_command(command)
    elif all_flag:
        _render_all()
    else:
        _render_overview()


# === ANCHOR: VIB_MANUAL_CMD_END ===
