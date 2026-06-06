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
import { OnboardingInputBar } from "./onboarding/OnboardingInputBar";
import { OnboardingStartProgress } from "./onboarding/OnboardingStartProgress";
import { OnboardingSystemWarnings } from "./onboarding/OnboardingSystemWarnings";
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
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", background: "var(--bg)", overflow: "auto" }}>
      <main style={{ width: "min(860px, calc(100% - 32px))", margin: "0 auto", padding: "72px 0 28px", flex: 1 }}>
        <section style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
          <h1 className="heading-xl" style={{ fontSize: 24, margin: 0, textAlign: "center" }}>
            계획부터, 바이브까지, 되돌림은 언제든
          </h1>
          <p style={{ margin: 0, textAlign: "center", color: "#666", fontSize: 14, fontWeight: 600 }}>
            무엇을 만들지 한 줄로 적어보세요. 나머지는 정렬해 드릴게요
          </p>
          <OnboardingInputBar
            promptText={promptText}
            selectedDirName={selectedDir ? selectedDirName : ""}
            folderHint={folderHint}
            inputRef={promptRef}
            onPromptChange={setPromptText}
            onPickFolder={pickFolder}
            onSubmit={handlePromptSubmit}
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
            <div style={{ width: "min(720px, 100%)", display: "grid", gap: 14 }}>
              <div style={{ display: "grid", gap: 6 }}>
                <div style={{ fontSize: 11, color: "#888", fontWeight: 700 }}>
                  MCP 자동 설정 <span style={{ color: "#aaa", fontWeight: 600 }}>(설치된 도구는 자동 선택돼요)</span>
                </div>
                <ToolSetupSelector detected={detectedTools} selected={selectedTools} onChange={setSelectedTools} />
              </div>
              <OnboardingClaudeSetup />
              <OnboardingSystemWarnings
                gitInstalled={gitInstalled}
                xcodeCltInstalled={xcodeCltInstalled}
                onboardingSnapshot={onboardingSnapshot}
              />
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
          )}
        </section>
      </main>
    </div>
  );
}
// === ANCHOR: ONBOARDING_END ===
