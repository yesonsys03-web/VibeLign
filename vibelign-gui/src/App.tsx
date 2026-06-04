// === ANCHOR: APP_START ===
import { useState, useEffect, Component, ReactNode, ErrorInfo } from "react";
import CustomTitleBar from "./components/CustomTitleBar";
import ScrollToTopButton from "./components/ScrollToTopButton";
import UpdateBanner from "./components/UpdateBanner";
import Onboarding from "./pages/Onboarding";
import PlanningRoom from "./pages/PlanningRoom";
import Doctor from "./pages/Doctor";
import Home from "./pages/Home";
import DocsViewer from "./pages/DocsViewer";
import CodeExplorer from "./pages/CodeExplorer";
import BackupDashboardPage from "./pages/BackupDashboard";
import ErrorLogs from "./pages/ErrorLogs";
import Settings from "./pages/Settings";
import { backupList, createPlanningChatSession, getEnvKeyStatus, getWatchErrors, loadApiKey, loadLatestPlanningChatSession, loadProviderApiKeys, loadRecentProjects, saveRecentProjects, startWatch, stopWatch, openFolder, type PlanningChatSessionResponse } from "./lib/vib";
import { installGuiErrorReporter, reportReactError, setErrorReporterProjectDir } from "./lib/errorReporter";
import "./styles/brutalism.css";
import "./App.css";

// ─── Error Boundary ────────────────────────────────────────────────────────────
class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    reportReactError(error, info.componentStack ?? undefined);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 20, fontFamily: "IBM Plex Mono, monospace", fontSize: 12 }}>
          <div style={{ background: "#FF4D4D", border: "2px solid #000", padding: 12, marginBottom: 12, color: "#fff", fontWeight: 700 }}>
            RENDER ERROR
          </div>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-all", background: "#1E2216", color: "#7DFF6B", padding: 12, border: "2px solid #000" }}>
            {this.state.error.message}
            {"\n\n"}
            {this.state.error.stack}
          </pre>
          <button
            style={{ marginTop: 12, padding: "8px 16px", border: "2px solid #000", background: "#FFE44D", fontWeight: 700, cursor: "pointer" }}
            onClick={() => this.setState({ error: null })}
          >
            재시도
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── App ──────────────────────────────────────────────────────────────────────
type Page = "home" | "manual" | "docs" | "code" | "doctor" | "backups" | "logs" | "settings" | "planning";

export default function App() {
  const [projectDir, setProjectDir] = useState<string | null>(null);
  const [recentDirs, setRecentDirs] = useState<string[]>([]);
  const [page, setPage] = useState<Page>("home");
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [providerKeys, setProviderKeys] = useState<Record<string, string>>({});
  const [envKeyStatus, setEnvKeyStatus] = useState<Record<string, boolean>>({});
  const [envKeyStatusLoaded, setEnvKeyStatusLoaded] = useState(false);
  const [prevPage, setPrevPage] = useState<Page>("home");
  const [settingsNotice, setSettingsNotice] = useState<string | null>(null);
  const [watchOn, setWatchOn] = useState(false);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<"manual" | "auto">("manual");
  const [planningPrompt, setPlanningPrompt] = useState("");
  const [planningResult, setPlanningResult] = useState<PlanningChatSessionResponse | null>(null);


  async function refreshAiKeys() {
    try {
      const [k, pk] = await Promise.all([loadApiKey(), loadProviderApiKeys()]);
      setApiKey(k ?? null);
      setProviderKeys(pk ?? {});
    } catch {
      /* ignore */
    }
  }

  function readableError(error: unknown): string {
    if (error instanceof Error) return error.message;
    return String(error);
  }

  useEffect(() => {
    installGuiErrorReporter();
    refreshAiKeys();
    getEnvKeyStatus()
      .then(setEnvKeyStatus)
      .catch(() => {})
      .finally(() => setEnvKeyStatusLoaded(true));
    loadRecentProjects().then(setRecentDirs).catch(() => {});
  }, []);

  useEffect(() => {
    setErrorReporterProjectDir(projectDir);
  }, [projectDir]);

  useEffect(() => {
    if (!projectDir) return;
    backupList(projectDir).catch(() => {});
  }, [projectDir]);

  useEffect(() => {
    if (!projectDir) {
      setWatchError(null);
      return;
    }
    getWatchErrors()
      .then((errors) => setWatchError(errors[0] ?? null))
      .catch((error: unknown) => setWatchError(readableError(error)));
  }, [projectDir, watchOn]);

  const hasGuiProviderKey = Object.values(providerKeys).some((v) => Boolean(v?.trim()));
  const hasAnyAiKey = Boolean(apiKey) || hasGuiProviderKey || Object.values(envKeyStatus).some(Boolean);

  function addToRecent(dir: string) {
    const next = [dir, ...recentDirs.filter((d) => d !== dir)].slice(0, 5);
    setRecentDirs(next);
    saveRecentProjects(next).catch(() => {});
  }

  function removeFromRecent(dir: string) {
    const next = recentDirs.filter((d) => d !== dir);
    setRecentDirs(next);
    saveRecentProjects(next).catch(() => {});
  }

  function openSettings(reason?: string) {
    setPrevPage(page === "settings" ? prevPage : page);
    setSettingsNotice(typeof reason === "string" ? reason : null);
    setPage("settings");
  }

  async function openPlanningRoom(dir: string, prompt: string) {
    const normalizedPrompt = prompt.trim().slice(0, 4000);
    if (!normalizedPrompt) return;
    addToRecent(dir);
    setProjectDir(dir);
    setPlanningPrompt(normalizedPrompt);
    setPlanningResult({
      ok: true,
      sessionId: null,
      prompt: normalizedPrompt,
      messages: [
        {
          id: "pending_initial",
          role: "user",
          personaId: null,
          content: normalizedPrompt,
          status: "pending",
          createdAt: new Date().toISOString(),
        },
      ],
    });
    setPage("planning");
    const result = await createPlanningChatSession({
      projectDir: dir,
      prompt: normalizedPrompt,
    });
    setPlanningResult(result);
  }

  async function retryWatch() {
    if (!projectDir) return;
    setWatchError(null);
    try {
      await startWatch(projectDir);
      setWatchOn(true);
      const errors = await getWatchErrors();
      setWatchError(errors[0] ?? null);
    } catch (error: unknown) {
      setWatchOn(false);
      setWatchError(readableError(error));
    }
  }

  async function resumeProject(dir: string) {
    addToRecent(dir);
    setProjectDir(dir);
    try {
      const result = await loadLatestPlanningChatSession(dir);
      if (!result.ok) return;
      setPlanningPrompt(result.prompt || result.messages[0]?.content || "기획방");
      setPlanningResult(result);
      setPage("planning");
    } catch {
      setPage("home");
    }
  }

  return (
    <div className="app-layout">
      <ErrorBoundary>
        <CustomTitleBar
          projectDir={projectDir}
          onSettings={projectDir ? () => openSettings() : undefined}
        />
      </ErrorBoundary>

      <ErrorBoundary>
        <UpdateBanner />
      </ErrorBoundary>

      <ErrorBoundary>
        {!projectDir ? (
          <Onboarding
            recentDirs={recentDirs}
            onComplete={(dir, key) => { addToRecent(dir); setProjectDir(dir); if (key) setApiKey(key); }}
            onPlanRequest={openPlanningRoom}
            onResume={(dir) => { void resumeProject(dir); }}
            onRemoveRecent={(dir) => removeFromRecent(dir)}
          />
        ) : (
          <>
            <div className="nav-tabs" style={{ paddingLeft: 8 }}>
              <button className={`nav-tab ${page === "home" ? "active" : ""}`} onClick={() => setPage("home")}>
                홈
              </button>
              <button className={`nav-tab ${page === "doctor" ? "active" : ""}`} onClick={() => setPage("doctor")}>
                Doctor
              </button>
              <button className={`nav-tab ${page === "manual" ? "active" : ""}`} onClick={() => setPage("manual")}>
                메뉴얼
              </button>
              <button className="nav-tab" onClick={() => openFolder(projectDir).catch(() => {})}>
                폴더열기
              </button>
              <button className={`nav-tab ${page === "docs" ? "active" : ""}`} onClick={() => setPage("docs")}>
                DOCS VIEWER
              </button>
              <button className={`nav-tab ${page === "code" ? "active" : ""}`} onClick={() => setPage("code")}>
                CODE EXPLORER
              </button>
              <button className={`nav-tab ${page === "backups" ? "active" : ""}`} onClick={() => setPage("backups")}>
                BACKUPS
              </button>
              <button className={`nav-tab ${page === "logs" ? "active" : ""}`} onClick={() => setPage("logs")}>
                에러로그
              </button>
              <div style={{ flex: 1 }} />
              <button
                className="nav-tab"
                style={{
                  borderRight: "none",
                  fontSize: 11,
                  color: "#777",
                  maxWidth: 260,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  display: "block",
                }}
                title={projectDir}
                onClick={() => { stopWatch().catch(() => {}); setProjectDir(null); setPage("home"); }}
              >
                {projectDir.replace(/\\/g, "/").split("/").filter(Boolean).slice(-1)[0] || projectDir} ↩
              </button>
            </div>

            <div style={{ flex: 1, overflow: "hidden" }}>
              <ErrorBoundary>
                {page === "home" && <Home key="home" projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={envKeyStatusLoaded} onNavigate={setPage} onOpenSettings={openSettings} watchOn={watchOn} setWatchOn={setWatchOn} watchError={watchError} onRetryWatch={() => { void retryWatch(); }} mapMode={mapMode} setMapMode={setMapMode} planningPrompt={planningPrompt} planningOutputPath={planningResult?.outputPath ?? null} planningPending={planningResult?.messages.some((message) => message.status === "pending") ?? false} onOpenPlanning={planningResult ? () => setPage("planning") : undefined} />}
                {page === "planning" && planningResult && <PlanningRoom projectDir={projectDir} result={planningResult} onBack={() => setPage("home")} onStartWork={() => setPage("code")} onResultChange={setPlanningResult} />}
                {page === "manual" && <Home key="manual" projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={envKeyStatusLoaded} onNavigate={setPage} onOpenSettings={openSettings} initialView="manual_list" watchOn={watchOn} setWatchOn={setWatchOn} mapMode={mapMode} setMapMode={setMapMode} />}
                {page === "docs" && <DocsViewer projectDir={projectDir} />}
                {page === "code" && <CodeExplorer projectDir={projectDir} planningPrompt={planningPrompt} planningOutputPath={planningResult?.outputPath ?? null} />}
                {page === "doctor" && <Doctor projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} />}
                {page === "backups" && <BackupDashboardPage projectDir={projectDir} />}
                {page === "logs" && <ErrorLogs projectDir={projectDir} />}
                {page === "settings" && (
                  <>
                    <div style={{ padding: "8px 12px 0", borderBottom: "2px solid #1A1A1A" }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => { setSettingsNotice(null); setPage(prevPage); }}
                        style={{ fontSize: 11 }}
                      >
                        ← 뒤로
                      </button>
                    </div>
                    <Settings apiKey={apiKey} onApiKeyChange={setApiKey} providerKeys={providerKeys} onKeysUpdated={refreshAiKeys} projectDir={projectDir} notice={settingsNotice} />
                  </>
                )}
              </ErrorBoundary>
            </div>
          </>
        )}
      </ErrorBoundary>
      <ScrollToTopButton />
    </div>
  );
}
// === ANCHOR: APP_END ===
