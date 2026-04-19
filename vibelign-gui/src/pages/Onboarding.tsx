// === ANCHOR: ONBOARDING_START ===
import { useState, useEffect } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import { openUrl } from "@tauri-apps/plugin-opener";
import {
  getVibPath,
  loadProviderApiKeys,
  vibStart,
  readProjectSummary,
  checkGitInstalled,
  checkXcodeClt,
  getOnboardingSnapshot,
  listenOnboardingProgress,
  retryOnboardingVerification,
  startNativeInstall,
  startOnboardingLoginProbe,
  addClaudeToUserPath,
  uninstallClaudeCode,
  getOnboardingLogs,
  type NextAction,
  type OnboardingProgressEvent,
  type OnboardingSnapshot,
} from "../lib/vib";
import { getHelpAnswer, resolveHelpAnswer } from "../lib/helpData";

const VIBELIGN_GITHUB_URL = "https://github.com/yesonsys03-web/VibeLign.git";

/** Threads 프로필(웹). 본인 @아이디에 맞게 이 한 줄만 수정하면 됩니다. */
const VIBELIGN_THREADS_PROFILE_URL = "https://www.threads.net/@jongjatdon";

/** 바이브라인 깃허브 카드 헤더 — Threads / 선택 버튼 공통 */
const githubCardHeaderBtnStyle = {
  fontSize: 10,
  fontWeight: 700,
  padding: "3px 10px",
  border: "2px solid #1A1A1A",
  flexShrink: 0,
} as const;

/** Simple Icons (Threads) — viewBox 0 0 24 24 */
function ThreadsIcon({ size = 14 }: { size?: number }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="currentColor"
      aria-hidden
    >
      <path d="M12.186 24h-.007c-3.581-.024-6.334-1.205-8.184-3.509C2.35 18.44 1.5 15.586 1.472 12.01v-.017c.03-3.579.879-6.43 2.525-8.482C5.845 1.205 8.6.024 12.18 0h.014c2.746.02 5.043.725 6.826 2.098 1.677 1.29 2.858 3.13 3.509 5.467l-2.04.569c-1.104-3.96-3.898-5.984-8.304-6.015-2.91.022-5.11.936-6.54 2.717C4.307 6.504 3.616 8.914 3.589 12c.027 3.086.718 5.496 2.057 7.164 1.43 1.783 3.631 2.698 6.54 2.717 2.623-.02 4.358-.631 5.8-2.045 1.647-1.613 1.618-3.593 1.09-4.798-.31-.71-.873-1.3-1.634-1.75-.192 1.352-.622 2.446-1.284 3.272-.886 1.102-2.14 1.704-3.73 1.79-1.202.065-2.361-.218-3.259-.801-1.063-.689-1.685-1.74-1.752-2.964-.065-1.19.408-2.285 1.33-3.082.88-.76 2.119-1.207 3.583-1.291a13.853 13.853 0 0 1 3.02.142c-.126-.742-.375-1.332-.75-1.757-.513-.586-1.308-.883-2.359-.89h-.029c-.844 0-1.992.232-2.721 1.32L7.734 7.847c.98-1.454 2.568-2.256 4.478-2.256h.044c3.194.02 5.097 1.975 5.287 5.388.108.046.216.094.321.142 1.49.7 2.58 1.761 3.154 3.07.797 1.82.871 4.79-1.548 7.158-1.85 1.81-4.094 2.628-7.277 2.65Zm1.003-11.69c-.242 0-.487.007-.739.021-1.836.103-2.98.946-2.916 2.143.067 1.256 1.452 1.839 2.784 1.767 1.224-.065 2.818-.543 3.086-3.71a10.5 10.5 0 0 0-2.215-.221z" />
    </svg>
  );
}

interface OnboardingProps {
  onComplete: (projectDir: string, apiKey: string | null) => void;
  onResume?: (dir: string) => void;
  onRemoveRecent?: (dir: string) => void;
  recentDirs?: string[];
}

const FEATURE_CARDS = [
  { icon: "MAP", color: "#F5621E", title: "코드맵 생성",   desc: "AI가 구조 즉시 이해" },
  { icon: "♥",   color: "#FF4D8B", title: "AI 폭주 방지", desc: "실시간 감시 모드" },
  { icon: "↺",   color: "#7B4DFF", title: "원클릭 복구",  desc: "checkpoint + undo" },
  { icon: "⇄",   color: "#4D9FFF", title: "AI 이동 자유", desc: "Claude · Cursor 즉시" },
];

type TermLine = { type: "prompt" | "check" | "arrow"; text: string; detail?: string };

const TERMINAL_LINES_DEFAULT: TermLine[] = [
  { type: "prompt", text: "vibelign start" },
  { type: "check",  text: "프로젝트 구조 스캔 완료" },
  { type: "check",  text: "앵커 18개 자동 삽입" },
  { type: "check",  text: "코드맵 생성 → .vibelign/" },
  { type: "check",  text: "체크포인트 자동 백업" },
  { type: "check",  text: "AI에게 코드맵만 주세요!" },
];

/** 온보딩 — 바이브라인 첫걸음 (아코디언 + 스텝) */
const ONBOARDING_GUIDE_STEPS: {
  title: string;
  lines: string[];
  bullets?: string[];
  code?: string;
  hint?: string;
}[] = [
  {
    title: "바이브라인이 뭐예요?",
    lines: [
      "AI가 코드를 고칠 때 어디까지 건드려도 되는지 정해 주고, 망가졌는지 검사하고, 되돌릴 수 있게 도와주는 도구예요.",
      "코드를 대신 짜 주진 않아요. 안전하게 같이 일하는 도우미에 가깝습니다.",
    ],
  },
  {
    title: "어떤 폴더를 열면 되나요?",
    lines: [
      "지금 작업 중인 코드가 있는 폴더를 고르면 됩니다. 새 빈 폴더보다는, 보통 git을 쓰는 프로젝트 루트가 잘 맞아요.",
    ],
    hint: "아래 「최근 프로젝트」가 있으면 한 번에 다시 열 수 있어요.",
  },
  {
    title: "처음에는 start 한 번",
    lines: [
      "터미널에서 그 폴더로 들어간 뒤 vib start 를 한 번 실행해요. 그러면 AI가 읽을 규칙 파일과 .vibelign 폴더가 생겨요.",
      "이 GUI에서 폴더만 고른 상태라도, 나중에 터미널에서 같은 폴더로 가서 실행하면 돼요.",
    ],
    code: "vib start",
  },
  {
    title: "API 키는 꼭일까요?",
    lines: [
      "필수는 아니에요. 다만 vib patch --ai 같이 AI에게 더 맡기는 기능을 쓰려면 API 키가 필요해요.",
      "⚙ 설정에서 Anthropic 등 API 키를 넣을 수 있어요.",
    ],
  },
  {
    title: "홈에서 자주 쓰는 것",
    lines: ["프로젝트를 연 뒤 홈 화면에서 이런 순서로 익혀 보면 좋아요."],
    bullets: [
      "코드맵 — 구조를 한눈에 (파일을 많이 바꾼 뒤 갱신하면 좋아요)",
      "패치 — 말로 바꿀 내용을 넣으면 어디를 고치면 될지 계획이 나와요",
      "AI 방지(guard) — AI가 고친 뒤 이상한지 점검",
      "체크포인트 — 지금 상태 저장 (게임 세이브 같아요)",
    ],
  },
  {
    title: "잘못됐으면",
    lines: [
      "먼저 가드로 확인해 보고, 안 되면 되돌리기(undo)를 생각하면 돼요.",
      "그전에 체크포인트를 자주 찍어 두면 훨씬 안심돼요.",
    ],
  },
  {
    title: "커맨드가 더 궁금하면",
    lines: [
      "앱 안 MANUAL 화면에서 커맨드마다 짧은 설명을 볼 수 있어요. 터미널에서는 vib manual 도 있어요.",
    ],
  },
];

export default function Onboarding({ onComplete, onResume, onRemoveRecent, recentDirs = [] }: OnboardingProps) {
  const [vibFound, setVibFound] = useState<string | null>(null);
  const [vibChecking, setVibChecking] = useState(true);
  const [selectedDir, setSelectedDir] = useState("");
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [githubOpen, setGithubOpen] = useState(false);
  const [guideOpen, setGuideOpen] = useState(true);
  const [guideStep, setGuideStep] = useState(0);
  const [recentOpen, setRecentOpen] = useState(true);
  const [helpOpen, setHelpOpen] = useState(true);
  const [helpQuestion, setHelpQuestion] = useState("");
  const [helpAnswer, setHelpAnswer] = useState("예: 이 툴로 뭘 할 수 있어?");
  const [helpLoading, setHelpLoading] = useState(false);
  const [gitInstalled, setGitInstalled] = useState<boolean | null>(null);
  const [xcodeCltInstalled, setXcodeCltInstalled] = useState<boolean | null>(null);
  const [summaryIdx, setSummaryIdx] = useState(0);
  const [termLines, setTermLines] = useState<TermLine[]>(TERMINAL_LINES_DEFAULT);
  const [animStep, setAnimStep] = useState(TERMINAL_LINES_DEFAULT.length);
  const [termDetail, setTermDetail] = useState<string | null>(null);
  const [onboardingSnapshot, setOnboardingSnapshot] = useState<OnboardingSnapshot | null>(null);
  const [onboardingProgress, setOnboardingProgress] = useState<OnboardingProgressEvent | null>(null);
  const [onboardingBusy, setOnboardingBusy] = useState(false);
  const [onboardingLogs, setOnboardingLogs] = useState("");
  const [onboardingLogsOpen, setOnboardingLogsOpen] = useState(false);

  useEffect(() => {
    getVibPath().then((p) => { setVibFound(p); setVibChecking(false); });
    checkGitInstalled().then(setGitInstalled).catch(() => setGitInstalled(false));
    checkXcodeClt().then(setXcodeCltInstalled).catch(() => setXcodeCltInstalled(true));
    getOnboardingSnapshot().then(setOnboardingSnapshot).catch(() => setOnboardingSnapshot(null));

    let active = true;
    let unlisten: (() => void) | undefined;
    listenOnboardingProgress((event) => {
      if (!active) return;
      setOnboardingProgress(event);
      getOnboardingSnapshot().then((snapshot) => {
        if (!active) return;
        setOnboardingSnapshot(snapshot);
      }).catch(() => undefined);
      // Git 을 직접 재검사해 Git 미설치 경고 배너가 설치 후에도 갱신되도록 한다.
      checkGitInstalled().then((ok) => { if (active) setGitInstalled(ok); }).catch(() => undefined);
    })
      .then((fn) => { unlisten = fn; })
      .catch(() => undefined);

    // 앱이 포커스를 다시 받으면 사용자가 외부에서 Git 을 설치했을 수 있으므로 재검사한다.
    const onFocus = () => {
      checkGitInstalled().then((ok) => { if (active) setGitInstalled(ok); }).catch(() => undefined);
    };
    window.addEventListener("focus", onFocus);

    return () => {
      active = false;
      unlisten?.();
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  useEffect(() => {
    const activeState = onboardingSnapshot?.state;
    const isActivePhase =
      activeState === "installing_native" ||
      activeState === "installing_wsl" ||
      activeState === "verifying_shells" ||
      activeState === "probing_login" ||
      activeState === "diagnosing";

    // 활성 단계에서는 logsAvailable 이 아직 false 여도 폴링을 돌린다.
    // 스트리밍 로그가 runtime 에 쌓이면 첫 줄이 나오는 순간 바로 보여줌.
    if (!isActivePhase && !onboardingSnapshot?.logsAvailable) {
      setOnboardingLogs("");
      setOnboardingLogsOpen(false);
      return;
    }

    let cancelled = false;
    const fetchLogs = () => {
      getOnboardingLogs()
        .then((result) => {
          if (cancelled) return;
          setOnboardingLogs(result.text ?? "");
        })
        .catch(() => {
          if (cancelled) return;
        });
    };
    fetchLogs();

    if (isActivePhase) {
      setOnboardingLogsOpen(true);
    } else if ((onboardingSnapshot?.lastError || onboardingProgress?.status === "failed")) {
      setOnboardingLogsOpen(true);
    }

    let intervalId: ReturnType<typeof setInterval> | undefined;
    if (isActivePhase) {
      intervalId = setInterval(fetchLogs, 1000);
    }

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [onboardingSnapshot?.logsAvailable, onboardingSnapshot?.state, onboardingSnapshot?.lastError, onboardingProgress?.status, onboardingProgress?.stepId]);

  // 최근 프로젝트 요약 로드 — git repo가 아닌 경로는 건너뜀
  useEffect(() => {
    if (recentDirs.length === 0) return;
    let cancelled = false;
    async function load() {
      // summaryIdx 기준으로 순서대로 시도, 유효한 데이터가 나올 때까지
      for (let offset = 0; offset < recentDirs.length; offset++) {
        const idx = (summaryIdx + offset) % recentDirs.length;
        const dir = recentDirs[idx]!;
        try {
          const s = await readProjectSummary(dir);
          if (cancelled) return;
          const lines: TermLine[] = [
            { type: "prompt", text: s.project_name },
            ...s.git_commits.slice(0, 3).map((c) => ({ type: "check" as const, text: c.display, detail: c.detail })),
            ...s.checkpoints.slice(0, 2).map((c) => ({ type: "arrow" as const, text: c.display, detail: c.detail })),
          ];
          if (lines.length >= 2) {
            setTermLines(lines);
            setAnimStep(0);
            if (offset > 0) setSummaryIdx(idx); // 건너뛴 경우 idx 보정
            return;
          }
        } catch {
          // 이 경로 실패 → 다음 시도
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [recentDirs, summaryIdx]);

  // 타이핑 애니메이션
  useEffect(() => {
    if (animStep >= termLines.length) return;
    const id = setTimeout(() => setAnimStep((s) => s + 1), 230);
    return () => clearTimeout(id);
  }, [animStep, termLines.length]);

  async function handleStart() {
    setStarting(true);
    setStartError(null);
    const r = await vibStart(selectedDir, selectedTools);
    setStarting(false);
    if (!r.ok) {
      setStartError(r.stderr || r.stdout || "vib start 실행에 실패했어요.");
      return;
    }
    onComplete(selectedDir, null);
  }

  async function pickFolder() {
    const dir = await openDialog({ directory: true, multiple: false, title: "프로젝트 폴더 선택" });
    if (typeof dir === "string") setSelectedDir(dir);
  }

  async function handleHelpAsk() {
    const question = helpQuestion.trim();
    if (!question) {
      setHelpAnswer("질문을 입력해 주세요. 예: '이 툴로 뭘 할 수 있어?'");
      return;
    }

    setHelpLoading(true);
    setHelpAnswer("생각 중...");
    try {
      let providerKeys = null;
      try {
        providerKeys = await loadProviderApiKeys();
      } catch {
        providerKeys = null;
      }

      setHelpAnswer(await resolveHelpAnswer(question, providerKeys));
    } catch {
      setHelpAnswer(getHelpAnswer(question));
    } finally {
      setHelpLoading(false);
    }
  }

  async function handleOnboardingPrimaryAction(nextAction: NextAction) {
    setOnboardingBusy(true);
    try {
      // 사용자가 외부에서 Git 을 설치했을 수 있으므로 버튼 클릭 시점에도
      // Git 상태를 재확인해 배너/설치 조건이 즉시 반영되도록 한다.
      let freshGit: boolean | null = null;
      try {
        freshGit = await checkGitInstalled();
        setGitInstalled(freshGit);
      } catch {
        /* ignore */
      }
      // install_git 버튼을 눌렀는데 Git 이 이미 설치되어 있다면 URL 을 다시 여는 대신
      // 스냅샷을 새로고침해서 ready_to_install 상태로 넘어가도록 한다 (앱 재시동 불필요).
      if (nextAction === "install_git" && freshGit === true) {
        const refreshed = await getOnboardingSnapshot().catch(() => null);
        if (refreshed) setOnboardingSnapshot(refreshed);
        return;
      }
      if (nextAction === "start_install") {
        const preferredPathKind = onboardingSnapshot?.installPathKind === "native-powershell" || onboardingSnapshot?.installPathKind === "native-cmd"
          ? onboardingSnapshot.installPathKind
          : onboardingSnapshot?.os === "windows"
          ? "native-powershell"
          : "native-cmd";
        setOnboardingSnapshot(await startNativeInstall(preferredPathKind));
      } else if (nextAction === "install_git") {
        await openUrl("https://git-scm.com/download/win").catch(() => {});
      } else if (nextAction === "retry_with_cmd") {
        setOnboardingSnapshot(await startNativeInstall("native-cmd"));
      } else if (nextAction === "retry") {
        setOnboardingSnapshot(await retryOnboardingVerification());
      } else if (nextAction === "add_to_path") {
        setOnboardingSnapshot(await addClaudeToUserPath());
      } else if (nextAction === "open_manual_steps") {
        const pathHint = onboardingSnapshot?.lastError?.code === "path_not_configured"
          ? onboardingSnapshot.lastError.detail?.trim()
          : "";
        if (pathHint) {
          await navigator.clipboard.writeText(pathHint).catch(() => {});
        }
        await openUrl("https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/path").catch(() => {});
      } else if (nextAction === "start_login") {
        setOnboardingSnapshot(await startOnboardingLoginProbe());
      }
    } finally {
      setOnboardingBusy(false);
    }
  }

  const onboardingPrimaryActionEnabled = !!onboardingSnapshot && ["start_install", "install_git", "retry", "retry_with_cmd", "open_manual_steps", "add_to_path", "start_login"].includes(onboardingSnapshot.nextAction);

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* 터미널 줄 상세 모달 */}
      {termDetail && (
        <div
          style={{ position: "fixed", inset: 0, background: "#00000066", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }}
          onClick={() => setTermDetail(null)}
        >
          <div
            style={{ background: "#1A1A1A", border: "2px solid #4DFF91", padding: "16px 20px", maxWidth: 340, width: "90%", fontFamily: "IBM Plex Mono, monospace" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ fontSize: 10, color: "#4DFF91", fontWeight: 700, marginBottom: 4 }}>▌ {termLines[0]?.text ?? "프로젝트"}</div>
            <div style={{ fontSize: 9, color: "#666", marginBottom: 10, borderBottom: "1px solid #333", paddingBottom: 8 }}>상세 내용</div>
            <div style={{ fontSize: 11, color: "#eee", lineHeight: 1.65, whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
              {termDetail}
            </div>
            <button
              type="button"
              onClick={() => setTermDetail(null)}
              style={{ marginTop: 14, fontSize: 10, background: "none", border: "1px solid #555", color: "#aaa", padding: "4px 12px", cursor: "pointer", fontFamily: "inherit" }}
            >
              닫기
            </button>
          </div>
        </div>
      )}

      {/* ─── 상단: 스크롤 가능 영역 ──────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "14px 20px 10px" }}>

        {/* 배지 + 헤더 */}
        <div style={{ marginBottom: 12 }}>
          <div className="badge" style={{ marginBottom: 10, fontSize: 10 }}>
            ▶ PIP INSTALL VIBELIGN
          </div>

          <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            {/* 타이틀 */}
            <div style={{ flex: 1 }}>
              <div className="heading-xl" style={{ marginBottom: 6, fontSize: 22 }}>
                <span style={{ background: "#F5621E", color: "#fff", padding: "0 5px", lineHeight: 1.3 }}>
                  커맨드 하나로
                </span>
                <br />
                바이브코딩 안전망
              </div>
              <div style={{ fontSize: 12, color: "#555", fontWeight: 600 }}>
                코드 몰라도 AI가 폭주 안 합니다
              </div>
            </div>

            {/* 터미널 */}
            <div className="terminal" style={{ width: 240, flexShrink: 0, padding: "10px 14px", height: 136, overflow: "hidden", boxSizing: "border-box" }}>
              <div className="terminal-header" style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 4 }}>
                <div className="terminal-dot red" />
                <div className="terminal-dot yellow" />
                <div className="terminal-dot green" />
                {recentDirs.length > 1 && (
                  <>
                    <div style={{ flex: 1 }} />
                    <button
                      onClick={() => setSummaryIdx((i) => (i - 1 + recentDirs.length) % recentDirs.length)}
                      style={{ background: "none", border: "none", color: "#888", cursor: "pointer", fontSize: 10, padding: "0 2px", lineHeight: 1 }}
                    >◀</button>
                    <span style={{ fontSize: 9, color: "#666" }}>{summaryIdx + 1}/{recentDirs.length}</span>
                    <button
                      onClick={() => setSummaryIdx((i) => (i + 1) % recentDirs.length)}
                      style={{ background: "none", border: "none", color: "#888", cursor: "pointer", fontSize: 10, padding: "0 2px", lineHeight: 1 }}
                    >▶</button>
                  </>
                )}
              </div>
              {termLines.slice(0, animStep).map((line, i) => (
                <div
                  key={i}
                  style={{ lineHeight: 1.6, cursor: line.detail ? "pointer" : "default", borderRadius: 2 }}
                  title={line.detail ? "클릭하면 자세히 보기" : undefined}
                  onClick={() => line.detail && setTermDetail(line.detail)}
                  onMouseEnter={(e) => { if (line.detail) e.currentTarget.style.background = "#ffffff18"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = ""; }}
                >
                  {line.type === "prompt"
                    ? <span><span className="terminal-prompt">$ </span>{line.text}</span>
                    : line.type === "check"
                    ? <span><span className="terminal-check">✓ </span>{line.text}</span>
                    : <span><span style={{ color: "#4D9FFF", fontWeight: 700 }}>→ </span>{line.text}</span>}
                </div>
              ))}
              {animStep < termLines.length && (
                <span style={{ color: "#4DFF91", fontWeight: 700 }}>▌</span>
              )}
            </div>
          </div>
        </div>

        {/* Git 미설치 안내 */}
        {gitInstalled === false && (() => {
          const ua = navigator.userAgent.toLowerCase();
          const isWin = ua.includes("win");
          const isMac = ua.includes("mac");
          const installCmd = isWin ? null : isMac ? "brew install git" : "sudo apt install git";
          const downloadUrl = isWin
            ? "https://git-scm.com/download/win"
            : isMac
            ? "https://git-scm.com/download/mac"
            : "https://git-scm.com/download/linux";
          return (
            <div style={{ border: "2px solid #FFD166", background: "#FFD16611", padding: "10px 14px", marginBottom: 8, fontSize: 11 }}>
              <div style={{ fontWeight: 800, color: "#B8860B", marginBottom: 6 }}>⚠ Git이 설치되지 않았어요</div>
              <div style={{ color: "#555", marginBottom: 8, lineHeight: 1.55 }}>
                일부 기능(시크릿 검사 등)에 Git이 필요해요. 핵심 기능은 Git 없이도 사용 가능합니다.
              </div>
              {installCmd && (
                <div style={{ fontFamily: "IBM Plex Mono, monospace", background: "#1A1A1A", color: "#4DFF91", padding: "6px 10px", fontSize: 10, marginBottom: 8 }}>
                  $ {installCmd}
                </div>
              )}
              <button
                type="button"
                onClick={() => openUrl(downloadUrl).catch(() => {})}
                style={{ fontSize: 10, fontWeight: 700, padding: "4px 12px", border: "2px solid #1A1A1A", background: "#FFD166", color: "#1A1A1A", cursor: "pointer" }}
              >
                Git 다운로드 ↗
              </button>
            </div>
          );
        })()}

        {onboardingSnapshot?.os === "macos" && xcodeCltInstalled === false && (
          <div style={{ border: "2px solid #FFD166", background: "#FFD16611", padding: "10px 14px", marginBottom: 8, fontSize: 11 }}>
            <div style={{ fontWeight: 800, color: "#B8860B", marginBottom: 6 }}>⚠ Xcode Command Line Tools 가 없을 수 있어요</div>
            <div style={{ color: "#555", marginBottom: 8, lineHeight: 1.55 }}>
              설치가 잘 되면 무시해도 괜찮아요. 만약 install.sh 가 `git` 또는 `curl` 을 못 찾으면 아래 명령을 터미널에서 한 번 실행해 주세요.
            </div>
            <div style={{ fontFamily: "IBM Plex Mono, monospace", background: "#1A1A1A", color: "#4DFF91", padding: "6px 10px", fontSize: 10 }}>
              $ xcode-select --install
            </div>
          </div>
        )}

        {onboardingSnapshot && (
          <div
            style={{
              border: "2px solid #1A1A1A",
              background: onboardingSnapshot.state === "success" ? "#F2FFF7" : "#FFF8E8",
              padding: "10px 14px",
              marginBottom: 10,
            }}
          >
            <div style={{ fontSize: 10, fontWeight: 800, color: "#666", marginBottom: 5 }}>
              CLAUDE CODE ONBOARDING
            </div>
            <div style={{ fontSize: 14, fontWeight: 800, color: "#1A1A1A", marginBottom: 4 }}>
              {onboardingSnapshot.headline}
            </div>
            {onboardingSnapshot.detail && (
              <div style={{ fontSize: 11, color: "#555", lineHeight: 1.6, marginBottom: 8 }}>
                {onboardingSnapshot.detail}
              </div>
            )}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: onboardingProgress || onboardingSnapshot.lastError ? 8 : 0 }}>
              <span className="badge" style={{ fontSize: 10 }}>state: {onboardingSnapshot.state}</span>
              <span className="badge" style={{ fontSize: 10 }}>os: {onboardingSnapshot.os}</span>
              <span className="badge" style={{ fontSize: 10 }}>path: {onboardingSnapshot.installPathKind}</span>
              <span className="badge" style={{ fontSize: 10 }}>next: {onboardingSnapshot.nextAction}</span>
            </div>
            {onboardingProgress && (
              <div style={{ fontSize: 11, color: "#555", marginBottom: onboardingSnapshot.lastError ? 6 : 8 }}>
                진행 상태: {onboardingProgress.phase} / {onboardingProgress.stepId} / {onboardingProgress.status} — {onboardingProgress.message}
              </div>
            )}
            {onboardingSnapshot.lastError && (
              <div style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 11, color: "#A14B00", lineHeight: 1.55, fontWeight: 700, marginBottom: onboardingSnapshot.lastError.detail ? 4 : 0 }}>
                  {onboardingSnapshot.lastError.summary}
                </div>
                {onboardingSnapshot.lastError.detail && (
                  <div style={{ fontSize: 10, color: "#8A5A00", lineHeight: 1.6 }}>
                    {onboardingSnapshot.lastError.detail}
                  </div>
                )}
              </div>
            )}
            {(onboardingLogs.trim() || onboardingSnapshot?.logsAvailable || onboardingSnapshot?.state === "installing_native" || onboardingSnapshot?.state === "installing_wsl" || onboardingSnapshot?.state === "verifying_shells" || onboardingSnapshot?.state === "probing_login") && (
              <div style={{ marginBottom: onboardingPrimaryActionEnabled ? 8 : 0 }}>
                <button
                  type="button"
                  onClick={() => setOnboardingLogsOpen((open) => !open)}
                  style={{
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "4px 10px",
                    border: "2px solid #1A1A1A",
                    background: "#fff",
                    color: "#1A1A1A",
                    cursor: "pointer",
                    marginBottom: onboardingLogsOpen ? 8 : 0,
                  }}
                >
                  {onboardingLogsOpen ? "설치 로그 숨기기" : "설치 로그 보기"}
                </button>
                {onboardingLogsOpen && (
                  <div
                    style={{
                      border: "2px solid #1A1A1A",
                      background: "#111",
                      color: "#4DFF91",
                      fontFamily: "IBM Plex Mono, monospace",
                      fontSize: 10,
                      lineHeight: 1.6,
                      padding: "10px 12px",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                      maxHeight: 420,
                      minHeight: 200,
                      overflowY: "auto",
                    }}
                  >
                    {onboardingLogs || "로그 수집 중… (설치 스크립트가 첫 줄을 내보낼 때까지 기다리는 중이에요)"}
                  </div>
                )}
              </div>
            )}
            {((onboardingPrimaryActionEnabled && onboardingSnapshot.primaryButtonLabel) || ((onboardingSnapshot.os === "windows" || onboardingSnapshot.os === "macos") && onboardingSnapshot.state !== "idle" && onboardingSnapshot.state !== "diagnosing")) && (
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                {onboardingPrimaryActionEnabled && onboardingSnapshot.primaryButtonLabel && (
                  <button
                    type="button"
                    onClick={() => handleOnboardingPrimaryAction(onboardingSnapshot.nextAction)}
                    disabled={onboardingBusy}
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      padding: "5px 12px",
                      border: "2px solid #1A1A1A",
                      background: onboardingBusy ? "#DDD" : "#F5621E",
                      color: onboardingBusy ? "#666" : "#fff",
                      cursor: onboardingBusy ? "default" : "pointer",
                    }}
                  >
                    {onboardingBusy ? "처리 중..." : onboardingSnapshot.primaryButtonLabel}
                  </button>
                )}
                {(onboardingSnapshot.os === "windows" || onboardingSnapshot.os === "macos") && onboardingSnapshot.state !== "idle" && onboardingSnapshot.state !== "diagnosing" && (
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={async () => {
                        const isMac = onboardingSnapshot.os === "macos";
                        const confirmMsg = isMac
                          ? "Claude Code 를 완전히 삭제할까요?\n\n바이너리·설정·PATH 추가 블록까지 모두 정리해요.\n되돌릴 수 없어요. 계속할까요?"
                          : "Claude Code 를 완전히 삭제할까요?\n\n네이티브(cmd/PowerShell) + WSL 양쪽 모두 삭제해요.\n되돌릴 수 없어요. 계속할까요?";
                        const ok = window.confirm(confirmMsg);
                        if (!ok) return;
                        setOnboardingBusy(true);
                        try {
                          setOnboardingSnapshot(await uninstallClaudeCode("all"));
                        } finally {
                          setOnboardingBusy(false);
                        }
                      }}
                      disabled={onboardingBusy}
                      style={{
                        fontSize: 10,
                        fontWeight: 700,
                        padding: "5px 12px",
                        border: "2px solid #A14B00",
                        background: "#fff",
                        color: "#A14B00",
                        cursor: onboardingBusy ? "default" : "pointer",
                      }}
                    >
                      {onboardingSnapshot.os === "macos" ? "Claude Code 삭제" : "전체 삭제"}
                    </button>
                    {onboardingSnapshot.os === "windows" && onboardingSnapshot.diagnostics.wslAvailable && (
                      <>
                        <button
                          type="button"
                          onClick={async () => {
                            const ok = window.confirm("네이티브(cmd/PowerShell) 트랙만 삭제할까요?\nWSL 쪽 Claude 는 유지돼요.");
                            if (!ok) return;
                            setOnboardingBusy(true);
                            try {
                              setOnboardingSnapshot(await uninstallClaudeCode("native"));
                            } finally {
                              setOnboardingBusy(false);
                            }
                          }}
                          disabled={onboardingBusy}
                          style={{
                            fontSize: 10,
                            fontWeight: 600,
                            padding: "5px 10px",
                            border: "1px solid #A14B00",
                            background: "#fff",
                            color: "#A14B00",
                            cursor: onboardingBusy ? "default" : "pointer",
                          }}
                        >
                          네이티브만 삭제
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            const ok = window.confirm("WSL 트랙만 삭제할까요?\ncmd/PowerShell 쪽 Claude 는 유지돼요.");
                            if (!ok) return;
                            setOnboardingBusy(true);
                            try {
                              setOnboardingSnapshot(await uninstallClaudeCode("wsl"));
                            } finally {
                              setOnboardingBusy(false);
                            }
                          }}
                          disabled={onboardingBusy}
                          style={{
                            fontSize: 10,
                            fontWeight: 600,
                            padding: "5px 10px",
                            border: "1px solid #A14B00",
                            background: "#fff",
                            color: "#A14B00",
                            cursor: onboardingBusy ? "default" : "pointer",
                          }}
                        >
                          WSL만 삭제
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 기능 카드 그리드 */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
          {FEATURE_CARDS.map((card) => (
            <div className="feature-card" key={card.icon}>
              <div className="feature-card-header" style={{ background: card.color + "18", padding: "8px 12px" }}>
                <div className="feature-card-icon"
                  style={{ background: card.color, color: "#fff", borderColor: card.color, width: 24, height: 24, fontSize: 12 }}>
                  {card.icon}
                </div>
                <div style={{ fontWeight: 700, fontSize: 11 }}>{card.title}</div>
              </div>
              <div className="feature-card-body" style={{ padding: "6px 12px", fontSize: 11 }}>{card.desc}</div>
            </div>
          ))}
        </div>

        <div className="feature-card" style={{ marginTop: 8, height: "auto" }}>
          <div
            className="feature-card-header"
            style={{ background: "#4D9FFF18", padding: "8px 12px", cursor: "pointer" }}
            onClick={() => setHelpOpen((o) => !o)}
          >
            <div
              className="feature-card-icon"
              style={{
                background: "#4D9FFF",
                color: "#fff",
                borderColor: "#4D9FFF",
                width: 24,
                height: 24,
                fontSize: 12,
                fontWeight: 900,
              }}
            >
              ?
            </div>
            <div style={{ fontWeight: 700, fontSize: 11, flex: 1 }}>도움말 질문하기</div>
            {helpOpen && <div style={{ fontSize: 10, color: "#666", fontWeight: 700 }}>엔터로 답하기</div>}
            <div style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>{helpOpen ? "▲" : "▼"}</div>
          </div>
          {helpOpen && <div className="feature-card-body" style={{ padding: "10px 12px" }}>
            <div style={{ fontSize: 11, color: "#444", lineHeight: 1.5, marginBottom: 8 }}>
              궁금한 걸 그냥 말해 보세요. 예: “이 툴로 뭘 할 수 있어?”
            </div>
            <input
              className="input-field"
              value={helpQuestion}
              onChange={(e) => setHelpQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleHelpAsk();
                }
              }}
              placeholder="예: 이 툴로 뭘 할 수 있어?"
              style={{ width: "100%", marginBottom: 8, fontSize: 11, boxSizing: "border-box" }}
            />
            <button
              type="button"
              className="btn btn-sm"
              disabled={helpLoading}
              onClick={handleHelpAsk}
              style={{ background: "#4D9FFF", color: "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
            >
              {helpLoading ? "생각 중..." : "답하기 ▶"}
            </button>
            <div
              style={{
                marginTop: 10,
                padding: "10px 12px",
                border: "2px solid #1A1A1A",
                background: "#fff",
                fontSize: 11,
                lineHeight: 1.55,
                whiteSpace: "pre-wrap",
                color: "#1A1A1A",
              }}
            >
              {helpAnswer}
            </div>
          </div>}
        </div>

        {/* 바이브라인 GitHub 카드 */}
        <div className="feature-card" style={{ cursor: "default", height: "auto" }}>
          <div
            className="feature-card-header"
            style={{ background: "#24292f18", padding: "8px 12px", display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}
            onClick={() => setGithubOpen((o) => !o)}
          >
            <div
              className="feature-card-icon"
              style={{
                background: "#24292f",
                color: "#fff",
                borderColor: "#24292f",
                width: 24,
                height: 24,
                fontSize: 10,
                fontWeight: 900,
              }}
            >
              GH
            </div>
            <div style={{ fontWeight: 700, fontSize: 11, flex: 1 }}>바이브라인 깃허브</div>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              title="Threads (@jongjatdon)"
              aria-label="Threads 프로필 열기"
              style={{
                ...githubCardHeaderBtnStyle,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
              onClick={(e) => {
                e.stopPropagation();
                openUrl(VIBELIGN_THREADS_PROFILE_URL).catch(() => {});
              }}
            >
              <ThreadsIcon size={14} />
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={githubCardHeaderBtnStyle}
              onClick={(e) => {
                e.stopPropagation();
                setGithubOpen((o) => !o);
              }}
            >
              선택
            </button>
            <div style={{ fontSize: 11, color: "#666", flexShrink: 0 }}>{githubOpen ? "▲" : "▼"}</div>
          </div>
          {githubOpen && (
            <div className="feature-card-body" style={{ padding: "10px 12px" }}>
              <div style={{ fontSize: 10, color: "#666", marginBottom: 8, lineHeight: 1.45 }}>
                소스 코드와 이슈는 GitHub에서 확인할 수 있어요. 아래 주소를 누르면 브라우저가 열려요.
              </div>
              <button
                type="button"
                onClick={() => openUrl(VIBELIGN_GITHUB_URL).catch(() => {})}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  fontFamily: "IBM Plex Mono, monospace",
                  fontSize: 10,
                  fontWeight: 700,
                  color: "#0969da",
                  background: "#fff",
                  border: "2px solid #1A1A1A",
                  padding: "8px 10px",
                  cursor: "pointer",
                  wordBreak: "break-all",
                  boxSizing: "border-box",
                }}
              >
                {VIBELIGN_GITHUB_URL}
              </button>
            </div>
          )}
        </div>

        {/* 바이브라인 첫걸음 — 아코디언 + 스텝 */}
        <div
          className="feature-card"
          style={{ cursor: "pointer", marginTop: 8, height: "auto" }}
          onClick={() => setGuideOpen((o) => !o)}
        >
          <div className="feature-card-header" style={{ background: "#F5621E18", padding: "8px 12px" }}>
            <div
              className="feature-card-icon"
              style={{
                background: "#F5621E",
                color: "#fff",
                borderColor: "#F5621E",
                width: 24,
                height: 24,
                fontSize: 12,
                fontWeight: 900,
              }}
            >
              📖
            </div>
            <div style={{ fontWeight: 700, fontSize: 11, flex: 1 }}>바이브라인 첫걸음</div>
            <div style={{ fontSize: 10, color: "#888", fontWeight: 700 }}>
              {guideStep + 1}/{ONBOARDING_GUIDE_STEPS.length}
            </div>
            <div style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>{guideOpen ? "▲" : "▼"}</div>
          </div>
          {guideOpen && (
            <div
              className="feature-card-body"
              style={{ padding: "10px 12px 12px" }}
              onClick={(e) => e.stopPropagation()}
            >
              {(() => {
                const step = ONBOARDING_GUIDE_STEPS[guideStep]!;
                return (
                  <>
                    <div style={{ fontWeight: 800, fontSize: 13, marginBottom: 8, color: "#1A1A1A" }}>
                      {step.title}
                    </div>
                    {step.lines.map((line, i) => (
                      <div key={i} style={{ fontSize: 11, color: "#444", lineHeight: 1.55, marginBottom: 6 }}>
                        {line}
                      </div>
                    ))}
                    {step.bullets && step.bullets.length > 0 && (
                      <ul style={{ margin: "6px 0 0 0", paddingLeft: 18, fontSize: 11, color: "#444", lineHeight: 1.5 }}>
                        {step.bullets.map((b, i) => (
                          <li key={i} style={{ marginBottom: 4 }}>{b}</li>
                        ))}
                      </ul>
                    )}
                    {step.code && (
                      <pre
                        style={{
                          margin: "8px 0 0 0",
                          padding: "8px 10px",
                          fontFamily: "IBM Plex Mono, monospace",
                          fontSize: 10,
                          background: "#fff",
                          border: "2px solid #1A1A1A",
                          color: "#1A1A1A",
                        }}
                      >
                        {step.code}
                      </pre>
                    )}
                    {step.hint && (
                      <div style={{ fontSize: 10, color: "#888", fontWeight: 600, marginTop: 8, lineHeight: 1.45 }}>
                        💡 {step.hint}
                      </div>
                    )}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        marginTop: 12,
                        flexWrap: "wrap",
                      }}
                    >
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: 10, border: "2px solid #1A1A1A", minWidth: 72 }}
                        disabled={guideStep <= 0}
                        onClick={() => setGuideStep((s) => Math.max(0, s - 1))}
                      >
                        이전
                      </button>
                      <div style={{ display: "flex", alignItems: "center", gap: 5, flex: 1, justifyContent: "center", flexWrap: "wrap" }}>
                        {ONBOARDING_GUIDE_STEPS.map((_, i) => (
                          <button
                            key={i}
                            type="button"
                            aria-label={`${i + 1}단계`}
                            onClick={() => setGuideStep(i)}
                            style={{
                              width: 8,
                              height: 8,
                              padding: 0,
                              border: "2px solid #1A1A1A",
                              borderRadius: 999,
                              background: i === guideStep ? "#F5621E" : "#fff",
                              cursor: "pointer",
                              flexShrink: 0,
                            }}
                          />
                        ))}
                      </div>
                      <button
                        type="button"
                        className="btn btn-sm"
                        style={{
                          fontSize: 10,
                          background: "#F5621E",
                          color: "#fff",
                          border: "2px solid #1A1A1A",
                          minWidth: 72,
                        }}
                        disabled={guideStep >= ONBOARDING_GUIDE_STEPS.length - 1}
                        onClick={() =>
                          setGuideStep((s) => Math.min(ONBOARDING_GUIDE_STEPS.length - 1, s + 1))
                        }
                      >
                        다음
                      </button>
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </div>
      </div>

      {/* ─── 하단: 항상 보이는 고정 영역 ────────────────────────── */}
      <div style={{ flexShrink: 0, borderTop: "2px solid #1A1A1A", background: "var(--bg)" }}>

        {/* RECENT 섹션 */}
        {recentDirs.length > 0 && onResume && (
          <div style={{ borderBottom: "2px solid #1A1A1A" }}>
            <div
              style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 20px", cursor: "pointer", background: "#4D9FFF11" }}
              onClick={() => setRecentOpen((o) => !o)}
            >
              <span style={{ fontSize: 11, color: "#4D9FFF", fontWeight: 900 }}>⊞</span>
              <span style={{ fontSize: 11, fontWeight: 700, flex: 1 }}>최근 프로젝트</span>
              <span style={{ fontSize: 10, color: "#4D9FFF", fontWeight: 700, marginRight: 6 }}>{recentDirs.length}개</span>
              <span style={{ fontSize: 11, color: "#666" }}>{recentOpen ? "▲" : "▼"}</span>
            </div>
            {recentOpen && recentDirs.map((dir, i) => (
              <div
                key={dir}
                onClick={() => onResume(dir)}
                style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 20px", cursor: "pointer", borderTop: "1px solid #1A1A1A" }}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#4D9FFF11")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "")}
              >
                <span style={{ fontWeight: 900, fontSize: 12, color: "#4D9FFF", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 140 }}>
                  {dir.split("/").filter(Boolean).at(-1)}
                </span>
                {i === 0 && (
                  <span style={{ fontSize: 9, fontWeight: 700, color: "#4D9FFF", background: "#4D9FFF22", padding: "1px 5px", border: "1px solid #4D9FFF55", flexShrink: 0 }}>
                    진행 중
                  </span>
                )}
                <span style={{ fontSize: 10, color: "#555", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{dir}</span>
                {onRemoveRecent && (
                  <button
                    type="button"
                    aria-label={`${dir} 최근 프로젝트 목록에서 제거`}
                    title="최근 프로젝트 목록에서 제거 (프로젝트 파일은 삭제되지 않음)"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveRecent(dir);
                    }}
                    style={{
                      fontSize: 10,
                      fontWeight: 900,
                      color: "#888",
                      border: "1px solid #1A1A1A",
                      background: "transparent",
                      width: 18,
                      height: 18,
                      lineHeight: "16px",
                      textAlign: "center",
                      cursor: "pointer",
                      flexShrink: 0,
                    }}
                  >
                    ×
                  </button>
                )}
                <span style={{ fontSize: 11, color: "#4D9FFF", fontWeight: 700, flexShrink: 0 }}>▶</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ padding: "12px 20px 14px" }}>
        {/* VIB 상태 + 폴더 선택 */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <span className="label" style={{ flexShrink: 0 }}>VIB CLI</span>
          {vibChecking ? (
            <span className="spinner" />
          ) : vibFound ? (
            <span className="badge" style={{ fontSize: 10, background: "#4DFF91", color: "#1A1A1A" }}>발견됨</span>
          ) : (
            <span className="badge" style={{ fontSize: 10, background: "#FF4D4D" }}>미설치 — pip install vibelign</span>
          )}
          <div style={{ flex: 1 }} />
          <input
            className="input-field"
            value={selectedDir}
            onChange={(e) => setSelectedDir(e.target.value)}
            placeholder="프로젝트 폴더 경로..."
            style={{ flex: 2, maxWidth: 320 }}
          />
          <button className="btn btn-ghost btn-sm" onClick={pickFolder} style={{ flexShrink: 0 }}>탐색</button>
        </div>

        {/* AI 도구 선택 */}
        <div style={{ marginBottom: 10 }}>
          <div style={{ fontSize: 11, color: "#888", marginBottom: 6 }}>
            사용하는 AI 도구를 선택하세요 <span style={{ color: "#555" }}>(선택 안 하면 기본 설정만 생성)</span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {(["claude", "cursor", "opencode", "antigravity", "codex"] as const).map((tool) => {
              const label: Record<string, string> = {
                claude: "Claude Code", cursor: "Cursor", opencode: "OpenCode",
                antigravity: "Antigravity", codex: "Codex",
              };
              const active = selectedTools.includes(tool);
              return (
                <button
                  key={tool}
                  onClick={() => setSelectedTools(prev =>
                    prev.includes(tool) ? prev.filter(t => t !== tool) : [...prev, tool]
                  )}
                  style={{
                    fontSize: 11, fontWeight: 700, padding: "4px 10px",
                    border: `2px solid ${active ? "#F5621E" : "#333"}`,
                    background: active ? "#F5621E" : "transparent",
                    color: active ? "#fff" : "#aaa",
                    cursor: "pointer",
                  }}
                >
                  {label[tool]}
                </button>
              );
            })}
            {(() => {
              const ALL_TOOLS = ["claude", "cursor", "opencode", "antigravity", "codex"];
              const allSelected = ALL_TOOLS.every(t => selectedTools.includes(t));
              return (
                <button
                  onClick={() => setSelectedTools(allSelected ? [] : ALL_TOOLS)}
                  style={{
                    fontSize: 11, fontWeight: 700, padding: "4px 10px",
                    border: `2px solid ${allSelected ? "#4DFF91" : "#333"}`,
                    background: allSelected ? "#4DFF91" : "transparent",
                    color: allSelected ? "#1A1A1A" : "#aaa",
                    cursor: "pointer",
                  }}
                >
                  {allSelected ? "전체 해제" : "전체 선택"}
                </button>
              );
            })()}
          </div>
        </div>

        {startError && (
          <div
            className="alert alert-error"
            style={{ margin: "10px 0 12px", padding: 12, fontSize: 11, whiteSpace: "pre-wrap" }}
          >
            시작 실패
            {"\n"}
            {startError}
          </div>
        )}

        <button
          className="btn btn-black"
          style={{ width: "100%", padding: "10px", fontSize: 13 }}
          disabled={!vibFound || !selectedDir || starting}
          onClick={handleStart}
        >
          {starting ? <><span className="spinner" style={{ marginRight: 8 }} />초기화 중...</> : "시작하기 ▶"}
        </button>
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: ONBOARDING_END ===
