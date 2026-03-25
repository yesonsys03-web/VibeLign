// === ANCHOR: APP_START ===
import { useState, useEffect, Component, ReactNode } from "react";
import CustomTitleBar from "./components/CustomTitleBar";
import Onboarding from "./pages/Onboarding";
import Doctor from "./pages/Doctor";
import Home from "./pages/Home";
import Checkpoints from "./pages/Checkpoints";
import Settings from "./pages/Settings";
import { loadApiKey, loadRecentProjects, saveRecentProjects, stopWatch } from "./lib/vib";
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
type Page = "home" | "doctor" | "checkpoints" | "settings";

export default function App() {
  const [projectDir, setProjectDir] = useState<string | null>(null);
  const [recentDirs, setRecentDirs] = useState<string[]>([]);
  const [page, setPage] = useState<Page>("home");
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [prevPage, setPrevPage] = useState<Page>("home");

  useEffect(() => {
    loadApiKey().then((k) => setApiKey(k ?? null)).catch(() => {});
    loadRecentProjects().then(setRecentDirs).catch(() => {});
  }, []);

  function addToRecent(dir: string) {
    const next = [dir, ...recentDirs.filter((d) => d !== dir)].slice(0, 5);
    setRecentDirs(next);
    saveRecentProjects(next).catch(() => {});
  }

  function openSettings() {
    setPrevPage(page === "settings" ? prevPage : page);
    setPage("settings");
  }

  return (
    <div className="app-layout">
      <ErrorBoundary>
        <CustomTitleBar
          projectDir={projectDir}
          onSettings={projectDir ? openSettings : undefined}
        />
      </ErrorBoundary>

      <ErrorBoundary>
        {!projectDir ? (
          <Onboarding
            recentDirs={recentDirs}
            onComplete={(dir, key) => { addToRecent(dir); setProjectDir(dir); if (key) setApiKey(key); }}
            onResume={(dir) => { addToRecent(dir); setProjectDir(dir); }}
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
              <button className={`nav-tab ${page === "checkpoints" ? "active" : ""}`} onClick={() => setPage("checkpoints")}>
                Checkpoints
              </button>
              <div style={{ flex: 1 }} />
              <button
                className="nav-tab"
                style={{ borderRight: "none", fontSize: 11, color: "#777" }}
                onClick={() => { stopWatch().catch(() => {}); setProjectDir(null); setPage("home"); }}
              >
                {projectDir.split("/").slice(-1)[0]} ↩
              </button>
            </div>

            <div style={{ flex: 1, overflow: "hidden" }}>
              <ErrorBoundary>
                {page === "home" && <Home projectDir={projectDir} onNavigate={setPage} />}
                {page === "doctor" && <Doctor projectDir={projectDir} apiKey={apiKey} />}
                {page === "checkpoints" && <Checkpoints projectDir={projectDir} />}
                {page === "settings" && (
                  <>
                    <div style={{ padding: "8px 12px 0", borderBottom: "2px solid #1A1A1A" }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => setPage(prevPage)}
                        style={{ fontSize: 11 }}
                      >
                        ← 뒤로
                      </button>
                    </div>
                    <Settings apiKey={apiKey} onApiKeyChange={setApiKey} projectDir={projectDir} />
                  </>
                )}
              </ErrorBoundary>
            </div>
          </>
        )}
      </ErrorBoundary>
    </div>
  );
}
// === ANCHOR: APP_END ===
