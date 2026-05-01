// === ANCHOR: HELPDATA_START ===
import { getManualJson } from "./vib";

export type HelpTopic = {
  id: string;
  title: string;
  command: string;
  summary: string;
  answer: string;
};

type ManualEntry = {
  emoji?: string;
  title?: string;
  one_line?: string;
  what?: string;
  when?: string[];
  examples?: Array<[string, string]>;
  options?: Array<[string, string]>;
  notes?: string[];
};

type ManualRecord = Record<string, ManualEntry>;

const FALLBACK_TOPICS: HelpTopic[] = [
  {
    id: "overview",
    title: "핵심 기능",
    command: "vib manual rules",
    summary: "VibeLign이 왜 필요한지 한 번에 설명하는 시작점이에요.",
    answer:
      "VibeLign은 AI가 코드를 안전하게 바꾸도록 도와주는 도구예요. 작업 전에는 checkpoint로 저장하고, AI가 바꾼 뒤에는 guard와 doctor로 검사하고, 필요하면 undo로 되돌릴 수 있어요. 중요한 파일은 protect로 지키고, 수정할 위치는 anchor로 정해요.",
  },
  {
    id: "cli",
    title: "CLI",
    command: "vib --help",
    summary: "터미널에서 명령어로 쓰는 도구인지 알려줘요.",
    answer:
      "네. VibeLign은 CLI 도구예요. 터미널에서 vib start, vib checkpoint, vib watch 같은 명령어로 써요. GUI도 있지만, 기본은 터미널 커맨드 기반이에요.",
  },
  {
    id: "commands",
    title: "커맨드 목록",
    command: "vib manual",
    summary: "VibeLign에서 쓸 수 있는 주요 명령어들을 알려줘요.",
    answer:
      "VibeLign의 주요 터미널 커맨드는 vib start, checkpoint, undo, doctor, guard, anchor, watch, patch, plan-structure, claude-hook, protect, secrets, explain, config, export, manual, install, completion이에요. 전체 설명은 vib manual이나 앱 안의 메뉴얼 화면에서 더 자세히 볼 수 있어요.",
  },
  {
    id: "install",
    title: "설치",
    command: "vib install",
    summary: "처음 설치하는 방법과 지원 환경을 알려줘요.",
    answer:
      "vib install은 처음 설치하는 방법을 차근차근 알려줘요. Mac, Linux, Windows 모두 안내하고, uv 설치부터 VibeLign 설치, 그리고 자주 만나는 에러 대처법까지 같이 볼 수 있어요.",
  },
  {
    id: "completion",
    title: "자동완성",
    command: "vib completion --install",
    summary: "터미널에서 vib 명령을 더 빨리 쓰게 도와줘요.",
    answer:
      "vib completion은 명령어 자동완성을 설정해줘요. zsh, bash, PowerShell에서 쓸 수 있고, 명령어 이름이 기억나지 않을 때 훨씬 편해져요.",
  },
  {
    id: "scan",
    title: "코드맵",
    command: "vib scan",
    summary: "앵커와 코드맵을 다시 점검해요.",
    answer:
      "vib scan은 앵커를 점검하고 코드맵을 다시 갱신해요. 파일이 많이 바뀌었을 때 정리용으로 좋아요.",
  },
  {
    id: "init",
    title: "초기화",
    command: "vib init",
    summary: "VibeLign 시작 상태를 다시 잡아줘요.",
    answer:
      "vib init은 VibeLign 시작 상태를 다시 만들거나 정리할 때 써요. 기존 설정을 초기 상태로 돌리고 싶을 때 도움이 돼요.",
  },
  {
    id: "install",
    title: "설치",
    command: "vib install",
    summary: "처음 설치하는 방법과 지원 환경을 알려줘요.",
    answer:
      "vib install은 처음 설치하는 방법을 차근차근 알려줘요. Mac, Linux, Windows 모두 안내하고, uv 설치부터 VibeLign 설치까지 볼 수 있어요.",
  },
  {
    id: "start",
    title: "시작",
    command: "vib start",
    summary: "처음 한 번 프로젝트를 준비해요.",
    answer:
      "vib start는 프로젝트를 VibeLign용으로 처음 준비할 때 써요. 규칙 파일을 만들고, AI가 작업하기 쉬운 상태로 맞춰줘요. --all-tools, --tools, --force, --quickstart 같은 옵션으로 준비 범위를 조절할 수 있어요.",
  },
  {
    id: "checkpoint",
    title: "체크포인트",
    command: "vib checkpoint",
    summary: "현재 상태를 저장해요.",
    answer:
      "vib checkpoint는 지금 상태를 저장해두는 기능이에요. 나중에 문제가 생기면 이 시점으로 돌아갈 수 있어요. Git commit 뒤 자동 백업은 Settings 또는 vib config auto-backup on|off|status로 조절하고, 쌓인 백업은 BACKUPS에서 확인해요. BACKUPS의 백업 범위는 복원 가능한 원본 크기 합계이고, 실제 백업 DB/object store 용량은 Backup DB Viewer에서 확인해요. DB 파일이 커졌다면 vib backup-db-maintenance --json으로 먼저 dry-run 점검한 뒤 필요할 때만 --apply로 정리해요.",
  },
  {
    id: "undo",
    title: "되돌리기",
    command: "vib undo",
    summary: "저장한 시점으로 돌아가요.",
    answer:
      "vib undo는 저장해둔 checkpoint로 돌아가는 기능이에요. AI가 잘못 바꾼 걸 되돌릴 때 써요.",
  },
  {
    id: "history",
    title: "기록",
    command: "vib history",
    summary: "저장 목록을 보여줘요.",
    answer:
      "vib history는 지금까지 저장한 checkpoint 목록을 보여줘요. 저장한 시점들을 확인하고 싶을 때 써요.",
  },
  {
    id: "doctor",
    title: "진단",
    command: "vib doctor",
    summary: "프로젝트 상태를 검사해요.",
    answer:
      "vib doctor는 프로젝트가 AI 작업을 받기 좋은 상태인지 검사해요. 각 문제마다 심각도(HIGH/MEDIUM/LOW), 분류(구조/앵커/MCP 등), 추천 명령, 자동 수정 가능 여부를 알려줘요. --detailed로 상세 보기, --apply로 자동 수정을 할 수 있어요.",
  },
  {
    id: "anchor",
    title: "앵커",
    command: "vib anchor",
    summary: "AI가 수정할 위치를 찾게 도와줘요.",
    answer:
      "vib anchor는 파일 안에 표식을 달아서 AI가 어디를 수정해야 하는지 더 잘 찾게 해줘요. 지도에 핀을 꽂는 것과 비슷해요.",
  },
  {
    id: "scan",
    title: "스캔",
    command: "vib scan",
    summary: "앵커와 코드맵을 다시 점검해요.",
    answer:
      "vib scan은 앵커를 점검하고 코드맵을 다시 갱신해요. 파일이 많이 바뀌었을 때 정리용으로 좋아요.",
  },
  {
    id: "patch",
    title: "패치",
    command: "vib patch",
    summary: "말로 요청하면 수정 계획을 만들어줘요.",
    answer:
      "vib patch는 말로 요청한 내용을 보고 어떤 파일을 어떻게 바꿔야 할지 계획을 만들어줘요. 코드 전체를 바꾸지 않고 필요한 부분만 고치게 도와줘요.",
  },
  {
    id: "guard",
    title: "가드",
    command: "vib guard",
    summary: "AI가 코드를 망가뜨리지 않았는지 검사해요.",
    answer:
      "vib guard는 AI가 바꾼 뒤 구조가 망가지지 않았는지 검사해요. 작업 후 확인용으로 좋고, 새 source 파일에 앵커가 없는지도 같이 알려줘요. --strict를 붙이면 더 강하게 막아요.",
  },
  {
    id: "explain",
    title: "설명",
    command: "vib explain",
    summary: "뭐가 바뀌었는지 쉽게 알려줘요.",
    answer:
      "vib explain은 최근에 무엇이 바뀌었는지 쉬운 말로 알려줘요. AI가 만든 변경을 이해할 때 써요.",
  },
  {
    id: "protect",
    title: "보호",
    command: "vib protect",
    summary: "중요한 파일을 잠가요.",
    answer:
      "vib protect는 중요한 파일을 AI가 건드리지 못하게 잠가요. .env 같은 파일을 지킬 때 좋아요.",
  },
  {
    id: "secrets",
    title: "비밀정보",
    command: "vib secrets",
    summary: "Git에 비밀정보가 올라가는 걸 막아요.",
    answer:
      "vib secrets는 커밋 전에 API 키, 토큰, .env 같은 비밀정보가 있는지 검사해요. 실수로 올리는 걸 막아주고, --install-hook를 켜면 strict guard 검사도 같이 돌아가요.",
  },
  {
    id: "watch",
    title: "감시",
    command: "vib watch",
    summary: "파일이 바뀔 때 실시간으로 감시해요.",
    answer:
      "vib watch는 파일이 바뀔 때마다 실시간으로 코드맵을 최신 상태로 유지해요. AI 작업 중에 켜두면 좋고, --auto-fix를 붙이면 새 source 파일에 앵커가 없을 때 자동으로 넣어줘요.",
  },
  {
    id: "plan-structure",
    title: "구조 계획",
    command: "vib plan-structure",
    summary: "코딩 전에 어느 파일을 바꿀지 먼저 정해요.",
    answer:
      "vib plan-structure는 큰 기능을 만들기 전에 어느 파일을 수정하고 어떤 파일을 새로 만들지 먼저 정해줘요. 여러 파일이 같이 바뀌거나 새 production 파일을 만들 때 특히 유용해요. 보통은 plan-structure로 설계도를 만들고, 그다음 구현한 뒤, 마지막에 guard --strict로 확인하면 돼요.",
  },
  {
    id: "claude-hook",
    title: "클로드 훅",
    command: "vib claude-hook",
    summary: "Claude가 저장 전에 검사를 하게 만들어요.",
    answer:
      "vib claude-hook는 Claude Code가 Write 도구를 쓰기 전에 VibeLign pre-check를 먼저 돌리게 해줘요. status로 상태를 보고, enable/disable로 켜고 끌 수 있어요.",
  },
  {
    id: "ask",
    title: "질문",
    command: "vib ask",
    summary: "파일이 뭘 하는지 쉬운 말로 설명해줘요.",
    answer:
      "vib ask는 코드 파일이 무엇을 하는지 쉬운 말로 설명해줘요. 파일을 이해하고 싶을 때 써요.",
  },
  {
    id: "config",
    title: "설정",
    command: "vib config",
    summary: "AI 기능용 API 키와 지원 모델을 설정해요.",
    answer:
      "vib config는 AI 기능을 쓰기 위한 API 키와 프로젝트 옵션을 설정해요. 커밋 후 자동 백업은 vib config auto-backup on|off|status로 켜고 끌 수 있어요.",
  },
  {
    id: "export",
    title: "내보내기",
    command: "vib export",
    summary: "다른 AI 도구 설정 파일을 만들어요.",
    answer:
      "vib export는 Claude, Cursor, OpenCode 같은 도구용 설정 파일을 만들어줘요. 다른 AI 도구로 옮길 때 편해요.",
  },
  {
    id: "transfer",
    title: "전환",
    command: "vib transfer",
    summary: "작업 맥락을 다른 AI 도구로 넘겨 이어서 쓰게 해줘요.",
    answer:
      "vib transfer는 지금까지의 작업 맥락을 다른 AI 도구로 넘겨서 이어 작업하게 해줘요. PROJECT_CONTEXT.md를 만들고, --handoff를 쓰면 새 AI가 바로 이어받기 쉬워요.",
  },
  {
    id: "mcp",
    title: "MCP",
    command: "vib start",
    summary: "AI가 VibeLign 기능을 직접 실행하게 연결해줘요.",
    answer:
      "네, 할 수 있어요. VibeLign은 MCP로 AI와 연결되면 AI가 checkpoint 저장, guard 확인 같은 기능을 직접 실행할 수 있어요.",
  },
  {
    id: "manual",
    title: "규칙",
    command: "vib manual rules",
    summary: "AI가 지켜야 할 코딩 규칙을 보여줘요.",
    answer:
      "vib manual rules에서 VibeLign 규칙을 볼 수 있어요. 새 기능은 새 파일로 나누고 한 파일에 너무 많이 몰아넣지 않는 게 핵심이에요.",
  },
];

const SYNTHETIC_TOPIC_IDS = new Set(["overview", "cli", "commands", "policy"]);

export const HELP_FALLBACK =
  "아직 정확히 못 찾았어요. '설치', '저장', '되돌리기', '검사', '앵커', '보호', 'MCP', '명령어'처럼 조금만 바꿔서 물어봐 주세요.";

let manualTopicsCache: HelpTopic[] | null = null;
let manualTopicsPromise: Promise<HelpTopic[]> | null = null;

// === ANCHOR: HELPDATA_NORMALIZETEXT_START ===
function normalizeText(text: string): string {
  return text.toLowerCase().replace(/[\s\p{P}\p{S}]+/gu, "");
}
// === ANCHOR: HELPDATA_NORMALIZETEXT_END ===

// === ANCHOR: HELPDATA_TOBIGRAMS_START ===
function toBigrams(text: string): string[] {
  const chars = [...normalizeText(text)];
  if (chars.length === 0) return [];
  if (chars.length === 1) return chars;
  const result: string[] = [];
  for (let i = 0; i < chars.length - 1; i += 1) {
    result.push(chars[i] + chars[i + 1]);
  }
  return result;
}
// === ANCHOR: HELPDATA_TOBIGRAMS_END ===

// === ANCHOR: HELPDATA_JACCARDSCORE_START ===
function jaccardScore(left: string[], right: string[]): number {
  if (left.length === 0 || right.length === 0) return 0;
  const leftSet = new Set(left);
  const rightSet = new Set(right);
  let intersection = 0;
  leftSet.forEach((item) => {
    if (rightSet.has(item)) intersection += 1;
  });
  const union = new Set([...leftSet, ...rightSet]).size;
  return union === 0 ? 0 : intersection / union;
}
// === ANCHOR: HELPDATA_JACCARDSCORE_END ===

// === ANCHOR: HELPDATA_FIRSTLINE_START ===
function firstLine(text: string | undefined): string {
  if (!text) return "";
  return text
    .trim()
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean)
    ?.replace(/[。.!?]+$/, "")
    ?? "";
}
// === ANCHOR: HELPDATA_FIRSTLINE_END ===

// === ANCHOR: HELPDATA_COMMANDLABEL_START ===
function commandLabel(id: string): string {
  if (id === "rules") return "vib manual rules";
  return `vib ${id}`;
}
// === ANCHOR: HELPDATA_COMMANDLABEL_END ===

// === ANCHOR: HELPDATA_ISSYNTHETICTOPIC_START ===
function isSyntheticTopic(topic: HelpTopic): boolean {
  return SYNTHETIC_TOPIC_IDS.has(topic.id);
}
// === ANCHOR: HELPDATA_ISSYNTHETICTOPIC_END ===

// === ANCHOR: HELPDATA_INCLUDESANY_START ===
function includesAny(text: string, markers: string[]): boolean {
  return markers.some((marker) => text.includes(normalizeText(marker)));
}
// === ANCHOR: HELPDATA_INCLUDESANY_END ===

// === ANCHOR: HELPDATA_TOPICALIASMARKERS_START ===
function topicAliasMarkers(topicId: string): string[] {
  const aliases: Record<string, string[]> = {
    start: ["start", "스타트", "시작", "시작하기", "셋업", "setup", "초기설정", "초기 설정", "온보딩"],
    checkpoint: ["checkpoint", "체크포인트", "첵포인트", "체크 포인트", "체크", "세이브", "저장", "백업", "save"],
    undo: ["undo", "언두", "언두하기", "되돌리기", "복구", "롤백", "rollback"],
    history: ["history", "히스토리", "기록", "내역", "저장목록"],
    doctor: ["doctor", "닥터", "도크터", "건강검진", "점검", "진단"],
    anchor: ["anchor", "앵커", "앵커링", "표식", "핀", "marker"],
    scan: ["scan", "스캔", "검사", "정리", "갱신", "코드맵", "코드 맵", "codemap", "code map", "project map"],
    patch: ["patch", "패치", "패칭", "수정계획", "수정 계획", "플랜", "request"],
    "plan-structure": ["plan-structure", "plan structure", "구조계획", "구조 계획", "설계도", "파일 계획", "플랜스트럭처"],
    guard: ["guard", "가드", "가아드", "검사", "검증", "보호"],
    "claude-hook": ["claude-hook", "claude hook", "클로드훅", "클로드 훅", "pretooluse", "pretoluse", "hook", "훅"],
    explain: ["explain", "익스플레인", "설명", "변경설명", "변경 설명"],
    protect: ["protect", "프로텍트", "보호", "잠금", "락", "lock"],
    secrets: ["secrets", "시크릿", "시크리츠", "비밀", "비밀정보", "토큰", "키", "env", "이엔브이", "엔브이"],
    watch: ["watch", "워치", "와치", "감시", "실시간", "자동감시", "자동 감시"],
    ask: ["ask", "애스크", "에스크", "아스크", "질문", "설명해줘", "무슨 파일", "뭐하는"],
    config: ["config", "컨피그", "콘피그", "설정", "모델", "model", "지원 모델", "지원하는 모델", "api키", "api key", "키 설정"],
    export: ["export", "익스포트", "엑스포트", "내보내기", "설정내보내기"],
    transfer: ["transfer", "트랜스퍼", "트렌스퍼", "전환", "이동", "넘기기", "넘겨", "이어받기", "인수인계", "핸드오프", "핸드 오프", "세션핸드오프", "세션 핸드오프", "handoff", "session handoff", "context"],
    completion: ["completion", "컴플리션", "컴플릿션", "자동완성", "자동 완성", "오토컴플릿", "탭", "tab", "autocomplete"],
    init: ["init", "이닛", "초기화", "초기설정", "reset"],
    install: ["install", "인스톨", "인설트", "설치"],
    rules: ["rules", "rule", "룰", "룰즈", "규칙", "가이드라인", "지침", "정책", "manual rules", "ai_dev_system", "개발 규칙"],
    policy: ["policy", "폴리시", "정책", "원칙", "지침", "가이드라인", "규칙"],
    mcp: ["mcp", "엠씨피", "엠 씨 피", "터미널 없이", "직접 실행", "자동연동"],
  };

  return aliases[topicId] ?? [];
}
// === ANCHOR: HELPDATA_TOPICALIASMARKERS_END ===

// === ANCHOR: HELPDATA_MANUALENTRYTOTOPIC_START ===
function manualEntryToTopic(id: string, entry: ManualEntry): HelpTopic | null {
  // === ANCHOR: HELPDATA_TITLE_START ===
  const title = (entry.title ?? "").trim();
  // === ANCHOR: HELPDATA_WHAT_START ===
  const what = (entry.what ?? "").trim();
  // === ANCHOR: HELPDATA_ONELINE_START ===
  const oneLine = (entry.one_line ?? "").trim();
  if (!title && !what && !oneLine) return null;
  // === ANCHOR: HELPDATA_TITLE_END ===

  // === ANCHOR: HELPDATA_WHAT_END ===
  const summary = oneLine || firstLine(what) || `vib ${id} 설명`;
  // === ANCHOR: HELPDATA_ONELINE_END ===
  const answerParts = [oneLine || title, what]
    .map((part) => part?.trim())
    .filter((part): part is string => Boolean(part));

  if (entry.when?.length) {
    answerParts.push(`언제 써요: ${entry.when.slice(0, 3).join(" / ")}`);
  }
  if (entry.examples?.length) {
    answerParts.push(
      `예시: ${entry.examples
        .slice(0, 2)
        .map(([cmd, desc]) => `${cmd} (${desc})`)
        .join(" / ")}`,
    );
  }
  if (entry.options?.length) {
    answerParts.push(
      `옵션: ${entry.options
        .slice(0, 2)
        .map(([opt, desc]) => `${opt} - ${desc.replace(/\n/g, " ")}`)
        .join(" / ")}`,
    );
  }
  if (entry.notes?.length) {
    answerParts.push(`참고: ${entry.notes.slice(0, 2).join(" / ")}`);
  }

  return {
    id,
// === ANCHOR: HELPDATA_MANUALENTRYTOTOPIC_END ===
    title: title || id,
    command: commandLabel(id),
    summary,
    answer: answerParts.join("\n\n"),
  };
}

// === ANCHOR: HELPDATA_BUILDTOPICSFROMMANUAL_START ===
function buildTopicsFromManual(manual: ManualRecord): HelpTopic[] {
  const manualTopics = Object.entries(manual)
    .map(([id, entry]) => manualEntryToTopic(id, entry))
    .filter((topic): topic is HelpTopic => Boolean(topic));

  const commandList = Object.keys(manual)
    .filter((id) => id !== "mcp")
    .map((id) => commandLabel(id))
    .join(", ");

  const syntheticTopics: HelpTopic[] = [
    {
      id: "overview",
      title: "핵심 기능",
      command: "vib manual rules",
      summary: "VibeLign이 왜 필요한지 한 번에 설명하는 시작점이에요.",
      answer:
        "VibeLign은 AI가 코드를 안전하게 바꾸도록 도와주는 도구예요. 작업 전에는 checkpoint로 저장하고, AI가 바꾼 뒤에는 guard와 doctor로 검사하고, 필요하면 undo로 되돌릴 수 있어요. 중요한 파일은 protect로 지키고, 수정할 위치는 anchor로 정해요.",
    },
    {
      id: "cli",
      title: "CLI",
      command: "vib --help",
      summary: "터미널에서 명령어로 쓰는 도구인지 알려줘요.",
      answer:
        "네. VibeLign은 CLI 도구예요. 터미널에서 vib start, vib checkpoint, vib watch 같은 명령어로 써요. GUI도 있지만, 기본은 터미널 커맨드 기반이에요.",
    },
    {
      id: "commands",
      title: "커맨드 목록",
      command: "vib manual",
      summary: "VibeLign에서 쓸 수 있는 주요 명령어들을 알려줘요.",
      answer: `VibeLign의 주요 터미널 커맨드는 ${commandList}예요. 전체 설명은 vib manual이나 앱 안의 메뉴얼 화면에서 더 자세히 볼 수 있어요.`,
    },
    {
      id: "policy",
      title: "정책",
      command: "vib manual rules",
      summary: "파일이 한곳에 몰리지 않게 하는 원칙을 설명해요.",
      answer:
        "VibeLign 정책의 핵심은 새 기능을 기존 큰 파일에 계속 붙이지 않고 새 파일/모듈로 나누는 거예요. AI가 한 파일에 몰빵하는 걸 막는 기본 원칙이라고 보면 돼요.",
    },
  ];

  return [...syntheticTopics, ...manualTopics];
}
// === ANCHOR: HELPDATA_BUILDTOPICSFROMMANUAL_END ===

// === ANCHOR: HELPDATA_LOADMANUALTOPICS_START ===
async function loadManualTopics(): Promise<HelpTopic[]> {
  if (manualTopicsCache) {
    return manualTopicsCache;
  }

  if (!manualTopicsPromise) {
    manualTopicsPromise = (async () => {
      try {
        const manual = await getManualJson();
        const topics = buildTopicsFromManual(manual as ManualRecord);
        manualTopicsCache = topics;
        return topics;
      } catch {
        return FALLBACK_TOPICS;
      } finally {
        manualTopicsPromise = null;
      }
    })();
  }

  return manualTopicsPromise;
}
// === ANCHOR: HELPDATA_LOADMANUALTOPICS_END ===

// === ANCHOR: HELPDATA_SCORETOPIC_START ===
function scoreTopic(question: string, topic: HelpTopic): number {
  const questionText = normalizeText(question);
  const questionBigrams = toBigrams(questionText);

  const topicText = [topic.title, topic.command, topic.summary, topic.answer].join(" ");
  const topicBigrams = toBigrams(topicText);

  let score = jaccardScore(questionBigrams, topicBigrams);

  const title = normalizeText(topic.title);
  const command = normalizeText(topic.command);
  const summary = normalizeText(topic.summary);
  const topicId = normalizeText(topic.id);

  if (title && questionText.includes(title)) score += 0.18;
  if (command && questionText.includes(command)) score += 0.28;
  if (summary && questionText.includes(summary)) score += 0.12;
  if (topicId && questionText.includes(topicId)) score += 0.22;
  const aliases = topicAliasMarkers(topic.id);
  if (aliases.length > 0 && includesAny(questionText, aliases)) score += 0.34;

  if (topic.id === "overview") {
    if (includesAny(questionText, ["좋은", "장점", "왜", "필요", "써야", "이유", "혜택", "도움"])) {
      score += 0.22;
    }
  }

  if (topic.id === "install") {
    if (includesAny(questionText, ["윈도", "windows", "맥", "mac", "리눅스", "linux", "크로스", "지원", "플랫폼"])) {
      score += 0.24;
    }
  }

  if (topic.id === "config") {
    if (includesAny(questionText, ["모델", "model", "지원모델", "지원하는모델", "provider", "프로바이더", "claude", "gemini", "api키", "api key", "키"])) {
      score += 0.46;
    }
  }

  if (topic.id === "cli") {
    if (includesAny(questionText, ["cli", "터미널", "커맨드", "명령어", "쉘", "bash", "zsh", "powershell", "terminal"])) {
      score += 0.36;
    }
  }

  if (topic.id === "commands") {
    if (includesAny(questionText, ["어떤", "목록", "뭐가", "무슨", "지원", "있어", "있나요", "명령어", "커맨드", "할 수 있는"])) {
      score += 0.42;
    }
  }

  if (topic.id === "watch") {
    if (includesAny(questionText, ["실시간", "감시", "watch", "watchdog", "자동감시", "자동 감시", "자동으로감시"])) {
      score += 0.35;
    }
  }

  if (topic.id === "anchor") {
    if (includesAny(questionText, ["anchor", "앵커", "표식", "핀", "pin", "marker", "마커", "고정"])) {
      score += 0.4;
    }
  }

  if (topic.id === "mcp") {
    if (includesAny(questionText, ["mcp", "자동연동", "자동으로", "직접 실행", "터미널 없이"])) {
      score += 0.3;
    }
  }

  if (topic.id === "transfer") {
    if (includesAny(questionText, ["transfer", "전달", "이동", "넘겨", "넘기", "다른ai", "다른툴", "다른도구", "handoff", "이어받", "인수인계", "교체"])) {
      score += 0.38;
    }
  }

  if (topic.id === "rules" || topic.id === "manual" || topic.id === "policy") {
    if (includesAny(questionText, ["rules", "규칙", "원칙", "가이드라인", "지침", "정책", "ai_dev_system", "개발규칙", "개발 규칙"])) {
      score += 0.4;
    }
  }

  if (topic.id === "completion") {
    if (includesAny(questionText, ["completion", "자동완성", "자동 완성", "tab", "탭", "autocomplete", "완성", "명령 자동완성"])) {
      score += 0.38;
    }
  }

  if (topic.id === "protect" || topic.id === "secrets") {
    if (includesAny(questionText, ["protect", "보호", "잠금", "지키", "금지", "secret", "secrets", "비밀", "키", "토큰", "env", "유출", "민감"])) {
      score += 0.36;
    }
  }

  if (topic.id === "checkpoint" || topic.id === "undo") {
    if (includesAny(questionText, ["checkpoint", "저장", "세이브", "되돌리", "복구", "이전", "백업", "undo", "취소"])) {
      score += 0.3;
    }
  }

  return score;
}
// === ANCHOR: HELPDATA_SCORETOPIC_END ===

// === ANCHOR: HELPDATA_SELECTTOPICS_START ===
function selectTopics(question: string, topics: HelpTopic[], limit = 4): Array<{ topic: HelpTopic; score: number }> {
  return topics
    .map((topic) => ({ topic, score: scoreTopic(question, topic) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}
// === ANCHOR: HELPDATA_SELECTTOPICS_END ===

// === ANCHOR: HELPDATA_BUILDCONTEXT_START ===
function buildContext(topics: Array<{ topic: HelpTopic; score: number }>): string {
  return topics
    .map(
      ({ topic }, index) =>
        `${index + 1}. [${topic.title}] ${topic.command}\n요약: ${topic.summary}\n설명: ${topic.answer}`,
    )
    .join("\n\n");
}
// === ANCHOR: HELPDATA_BUILDCONTEXT_END ===

// === ANCHOR: HELPDATA_COMPOSELOCALANSWER_START ===
function composeLocalAnswer(question: string, topics: HelpTopic[]): string {
  const ranked = selectTopics(question, topics, 3);
  const top = ranked[0];
  const runnerUp = ranked[1];
  const clearWinner =
    Boolean(top) &&
    top.score >= 0.03 &&
    (!runnerUp || top.score >= runnerUp.score + 0.03 || top.score >= runnerUp.score * 2);

  if (top) {
    const answerThreshold = isSyntheticTopic(top.topic) ? 0.05 : 0.04;
    if (clearWinner || top.score >= answerThreshold) {
      return top.topic.answer;
    }
  }

  if (!top || top.score < 0.06) {
    const suggestions = ranked.filter((item) => item.score > 0).slice(0, 2);
    if (suggestions.length === 0) return HELP_FALLBACK;
    return `정확히는 못 잡았어요. 혹시 ${suggestions.map((item) => `${item.topic.title}(${item.topic.command})`).join("이나 ")} 쪽을 물어본 걸까요?`;
  }

  return top.topic.answer;
}
// === ANCHOR: HELPDATA_COMPOSELOCALANSWER_END ===

// === ANCHOR: HELPDATA_GETSTRONGLOCALANSWER_START ===
function getStrongLocalAnswer(question: string, topics: HelpTopic[]): string | null {
  const ranked = selectTopics(question, topics, 2);
  const top = ranked[0];
  if (!top) return null;

  const questionText = normalizeText(question);
  const title = normalizeText(top.topic.title);
  const command = normalizeText(top.topic.command);
  // === ANCHOR: HELPDATA_STRONGNAMEHIT_START ===
  const strongNameHit = (title && questionText.includes(title)) || (command && questionText.includes(command));
  const threshold = isSyntheticTopic(top.topic) ? 0.18 : 0.14;

  if (strongNameHit || top.score >= threshold) {
    return top.topic.answer;
  }
  // === ANCHOR: HELPDATA_STRONGNAMEHIT_END ===

// === ANCHOR: HELPDATA_GETSTRONGLOCALANSWER_END ===
  return null;
}

type GeminiCandidate = { content?: { parts?: Array<{ text?: string }> } };
type GeminiResponse = { candidates?: GeminiCandidate[] };

const GEMINI_HELP_MODEL = "gemini-1.5-flash";

// === ANCHOR: HELPDATA_ANSWERWITHGEMINI_START ===
async function answerWithGemini(question: string, providerKey: string, topics: HelpTopic[]): Promise<string | null> {
  const ranked = selectTopics(question, topics, 4);
  const context = buildContext(ranked);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 4500);
  try {
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_HELP_MODEL}:generateContent?key=${encodeURIComponent(providerKey)}`,
      {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              role: "user",
              parts: [
                {
                  text:
                    "You are a VibeLign help assistant. Answer the user's question using only the CONTEXT below. " +
                    "Use simple Korean, 2-4 sentences. Do not invent features or facts not present in the context. " +
                    "If the context is not enough, say you cannot confirm it from the available VibeLign docs.\n\n" +
                    `QUESTION: ${question}\n\nCONTEXT:\n${context}`,
                },
              ],
            },
          ],
          generationConfig: {
            temperature: 0.2,
            topK: 1,
            topP: 1,
            maxOutputTokens: 180,
          },
        }),
      },
    );

    if (!response.ok) return null;

    // === ANCHOR: HELPDATA_DATA_START ===
    const data = (await response.json()) as GeminiResponse;
    const text = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? "";
    return text || null;
  } catch {
    // === ANCHOR: HELPDATA_DATA_END ===
    return null;
  } finally {
    clearTimeout(timeout);
// === ANCHOR: HELPDATA_ANSWERWITHGEMINI_END ===
  }
}

// === ANCHOR: HELPDATA_RESOLVEHELPANSWER_START ===
export async function resolveHelpAnswer(
  question: string,
  providerKeys?: Record<string, string> | null,
): Promise<string> {
  const topics = await loadManualTopics();

  const strongLocal = getStrongLocalAnswer(question, topics);
  if (strongLocal) {
    return strongLocal;
  }

  const geminiKey = providerKeys?.GEMINI?.trim() ?? "";
  if (geminiKey) {
    const grounded = await answerWithGemini(question, geminiKey, topics);
    if (grounded) {
      return grounded;
    }
  }

  return composeLocalAnswer(question, topics);
}
// === ANCHOR: HELPDATA_RESOLVEHELPANSWER_END ===

// === ANCHOR: HELPDATA_GETHELPANSWER_START ===
export function getHelpAnswer(question: string): string {
  const normalized = normalizeText(question);
  if (!normalized) {
    return "질문을 입력해 주세요. 예: '이 툴로 뭘 할 수 있어?'";
  }

  return composeLocalAnswer(question, FALLBACK_TOPICS);
}
// === ANCHOR: HELPDATA_GETHELPANSWER_END ===
// === ANCHOR: HELPDATA_END ===
