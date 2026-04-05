// === ANCHOR: COMMAND_DATA2_START ===
import { GuideStep, FlagDef } from "./commandData";

export const COMMANDS_EXT = [
  {
    name: "install", icon: "📦", color: "#4DFF91",
    title: "인스톨",
    short: "단계별 설치 방법 안내",
    desc: "VibeLign을 처음 설치하는 방법을 단계별로 안내해줘요. 터미널 여는 법부터 uv 설치, vibelign 설치까지 모두 알려줘요. 설치 에러 대처법도 포함돼요.",
    usage: "vib install",
    tips: ["처음 설치하는데 어떻게 해야 할지 모를 때 쓰세요", "Mac, Windows, Linux 모두 안내해줘요", "설치 후 vib start로 시작하면 돼요"],
    guide: [
      {
        step: "1단계", title: "터미널 열기",
        lines: [
          { t: "info", v: "Mac  →  ⌘ + 스페이스  →  'Terminal' 검색 후 엔터" },
          { t: "info", v: "Windows  →  시작 버튼  →  'PowerShell' 검색 후 엔터" },
          { t: "info", v: "Linux  →  Ctrl + Alt + T" },
        ],
      },
      {
        step: "2단계", title: "uv 설치", subtitle: "더 빠르고 안정적이에요 (없으면 설치하세요)",
        lines: [
          { t: "label", v: "Mac / Linux" },
          { t: "code",  v: "curl -LsSf https://astral.sh/uv/install.sh | sh" },
          { t: "label", v: "Windows (PowerShell)" },
          { t: "code",  v: 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"' },
        ],
        warn: "설치 후 터미널을 닫고 새로 열어주세요",
      },
      {
        step: "3단계", title: "vibelign 설치",
        lines: [
          { t: "label", v: "Mac / Linux" },
          { t: "code",  v: "pip install vibelign" },
          { t: "label", v: "Windows (권장 — vib 바로 사용 가능)" },
          { t: "code",  v: "uv tool install vibelign" },
          { t: "label", v: "Windows (uv 없을 때 대안)" },
          { t: "code",  v: "py -m pip install vibelign --no-warn-script-location" },
          { t: "info",  v: "→ 실행 시 vib 대신:  py -m vibelign start / checkpoint ..." },
        ],
      },
      {
        step: "4단계", title: "설치 확인",
        lines: [
          { t: "code", v: "vib --help" },
        ],
      },
      {
        step: "5단계", title: "빠른 검색 도구 설치", subtitle: "선택 — 없어도 잘 작동해요", optional: true,
        lines: [
          { t: "info",  v: "파일이 수백 개 이상인 프로젝트에서 스캔 속도 차이가 체감돼요." },
          { t: "label", v: "Mac (Homebrew)" },
          { t: "code",  v: "brew install fd ripgrep" },
          { t: "label", v: "Windows (winget)" },
          { t: "code",  v: "winget install sharkdp.fd BurntSushi.ripgrep.MSVC" },
          { t: "label", v: "Ubuntu / Debian (Linux)" },
          { t: "code",  v: "sudo apt install fd-find ripgrep" },
        ],
        warn: "설치 안 해도 VibeLign은 정상 작동해요. 속도 차이만 있어요.",
      },
      {
        step: "에러 대처", title: "설치 중 에러가 나면?",
        lines: [
          { t: "error", v: '"command not found"' },
          { t: "info",  v: "→  python3 --version 확인 후 python.org에서 Python 3.9+ 설치" },
          { t: "error", v: '"permission denied"' },
          { t: "info",  v: "→  Mac/Linux:  sudo pip install vibelign" },
          { t: "info",  v: "→  Windows:  관리자 권한으로 PowerShell 열기" },
          { t: "error", v: '"pip not found"' },
          { t: "info",  v: "→  Windows:  py -m pip install vibelign --no-warn-script-location" },
          { t: "info",  v: "→  Mac/Linux:  python3 -m pip install vibelign" },
          { t: "error", v: '"vib not found" (Windows)' },
          { t: "info",  v: "→  권장:  uv tool install vibelign  (vib 바로 사용)" },
          { t: "info",  v: "→  대안:  py -m vibelign [명령어]  (PATH 불필요)" },
          { t: "info",  v: "→  pip 설치 후 안 되면:  uv tool update-shell 후 터미널 재시작" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "history", icon: "🕓", color: "#7B4DFF",
    title: "히스토리",
    short: "체크포인트 저장 기록 전체 보기",
    desc: "지금까지 checkpoint로 저장한 기록을 전부 보여줘요. 언제 저장했는지, 어떤 메시지를 남겼는지 한눈에 확인할 수 있어요. 되돌리기 전에 먼저 이걸 보세요.",
    usage: "vib history",
    tips: ["저장이 제대로 됐는지 확인할 때 써요", "어떤 버전으로 되돌릴지 결정하기 전에 목록을 먼저 보세요", "되돌리려면 vib undo를 쓰세요"],
    guide: [
      {
        step: "기능", title: "체크포인트 저장 기록 조회",
        lines: [
          { t: "info",  v: "지금까지 저장한 기록을 전부 보여줘요." },
          { t: "info",  v: "시간은 '오늘 16:52' / '어제 09:00' 처럼 읽기 쉽게 나와요." },
          { t: "code",  v: "vib history" },
        ],
      },
      {
        step: "함께 쓰는 커맨드", title: "세트로 쓰면 좋아요",
        lines: [
          { t: "code", v: "vib history" },
          { t: "info", v: "목록 확인 후" },
          { t: "code", v: "vib undo" },
          { t: "info", v: "특정 시점으로 되돌리기" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "ask", icon: "🤖", color: "#F5621E",
    title: "애스크",
    short: "파일이 뭘 하는지 AI가 설명해줘요",
    desc: "코드 파일을 AI가 분석해서 쉬운 말로 설명해줘요. 코드를 모르는 사람도 이 파일이 뭘 하는 건지 알 수 있어요. API 키가 없으면 프롬프트 파일로 저장할 수 있어요.",
    usage: "vib ask 파일명",
    tips: ["vib ask main.py — main.py가 뭘 하는지 설명해줘요", "특정 질문도 붙일 수 있어요: vib ask login.py \"비밀번호 어디서 확인해?\"", "--write 붙이면 설명을 VIBELIGN_ASK.md 파일로 저장해요"],
    guide: [
      {
        step: "기능", title: "파일을 AI가 쉬운 말로 설명",
        lines: [
          { t: "info",  v: "코드를 모르는 사람도 이 파일이 뭘 하는 건지 알 수 있어요." },
          { t: "code",  v: "vib ask main.py" },
          { t: "info",  v: "main.py가 뭘 하는지 설명" },
          { t: "code",  v: 'vib ask login.py "비밀번호는 어디서 확인해?"' },
          { t: "info",  v: "특정 질문하기" },
        ],
      },
      {
        step: "API 키 없을 때", title: "API 키 없을 때",
        lines: [
          { t: "code", v: "vib ask app.py --write" },
          { t: "info", v: "프롬프트를 VIBELIGN_ASK.md로 저장해요." },
          { t: "info", v: "이 파일 내용을 Claude, ChatGPT 등에 붙여넣으면 돼요." },
          { t: "label", v: "API 키 설정" },
          { t: "code", v: "vib config" },
        ],
      },
    ] as GuideStep[],
    flags: [
      { type: "text" as const, key: "_file", label: "파일", placeholder: "main.py", required: true },
      { type: "text" as const, key: "_question", label: "질문", placeholder: "이거 뭐해?" },
      { type: "bool" as const, key: "write", label: "파일 저장" },
    ] as FlagDef[],
  },
  {
    name: "config", icon: "🔑", color: "#FFD166",
    title: "컨피그",
    short: "AI 기능용 API 키 설정",
    desc: "AI 기능(ask, patch --ai 등)을 쓰려면 API 키가 필요해요. Anthropic(Claude), Gemini, OpenAI 등의 키를 여기서 설정해요. Gemini는 무료로 시작할 수 있어요.",
    usage: "vib config",
    tips: ["Gemini API 키는 Google AI Studio에서 무료로 발급받을 수 있어요", "영구 저장 또는 현재 터미널 임시 저장 중 선택할 수 있어요", "설정 후 vib ask로 바로 AI 설명을 받을 수 있어요"],
    guide: [
      {
        step: "기능", title: "AI 기능용 API 키 설정",
        lines: [
          { t: "info",  v: "vib ask, vib explain --ai 등 AI 기능을 쓰려면 API 키가 필요해요." },
          { t: "code",  v: "vib config" },
          { t: "info",  v: "설정할 AI 서비스를 고르고 API 키를 입력하면 돼요." },
        ],
      },
      {
        step: "무료 시작", title: "무료로 시작하려면",
        lines: [
          { t: "info",  v: "Gemini API 키는 Google 계정만 있으면 무료로 발급받을 수 있어요." },
          { t: "label", v: "발급 방법" },
          { t: "info",  v: "Google AI Studio 접속 → API 키 생성" },
          { t: "code",  v: "vib config  →  3번 (Gemini) 선택" },
        ],
      },
      {
        step: "저장 방식", title: "영구 저장 vs 임시 저장",
        lines: [
          { t: "label", v: "영구 저장 (권장)" },
          { t: "info",  v: "~/.zshrc 또는 ~/.bashrc에 저장 → 새 터미널에서도 유지" },
          { t: "label", v: "임시 저장" },
          { t: "info",  v: "현재 터미널 세션에서만 유효 → 터미널 닫으면 사라져요" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "export", icon: "📤", color: "#4D9FFF",
    title: "익스포트",
    short: "AI 도구 연동 설정 파일 생성",
    desc: "Claude Code, Cursor, OpenCode 같은 AI 도구에서 VibeLign 규칙을 자동으로 적용할 수 있도록 설정 파일을 만들어줘요. 한 번만 실행하면 돼요.",
    usage: "vib export claude",
    tips: ["vib export claude — Claude Code용 CLAUDE.md 생성", "vib export cursor — Cursor용 .cursorrules 생성", "vib export opencode — OpenCode용 설정 생성"],
    guide: [
      {
        step: "기능", title: "AI 도구 연동 설정 파일 생성",
        lines: [
          { t: "info", v: "AI 도구에서 VibeLign 규칙을 자동으로 적용할 수 있도록 설정 파일을 만들어줘요." },
        ],
      },
      {
        step: "도구별 명령어", title: "지원 AI 도구",
        lines: [
          { t: "code", v: "vib export claude" },
          { t: "info", v: "CLAUDE.md 생성  →  Claude Code가 자동으로 읽어요" },
          { t: "code", v: "vib export opencode" },
          { t: "info", v: "OPENCODE.md 생성  →  OpenCode가 자동으로 읽어요" },
          { t: "code", v: "vib export cursor" },
          { t: "info", v: ".cursorrules 생성  →  Cursor가 자동으로 읽어요" },
          { t: "code", v: "vib export antigravity" },
          { t: "info", v: "작업 요청서, 체크리스트 생성" },
          { t: "code", v: "vib export codex" },
          { t: "info", v: "AGENTS.md 기반으로 Codex와 연동" },
        ],
      },
    ] as GuideStep[],
    flags: [
      { type: "select" as const, key: "_tool", label: "도구", required: true, options: [
        { v: "", l: "선택..." }, { v: "claude", l: "Claude" }, { v: "opencode", l: "OpenCode" },
        { v: "cursor", l: "Cursor" }, { v: "antigravity", l: "Antigravity" }, { v: "codex", l: "Codex" },
      ]},
    ] as FlagDef[],
  },
  {
    name: "manual", icon: "📖", color: "#FF4D8B",
    title: "매뉴얼",
    short: "커맨드 상세 메뉴얼 보기",
    desc: "커맨드 이름을 붙이면 해당 커맨드의 상세 설명, 옵션, 예시를 볼 수 있어요. 커맨드 이름 없이 실행하면 전체 목록이 나와요.",
    usage: "vib manual checkpoint",
    tips: ["vib manual만 치면 전체 커맨드 목록이 나와요", "vib manual checkpoint처럼 이름 붙이면 상세 설명이 나와요", "GUI 홈 화면의 메뉴얼 카드로도 볼 수 있어요"],
    guide: [
      {
        step: "기능", title: "커맨드 상세 메뉴얼 보기",
        lines: [
          { t: "info",  v: "커맨드 이름을 붙이면 해당 커맨드의 상세 설명, 옵션, 예시를 볼 수 있어요." },
          { t: "code",  v: "vib manual" },
          { t: "info",  v: "전체 커맨드 목록 보기" },
          { t: "code",  v: "vib manual checkpoint" },
          { t: "info",  v: "checkpoint 상세 설명" },
          { t: "code",  v: "vib manual transfer" },
          { t: "info",  v: "transfer 상세 설명" },
        ],
      },
      {
        step: "커맨드 목록", title: "자주 찾는 커맨드",
        lines: [
          { t: "info", v: "start  /  checkpoint  /  undo  /  history" },
          { t: "info", v: "doctor  /  guard  /  explain" },
          { t: "info", v: "anchor  /  scan  /  watch  /  patch" },
          { t: "info", v: "protect  /  secrets  /  ask  /  config" },
          { t: "info", v: "transfer  /  export  /  install  /  rules" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "rules", icon: "📋", color: "#FF6B35",
    title: "룰스",
    short: "AI 코딩 규칙 전체 보기",
    desc: "AI가 코드를 수정할 때 지켜야 할 규칙들을 보여줘요. 패치 우선 원칙, 앵커 규칙, 파일 구조, 함수 설계 등 AI가 어떻게 코딩해야 하는지 가이드예요.",
    usage: "vib manual rules",
    tips: ["vib start를 실행하면 AI_DEV_SYSTEM_SINGLE_FILE.md에 규칙이 저장돼요", "Claude, Cursor, OpenCode 등 어떤 AI든 이 규칙을 자동으로 읽어요", "요청에 '바이브라인으로'를 붙이면 안전 수정 모드로 동작해요"],
    guide: [
      {
        step: "핵심 원칙", title: "패치 우선 원칙",
        lines: [
          { t: "info", v: "AI는 파일 전체를 다시 쓰지 않아요." },
          { t: "info", v: "꼭 필요한 부분만 최소한으로 수정해요." },
          { t: "info", v: "관련 없는 파일은 절대 건드리지 않아요." },
        ],
      },
      {
        step: "수정 방식 1", title: "일반 수정 (기본)",
        subtitle: "평소처럼 말하면 AI가 알아서 수정해요",
        lines: [
          { t: "code", v: '"로그인 버튼 색 파란색으로 바꿔줘"' },
          { t: "info", v: "→ AI가 직접 수정해요. VibeLign 툴은 사용하지 않아요." },
        ],
      },
      {
        step: "수정 방식 2", title: "바이브라인 안전 수정",
        subtitle: "요청에 '바이브라인으로'를 붙이면 전체 안전 워크플로우 자동 실행",
        lines: [
          { t: "code", v: '"바이브라인으로 로그인 버튼 색 파란색으로 바꿔줘"' },
          { t: "info", v: "patch_get → 정확한 위치 확인 → 수정 → guard_check → checkpoint 저장" },
        ],
        warn: "'바이브라인으로' 없으면 → AI가 직접 수정 (VibeLign 안전 워크플로우 사용 안 함)",
      },
      {
        step: "파일 구조", title: "파일 구조 규칙",
        lines: [
          { t: "label", v: "🔹 진입 파일 보호 (main.py, index.js 등)" },
          { t: "info",  v: "진입 파일은 작게 유지해요. 실제 로직은 별도 파일로 분리해요." },
          { t: "label", v: "🔹 UI와 비즈니스 로직 분리" },
          { t: "info",  v: "UI 파일: 화면 레이아웃, 버튼, 입력창만" },
          { t: "info",  v: "로직 파일: 실제 처리, 파일 읽기/쓰기, 네트워크" },
          { t: "label", v: "🔹 파일 크기 관리" },
          { t: "info",  v: "파일이 커지면 역할별로 나눠요." },
          { t: "label", v: "🔹 기능 분리 원칙" },
          { t: "info",  v: "새 기능은 기본적으로 새 파일/모듈/컴포넌트로 만들어요." },
          { t: "info",  v: "파일에 두 번째 역할이 생기면, 새 로직은 밖으로 빼고 기존 파일은 연결만 담당해요." },
          { t: "error", v: "금지:  utils.py  helpers.py  misc.py  (모호한 이름)" },
          { t: "info",  v: "권장:  backup_worker.py  translation_pipeline.py  (구체적으로)" },
        ],
      },
      {
        step: "함수 설계", title: "함수 설계 규칙",
        lines: [
          { t: "label", v: "🔹 함수 길이" },
          { t: "info",  v: "40줄 넘으면 → 분리 고려  /  80줄 넘으면 → 반드시 분리" },
          { t: "info",  v: "한 함수는 딱 한 가지 일만 해요." },
          { t: "label", v: "🔹 함수 이름" },
          { t: "info",  v: "✓  load_config()  /  parse_excel_row()  /  validate_input_path()" },
          { t: "error", v: "✗  do_stuff()  /  process()  /  handle()  /  run_all()" },
          { t: "label", v: "🔹 파일 간 연결" },
          { t: "error", v: "순환 import 금지  (A가 B를 부르고 B가 다시 A를 부르는 구조)" },
          { t: "info",  v: "공통 로직은 별도 파일로 분리해서 양쪽에서 가져다 써요." },
        ],
      },
      {
        step: "유지보수", title: "유지보수 규칙",
        lines: [
          { t: "label", v: "🔹 매직 넘버 금지" },
          { t: "error", v: "나쁜 예:  if retry > 3" },
          { t: "info",  v: "좋은 예:  MAX_RETRY = 3  →  if retry > MAX_RETRY" },
          { t: "label", v: "🔹 에러 메시지는 사람이 읽을 수 있게" },
          { t: "error", v: "나쁜 예:  raise Exception('NoneType')" },
          { t: "info",  v: "좋은 예:  raise Exception('파일을 찾을 수 없어요. 경로를 확인하세요')" },
          { t: "label", v: "🔹 조용한 실패 금지" },
          { t: "error", v: "except: pass  절대 금지 — 에러가 나면 반드시 화면에 표시해요." },
          { t: "label", v: "🔹 죽은 코드 제거" },
          { t: "info",  v: "주석 처리된 코드 덩어리, 쓰지 않는 import·변수·함수 삭제해요." },
          { t: "label", v: "🔹 의존성 동기화" },
          { t: "info",  v: "새 패키지를 추가하면 pyproject.toml도 함께 업데이트해요." },
          { t: "label", v: "🔹 주석도 함께 업데이트" },
          { t: "info",  v: "코드를 바꾸면 위에 있는 설명 주석도 같이 바꿔요." },
          { t: "info",  v: "오래된 주석은 없는 것보다 더 혼란스러워요." },
        ],
      },
      {
        step: "앵커 규칙", title: "앵커(ANCHOR) 규칙",
        lines: [
          { t: "label", v: "🔹 앵커가 있으면 그 안에서만 수정" },
          { t: "info",  v: "앵커를 무시하고 파일 전체를 바꾸면 안 돼요." },
          { t: "info",  v: "앵커가 없는 큰 파일은 먼저 앵커를 달고 작업해요." },
          { t: "label", v: "🔹 앵커를 허락 없이 지우면 안 돼요" },
          { t: "code",  v: "// === ANCHOR: NAME_START ===" },
          { t: "code",  v: "// === ANCHOR: NAME_END ===" },
          { t: "label", v: "🔹 앵커 달기 / 확인" },
          { t: "code",  v: "vib anchor --auto" },
          { t: "code",  v: "vib anchor --validate" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "policy", icon: "🧭", color: "#4D9FFF",
    title: "정책",
    short: "AI가 지켜야 할 핵심 신뢰 규칙",
    desc: "VibeLign이 AI를 어떻게 제한하고 안전하게 쓰게 하는지, `AI_DEV_SYSTEM_SINGLE_FILE.md`의 핵심 정책을 중학생도 읽을 수 있게 정리한 카드예요.",
    usage: "vib manual rules",
    tips: ["AI가 한 파일에 몰빵하지 못하게 막아요", "작게 고치고, 관계없는 건 건드리지 않아요", "정책이 바뀌면 문서와 테스트도 같이 맞춰요"],
    guide: [
      {
        step: "핵심 원칙", title: "AI는 빠르지만, 안전이 먼저예요",
        lines: [
          { t: "info", v: "가장 중요한 규칙은: 가장 작고 안전한 패치만 적용하기예요." },
          { t: "info", v: "AI는 요청을 intent / source / destination / behavior_constraint로 쪼개서 이해해요." },
          { t: "info", v: "수정은 한 파일, 한 앵커처럼 좁게 시작해요." },
          { t: "info", v: "target_file과 target_anchor 밖은 건드리지 않아요." },
          { t: "info", v: "관련 없는 파일이나 모듈은 절대 같이 건드리지 않아요." },
        ],
      },
      {
        step: "패치 우선", title: "말보다 패치가 먼저예요",
        lines: [
          { t: "info", v: "파일 전체를 다시 쓰지 않고, 필요한 부분만 조금 고쳐요." },
          { t: "info", v: "한 번에 이것저것 많이 바꾸지 않고, 한 가지 작업만 집중해요." },
          { t: "info", v: "불필요한 정리나 이름 바꾸기는 요청받았을 때만 해요." },
          { t: "info", v: "파일을 옮기거나 지우는 일도 꼭 필요할 때만 해요." },
        ],
      },
      {
        step: "요청 해석", title: "요청은 먼저 안전한 말로 나눠요",
        lines: [
          { t: "label", v: "분해 단위" },
          { t: "info", v: "intent / source / destination / behavior_constraint 로 나눠서 봐요." },
          { t: "label", v: "move + delete" },
          { t: "info", v: "명시적 삭제가 아니면 이동 + 보존으로 처리해요." },
          { t: "label", v: "source / destination" },
          { t: "info", v: "같은 규칙을 쓰지 않고 역할에 맞게 따로 판단해요." },
        ],
      },
      {
        step: "수정 방식", title: "일반 수정과 안전 수정은 달라요",
        lines: [
          { t: "code", v: '"로그인 버튼 색 파란색으로 바꿔줘"' },
          { t: "info", v: "→ 일반 수정: AI가 직접 처리해요." },
          { t: "code", v: '"바이브라인으로 로그인 버튼 색 파란색으로 바꿔줘"' },
          { t: "info", v: "→ 안전 수정: patch_get → guard_check → checkpoint_create 흐름으로 처리해요." },
        ],
      },
      {
        step: "파일 구조", title: "큰 파일과 애매한 이름을 막아요",
        lines: [
          { t: "label", v: "진입 파일" },
          { t: "info", v: "main.py, index.js 같은 시작 파일은 작게 유지해요." },
          { t: "label", v: "역할 분리" },
          { t: "info", v: "UI와 비즈니스 로직은 분리해요." },
          { t: "label", v: "기능 분리" },
          { t: "info", v: "새 기능은 새 파일/모듈/컴포넌트로 만들고, 역할이 2개가 되면 새 로직은 밖으로 빼요." },
          { t: "error", v: "금지: utils.py / helpers.py / misc.py 같은 모호한 이름" },
          { t: "info", v: "권장: backup_worker.py / translation_pipeline.py 같은 구체적인 이름" },
        ],
      },
      {
        step: "함수 설계", title: "한 함수는 한 가지 일만 해요",
        lines: [
          { t: "info", v: "40줄이 넘으면 분리 고려, 80줄이 넘으면 반드시 분리해요." },
          { t: "info", v: "load_config(), parse_excel_row(), validate_input_path()처럼 이름이 설명적이어야 해요." },
          { t: "error", v: "do_stuff(), process(), handle(), run_all() 같은 이름은 피하세요." },
          { t: "error", v: "순환 import는 금지예요." },
        ],
      },
      {
        step: "유지보수", title: "바꾸면 같이 바꿔야 하는 것들이 있어요",
        lines: [
          { t: "error", v: "매직 넘버 금지 — 상수로 이름을 붙여요." },
          { t: "info", v: "에러 메시지는 사람이 읽을 수 있게 써요." },
          { t: "error", v: "except: pass 같은 조용한 실패는 안 돼요." },
          { t: "info", v: "죽은 코드, 오래된 주석, 쓰지 않는 import는 같이 정리해요." },
          { t: "info", v: "새 패키지를 추가하면 pyproject.toml도 함께 업데이트해요." },
          { t: "info", v: "코드가 바뀌면 주석도 같이 바꿔요." },
        ],
      },
      {
        step: "검증 / 보호", title: "수정 뒤엔 꼭 확인하고 저장해요",
        lines: [
          { t: "info", v: "AI 작업 전에 checkpoint로 저장해요." },
          { t: "info", v: "수정 후에는 guard로 이상 여부를 확인해요." },
          { t: "info", v: "protect 된 파일과 .env 같은 중요한 파일은 우회해서 건드리면 안 돼요." },
          { t: "info", v: "기능이 바뀌면 관련 테스트와 문서도 같이 바꿔요." },
          { t: "info", v: "뭔가 바뀌면 왜 바뀌었는지 설명할 수 있어야 해요." },
        ],
      },
      {
        step: "비개발자 배려", title: "코드 몰라도 이해되게 만들어요",
        lines: [
          { t: "info", v: "구조는 예측 가능해야 해요." },
          { t: "info", v: "숨은 부작용은 줄여요." },
          { t: "info", v: "말로 설명하기 쉬운 코드를 좋아해요." },
          { t: "info", v: "원래 잘 되던 흐름은 되도록 유지해요." },
        ],
      },
      {
        step: "추천 작업 순서", title: "이 순서대로 하면 안전해요",
        lines: [
          { t: "code", v: "vib doctor --strict" },
          { t: "code", v: "vib anchor" },
          { t: "code", v: 'vib patch "your request here"' },
          { t: "code", v: "vib explain --write-report" },
          { t: "code", v: "vib guard --strict --write-report" },
        ],
      },
      {
        step: "도구별 참고", title: "어떤 AI를 쓰는지도 같이 봐요",
        lines: [
          { t: "info", v: "OpenCode, Claude Code, Cursor, Antigravity마다 참고 문서가 달라요." },
          { t: "info", v: "도구별로 export 문서와 setup 문서를 같이 읽어야 해요." },
          { t: "info", v: "환경에 맞는 규칙 파일도 같이 써요." },
        ],
      },
      {
        step: "기본 지시문", title: "AI에게 이렇게 부탁하면 돼요",
        lines: [
          { t: "code", v: "Follow AI_DEV_SYSTEM_SINGLE_FILE.md." },
          { t: "info", v: "Task / Target file / Target anchor / Constraints / Goal 을 적어요." },
          { t: "info", v: "패치만 하라고, 관계없는 파일은 건드리지 말라고 적어요." },
        ],
      },
      {
        step: "마지막 원칙", title: "빠른 것보다 안전한 게 더 좋아요",
        lines: [
          { t: "info", v: "AI가 빨리 고치는 것도 좋지만, 안전하게 고치는 게 더 중요해요." },
          { t: "info", v: "속도와 구조가 싸우면 구조를 먼저 지켜요." },
        ],
      },
    ] as GuideStep[],
  },
];
// === ANCHOR: COMMAND_DATA2_END ===
