// === ANCHOR: ONBOARDING_START ===
import { useState, useEffect, useLayoutEffect, useRef, type CSSProperties } from "react";
import { open as openDialog } from "@tauri-apps/plugin-dialog";
import {
  getVibPath,
  checkGitInstalled,
  checkXcodeClt,
  detectInstalledTools,
  getOnboardingSnapshot,
  runVibWithProgress,
  startWatch,
  type VibProgressEvent,
  type OnboardingSnapshot,
} from "../lib/vib";
import { OnboardingAdvancedPanel } from "./onboarding/OnboardingAdvancedPanel";
import { OnboardingClaudeSetup } from "./onboarding/OnboardingClaudeSetup";
import { OnboardingInputBar, type OnboardingCoach } from "./onboarding/OnboardingInputBar";
import { OnboardingStartProgress } from "./onboarding/OnboardingStartProgress";
import { OnboardingGitWarning, OnboardingSystemWarnings } from "./onboarding/OnboardingSystemWarnings";
import { ToolSetupSelector } from "../components/ToolSetupSelector";

interface OnboardingProps {
  readonly onComplete: (projectDir: string, apiKey: string | null) => void;
  readonly onPlanRequest?: (projectDir: string, prompt: string) => Promise<void>;
  readonly onResume?: (dir: string) => void;
  readonly onRemoveRecent?: (dir: string) => void;
  readonly recentDirs?: readonly string[];
}

export default function Onboarding({ onComplete, onPlanRequest, onResume, onRemoveRecent, recentDirs = [] }: OnboardingProps) {
  const [vibFound, setVibFound] = useState<string | null>(null);
  const [vibChecking, setVibChecking] = useState(true);
  const [selectedDir, setSelectedDir] = useState("");
  const [promptText, setPromptText] = useState("");
  const promptRef = useRef<HTMLTextAreaElement>(null);
  const [folderHint, setFolderHint] = useState<string | null>(null);
  const [setupOpen, setSetupOpen] = useState(false);
  const [gitInstalled, setGitInstalled] = useState<boolean | null>(null);
  const [xcodeCltInstalled, setXcodeCltInstalled] = useState<boolean | null>(null);
  const [claudeInstalled, setClaudeInstalled] = useState<boolean | null>(null);
  const [detectedTools, setDetectedTools] = useState<string[] | null>(null);
  const [selectedTools, setSelectedTools] = useState<Set<string>>(new Set());
  const [onboardingSnapshot, setOnboardingSnapshot] = useState<OnboardingSnapshot | null>(null);
  const [startProgressLabels, setStartProgressLabels] = useState<string[]>([]);
  const [startStatusMessage, setStartStatusMessage] = useState<string | null>(null);
  // 게임형 코치마크(W3) — 첫 화면 "folder", 폴더 선택 후 "prompt", 시작/닫기 시 null.
  const [coach, setCoach] = useState<OnboardingCoach>("folder");
  // 환영 말풍선(W2) 접기/펼치기 — 마스코트(🧭) 탭으로 토글. open=표시, mounted=DOM 잔류(나갈 때 "쏙" 후 언마운트).
  const [welcomeOpen, setWelcomeOpen] = useState(true);
  // 앱 실행 시 마스코트가 굴러와 멈춘 뒤에 말풍선을 펼치므로 처음엔 미마운트.
  const [welcomeMounted, setWelcomeMounted] = useState(false);
  // 마스코트가 멈출 가로 위치 — 타이틀 "계" 글자 중심에 맞추는 오프셋(측정 기반, 창 크기 무관).
  const [welcomeShift, setWelcomeShift] = useState(0);
  // 굴러 들어오기 시작하는 가로 거리(px, 음수) — "프레임 왼쪽 끝 바로 밖"으로 측정해 둔다(처음엔 안 보임).
  const [rollFrom, setRollFrom] = useState(-600);
  const sectionRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const toggleWelcome = () => {
    if (welcomeOpen) {
      setWelcomeOpen(false); // suck-in 애니메이션 → onAnimationEnd 에서 언마운트
    } else {
      setWelcomeMounted(true);
      setWelcomeOpen(true);
    }
  };

  // 마스코트가 멈출 지점을 타이틀 "계" 위로 정렬 — 페인트 전 측정(useLayoutEffect)이라 깜빡임 없음.
  // 마스코트 .big 폭 46px(border-box) → 중심은 좌측+23. 창 리사이즈에도 재정렬.
  useLayoutEffect(() => {
    const align = () => {
      const sec = sectionRef.current;
      const title = titleRef.current;
      if (!sec || !title?.firstChild) return;
      // 제목 텍스트의 첫 글자("계")만 Range 로 측정 — DOM(텍스트 노드)을 쪼개지 않는다.
      const range = document.createRange();
      range.setStart(title.firstChild, 0);
      range.setEnd(title.firstChild, 1);
      // jsdom 등 비레이아웃 환경엔 Range.getBoundingClientRect 가 없다 — 정렬 생략.
      if (typeof range.getBoundingClientRect !== "function") return;
      const a = range.getBoundingClientRect();
      if (a.width === 0) return; // 레이아웃 측정 불가 — 정렬 생략
      const s = sec.getBoundingClientRect();
      const shift = Math.max(0, a.left + a.width / 2 - s.left - 23);
      setWelcomeShift(shift);
      // 마스코트 정지 지점의 화면상 왼쪽 x = 섹션좌측 + shift. 그보다 (자신 폭+여유)만큼 더 왼쪽,
      // 즉 프레임 끝 바로 밖에서 출발시킨다 → 등속 슬라이드 전체가 화면 안에서 보인다.
      setRollFrom(-(s.left + shift + 120));
    };
    align();
    window.addEventListener("resize", align);
    return () => window.removeEventListener("resize", align);
  }, []);

  // 굴러 들어오는 동안(약 1.2s)은 말풍선을 숨기고, 멈춘 뒤 한 템포(약 0.45s) 쉬었다가 "뽁" 펼친다(앱 실행 1회).
  useEffect(() => {
    const t = setTimeout(() => setWelcomeMounted(true), 1650);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    getVibPath().then((p) => { setVibFound(p); setVibChecking(false); });
    checkGitInstalled().then(setGitInstalled).catch(() => setGitInstalled(false));
    checkXcodeClt().then(setXcodeCltInstalled).catch(() => setXcodeCltInstalled(true));
    getOnboardingSnapshot().then(setOnboardingSnapshot).catch(() => setOnboardingSnapshot(null));
    // 설치된 AI 도구를 탐지해 시스템 상태 표시 + 도구 선택 기본값(설치된 것 자동 선택)에 쓴다.
    detectInstalledTools()
      .then((tools) => {
        setClaudeInstalled(tools.includes("claude"));
        setDetectedTools(tools);
        setSelectedTools(new Set(tools));
      })
      .catch(() => {
        setClaudeInstalled(false);
        setDetectedTools([]);
      });

    // 앱이 포커스를 다시 받으면 사용자가 외부에서 Git/Claude 를 설치했을 수 있으므로 재검사한다.
    let active = true;
    const onFocus = () => {
      checkGitInstalled().then((ok) => { if (active) setGitInstalled(ok); }).catch(() => undefined);
      detectInstalledTools().then((tools) => { if (active) { setClaudeInstalled(tools.includes("claude")); setDetectedTools(tools); } }).catch(() => undefined);
    };
    window.addEventListener("focus", onFocus);

    return () => {
      active = false;
      window.removeEventListener("focus", onFocus);
    };
  }, []);

  async function pickFolder() {
    const dir = await openDialog({ directory: true, multiple: false, title: "프로젝트 폴더 선택" });
    if (typeof dir === "string") {
      setSelectedDir(dir);
      setFolderHint(null);
      setCoach((c) => (c === "folder" ? "prompt" : c)); // 코치 1→2단계: 폴더 골랐으니 입력 안내로
      promptRef.current?.focus();
    }
  }

  function appendStartProgress(event: VibProgressEvent) {
    if (event.step !== "vib_start_progress" || !event.message) {
      return;
    }
    setStartProgressLabels((labels) => (
      labels.includes(event.message ?? "") ? labels : [...labels, event.message ?? ""]
    ));
  }

  async function handlePromptSubmit() {
    const prompt = promptText.trim().slice(0, 4000);
    if (!selectedDir) {
      setFolderHint("먼저 프로젝트 폴더를 선택해 주세요.");
      return;
    }
    setFolderHint(null);
    setCoach(null); // 시작하면 코치 인도 완료
    setStartStatusMessage(null);
    setStartProgressLabels([]);

    const tools = Array.from(selectedTools);
    const startArgs = tools.length > 0
      ? ["start", "--non-interactive", "--tools", tools.join(",")]
      : ["start", "--non-interactive"];
    const startResult = await runVibWithProgress(
      startArgs,
      selectedDir,
      undefined,
      appendStartProgress,
    );
    if (!startResult.ok) {
      setStartStatusMessage("시작 실패");
      return;
    }

    try {
      await startWatch(selectedDir);
    } catch {
      setStartStatusMessage("파일 변경 감시를 켜지 못했어요. 다시 켜기");
    }
    if (prompt && onPlanRequest) {
      await onPlanRequest(selectedDir, prompt);
      return;
    }
    onComplete(selectedDir, null);
  }

  const selectedDirName = selectedDir.split(/[\\/]/).filter(Boolean).at(-1) ?? selectedDir;

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", background: "var(--bg)", overflowY: "auto", overflowX: "hidden" }}>
      <main style={{ width: "min(860px, calc(100% - 32px))", margin: "0 auto", padding: setupOpen ? "20px 0 24px" : "72px 0 28px", flex: 1 }}>
        <section ref={sectionRef} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          {/* 환영 인사(W2) — 🧭 마스코트 말풍선. 앱 실행 시 마스코트가 "계" 위로 굴러와 멈춘 뒤 "뽁" 펼침.
              가운데 정렬 대신 좌측 정렬 + 측정 오프셋(welcomeShift)으로 마스코트를 "계"에 고정한다. */}
          <div className="onb-welcome" style={{ alignSelf: "flex-start", marginLeft: welcomeShift }}>
            <button
              type="button"
              className="guide-mascot big rollin tappable"
              style={{ "--roll-from": `${rollFrom}px` } as CSSProperties}
              title={welcomeOpen ? "말풍선 접기" : "말풍선 펼치기"}
              aria-expanded={welcomeOpen}
              aria-label="길잡이 말풍선 접기/펼치기"
              onClick={toggleWelcome}
            >
              🧭
            </button>
            {welcomeMounted && (
              <span
                className={`guide-bubble ${welcomeOpen ? "pop" : "suck"}`}
                onAnimationEnd={() => { if (!welcomeOpen) setWelcomeMounted(false); }}
              >
                <span className="em">👋</span> 안녕, 반가워! 난 바이브라인 길잡이 🧭
                <br />
                처음이어도 걱정 마 — <b>폴더 고르기</b>부터 <b>기획·코딩·확인·백업</b>까지 한 칸씩 같이 갈게. 시작은 아래 <b>＋</b>부터!
              </span>
            )}
          </div>
          <h1 ref={titleRef} className="heading-xl" style={{ fontSize: 24, margin: 0, textAlign: "center" }}>
            계획부터, 바이브까지, 되돌림은 언제든
          </h1>
          <p style={{ margin: 0, textAlign: "center", color: "#666", fontSize: 14, fontWeight: 600 }}>
            무엇을 만들지 한 줄로 적어보세요. 나머지는 정렬해 드릴게요
          </p>
          {gitInstalled === false && <OnboardingGitWarning />}
          <OnboardingInputBar
            promptText={promptText}
            selectedDirName={selectedDir ? selectedDirName : ""}
            folderHint={folderHint}
            inputRef={promptRef}
            onPromptChange={setPromptText}
            onPickFolder={pickFolder}
            onSubmit={handlePromptSubmit}
            coach={coach}
            onDismissCoach={() => setCoach(null)}
          />
          <OnboardingStartProgress
            labels={startProgressLabels}
            statusMessage={startStatusMessage}
          />
          <button
            type="button"
            aria-expanded={setupOpen}
            onClick={() => setSetupOpen((open) => !open)}
            style={{ border: "none", background: "transparent", color: "#555", fontSize: 12, fontWeight: 800, cursor: "pointer" }}
          >
            {setupOpen ? "▾" : "▸"} AI 도구 · 설치 · 시스템 상태
          </button>
          {setupOpen && (
            <div style={{ width: "min(860px, 100%)", display: "grid", gap: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, alignItems: "stretch" }}>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <OnboardingClaudeSetup
                    topContent={
                      <div style={{ display: "grid", gap: 6 }}>
                        <div style={{ fontSize: 11, color: "#1E7FB5", fontWeight: 800 }}>
                          MCP 자동 설정 <span style={{ color: "#7FB2CE", fontWeight: 600 }}>(설치된 도구는 자동 선택돼요)</span>
                        </div>
                        <ToolSetupSelector detected={detectedTools} selected={selectedTools} onChange={setSelectedTools} />
                      </div>
                    }
                  />
                </div>
                <div style={{ display: "flex", flexDirection: "column" }}>
                  <OnboardingAdvancedPanel
                    vibFound={vibFound}
                    vibChecking={vibChecking}
                    gitInstalled={gitInstalled}
                    xcodeCltInstalled={xcodeCltInstalled}
                    claudeInstalled={claudeInstalled}
                    onboardingSnapshot={onboardingSnapshot}
                    recentDirs={recentDirs}
                    onResume={onResume}
                    onRemoveRecent={onRemoveRecent}
                  />
                </div>
              </div>
              <OnboardingSystemWarnings
                gitInstalled={gitInstalled}
                xcodeCltInstalled={xcodeCltInstalled}
                onboardingSnapshot={onboardingSnapshot}
              />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
// === ANCHOR: ONBOARDING_END ===
