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
  const [claudeSetupOpen, setClaudeSetupOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [gitInstalled, setGitInstalled] = useState<boolean | null>(null);
  const [xcodeCltInstalled, setXcodeCltInstalled] = useState<boolean | null>(null);
  const [claudeInstalled, setClaudeInstalled] = useState<boolean | null>(null);
  const [onboardingSnapshot, setOnboardingSnapshot] = useState<OnboardingSnapshot | null>(null);
  const [startProgressLabels, setStartProgressLabels] = useState<string[]>([]);
  const [startStatusMessage, setStartStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    getVibPath().then((p) => { setVibFound(p); setVibChecking(false); });
    checkGitInstalled().then(setGitInstalled).catch(() => setGitInstalled(false));
    checkXcodeClt().then(setXcodeCltInstalled).catch(() => setXcodeCltInstalled(true));
    getOnboardingSnapshot().then(setOnboardingSnapshot).catch(() => setOnboardingSnapshot(null));
    // 실제 설치 여부로 시스템 상태를 표시하기 위해 claude 가 PATH 에 있는지 탐지한다.
    detectInstalledTools().then((tools) => setClaudeInstalled(tools.includes("claude"))).catch(() => setClaudeInstalled(false));

    // 앱이 포커스를 다시 받으면 사용자가 외부에서 Git/Claude 를 설치했을 수 있으므로 재검사한다.
    let active = true;
    const onFocus = () => {
      checkGitInstalled().then((ok) => { if (active) setGitInstalled(ok); }).catch(() => undefined);
      detectInstalledTools().then((tools) => { if (active) setClaudeInstalled(tools.includes("claude")); }).catch(() => undefined);
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

    const installedTools = await detectInstalledTools().catch(() => [] as string[]);
    const startArgs = installedTools.length > 0
      ? ["start", "--non-interactive", "--tools", installedTools.join(",")]
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
            claudeSetupOpen={claudeSetupOpen}
            inputRef={promptRef}
            onPromptChange={setPromptText}
            onPickFolder={pickFolder}
            onSubmit={handlePromptSubmit}
            onToggleClaudeSetup={() => setClaudeSetupOpen((open) => !open)}
          />
          <OnboardingStartProgress
            labels={startProgressLabels}
            statusMessage={startStatusMessage}
          />
          {claudeSetupOpen && <OnboardingClaudeSetup />}
          <button
            type="button"
            onClick={() => setAdvancedOpen((open) => !open)}
            style={{ border: "none", background: "transparent", color: "#555", fontSize: 12, fontWeight: 800, cursor: "pointer" }}
          >
            {advancedOpen ? "고급 설정 숨기기" : "고급 설정 보기"}
          </button>
        </section>

        <OnboardingSystemWarnings
          gitInstalled={gitInstalled}
          xcodeCltInstalled={xcodeCltInstalled}
          onboardingSnapshot={onboardingSnapshot}
        />

        {advancedOpen && (
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
        )}
      </main>
    </div>
  );
}
// === ANCHOR: ONBOARDING_END ===
