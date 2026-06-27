// === ANCHOR: RUN_PANEL_START ===
// 실행해보기(Run & Preview) M3 (plans/2026-06-12-실행해보기-run-preview-design.md §7).
// 초보의 "완성 코드를 어떻게 켜?" 해소 — 버튼 하나로 dev 실행, 웹은 앱 내 미리보기.
// 백엔드 commands/run_preview.rs 의 run_detect/run_start/run_stop/run_status + open_preview.
//
// 이벤트 3종(run-output/run-status/run-preview-ready)은 모두 runId 로 필터링한다 —
// 이전 실행의 잔여 라인이 새 실행 화면에 새지 않게(작업방 동형, M2 리뷰 cross-file 항목).
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import {
  openPreview,
  runDetect,
  runStart,
  runStatus,
  runStop,
  type RunOutputEvent,
  type RunPreviewReadyEvent,
  type RunRecipe,
  type RunStatusEvent,
  type RunStatusKind,
} from "../lib/vib/run";
import {
  collectErrorTail,
  isTerminal,
  kindLabel,
  statusView,
  type RunTone,
} from "../lib/run-preview/runView";
import type { Page } from "../lib/nav/stages";
import type { WorkHandoff } from "../lib/run-preview/workHandoff";

interface RunPanelProps {
  projectDir: string;
  onNavigate: (page: Page) => void;
  /** 실행해보기 → 작업방 핸드오프(§4·§6): error(실패 고치기)·improve(개선 요청). */
  onRequestWorkHandoff?: (handoff: WorkHandoff) => void;
  /** 안전 축 상태(가이드 신호) — 완주 🎉·교차 nudge 표시용. */
  guardStatus?: "ok" | "issue" | null;
  /** 작동 축 — 사용자가 "✓ 잘 돼요"로 확인했는지. */
  runVerified?: boolean;
  /** 작동 검증 보고 — guardStatus 동형 채널(App). */
  onRunVerified?: () => void;
}

type PanelStatus = RunStatusKind | "starting" | null;

/** 표시 라인 상한 — 긴 dev 로그에서도 메모리/렌더를 보호(앞부분부터 버림). */
const LINE_CAP = 500;

interface LogLine {
  runId: number;
  stream: "stdout" | "stderr";
  text: string;
}

const TONE_COLOR: Record<RunTone, string> = {
  idle: "#666",
  info: "#1D4ED8",
  running: "#166534",
  success: "#166534",
  error: "#b42318",
};

const MISSING_RUN_TARGET_HANDOFF = [
  "실행 방법을 못 찾았어요.",
  "프로젝트 루트에 index.html 파일을 만들거나, package.json에 dev 또는 start 스크립트를 제공해서 실행해보기 버튼이 활성화되게 고쳐주세요.",
  "정적 HTML 앱이면 하위 폴더가 아니라 프로젝트 루트의 index.html 하나만으로 바로 열리게 만들어 주세요.",
].join("\n");

export default function RunPanel({ projectDir, onNavigate, onRequestWorkHandoff, guardStatus, runVerified, onRunVerified }: RunPanelProps) {
  const [recipe, setRecipe] = useState<RunRecipe | null>(null);
  const [detectState, setDetectState] = useState<"loading" | "ready" | "none">("loading");
  const [status, setStatus] = useState<PanelStatus>(null);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [improveOpen, setImproveOpen] = useState(false);
  const [improveText, setImproveText] = useState("");
  const activeRunIdRef = useRef<number | null>(null);
  const outputRef = useRef<HTMLDivElement | null>(null);

  const kind = recipe?.kind ?? null;
  const isActive = status === "starting" || status === "installing" || status === "running";

  // 타입 감지 + 탭 복귀 시 진행 중 실행 복원(run_status — previewUrl 까지 복원).
  useEffect(() => {
    let alive = true;
    void runDetect(projectDir)
      .then((r) => {
        if (!alive) return;
        setRecipe(r);
        setDetectState(r ? "ready" : "none");
      })
      .catch(() => alive && setDetectState("none"));
    void runStatus()
      .then((s) => {
        if (!alive || !s.running) return;
        activeRunIdRef.current = s.runId;
        // 진짜 단계로 복원 — install 중 탭 복귀 시 "실행 중" 오표시 방지(M3a 리뷰 P2).
        setStatus(s.status ?? "running");
        if (s.previewUrl) setPreviewUrl(s.previewUrl);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [projectDir]);

  // 이벤트 구독(마운트 1회) — 세 이벤트 모두 runId 필터.
  useEffect(() => {
    let unOut: UnlistenFn | null = null;
    let unStatus: UnlistenFn | null = null;
    let unReady: UnlistenFn | null = null;
    void listen<RunOutputEvent>("run-output", (ev) => {
      if (activeRunIdRef.current !== null && ev.payload.runId !== activeRunIdRef.current) return;
      setLines((prev) => {
        const next = [...prev, { runId: ev.payload.runId, stream: ev.payload.stream, text: ev.payload.line }];
        return next.length > LINE_CAP ? next.slice(next.length - LINE_CAP) : next;
      });
    }).then((u) => {
      unOut = u;
    });
    void listen<RunStatusEvent>("run-status", (ev) => {
      if (activeRunIdRef.current !== null && ev.payload.runId !== activeRunIdRef.current) return;
      setStatus(ev.payload.status);
    }).then((u) => {
      unStatus = u;
    });
    void listen<RunPreviewReadyEvent>("run-preview-ready", (ev) => {
      if (activeRunIdRef.current !== null && ev.payload.runId !== activeRunIdRef.current) return;
      setPreviewUrl(ev.payload.url);
    }).then((u) => {
      unReady = u;
    });
    return () => {
      unOut?.();
      unStatus?.();
      unReady?.();
    };
  }, []);

  // 새 라인마다 출력 바닥으로 스크롤.
  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
  }, [lines]);

  async function handleStart() {
    setStartError(null);
    setLines([]);
    setPreviewUrl(null);
    // 새 실행마다 개선 입력 초기화 — 이전 실행의 입력이 stale 하게 남지 않게(M3 최종 리뷰 P2).
    setImproveOpen(false);
    setImproveText("");
    // 새 실행 시작 전 옛 run_id 해제 — 응답 전 도착한 새 실행 이벤트가 옛 id 로 걸러지지
    // 않게(첫 실행의 null pass-through 와 동일 의미로 맞춘다, M3a 리뷰 P3).
    activeRunIdRef.current = null;
    setStarting(true);
    setStatus("starting");
    try {
      const info = await runStart(projectDir);
      activeRunIdRef.current = info.runId;
      setStatus((prev) => (prev === "running" ? "running" : (info.needsInstall ? "installing" : "starting")));
    } catch (e) {
      activeRunIdRef.current = null;
      setStatus(null);
      setStartError(e instanceof Error ? e.message : String(e));
    } finally {
      setStarting(false);
    }
  }

  async function handleStop() {
    try {
      await runStop();
    } catch {
      /* 중지 실패는 무시 — 상태 이벤트가 정정한다 */
    }
  }

  async function handleOpenPreview() {
    if (!previewUrl) return;
    setStartError(null);
    try {
      await openPreview(previewUrl);
    } catch (e) {
      setStartError(e instanceof Error ? e.message : String(e));
    }
  }

  const statusLine: { text: string; tone: RunTone } | null =
    status === "starting"
      ? { text: "시작 중…", tone: "info" }
      : status
        ? statusView(status)
        : null;

  const showPreviewButton = previewUrl !== null && kind !== "electron";
  const electronRunning = kind === "electron" && status === "running";

  return (
    <div className="page-content" style={{ height: "100%" }}>
      <div style={{ display: "grid", gap: 12, maxWidth: 860 }}>
        <div className="page-header" style={{ marginBottom: 0 }}>
          <div className="page-title">실행해보기</div>
        </div>

        {/* 감지 결과 카드 */}
        <section className="card" style={{ display: "grid", gap: 8, padding: 12, background: "#F5F1E3" }}>
          {detectState === "loading" && (
            <div style={{ fontSize: 13, fontWeight: 700, color: "#666" }}>프로젝트를 살펴보는 중…</div>
          )}
          {detectState === "none" && (
            <div style={{ display: "grid", gap: 6 }}>
              <div style={{ fontSize: 13, fontWeight: 800 }}>실행 방법을 못 찾았어요</div>
              <div style={{ fontSize: 12, color: "#666", lineHeight: 1.6 }}>
                index.html 파일이 있으면 바로 실행돼요. 또는 package.json 에 <b>dev</b> 또는 <b>start</b>{" "}
                스크립트가 있어야 해요.
              </div>
              {onRequestWorkHandoff && (
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ justifySelf: "start", fontSize: 12 }}
                  onClick={() => onRequestWorkHandoff({ kind: "error", text: MISSING_RUN_TARGET_HANDOFF })}
                >
                  작업방에서 실행 형태 만들기 →
                </button>
              )}
            </div>
          )}
          {detectState === "ready" && recipe && kind && (
            <div style={{ display: "grid", gap: 4 }}>
              <div style={{ fontSize: 13, fontWeight: 800 }}>
                {kindLabel(kind)}으로 감지됐어요
              </div>
              <div style={{ fontSize: 11, color: "#666", fontWeight: 700, fontFamily: "IBM Plex Mono, monospace" }}>
                {recipe.commandLabel}
              </div>
            </div>
          )}
        </section>

        {/* 주행동: 실행 / 중지 */}
        <section className="card" style={{ display: "grid", gap: 8, padding: 12 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {!isActive && (
              <button
                className="btn"
                data-tour="run-app"
                disabled={detectState !== "ready" || starting}
                onClick={() => void handleStart()}
              >
                {status && isTerminal(status) ? "다시 실행" : "▶ 실행해보기"}
              </button>
            )}
            {isActive && (
              <button className="btn btn-danger" onClick={() => void handleStop()}>
                ■ 중지
              </button>
            )}
            {showPreviewButton && (
              <button className="btn btn-ghost" onClick={() => void handleOpenPreview()}>
                미리보기 열기 ↗
              </button>
            )}
            {(status === "installing" || status === "starting" || status === "running") && (
              <span className="spinner" />
            )}
          </div>

          {statusLine && (
            <div style={{ fontSize: 13, fontWeight: 800, color: TONE_COLOR[statusLine.tone] }}>
              {statusLine.text}
            </div>
          )}

          {electronRunning && (
            <div style={{ fontSize: 12, color: "#444", lineHeight: 1.6 }}>
              앱 창이 열렸어요 — 별도 창에서 직접 확인해 보세요. 닫으려면 아래 <b>중지</b>를 누르세요.
            </div>
          )}

          {status === "running" && onRunVerified && (
            runVerified ? (
              <div style={{ fontSize: 13, fontWeight: 800, color: "#166534" }}>
                {guardStatus === "ok"
                  ? "🎉 안전·작동 둘 다 확인했어요 — 한 사이클 완주!"
                  : "✓ 작동 확인 완료 — 안전도 확인해볼까요?"}
                {guardStatus !== "ok" && (
                  <button className="btn btn-ghost btn-sm" style={{ fontSize: 12, marginLeft: 6 }} onClick={() => onNavigate("home")}>
                    상태 확인 →
                  </button>
                )}
              </div>
            ) : (
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <button className="btn btn-sm" onClick={() => onRunVerified()}>
                  ✓ 잘 돼요 — 작동 확인 완료
                </button>
                <span style={{ fontSize: 12, color: "#888", fontWeight: 700 }}>
                  미리보기에서 직접 써보고 잘 되면 눌러주세요
                </span>
              </div>
            )
          )}

          {status === "running" && onRequestWorkHandoff && (
            <div style={{ display: "grid", gap: 6 }}>
              {!improveOpen ? (
                <button className="btn btn-ghost btn-sm" style={{ justifySelf: "start" }} onClick={() => setImproveOpen(true)}>
                  ✏ 뭔가 부족해요 — 고치고 싶어요
                </button>
              ) : (
                <div style={{ display: "grid", gap: 6 }}>
                  <textarea
                    value={improveText}
                    onChange={(e) => setImproveText(e.target.value)}
                    placeholder="써보니 어떤 점이 부족했나요? (예: 버튼이 너무 작아요 / 로그인 후 화면이 비어요)"
                    style={{ width: "100%", minHeight: 64, fontSize: 13, padding: 8, border: "2px solid #1A1A1A", borderRadius: 4, fontFamily: "inherit", boxSizing: "border-box" }}
                  />
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <button
                      className="btn"
                      disabled={improveText.trim().length === 0}
                      onClick={() => onRequestWorkHandoff({ kind: "improve", text: improveText.trim() })}
                    >
                      작업방에서 개선하기 →
                    </button>
                    <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("planning")} style={{ fontSize: 12 }}>
                      큰 방향을 바꿀래요 → 기획방
                    </button>
                    <button className="btn btn-ghost btn-sm" onClick={() => { setImproveOpen(false); setImproveText(""); }} style={{ fontSize: 12 }}>
                      닫기
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {status === "failed" && onRequestWorkHandoff && (
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <button className="btn" onClick={() => onRequestWorkHandoff({ kind: "error", text: collectErrorTail(lines) })}>
                이 에러 고쳐줘 → 작업방
              </button>
              <span style={{ fontSize: 12, color: "#888", fontWeight: 700 }}>
                실행 출력을 작업방으로 넘겨 AI가 원인을 찾아 고쳐요
              </span>
            </div>
          )}

          {startError && (
            <div
              style={{
                fontSize: 12,
                color: "#b42318",
                fontWeight: 700,
                background: "#FDECEA",
                border: "1px solid #1A1A1A",
                padding: "6px 8px",
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
              }}
            >
              {startError}
            </div>
          )}
        </section>

        {/* 실행 로그 */}
        {lines.length > 0 && (
          <section className="card" style={{ display: "grid", gap: 6, padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 900 }}>실행 로그</div>
            <div
              ref={outputRef}
              style={{
                maxHeight: 360,
                overflowY: "auto",
                background: "#1A1A1A",
                color: "#E5E5E5",
                padding: 10,
                borderRadius: 4,
                fontFamily: "IBM Plex Mono, monospace",
                fontSize: 11,
                lineHeight: 1.6,
              }}
            >
              {lines.map((l, i) => (
                <div key={i} style={lineStyle(l.stream)}>
                  {l.text}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 5️⃣ 가이드 — 실행은 검증의 한 축(작동). guard(안전)와 짝. */}
        <div style={{ fontSize: 12, color: "#888", fontWeight: 700, lineHeight: 1.6 }}>
          실행해보기는 "진짜 작동하나"를 확인하는 단계예요. 코드가 약속 범위를 지켰는지(안전)는
          <button
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 12, marginLeft: 6 }}
            onClick={() => onNavigate("home")}
          >
            홈 상태 확인 →
          </button>
        </div>
      </div>
    </div>
  );
}

function lineStyle(stream: "stdout" | "stderr"): CSSProperties {
  return {
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    color: stream === "stderr" ? "#FCA5A5" : "#E5E5E5",
  };
}
// === ANCHOR: RUN_PANEL_END ===
