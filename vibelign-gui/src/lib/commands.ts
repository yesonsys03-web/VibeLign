// === ANCHOR: COMMANDS_START ===
export type CardState = "idle" | "loading" | "done" | "error";

export type FlagDef =
  | { type: "bool"; key: string; label: string }
  | { type: "text"; key: string; label: string; placeholder?: string; required?: boolean; numeric?: boolean }
  | { type: "select"; key: string; label: string; required?: boolean; options: { v: string; l: string }[] };

export type GuideLine = { t: "info" | "code" | "label" | "error" | "warn"; v: string };
export type GuideStep = { step: string; title: string; subtitle?: string; optional?: boolean; warn?: string; lines: GuideLine[] };

export const COMMANDS = [
  {
    name: "start", icon: "▶", color: "#F5621E",
    title: "시작하기",
    short: "처음 딱 한 번 실행하면 끝",
    desc: "새 프로젝트 폴더에서 처음 실행하는 커맨드예요. VibeLign이 필요한 파일을 자동으로 만들어줘요. 게임으로 치면 '새 게임 시작' 버튼이에요.",
    usage: "vib start",
    tips: ["프로젝트 폴더에서 딱 한 번만 실행해요", "AGENTS.md, .vibelign 폴더가 자동으로 생겨요", "AI한테 이 폴더 구조를 알려주는 파일도 만들어줘요"],
    guide: [
      {
        step: "기능", title: "프로젝트 처음 세팅",
        lines: [
          { t: "info",  v: "프로젝트 폴더에서 딱 한 번만 실행하면 돼요." },
          { t: "label", v: "자동으로 만들어지는 것들" },
          { t: "info",  v: "AGENTS.md  —  AI 규칙 파일 (어떤 AI든 자동으로 읽어요)" },
          { t: "info",  v: "AI_DEV_SYSTEM_SINGLE_FILE.md  —  상세 코딩 가이드" },
          { t: "info",  v: ".vibelign/  —  체크포인트, 코드맵 저장 폴더" },
        ],
      },
      {
        step: "주요 옵션", title: "자주 쓰는 옵션",
        lines: [
          { t: "code", v: "vib start" },
          { t: "info", v: "기본 세팅 (가장 많이 씀)" },
          { t: "code", v: "vib start --all-tools" },
          { t: "info", v: "Claude, Antigravity, OpenCode, Cursor, Codex 한 번에 준비" },
          { t: "code", v: "vib start --quickstart" },
          { t: "info", v: "세팅 + 앵커 자동 삽입까지 한 번에" },
          { t: "code", v: "vib start --force" },
          { t: "info", v: "기존 VibeLign 설정도 다시 생성" },
        ],
      },
      {
        step: "참고", title: "AI 도구별 준비 상태",
        lines: [
          { t: "info",  v: "✓  Claude, Antigravity, OpenCode  →  바로 사용 가능" },
          { t: "info",  v: "⚠  Cursor, Codex  →  설정 화면에서 한 번 더 확인 필요" },
          { t: "label", v: "Git 저장소라면" },
          { t: "info",  v: "커밋 전 비밀정보 자동 검사(vib secrets)도 같이 켜줘요" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "checkpoint", icon: "💾", color: "#7B4DFF",
    title: "체크포인트",
    short: "지금 상태를 저장 — 게임 세이브",
    desc: "지금 코드 상태를 저장해요. AI가 코드를 망가뜨리기 전에 미리 저장해두면, 나중에 그 시점으로 되돌릴 수 있어요. 마치 게임에서 중간 저장하는 것처럼요.",
    usage: "vib checkpoint \"기능 추가 전\"",
    tips: ["AI한테 뭔가 시키기 전에 꼭 저장하세요", "설명을 짧게 써두면 나중에 찾기 쉬워요", "여러 번 저장해도 괜찮아요"],
    guide: [
      {
        step: "기능", title: "게임 세이브처럼 저장해요",
        lines: [
          { t: "info",  v: "AI 작업 전에 꼭 저장하세요. 나중에 이 시점으로 되돌릴 수 있어요." },
          { t: "info",  v: "저장 시 PROJECT_CONTEXT.md도 자동으로 갱신돼요." },
          { t: "label", v: "메시지 없이 실행" },
          { t: "code",  v: "vib checkpoint" },
          { t: "info",  v: "→ 메시지 입력 화면이 나와요. 엔터만 누르면 메시지 없이 저장." },
          { t: "label", v: "메시지 바로 지정" },
          { t: "code",  v: 'vib checkpoint "로그인 완성"' },
          { t: "code",  v: 'vib checkpoint "버그 수정 전"' },
        ],
      },
      {
        step: "워크플로우", title: "AI 작업과 함께 쓰는 법",
        lines: [
          { t: "code", v: 'vib checkpoint "작업 전"' },
          { t: "info", v: "↓  AI 작업 수행" },
          { t: "code", v: "vib guard" },
          { t: "info", v: "→ 괜찮으면:    vib checkpoint \"완료\"" },
          { t: "info", v: "→ 문제 있으면: vib undo" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "undo", icon: "↩", color: "#FF4D4D",
    title: "되돌리기",
    short: "저장했던 그 시점으로 되돌아가기",
    desc: "체크포인트로 저장했던 상태로 코드를 되돌려요. AI가 코드를 이상하게 바꿔놨을 때 '그냥 없던 일로 해줘!' 할 때 쓰는 커맨드예요.",
    usage: "vib undo",
    tips: ["실행하면 어느 시점으로 돌아갈지 고를 수 있어요", "저장 안 하고 undo하면 못 돌아가니까 checkpoint 먼저!"],
    guide: [
      {
        step: "어떻게 작동해요?", title: "저장 목록에서 선택해요",
        lines: [
          { t: "info",  v: "실행하면 저장된 목록이 번호와 함께 나와요:" },
          { t: "label", v: "목록 예시" },
          { t: "info",  v: "[1] 오늘 16:52  로그인 기능 추가 전  ← 가장 최근" },
          { t: "info",  v: "[2] 오늘 14:30  시작" },
          { t: "info",  v: "[0] 취소" },
          { t: "label", v: "입력 방법" },
          { t: "info",  v: "번호 입력  →  그 시점으로 되돌아가요" },
          { t: "info",  v: "엔터만 누르면  →  가장 최근 저장으로 되돌아가요" },
          { t: "info",  v: "0 또는 q  →  취소" },
        ],
        warn: "checkpoint로 저장해뒀어야 쓸 수 있어요. 저장 안 하면 되돌릴 수 없어요.",
      },
    ] as GuideStep[],
  },
  {
    name: "doctor", icon: "🩺", color: "#FF4D8B",
    title: "닥터",
    short: "프로젝트 건강 검진",
    desc: "프로젝트 상태가 괜찮은지 검사해줘요. 점수(0~100)랑 어떤 문제가 있는지 알려줘요. 병원 건강검진처럼 '지금 코드 상태가 어때요?'를 확인하는 거예요.",
    usage: "vib doctor",
    tips: ["점수가 낮으면 뭘 고쳐야 하는지 알려줘요", "--strict 붙이면 더 꼼꼼하게 검사해요", "GUI에서 Doctor 탭으로도 볼 수 있어요"],
    guide: [
      {
        step: "기능", title: "프로젝트 건강 점검",
        lines: [
          { t: "info",  v: "점수(0~100)와 문제 목록을 보여줘요." },
          { t: "info",  v: "AI 작업 전에 실행해서 준비됐는지 확인하세요." },
          { t: "label", v: "결과 예시" },
          { t: "info",  v: "점수: 85/100  —  앵커 없는 파일 2개 발견" },
        ],
      },
      {
        step: "주요 옵션", title: "자주 쓰는 옵션",
        lines: [
          { t: "code", v: "vib doctor" },
          { t: "info", v: "기본 점검 (점수 + 문제 목록)" },
          { t: "code", v: "vib doctor --strict" },
          { t: "info", v: "더 꼼꼼하게 검사 — 작은 문제도 잡아줘요" },
          { t: "code", v: "vib doctor --fix" },
          { t: "info", v: "앵커 없는 파일에 자동으로 앵커 추가" },
          { t: "code", v: "vib doctor --write-report" },
          { t: "info", v: "점검 결과를 파일로 저장" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "guard", icon: "🛡", color: "#FF6B35",
    title: "가드",
    short: "AI가 코드 망가뜨렸는지 검사",
    desc: "AI가 코드를 수정한 후에 이상한 짓을 했는지 체크해요. pass(괜찮음), warn(조심), fail(위험) 중 하나로 알려줘요. 경호원처럼 코드를 지켜주는 거예요.",
    usage: "vib guard",
    tips: ["AI 작업 끝나고 꼭 실행해보세요", "--strict 붙이면 경고도 실패로 처리해요"],
    guide: [
      {
        step: "기능", title: "AI 작업 후 종합 검사",
        lines: [
          { t: "info",  v: "doctor(건강 점검) + explain(변경 설명)을 합친 종합 검사예요." },
          { t: "info",  v: "AI가 코드를 수정한 후 항상 실행하세요." },
          { t: "label", v: "결과 3가지" },
          { t: "info",  v: "pass  —  이상 없어요 ✓" },
          { t: "info",  v: "warn  —  주의할 점이 있어요 ⚠" },
          { t: "info",  v: "fail  —  위험한 변경 감지 ✗" },
        ],
      },
      {
        step: "주요 옵션", title: "자주 쓰는 옵션",
        lines: [
          { t: "code", v: "vib guard" },
          { t: "info", v: "기본 검사" },
          { t: "code", v: "vib guard --strict" },
          { t: "info", v: "더 꼼꼼하게 — 경고도 실패로 처리해요" },
          { t: "code", v: "vib guard --write-report" },
          { t: "info", v: "결과를 파일로 저장" },
          { t: "code", v: "vib guard --since-minutes 60" },
          { t: "info", v: "최근 60분 변경만 확인" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "anchor", icon: "⚓", color: "#4D9FFF",
    title: "앵커",
    short: "AI가 건드려도 되는 구역 표시",
    desc: "코드 파일에 'AI야, 여기 건드려도 돼!' 표시를 자동으로 달아줘요. 앵커가 있어야 AI가 정확한 위치를 찾아서 수정할 수 있어요. 지도의 위치 핀 같은 거예요.",
    usage: "vib anchor",
    tips: ["새 파일 만들면 꼭 실행해주세요", "파일 맨 위/아래에 주석 형태로 달려요", "AI한테 '앵커 범위 안에서만 수정해줘' 라고 하면 돼요"],
    guide: [
      {
        step: "앵커란?", title: "코드 위치 표식",
        lines: [
          { t: "info",  v: "파일에 '여기서부터 여기까지가 이 기능이야'라는 표식이에요." },
          { t: "info",  v: "AI가 수정할 때 정확한 위치를 찾을 수 있어요." },
          { t: "label", v: "파일에 이렇게 달려요" },
          { t: "code",  v: "// === ANCHOR: FUNCTION_NAME_START ===" },
          { t: "code",  v: "// === ANCHOR: FUNCTION_NAME_END ===" },
        ],
      },
      {
        step: "주요 옵션", title: "자주 쓰는 옵션",
        lines: [
          { t: "code", v: "vib anchor --auto" },
          { t: "info", v: "모든 파일에 자동으로 앵커 달기 (처음 설정 시 추천)" },
          { t: "code", v: "vib anchor --validate" },
          { t: "info", v: "앵커가 제대로 달려있는지 검사" },
          { t: "code", v: "vib anchor --dry-run" },
          { t: "info", v: "실제로 바꾸지 않고 어떻게 바뀔지 미리 보기" },
          { t: "code", v: "vib anchor --only-ext .py" },
          { t: "info", v: "특정 확장자 파일만 처리" },
        ],
      },
    ] as GuideStep[],
    flags: [
      { type: "select" as const, key: "_mode", label: "모드", options: [
        { v: "", l: "기본" },
        { v: "--suggest", l: "추천" },
        { v: "--suggest --dry-run", l: "추천 미리보기" },
        { v: "--auto --dry-run", l: "자동 미리보기" },
        { v: "--auto --json", l: "자동 삽입" },
        { v: "--validate", l: "검증" },
      ]},
    ] as FlagDef[],
  },
  {
    name: "scan", icon: "🔍", color: "#F5621E",
    title: "스캔",
    short: "코드맵 갱신 — 구조 다시 분석",
    desc: "프로젝트 전체를 훑어서 코드맵을 새로 만들어요. 파일을 많이 바꿨거나 AI한테 새 파일을 알려주고 싶을 때 써요. 마치 내비게이션 지도를 업데이트하는 거예요.",
    usage: "vib scan",
    tips: ["파일 많이 바꾼 뒤에 실행하면 좋아요", "AI한테 project_map.json을 주면 전체 구조를 한 번에 파악해요"],
    guide: [
      {
        step: "기능", title: "앵커 + 코드맵 한 번에 갱신",
        lines: [
          { t: "info", v: "앵커 검사, 앵커 인덱스 갱신, 코드맵 재생성을 한 번에 실행해요." },
          { t: "info", v: "파일을 많이 추가/삭제했거나 뭔가 꼬인 것 같을 때 실행하세요." },
        ],
      },
      {
        step: "옵션", title: "주요 옵션",
        lines: [
          { t: "code", v: "vib scan" },
          { t: "info", v: "앵커 스캔 + 코드맵 갱신" },
          { t: "code", v: "vib scan --auto" },
          { t: "info", v: "문제 있는 앵커 자동 수정 + 코드맵 갱신" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "watch", icon: "👁", color: "#4DFF91",
    title: "워치",
    short: "실시간 자동 감시 모드",
    desc: "파일이 바뀔 때마다 자동으로 코드맵을 갱신해줘요. 켜두고 AI 작업하면 항상 최신 상태가 유지돼요. 자동으로 돌아가는 CCTV 같은 거예요.",
    usage: "vib watch",
    tips: ["AI 작업 중에 켜두면 편해요", "Ctrl+C로 끌 수 있어요", "GUI 홈 화면에서 버튼으로도 켤 수 있어요"],
    guide: [
      {
        step: "기능", title: "파일 변경 자동 감지",
        lines: [
          { t: "info", v: "파일이 저장될 때마다 자동으로 코드맵을 최신 상태로 유지해요." },
          { t: "info", v: "AI가 작업하는 동안 켜두면 항상 최신 정보로 작업해요." },
          { t: "info", v: "종료: Ctrl+C  /  GUI 홈 화면에서 버튼으로도 켤 수 있어요." },
        ],
      },
      {
        step: "옵션", title: "주요 옵션",
        lines: [
          { t: "code", v: "vib watch" },
          { t: "info", v: "실시간 감시 시작 (Ctrl+C로 종료)" },
          { t: "code", v: "vib watch --strict" },
          { t: "info", v: "더 꼼꼼한 감시 모드" },
          { t: "code", v: "vib watch --debounce-ms 1500" },
          { t: "info", v: "파일 변경 후 1.5초 대기 후 처리 (기본 800ms)" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "transfer", icon: "📤", color: "#4D9FFF",
    title: "트랜스퍼",
    short: "다른 AI 툴로 이사갈 때",
    desc: "Claude에서 Cursor로, 또는 다른 AI 툴로 바꿀 때 '지금까지 뭘 했는지' 요약 파일을 만들어줘요. 새 AI한테 이 파일을 주면 처음부터 설명 안 해도 돼요.",
    usage: "vib transfer",
    tips: ["AI 툴 바꾸기 직전에 실행해요", "만들어진 PROJECT_CONTEXT.md를 새 AI에게 주세요"],
    guide: [
      {
        step: "기능", title: "AI 전환용 맥락 파일 생성",
        lines: [
          { t: "info",  v: "AI 툴을 바꾸거나 새 채팅을 열 때 지금까지 뭘 했는지 요약 파일을 만들어요." },
          { t: "info",  v: "만들어지는 파일: PROJECT_CONTEXT.md" },
          { t: "info",  v: "새 AI에게 이 파일을 주면 처음부터 설명 안 해도 돼요." },
        ],
      },
      {
        step: "--handoff", title: "AI 전환 인수인계 블록",
        lines: [
          { t: "code", v: "vib transfer --handoff" },
          { t: "info", v: "파일 맨 위에 'Session Handoff' 블록 추가" },
          { t: "info", v: "오늘 뭘 했는지, 다음에 뭘 해야 하는지 한 줄로 담아줘요" },
          { t: "code", v: "vib transfer --handoff --print" },
          { t: "info", v: "내용을 파일 저장 + 화면에도 출력 (새 채팅에 복붙하기 편해요)" },
          { t: "code", v: "vib transfer --handoff --dry-run" },
          { t: "info", v: "저장 없이 내용 미리 보기" },
        ],
      },
      {
        step: "기타 옵션", title: "자주 쓰는 옵션",
        lines: [
          { t: "code", v: "vib transfer --compact" },
          { t: "info", v: "가벼운 버전 (토큰 절약 — 무료 플랜에 좋아요)" },
          { t: "code", v: "vib transfer --full" },
          { t: "info", v: "파일 트리를 더 깊이 포함" },
          { t: "code", v: "vib transfer --out ctx.md" },
          { t: "info", v: "저장 파일 이름 바꾸기" },
        ],
      },
    ] as GuideStep[],
  },
  {
    name: "patch", icon: "🔧", color: "#FFD166",
    title: "패치",
    short: "말로 수정 요청 → 안전한 계획 생성",
    desc: "수정하고 싶은 걸 말로 설명하면, 어느 파일 어느 부분을 바꿔야 하는지 계획을 세워줘요. 직접 코드를 바꾸는 게 아니라 '여기 바꾸세요' 지시서를 만들어주는 거예요.",
    usage: "vib patch \"로그인 버튼 색깔 바꿔줘\"",
    tips: ["코드 수정 전에 뭘 바꿔야 하는지 확인할 수 있어요", "AI한테 그대로 전달하면 돼요"],
    guide: [
      {
        step: "기능", title: "말로 요청 → 수정 계획 생성",
        lines: [
          { t: "info",  v: "'로그인 버튼 추가해줘' 같이 말로 요청하면," },
          { t: "info",  v: "어떤 파일의 어느 부분을 수정할지 계획을 만들어줘요." },
          { t: "info",  v: "이 계획을 AI에게 붙여넣으면 정확하게 수정할 수 있어요." },
          { t: "code",  v: 'vib patch "로그인 버튼 추가"' },
        ],
      },
      {
        step: "주요 옵션", title: "자주 쓰는 옵션",
        lines: [
          { t: "code", v: 'vib patch "요청" --ai' },
          { t: "info", v: "AI가 코드를 더 자세히 분석해서 정확한 계획 생성 (API 키 필요)" },
          { t: "code", v: 'vib patch "요청" --copy' },
          { t: "info", v: "결과를 클립보드에 복사 → AI에 바로 붙여넣기" },
          { t: "code", v: 'vib patch "요청" --preview' },
          { t: "info", v: "수정 계획 미리 보기" },
          { t: "code", v: 'vib patch "요청" --write-report' },
          { t: "info", v: "결과를 파일로 저장" },
        ],
      },
    ] as GuideStep[],
    flags: [
      { type: "text" as const, key: "_request", label: "요청", placeholder: "로그인 버튼 추가...", required: true },
      { type: "bool" as const, key: "ai", label: "--ai" },
      { type: "bool" as const, key: "preview", label: "--preview" },
      { type: "bool" as const, key: "copy", label: "--copy" },
      { type: "bool" as const, key: "write-report", label: "--write-report" },
    ] as FlagDef[],
  },
  {
    name: "protect", icon: "🔒", color: "#FF4D4D",
    title: "프로텍트",
    short: "중요 파일 잠금 — AI 접근 금지",
    desc: "절대 건드리면 안 되는 파일을 잠가요. 잠긴 파일은 guard 검사에서 위반 사항으로 잡혀요. 소중한 파일에 자물쇠 채우는 거예요.",
    usage: "vib protect 파일경로",
    tips: ["설정 파일, 비밀 키 파일 등을 잠가두세요", "vib guard 실행할 때 잠긴 파일 건드리면 경고해줘요"],
    guide: [
      {
        step: "기능", title: "파일 보호 (잠금)",
        lines: [
          { t: "info",  v: "절대 바뀌면 안 되는 파일을 잠가요." },
          { t: "info",  v: "guard 실행 시 잠긴 파일이 수정됐으면 경고해줘요." },
          { t: "code",  v: "vib protect .env" },
          { t: "code",  v: "vib protect settings.py" },
        ],
      },
      {
        step: "관리", title: "보호 목록 관리",
        lines: [
          { t: "code", v: "vib protect --list" },
          { t: "info", v: "현재 보호된 파일 목록 보기" },
          { t: "code", v: "vib protect main.py --remove" },
          { t: "info", v: "보호 해제" },
        ],
      },
    ] as GuideStep[],
    flags: [
      { type: "text" as const, key: "_file", label: "파일", placeholder: ".env" },
      { type: "select" as const, key: "_action", label: "", options: [
        { v: "", l: "보호" }, { v: "--list", l: "목록" }, { v: "--remove", l: "해제" },
      ]},
    ] as FlagDef[],
  },
  {
    name: "secrets", icon: "🔑", color: "#FFE44D",
    title: "시크릿",
    short: "API 키가 실수로 올라가는 거 막기",
    desc: "API 키, 비밀번호 같은 걸 실수로 GitHub에 올리는 걸 막아줘요. 커밋하기 전에 자동으로 체크해서 '위험한 내용 발견!' 하고 알려줘요.",
    usage: "vib secrets",
    tips: ["git commit 전에 자동으로 실행되게 설정할 수 있어요", "비밀 정보가 발견되면 커밋을 막아줘요"],
    guide: [
      {
        step: "기능", title: "비밀정보 커밋 방지",
        lines: [
          { t: "info",  v: "API 키, 토큰, .env 같은 걸 실수로 GitHub에 올리는 걸 막아줘요." },
          { t: "info",  v: "vib start를 하면 자동으로 연결돼요. 따로 신경 쓸 일이 거의 없어요." },
          { t: "label", v: "직접 확인하고 싶을 때" },
          { t: "code",  v: "vib secrets --staged" },
          { t: "info",  v: "지금 커밋하려는 내용에 비밀정보가 있는지 검사" },
        ],
      },
      {
        step: "자동 검사", title: "커밋 시 자동 검사 설정",
        lines: [
          { t: "code", v: "vib secrets --install-hook" },
          { t: "info", v: "커밋할 때마다 자동 검사 켜기 (vib start가 자동으로 해줘요)" },
          { t: "code", v: "vib secrets --uninstall-hook" },
          { t: "info", v: "자동 검사 끄기" },
          { t: "label", v: "오탐이 나면" },
          { t: "info",  v: "해당 줄 끝에 추가:  # vibelign: allow-secret" },
        ],
      },
    ] as GuideStep[],
    flags: [
      { type: "select" as const, key: "_mode", label: "모드", options: [
        { v: "--staged", l: "staged 검사" }, { v: "--install-hook", l: "훅 설치" }, { v: "--uninstall-hook", l: "훅 제거" },
      ]},
    ] as FlagDef[],
  },
  {
    name: "explain", icon: "💬", color: "#7B4DFF",
    title: "익스플레인",
    short: "뭐가 바뀌었는지 쉽게 설명",
    desc: "최근에 바뀐 파일들을 분석해서 '이게 바뀌었어요'를 알기 쉽게 설명해줘요. AI가 뭘 했는지 한눈에 파악하고 싶을 때 써요.",
    usage: "vib explain",
    tips: ["AI 작업 후에 실행하면 뭐가 바뀌었는지 바로 알 수 있어요", "--since-minutes 30 하면 30분 이내 변경사항만 봐요"],
    guide: [
      {
        step: "기능", title: "변경 내용 쉬운 말로 설명",
        lines: [
          { t: "info",  v: "최근에 코드가 어떻게 바뀌었는지 쉬운 말로 알려줘요." },
          { t: "info",  v: "AI가 수정한 내용이 뭔지 이해하기 어려울 때 쓰세요." },
          { t: "code",  v: "vib explain" },
          { t: "info",  v: "전체 변경 설명 (기본 2시간 이내)" },
          { t: "code",  v: "vib explain main.py" },
          { t: "info",  v: "특정 파일만 설명" },
        ],
      },
      {
        step: "주요 옵션", title: "자주 쓰는 옵션",
        lines: [
          { t: "code", v: "vib explain --ai" },
          { t: "info", v: "AI가 더 자세하게 분석해서 설명 (API 키 필요)" },
          { t: "code", v: "vib explain --since-minutes 30" },
          { t: "info", v: "최근 30분 변경만 보기" },
          { t: "code", v: "vib explain --write-report" },
          { t: "info", v: "설명을 파일로 저장" },
        ],
      },
    ] as GuideStep[],
    flags: [
      { type: "text" as const, key: "_file", label: "파일", placeholder: "main.py" },
      { type: "bool" as const, key: "ai", label: "--ai" },
      { type: "text" as const, key: "since-minutes", label: "분", placeholder: "120", numeric: true },
      { type: "bool" as const, key: "write-report", label: "--write-report" },
      { type: "bool" as const, key: "json", label: "--json" },
    ] as FlagDef[],
  },
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
          { t: "info",  v: "주석 처리된 코드 덩어리, �지 않는 import·변수·함수 삭제해요." },
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

export const PATCH_COMMAND = COMMANDS.find((c) => c.name === "patch")!;

/**
 * 커맨드 이름과 플래그 값으로 vib CLI 인수 배열을 만든다.
 * 필수 플래그가 누락되면 null을 반환한다.
 */
export function buildCmdArgs(
  name: string,
  cmdFlagValues: Record<string, Record<string, string | boolean>>
): string[] | null {
  const cmd = COMMANDS.find((c) => c.name === name);
  const flags = (cmd as any)?.flags as FlagDef[] | undefined;
  if (!flags?.length) return [name];

  const fvals = cmdFlagValues[name] ?? {};
  const args: string[] = [name];
  let positional: string | null = null;

  for (const fd of flags) {
    const val: string | boolean =
      fvals[fd.key] ??
      (fd.type === "bool"
        ? false
        : fd.type === "select" && fd.options.length > 0
          ? fd.options[0].v
          : "");
    if (fd.key === "_mode" || fd.key === "_action") {
      if (val) args.push(...String(val).split(" ").filter(Boolean));
    } else if (fd.key === "_file" || fd.key === "_request" || fd.key === "_tool") {
      if (val) positional = String(val).trim();
    } else if (fd.key === "_question") {
      if (val) args.push(String(val).trim());
    } else if (fd.type === "bool" && val) {
      args.push(`--${fd.key}`);
    } else if (fd.type === "text" && val) {
      if (fd.numeric && isNaN(Number(String(val)))) continue;
      args.push(`--${fd.key}`, String(val));
    }
  }

  for (const fd of flags) {
    if ((fd as any).required) {
      const val = fvals[fd.key] ?? "";
      if (!val) return null;
    }
  }

  if (positional) args.splice(1, 0, positional);
  return args;
}
// === ANCHOR: COMMANDS_END ===
