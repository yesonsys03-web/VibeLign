// === ANCHOR: ONBOARDING_START ===
import { useState, useEffect, useRef } from "react";
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
  // 갸리카(🚗) 마스코트 클릭 루프:
  //   [차 안·말풍선 열림] →차클릭→ [차 안·말풍선 닫힘] →차클릭→ [차 오른쪽 밖 퇴장] →아무데나클릭→ [차 재진입] → …
  // carIn: 차가 화면 안(true)/오른쪽 밖(false). welcomeOpen/Mounted: 환영 말풍선 표시.
  const [carIn, setCarIn] = useState(true);
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [welcomeMounted, setWelcomeMounted] = useState(false);

  // 차가 들어와 급정거(약 1.7s)한 뒤 1초 쉬었다가 말풍선을 "뽁" 펼친다. 재진입(carIn false→true)에도 동일.
  useEffect(() => {
    if (!carIn) return;
    const t = setTimeout(() => { setWelcomeMounted(true); setWelcomeOpen(true); }, 2700);
    return () => clearTimeout(t);
  }, [carIn]);

  // 차가 나간 상태에서는 화면 아무 곳이나 한 번 클릭하면 처음 등장과 똑같이 다시 운전해 들어온다.
  // 퇴장을 부른 "그 클릭"이 이 리스너에 곧바로 잡혀 즉시 재진입해 버리는 걸 막으려고, 한 틱 미뤄 부착한다(self-trigger 방지). once 로 한 번만.
  useEffect(() => {
    if (carIn) return;
    const reenter = () => { setWelcomeMounted(false); setWelcomeOpen(false); setCarIn(true); };
    const id = window.setTimeout(() => window.addEventListener("click", reenter, { once: true }), 0);
    return () => { window.clearTimeout(id); window.removeEventListener("click", reenter); };
  }, [carIn]);

  // 차 클릭: 말풍선이 열려 있으면 먼저 접고(쏙), 이미 닫혀 있으면 차를 오른쪽 밖으로 내보낸다.
  const onCarClick = () => {
    if (welcomeOpen) {
      setWelcomeOpen(false); // suck → onAnimationEnd 에서 언마운트
    } else {
      setWelcomeMounted(false);
      setCarIn(false);
    }
  };

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
        <section style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <h1 className="heading-xl" style={{ fontSize: 24, margin: 0, textAlign: "center" }}>
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
          {/* 갸리카 운전 마스코트(환영) — 왼쪽에서 운전해 들어와 멈춘 뒤 말풍선 "뽁".
              차 클릭: 말풍선 접기 → (다시) 오른쪽 밖으로 퇴장. 나간 뒤 아무 곳이나 클릭하면 재진입(루프).
              key 를 carIn 으로 바꿔 토글마다 요소를 새로 마운트 → 진입/퇴장 CSS 애니메이션이 매번 다시 재생된다. */}
          <div key={carIn ? "gyari-in" : "gyari-out"} className={`gyari-car-wrap ${carIn ? "rollin" : "rollout"}`}>
            <button
              type="button"
              className="gyari-car tappable"
              title={welcomeOpen ? "말풍선 접기" : "갸리카 보내기"}
              aria-label="갸리카 길잡이"
              onClick={onCarClick}
            />
            {welcomeMounted && (
              <span className="gyari-bubble-slot">
                <span
                  className={`guide-bubble ${welcomeOpen ? "pop" : "suck"}`}
                  onAnimationEnd={() => { if (!welcomeOpen) setWelcomeMounted(false); }}
                >
                  <span className="em">👋</span> 안녕! 난 바이브라인 길잡이 🚗
                  <br />
                  <b>위 ＋</b>로 폴더 고르고 한 칸씩 같이 가자!
                </span>
              </span>
            )}
          </div>
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
