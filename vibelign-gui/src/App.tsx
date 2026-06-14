// === ANCHOR: APP_START ===
import { useState, useEffect, useRef, Component, ReactNode, ErrorInfo } from "react";
import CustomTitleBar from "./components/CustomTitleBar";
import ScrollToTopButton from "./components/ScrollToTopButton";
import UpdateBanner from "./components/UpdateBanner";
import Onboarding from "./pages/Onboarding";
import PlanningRoom from "./pages/PlanningRoom";
import Doctor from "./pages/Doctor";
import Home from "./pages/Home";
import DocsViewer from "./pages/DocsViewer";
import CodeExplorer from "./pages/CodeExplorer";
import WorkRoom from "./pages/WorkRoom";
import RunPanel from "./pages/RunPanel";
import type { WorkHandoff } from "./lib/run-preview/workHandoff";
import BackupDashboardPage from "./pages/BackupDashboard";
import ErrorLogs from "./pages/ErrorLogs";
import Settings from "./pages/Settings";
import { buildGuardDoctorLaunchIntent } from "./pages/doctorFlow";
import type { DoctorLaunchIntent } from "./pages/doctorFlow";
import { backupList, createPlanningChatSession, detectInstalledTools, enrichPlanningChatPlan, getEnvKeyStatus, getWatchErrors, listChangedFiles, listPlanningChatSessions, loadApiKey, loadLatestPlanningChatSession, loadPlanningChatSession, loadProviderApiKeys, loadRecentProjects, saveRecentProjects, startWatch, stopWatch, openFolder, type PlanningChatSessionResponse } from "./lib/vib";
import { GuideStrip } from "./components/nav/GuideStrip";
import { useGuide } from "./lib/nav/useGuide";
import {
  changedSetFingerprint,
  countChangesSinceBaseline,
  guideBaselineKey,
  guideCelebratedKey,
  guideRelevantEntries,
  hasManualCheckpoint,
  latestCheckpointId,
  shouldCelebrate,
  type ActiveGuideStep,
  type GuideBaseline,
} from "./lib/nav/guide";
import { PlanningSessionPicker } from "./pages/planning/PlanningSessionPicker";
import { installGuiErrorReporter, reportReactError, setErrorReporterProjectDir } from "./lib/errorReporter";
import { type Page } from "./lib/nav/stages";
import { StageSwitcherBar } from "./components/nav/StageSwitcherBar";
import { StageSubnav } from "./components/nav/StageSubnav";
import { StageHubCards } from "./components/nav/StageHubCards";
import PlanDocView from "./pages/PlanDocView";
import DesignPreview, { type DesignBinding } from "./pages/DesignPreview";
import { runDetect } from "./lib/vib/run";
import { HomePlanningStart } from "./components/home/HomePlanningStart";
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
export default function App() {
  const [projectDir, setProjectDir] = useState<string | null>(null);
  const [recentDirs, setRecentDirs] = useState<string[]>([]);
  const [page, setPage] = useState<Page>("home");
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [providerKeys, setProviderKeys] = useState<Record<string, string>>({});
  const [envKeyStatus, setEnvKeyStatus] = useState<Record<string, boolean>>({});
  const [envKeyStatusLoaded, setEnvKeyStatusLoaded] = useState(false);
  const [prevPage, setPrevPage] = useState<Page>("home");
  // 실행해보기 → 작업방 핸드오프(§4·§6): error(시작 실패 고치기)·improve(써보니 다듬기).
  // RunPanel 이 싣고, WorkRoom 이 마운트 시 consume-once 로 받아 비운다.
  const [workHandoff, setWorkHandoff] = useState<WorkHandoff | null>(null);
  const [settingsNotice, setSettingsNotice] = useState<string | null>(null);
  const [watchOn, setWatchOn] = useState(false);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [hasCheckpoint, setHasCheckpoint] = useState(false);
  // 가이드 3️⃣ 신호 전용 — vib start 자동 초기 저장 제외(사용자가 만든 체크포인트만).
  // hasCheckpoint(되돌리기 가능 여부, Home 전달)와 의미가 달라 분리한다.
  const [hasUserCheckpoint, setHasUserCheckpoint] = useState(false);
  const [backupCount, setBackupCount] = useState(0);
  const [backupLoaded, setBackupLoaded] = useState(false);
  // 백업 탭 안에서 저장/복원하면 page가 안 바뀌어 backupList effect가 재실행되지 않는다 —
  // 콜백으로 버전을 올려 같은 페이지에서도 가이드 신호(3️⃣→4️⃣ 전환)를 즉시 갱신한다.
  const [backupsVersion, setBackupsVersion] = useState(0);
  const [latestBackupId, setLatestBackupId] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<"manual" | "auto">("manual");
  const [planningPrompt, setPlanningPrompt] = useState("");
  const [planningResult, setPlanningResult] = useState<PlanningChatSessionResponse | null>(null);
  // 디자인 미리보기: PlanDocView 가 선택한 기획안 경로(designPlanPath) → 확정 시 designBinding 으로 작업방에 바인딩.
  const [designPlanPath, setDesignPlanPath] = useState<string | null>(null);
  const [designBinding, setDesignBinding] = useState<DesignBinding | null>(null);
  // 웹 게이트(비차단): run_detect 가 electron 으로 확정될 때만 경고. unknown/null 은 불확실 → 경고 안 함.
  const [designIsWeb, setDesignIsWeb] = useState(true);
  const [reviewSourcePath, setReviewSourcePath] = useState<string | null>(null);
  const [doctorLaunchIntent, setDoctorLaunchIntent] = useState<DoctorLaunchIntent | null>(null);
  const [showSessionPicker, setShowSessionPicker] = useState(false);
  // 다중 기획안 요약(홈 허브 배지) — 저장(완료)/미저장(진행중)/갱신필요 집계. 홈 진입 시 새로고침.
  const [planningSummary, setPlanningSummary] = useState({ total: 0, saved: 0, draft: 0, stale: 0 });
  // 기획안 저장 후 백그라운드 보강(준비상태·계약 AI 분석) 진행 중인 세션 — "분석 중" 표시용.
  // App(루트) 이 소유해 PlanningRoom 을 떠나도 완료되고 contract 가 planningResult 로 흘러든다.
  const [enrichingSessionId, setEnrichingSessionId] = useState<string | null>(null);
  function enrichPlanAfterSave(sessionId: string) {
    if (!projectDir) return;
    setEnrichingSessionId(sessionId);
    void enrichPlanningChatPlan({ projectDir, sessionId })
      .then((enriched) => {
        if (!enriched.ok) return;
        // 활성 세션이 그대로일 때만, enrich 가 소유한 필드(분석 결과)만 병합한다 — enrich 창
        // 동안 사용자가 같은 세션에 더한 대화·카드(messages/cards)를 통째 교체로 되돌리지 않게
        // (M3 enrich 리뷰 P2). contract 는 작업방 지시문이 쓰는 핵심.
        setPlanningResult((prev) =>
          prev && prev.sessionId === enriched.sessionId
            ? { ...prev, contract: enriched.contract, readiness: enriched.readiness, markdown: enriched.markdown }
            : prev,
        );
      })
      .catch(() => {})
      .finally(() => setEnrichingSessionId((cur) => (cur === sessionId ? null : cur)));
  }


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

  // 프로젝트가 바뀌면 신호 로딩 상태부터 리셋 — 아래 조회 effect보다 먼저 선언할 것.
  useEffect(() => {
    setBackupLoaded(false);
  }, [projectDir]);

  useEffect(() => {
    if (!projectDir) {
      setHasCheckpoint(false);
      setHasUserCheckpoint(false);
      setBackupCount(0);
      setLatestBackupId(null);
      setBackupLoaded(false);
      return;
    }
    let active = true;
    backupList(projectDir)
      .then((result) => {
        if (active) {
          setHasCheckpoint(result.backups.length > 0);
          setHasUserCheckpoint(hasManualCheckpoint(result.backups));
          setBackupCount(result.backups.length);
          setLatestBackupId(latestCheckpointId(result.backups));
        }
      })
      .catch(() => {
        if (active) {
          setHasCheckpoint(false);
          setHasUserCheckpoint(false);
          setBackupCount(0);
          setLatestBackupId(null);
        }
      })
      .finally(() => {
        if (active) setBackupLoaded(true);
      });
    return () => {
      active = false;
    };
  }, [projectDir, page, backupsVersion]);

  // 체크포인트 이후 변경 감지(spec §3.1) — git changed-set을 체크포인트 시점 baseline과
  // "변경 지문(path+status+mtime_ms+size)" 단위로 비교(v6 외부 리뷰 H1). 경로 집합 비교는
  // 이미 dirty였던 파일의 재수정(커밋 안 하는 초보자의 2사이클차부터 일상)을 못 본다.
  // null은 조회가 예외로 실패한 경우만. 비-git 프로젝트는 git_status가 빈 목록을 반환(에러 아님)해
  // 항상 0으로 읽힌다 — 자동 5️⃣ 전환 없음, 4️⃣ affordance가 유일한 출구(spec §4-5, critic 재리뷰 C1).
  const [changedFileCount, setChangedFileCount] = useState<number | null>(null);
  // 현재 changed-set의 지문 — guard 결과 stale 판정의 기준(Step 4, 외부 리뷰 H2).
  const [changedFingerprint, setChangedFingerprint] = useState<string | null>(null);
  useEffect(() => {
    if (!projectDir || !backupLoaded || !latestBackupId) {
      // 체크포인트가 없으면 기준점도 없음 — 3️⃣ 안내 단계라 변경 신호 자체가 불필요.
      setChangedFileCount(null);
      setChangedFingerprint(null);
      return;
    }
    let active = true;
    listChangedFiles(projectDir)
      .then((entries) => {
        if (!active) return;
        const current = guideRelevantEntries(entries);
        const key = guideBaselineKey(projectDir);
        let baseline: GuideBaseline | null = null;
        try {
          const parsed = JSON.parse(localStorage.getItem(key) ?? "null") as GuideBaseline | null;
          // entries 배열이 없으면(미래의 스키마 변경·손상 대비) 기준점 없음으로 보고 재캡처.
          baseline = parsed && Array.isArray(parsed.entries) ? parsed : null;
        } catch {
          baseline = null;
        }
        if (!baseline || baseline.checkpointId !== latestBackupId) {
          // 새 최신 체크포인트를 알아챈 순간의 changed-set이 새 기준점(spec §4-7) — 6️⃣ 저장 후 4️⃣ 복귀가 여기서 일어난다.
          localStorage.setItem(key, JSON.stringify({ checkpointId: latestBackupId, entries: current }));
          setChangedFileCount(0);
          setChangedFingerprint(changedSetFingerprint(current));
          return;
        }
        setChangedFileCount(countChangesSinceBaseline(baseline.entries, current));
        setChangedFingerprint(changedSetFingerprint(current));
      })
      .catch(() => {
        if (active) {
          setChangedFileCount(null);
          setChangedFingerprint(null);
        }
      });
    return () => {
      active = false;
    };
  }, [projectDir, page, latestBackupId, backupLoaded, backupsVersion]);

  const [guardStatus, setGuardStatus] = useState<"ok" | "issue" | null>(null);
  // guard가 "어떤 변경 상태"를 검사했는지 지문으로 기억(spec §3.1, v6 외부 리뷰 H2).
  // 리셋 기준은 "검사 시점 지문 ≠ 현재 지문" — 이전 기준(변경 수 증가)은 같은 파일 재수정·
  // 동수 집합 교체(A/B→C/D)에서 stale pass(거짓 6️⃣)를 남겼다. 무변경 재조회(탭 전환)는
  // 지문이 같아 리셋되지 않으므로, critic 재리뷰 M1이 막으려던 오리셋도 그대로 없다.
  // 부분 undo도 지문이 달라져 리셋(=5️⃣ 재검증 안내) — 변경 상태가 달라졌으면 옳은 방향(의도된 강화).
  const guardCheckedFingerprintRef = useRef<string | null>(null); // useRef는 App.tsx에 이미 import됨(resumingRef)
  useEffect(() => {
    // 조회 실패(null)는 판단 불가라 보류 — 그 동안 changedFileCount도 null이라 추론이 이미 4️⃣로 보수적.
    if (guardStatus === null || changedFingerprint === null) return;
    if (changedFingerprint !== guardCheckedFingerprintRef.current) {
      setGuardStatus(null);
      guardCheckedFingerprintRef.current = null;
    }
  }, [changedFingerprint, guardStatus]);
  useEffect(() => {
    setGuardStatus(null);
    guardCheckedFingerprintRef.current = null;
  }, [projectDir]);

  // 작동 검증(써봤다 ✓) 신호 — guardStatus 와 짝이되 inferStep 게이팅은 안 건드린다(추가 축).
  // 리셋 규칙도 guardStatus 동형: 검증 시점 지문 ≠ 현재 지문이면 stale → 무효화(코드 또 고치면 재검증).
  const [runVerified, setRunVerified] = useState(false);
  const runVerifiedFingerprintRef = useRef<string | null>(null);
  useEffect(() => {
    if (!runVerified || changedFingerprint === null) return;
    if (changedFingerprint !== runVerifiedFingerprintRef.current) {
      setRunVerified(false);
      runVerifiedFingerprintRef.current = null;
    }
  }, [changedFingerprint, runVerified]);
  useEffect(() => {
    setRunVerified(false);
    runVerifiedFingerprintRef.current = null;
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
    const next = [dir, ...recentDirs.filter((d) => d !== dir)].slice(0, 20);
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

  function openDoctorFromGuardIssue() {
    setDoctorLaunchIntent(buildGuardDoctorLaunchIntent(hasAnyAiKey));
    setPage("doctor");
  }

  function openDoctorTab() {
    setDoctorLaunchIntent(null);
    setPage("doctor");
  }

  function navigate(next: Page) {
    if (next === "doctor") { openDoctorTab(); return; }
    setPage(next);
  }

  useEffect(() => {
    if (page !== "doctor" || !doctorLaunchIntent) return;
    const nextIntent = buildGuardDoctorLaunchIntent(hasAnyAiKey);
    if (doctorLaunchIntent.applyMode !== nextIntent.applyMode) {
      setDoctorLaunchIntent(nextIntent);
    }
  }, [doctorLaunchIntent, hasAnyAiKey, page]);

  function buildPlanReviewPrompt(path: string): string {
    return `프로젝트의 기획/스펙 문서 「${path}」 를 읽고 검토해줘. 빠진 부분, 모순, 개선점을 짚고 더 나은 기획안을 제안해줘.`;
  }

  async function openPlanningRoom(dir: string, prompt: string, sourcePath: string | null = null) {
    const normalizedPrompt = prompt.trim().slice(0, 4000);
    if (!normalizedPrompt) return;
    setReviewSourcePath(sourcePath);
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

  async function resumeSession(sessionId: string) {
    if (!projectDir) return;
    setShowSessionPicker(false);
    const result = await loadPlanningChatSession(projectDir, sessionId);
    if (!result.ok) return;
    setReviewSourcePath(null);
    setPlanningPrompt(result.prompt || result.messages[0]?.content || "기획방");
    setPlanningResult(result);
    setPage("planning");
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

  async function loadProjectPlanning(dir: string): Promise<boolean> {
    setReviewSourcePath(null);
    try {
      const result = await loadLatestPlanningChatSession(dir);
      if (result.ok) {
        setPlanningPrompt(result.prompt || result.messages[0]?.content || "기획방");
        setPlanningResult(result);
        return true;
      }
    } catch {
      // 세션 로드 실패 시 아래에서 기획방 상태를 비운다.
    }
    // 기획방이 없는 프로젝트면 이전 프로젝트의 상태가 남지 않도록 비운다.
    setPlanningPrompt("");
    setPlanningResult(null);
    return false;
  }

  async function resumeProject(dir: string) {
    addToRecent(dir);
    setProjectDir(dir);
    const hasPlanning = await loadProjectPlanning(dir);
    setPage(hasPlanning ? "planning" : "home");
  }

  const planningStatus: "none" | "active" | "done" = !planningResult
    ? "none"
    : planningResult.messages.some((m) => m.status === "pending")
      ? "active"
      : "done";

  const planningPendingNow = planningResult?.messages.some((m) => m.status === "pending") ?? false;

  // 홈 진입·기획안 변경 시 기획안 현황 집계(다중 기획안 요약 배지). "기획안"의 정의는
  // 기획안 탭(PlanDocView)과 동일하게 outputPath 보유 = 저장된 plan doc 으로 맞춘다 —
  // 그래야 탭(목록)과 홈 배지가 어긋나지 않는다. outputPath 없는 행은 미저장 "초안".
  useEffect(() => {
    if (page !== "home" || !projectDir) return;
    let alive = true;
    void listPlanningChatSessions(projectDir)
      .then((rows) => {
        if (!alive) return;
        const docs = rows.filter((r) => Boolean(r.outputPath));
        const stale = docs.filter((r) => r.docStale).length;
        setPlanningSummary({ total: rows.length, saved: docs.length, draft: rows.length - docs.length, stale });
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [page, projectDir, planningResult]);
  // 가이드 레이어 — 신호 전부 배선(v2): 기획안·기획진행·체크포인트·체크포인트 이후 변경·guard.
  const guide = useGuide(
    projectDir,
    {
      hasPlanDoc: Boolean(planningResult?.outputPath),
      planningPending: planningPendingNow,
      hasCheckpoint: hasUserCheckpoint,
      changedFileCount,
      guardStatus,
      runVerified,
    },
    backupLoaded,
  );

  // 4️⃣ 도구 미보유 분기(spec §3.2) — 0개 "확정 탐지"일 때만 true. 탐지 실패는 기존 값 유지(추측 안내 금지).
  const [aiToolMissing, setAiToolMissing] = useState(false);
  const prevPageForToolsRef = useRef<Page | null>(null);
  useEffect(() => {
    const prev = prevPageForToolsRef.current;
    prevPageForToolsRef.current = page;
    // 마운트 1회(prev=null) + 설정 이탈(prev="settings") 시에만 탐지 — 그 외 탭 전환엔 침묵.
    if (prev !== null && !(prev === "settings" && page !== "settings")) return;
    let active = true;
    detectInstalledTools()
      .then((tools) => {
        if (active) setAiToolMissing(tools.length === 0);
      })
      .catch(() => {
        // 탐지 실패 → 기존 값 유지(추측 안내 금지)
      });
    return () => {
      active = false;
    };
  }, [page]);

  // 첫 사이클 완주 축하(spec §3.2) — 6️⃣→4️⃣ 전환(저장으로 루프 닫힘)에 프로젝트당 1회.
  // guide.enabled 게이트(v6 외부 리뷰 M1): useGuide는 OFF여도 step을 계산하므로, 게이트 없이는
  // 가이드를 끈 사용자에게 축하가 튀어나온다. 게이트는 여기(발화 effect)에 — GuideStrip prop에서
  // 막으면 OFF 중에 1회성 플래그만 소모돼, 나중에 켠 사용자가 축하를 영영 못 받는다.
  const [celebrating, setCelebrating] = useState(false);
  const prevGuideStepRef = useRef<ActiveGuideStep | null>(null);
  useEffect(() => {
    if (!projectDir || !guide.enabled) return;
    // ref 전진은 게이트 뒤 — OFF 중 전환을 ref가 소모하면(6을 지나쳐 전진) 재활성 사용자가
    // 축하를 영영 못 받는다. ref는 "마지막으로 관찰한 단계"에 머문다(품질 리뷰 반영).
    const prev = prevGuideStepRef.current;
    prevGuideStepRef.current = guide.step;
    const already = localStorage.getItem(guideCelebratedKey(projectDir)) === "1";
    if (shouldCelebrate(prev, guide.step, already)) {
      localStorage.setItem(guideCelebratedKey(projectDir), "1");
      setCelebrating(true);
    }
  }, [guide.step, guide.enabled, projectDir]);
  useEffect(() => {
    // 프로젝트 전환 시 축하 상태·전환 추적 리셋
    setCelebrating(false);
    prevGuideStepRef.current = null;
  }, [projectDir]);

  // 기획 탭에 들어갔는데 활성 세션이 없으면 최근 세션을 자동으로 이어서 연다(resume).
  // 세션이 하나도 없으면 loadProjectPlanning 이 planningResult 를 null 로 둬 시작 화면이 뜬다.
  const resumingRef = useRef(false);
  useEffect(() => {
    if (page !== "planning" || planningResult || !projectDir || resumingRef.current) return;
    resumingRef.current = true;
    void loadProjectPlanning(projectDir).finally(() => {
      resumingRef.current = false;
    });
  }, [page, projectDir, planningResult]);

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
            onComplete={(dir, key) => { addToRecent(dir); setProjectDir(dir); if (key) setApiKey(key); setPage("home"); void loadProjectPlanning(dir); }}
            onPlanRequest={openPlanningRoom}
            onResume={(dir) => { void resumeProject(dir); }}
            onRemoveRecent={(dir) => removeFromRecent(dir)}
          />
        ) : (
          <>
            <StageSwitcherBar
              page={page}
              projectDir={projectDir}
              onHome={() => setPage("home")}
              onNavigate={navigate}
              onOpenManual={() => setPage("manual")}
              onOpenFolder={() => openFolder(projectDir).catch(() => {})}
              onExitProject={() => { stopWatch().catch(() => {}); setProjectDir(null); setPlanningResult(null); setReviewSourcePath(null); setPlanningPrompt(""); setWorkHandoff(null); setPage("home"); }}
            />
            <StageSubnav page={page} onNavigate={navigate} />

            <GuideStrip
              enabled={guide.enabled}
              step={guide.step}
              currentPage={page}
              hasCheckpoint={hasCheckpoint}
              planningPending={planningPendingNow}
              aiToolMissing={aiToolMissing}
              celebrating={celebrating}
              runVerified={runVerified}
              onNavigate={navigate}
              onStepChange={guide.setStep}
              onDisable={() => guide.setEnabled(false)}
              onOpenSettings={() => openSettings()}
              onCelebrateDismiss={() => setCelebrating(false)}
            />

            <div style={{ flex: 1, overflow: "hidden" }}>
              <ErrorBoundary>
                {page === "home" && (
                  <>
                    <StageHubCards onNavigate={navigate} planningStatus={planningStatus} planningSummary={planningSummary} backupCount={backupCount} currentStep={guide.enabled ? guide.step : null} />
                    <Home key="home" projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={envKeyStatusLoaded} onNavigate={setPage} onOpenDoctor={openDoctorFromGuardIssue} onOpenSettings={openSettings} watchOn={watchOn} setWatchOn={setWatchOn} watchError={watchError} onRetryWatch={() => { void retryWatch(); }} hasCheckpoint={hasCheckpoint} mapMode={mapMode} setMapMode={setMapMode} planningPrompt={planningPrompt} planningOutputPath={planningResult?.outputPath ?? null} planningPending={planningResult?.messages.some((message) => message.status === "pending") ?? false} onOpenPlanning={planningResult ? () => setPage("planning") : undefined} onStartPlanning={(idea) => { if (projectDir) void openPlanningRoom(projectDir, idea); }} onOpenPlanningHistory={() => setShowSessionPicker(true)} planningContract={planningResult?.contract ?? null} onGuardResult={(status) => {
                        // guard가 검사한 변경 상태의 지문 기록 — 이후 지문이 달라지면 (a)의 effect가 리셋.
                        // 기록되는 지문은 홈 진입 시 조회분이라 "진입~클릭 사이" 변경은 한 박자 늦게(다음
                        // 재조회에서 지문 불일치로) 리셋된다 — baseline과 같은 좁은 경쟁 구간 허용(spec §4-7).
                        guardCheckedFingerprintRef.current = changedFingerprint;
                        setGuardStatus(status);
                      }} />
                  </>
                )}
                {page === "planning" && (planningResult ? (
                  <PlanningRoom projectDir={projectDir} result={planningResult} sourcePath={reviewSourcePath} onBack={() => setPage("home")} onStartWork={() => navigate("work")} onDesignPreview={(planPath) => {
                    setDesignPlanPath(planPath);
                    void runDetect(projectDir).then((r) => setDesignIsWeb(r == null ? true : r.kind === "web")).catch(() => setDesignIsWeb(true));
                    navigate("design-preview");
                  }} onResultChange={setPlanningResult} isEnriching={enrichingSessionId !== null && enrichingSessionId === planningResult.sessionId} onEnrich={enrichPlanAfterSave} />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, padding: 24 }}>
                    <div style={{ fontSize: 32 }}>📋</div>
                    <div style={{ fontSize: 14, color: "#555" }}>무엇을 만들고 싶은지 적으면 기획방이 열립니다.</div>
                    <div style={{ width: "100%", maxWidth: 520 }}>
                      <HomePlanningStart onStart={(idea) => { if (projectDir) void openPlanningRoom(projectDir, idea); }} />
                    </div>
                    <button className="nav-tab" onClick={() => setShowSessionPicker(true)}>이전 기획 불러오기</button>
                  </div>
                ))}
                {page === "plan-doc" && <PlanDocView projectDir={projectDir} activeSessionId={planningResult?.sessionId ?? null} onStart={() => { if (planningResult) navigate("planning"); else setPage("home"); }} onDeleted={(sessionId) => { if (planningResult?.sessionId === sessionId) setPlanningResult(null); }} onEdit={(sessionId) => void resumeSession(sessionId)} onDesignPreview={(planPath) => {
                  setDesignPlanPath(planPath);
                  // 웹 게이트(비차단): 확정 web 일 때만 무경고. electron·unknown 은 경고, 탐지 실패(null)는 무경고.
                  void runDetect(projectDir).then((r) => setDesignIsWeb(r == null ? true : r.kind === "web")).catch(() => setDesignIsWeb(true));
                  navigate("design-preview");
                }} />}
                {page === "design-preview" && (designPlanPath ? (
                  <DesignPreview
                    projectDir={projectDir}
                    planPath={designPlanPath}
                    isLikelyWeb={designIsWeb}
                    onBack={() => navigate("plan-doc")}
                    onConfirm={(b) => { setDesignBinding(b); navigate("work"); }}
                  />
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 16, padding: 24 }}>
                    <div style={{ fontSize: 32 }}>🎨</div>
                    <div style={{ fontSize: 14, color: "#555", textAlign: "center", lineHeight: 1.6 }}>
                      디자인 미리보기는 기획안이 필요해요.<br />
                      기획 단계에서 기획안을 고르고 <strong>🎨 디자인 미리보기</strong> 를 누르면 여기에 목업이 그려집니다.
                    </div>
                    <button className="btn" onClick={() => navigate("plan-doc")}>기획안 고르러 가기</button>
                  </div>
                ))}
                {page === "manual" && <Home key="manual" projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} hasAnyAiKey={hasAnyAiKey} aiKeyStatusLoaded={envKeyStatusLoaded} onNavigate={navigate} onOpenSettings={openSettings} initialView="manual_list" watchOn={watchOn} setWatchOn={setWatchOn} mapMode={mapMode} setMapMode={setMapMode} onStartPlanning={(idea) => { if (projectDir) void openPlanningRoom(projectDir, idea); }} guideStep={guide.enabled ? guide.step : null} />}
                {page === "docs" && <DocsViewer projectDir={projectDir} />}
                {page === "code" && <CodeExplorer projectDir={projectDir} planningPrompt={planningPrompt} planningOutputPath={planningResult?.outputPath ?? null} planningContract={planningResult?.contract ?? null} planningDocStale={planningResult?.docStale ?? false} onReviewInPlanning={(path) => { if (projectDir) void openPlanningRoom(projectDir, buildPlanReviewPrompt(path), path); }} />}
                {page === "work" && <WorkRoom projectDir={projectDir} planningPrompt={planningPrompt} planningOutputPath={planningResult?.outputPath ?? null} planningContract={planningResult?.contract ?? null} planningDocStale={planningResult?.docStale ?? false} design={designBinding ?? undefined} designPlanPath={designPlanPath ?? undefined} workHandoff={workHandoff} onWorkHandoffConsumed={() => setWorkHandoff(null)} onNavigate={navigate} onOpenSettings={() => openSettings()} onGuardResult={(status) => {
                  // 작업방 자동 검사도 홈 '상태 확인'과 같은 가이드 신호 채널로 보고(spec §4-7와 동일 지문 기록).
                  guardCheckedFingerprintRef.current = changedFingerprint;
                  setGuardStatus(status);
                }} />}
                {page === "run" && <RunPanel projectDir={projectDir} onNavigate={navigate} guardStatus={guardStatus} runVerified={runVerified} onRunVerified={() => { runVerifiedFingerprintRef.current = changedFingerprint; setRunVerified(true); }} onRequestWorkHandoff={(h) => { setWorkHandoff(h); navigate("work"); }} />}
                {page === "doctor" && <Doctor projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} launchIntent={doctorLaunchIntent} />}
                {page === "backups" && <BackupDashboardPage projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} onBackupsChanged={() => setBackupsVersion((v) => v + 1)} />}
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
                    <Settings apiKey={apiKey} onApiKeyChange={setApiKey} providerKeys={providerKeys} onKeysUpdated={refreshAiKeys} projectDir={projectDir} notice={settingsNotice} guideEnabled={guide.enabled} onGuideEnabledChange={guide.setEnabled} />
                  </>
                )}
              </ErrorBoundary>
            </div>
          </>
        )}
      </ErrorBoundary>
      {showSessionPicker && projectDir && (
        <PlanningSessionPicker
          projectDir={projectDir}
          onSelect={(sessionId) => void resumeSession(sessionId)}
          onClose={() => setShowSessionPicker(false)}
          onDeleted={(sessionId) => {
            if (planningResult?.sessionId === sessionId) {
              setPlanningResult(null);
              if (page === "planning" || page === "plan-doc") setPage("home");
            }
          }}
        />
      )}
      <ScrollToTopButton />
    </div>
  );
}
// === ANCHOR: APP_END ===
