// === ANCHOR: WORKROOM_START ===
// 작업방 Tier 1 (plans/2026-06-12-작업방-tier1-design.md §4·§5) — 기획안 기반 지시문을
// 사용자의 코딩 CLI(BYO, MVP=Claude Code)로 헤드리스 실행. M3: 체크포인트→실행→guard
// 안전 시퀀스를 자동으로 잇는다 — 이 시퀀스 강제가 외부 도구 대비 작업방의 존재 이유다.
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import { buildPlanningWorkInstruction } from "../lib/code-explorer/planningInstruction";
import { buildHandoffInstruction, type WorkHandoff } from "../lib/run-preview/workHandoff";
import { formatWorkOutputLine, type WorkDisplayLine } from "../lib/work-room/streamJson";
import { checkpointCreate, runVib, vibGuard } from "../lib/vib";
import type { GuardResult, PlanningContract } from "../lib/vib/types";
import type { Page } from "../lib/nav/stages";

interface WorkRoomProps {
  projectDir: string;
  planningPrompt: string;
  planningOutputPath: string | null;
  planningContract: PlanningContract | null;
  planningDocStale: boolean;
  /** 실행해보기 → 작업방 핸드오프(§4): error/improve. 마운트 시 consume-once 로 받는다. */
  workHandoff?: WorkHandoff | null;
  /** 핸드오프 소비 완료 — App 의 workHandoff 를 비워 재진입 재발동 방지. */
  onWorkHandoffConsumed?: () => void;
  onNavigate: (page: Page) => void;
  onOpenSettings: () => void;
  /** guard 자동 검사 결과를 가이드 신호(App guardStatus)로 보고 — 홈 '상태 확인'과 동일 채널 */
  onGuardResult?: (status: "ok" | "issue") => void;
}

type Phase =
  | "idle"
  | "confirm"
  | "checkpointing"
  | "checkpoint-blocked"
  | "running"
  | "verifying"
  | "finished";

type RunOutcome = "done" | "failed" | "cancelled";

interface WorkOutputEvent {
  runId: number;
  stream: "stdout" | "stderr";
  line: string;
}

interface WorkStatusEvent {
  runId: number;
  status: RunOutcome;
  exitCode: number | null;
}

interface WorkRoomStatusPayload {
  running: boolean;
  runId: number;
}

/** 러너가 .vibelign/logs/work-room-last.jsonl 에 영속한 지난 실행 기록(work_last_log). */
interface WorkLastLogLine {
  stream: "stdout" | "stderr";
  line: string;
}

interface WorkLastLog {
  provider: string | null;
  planPath: string | null;
  startedAt: number | null;
  finishedAt: number | null;
  status: string | null;
  exitCode: number | null;
  lines: WorkLastLogLine[];
}

const RESTORED_STATUS_LABEL: Record<string, string> = {
  done: "완료",
  failed: "실패",
  cancelled: "취소",
};

const LINE_STYLE: Record<WorkDisplayLine["kind"], CSSProperties> = {
  info: { fontFamily: "IBM Plex Mono, monospace", fontSize: 12, color: "#777" },
  text: { fontSize: 14, color: "#1A1A1A", whiteSpace: "pre-wrap", lineHeight: 1.6 },
  tool: { fontFamily: "IBM Plex Mono, monospace", fontSize: 12, color: "#555" },
  result: { fontSize: 14, color: "#166534", fontWeight: 700, whiteSpace: "pre-wrap" },
  error: { fontSize: 13, color: "#b42318", fontWeight: 700, whiteSpace: "pre-wrap" },
  raw: { fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "#888", whiteSpace: "pre-wrap", wordBreak: "break-word" },
};

/** MVP 프로바이더 — 코딩 에이전트로 검증된 CLI 만(기획안 §1). 러너 work_adapter 와 짝. */
const PROVIDER_DEFS: { id: "claude" | "codex"; label: string }[] = [
  { id: "claude", label: "Claude Code" },
  { id: "codex", label: "Codex" },
];

type ProviderId = (typeof PROVIDER_DEFS)[number]["id"];

/** 출력 무변화 경고 임계 — 첫 spawn 지연(Defender 등)을 덮을 만큼 넉넉하게(§10). */
const IDLE_HINT_MS = 90_000;

const OUTCOME_LABEL: Record<RunOutcome, { text: string; color: string }> = {
  done: { text: "✅ AI 작업이 끝났어요", color: "#166534" },
  failed: { text: "❌ AI 작업이 실패했어요 — 출력 끝부분을 확인하세요", color: "#b42318" },
  cancelled: { text: "✋ 작업을 취소했어요 — 이미 바뀐 파일이 있을 수 있어요", color: "#92400E" },
};

/** 체크포인트 설명용 요약 — 기획 요청 앞부분만. */
function noteSummary(prompt: string): string {
  const trimmed = prompt.trim().replace(/\s+/g, " ");
  return trimmed.length > 40 ? `${trimmed.slice(0, 40)}…` : trimmed || "기획안 작업";
}

export default function WorkRoom({
  projectDir,
  planningPrompt,
  planningOutputPath,
  planningContract,
  planningDocStale,
  workHandoff,
  onWorkHandoffConsumed,
  onNavigate,
  onOpenSettings,
  onGuardResult,
}: WorkRoomProps) {
  const [providers, setProviders] = useState<string[] | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<ProviderId | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [idleHint, setIdleHint] = useState(false);
  const lastOutputAtRef = useRef<number>(Date.now());
  const [runOutcome, setRunOutcome] = useState<RunOutcome | null>(null);
  const [items, setItems] = useState<{ runId: number; line: WorkDisplayLine }[]>([]);
  const [lastLog, setLastLog] = useState<WorkLastLog | null>(null);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const activeRunIdRef = useRef<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  // 실행해보기 핸드오프(§4) — 있으면 실행 지시문을 핸드오프(error/improve)용으로 바꾼다.
  const [handoff, setHandoff] = useState<WorkHandoff | null>(null);
  const [checkpointError, setCheckpointError] = useState<string | null>(null);
  const [guardResult, setGuardResult] = useState<GuardResult | null>(null);
  const [guardError, setGuardError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [anchorFixState, setAnchorFixState] = useState<"idle" | "running" | "error">("idle");
  const [anchorAutoApplied, setAnchorAutoApplied] = useState(false);
  const outputRef = useRef<HTMLDivElement | null>(null);

  const isDetected = (id: ProviderId) => providers?.includes(id) ?? false;
  const ready = selectedProvider !== null && isDetected(selectedProvider);
  const anyDetected = PROVIDER_DEFS.some((d) => isDetected(d.id));
  const instruction = planningOutputPath
    ? buildPlanningWorkInstruction({ prompt: planningPrompt, outputPath: planningOutputPath, contract: planningContract })
    : null;
  // 핸드오프(error/improve) 모드면 실행 지시문을 핸드오프 text 기반으로 교체(기획 표시는
  // instruction 그대로 유지). plan-less 도 동작 — planPath 없으면 text 만으로 작업(§4·§6).
  // != null 로 — 핸드오프 text 가 빈 문자열이어도 핸드오프 모드다(즉시 실패/빈 요청).
  // 빈 text 는 각 builder(buildRunErrorFixInstruction/buildImproveInstruction)가 degrade.
  const effectiveInstruction =
    handoff != null ? buildHandoffInstruction(handoff, planningOutputPath) : instruction;

  useEffect(() => {
    void invoke<string[]>("planning_provider_status")
      .then((list) => {
        setProviders(list);
        // 탐지된 첫 지원 CLI 를 기본 선택 — 없으면 null(실행 잠금 + 설치 안내).
        setSelectedProvider((cur) => cur ?? PROVIDER_DEFS.find((d) => list.includes(d.id))?.id ?? null);
      })
      .catch(() => setProviders([]));
  }, []);

  // 지난 실행 기록 복원 — 앱 재시작 후에도 직전 실행을 볼 수 있게(알람앱 트라이얼 요구).
  useEffect(() => {
    void invoke<WorkLastLog | null>("work_last_log", { cwd: projectDir })
      .then((log) => {
        if (log && log.lines.length > 0) setLastLog(log);
      })
      .catch(() => {});
  }, [projectDir]);

  // idle 경고 — "출력 무변화 + 실행 중" 기준(§10 P1). 슬립 복귀 직후 오탐이 가능하지만
  // 파괴적 동작 없는 힌트라 수용. 새 출력이 오면 리스너가 끈다.
  useEffect(() => {
    if (phase !== "running") {
      setIdleHint(false);
      return;
    }
    lastOutputAtRef.current = Date.now();
    const timer = window.setInterval(() => {
      if (Date.now() - lastOutputAtRef.current > IDLE_HINT_MS) setIdleHint(true);
    }, 10_000);
    return () => window.clearInterval(timer);
  }, [phase]);

  // 탭 이탈 후 복귀 — 백그라운드에서 계속 도는 작업의 상태만 복원한다.
  // (이탈 중 흘러간 라인의 백버퍼는 후속 — 지금은 "실행 중" 표시와 취소만 보장)
  useEffect(() => {
    void invoke<WorkRoomStatusPayload>("work_status")
      .then((s) => {
        if (s.running) {
          setActiveRunId(s.runId);
          activeRunIdRef.current = s.runId;
          setPhase("running");
        }
      })
      .catch(() => {});
  }, []);

  // 실행해보기 핸드오프 캡처(consume-once) — App 의 workHandoff(error/improve)가 실리면 로컬로
  // 받아 핸드오프 모드로 진입하고, onWorkHandoffConsumed 로 App 상태를 비운다(다음 렌더에 null →
  // 조기 return 으로 1회만). resetForNextRun 을 먼저, setHandoff 를 마지막에 둬 reset 이
  // 방금 받은 값을 지우지 않게 한다(advisor).
  useEffect(() => {
    // == null 로 검사 — 즉시 실패(출력 0줄)·빈 개선요청이면 text 가 빈 문자열("")로 와도
    // 핸드오프는 유효하다(builder 가 "출력/요청 없음"으로 degrade). !workHandoff 면 ""를
    // 삼켜 사용자가 작업방에서 막힌다(M3b 리뷰 HIGH).
    if (workHandoff == null) return;
    resetForNextRun();
    setHandoff(workHandoff);
    onWorkHandoffConsumed?.();
    // workHandoff 변화에만 반응 — reset/consumed 는 안정 함수(매 렌더 새로 만들어져도 의미 동일).
  }, [workHandoff]);

  useEffect(() => {
    let unOut: UnlistenFn | null = null;
    let unStatus: UnlistenFn | null = null;
    void listen<WorkOutputEvent>("work-output", (ev) => {
      lastOutputAtRef.current = Date.now();
      setIdleHint(false);
      const lines = formatWorkOutputLine(ev.payload.line);
      if (lines.length > 0) {
        setItems((prev) => [...prev, ...lines.map((line) => ({ runId: ev.payload.runId, line }))]);
      }
    }).then((u) => {
      unOut = u;
    });
    void listen<WorkStatusEvent>("work-status", (ev) => {
      // runId 미확정(invoke 응답 전 즉사) 동안은 동시 1개 제한 덕에 수신분을 신뢰한다.
      if (activeRunIdRef.current !== null && ev.payload.runId !== activeRunIdRef.current) return;
      setRunOutcome(ev.payload.status);
      // 종료 즉시 자동 검사(기획안 §4) — 취소·실패여도 파일이 바뀌었을 수 있어 동일 적용.
      setPhase("verifying");
      void verifyAfterRun();
    }).then((u) => {
      unStatus = u;
    });
    return () => {
      unOut?.();
      unStatus?.();
    };
    // verifyAfterRun 은 projectDir 만 캡처하는 안정 함수 — 리스너는 마운트 1회 등록.
  }, []);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
  }, [items, phase]);

  /** 앵커 권고 포함 여부 — 자동 처리 대상 식별. */
  function hasAnchorRecommendation(recommendations: string[]): boolean {
    return recommendations.some((r) => r.includes("앵커") || r.toLowerCase().includes("anchor"));
  }

  async function verifyAfterRun() {
    setGuardResult(null);
    setGuardError(null);
    setAnchorAutoApplied(false);
    try {
      let result = await vibGuard(projectDir, { strict: true });
      // 앵커 부재는 기계적으로 해결 가능한 준비 항목 — 사용자에게 시키지 않고 시퀀스가
      // 자동 처리한다(2026-06-12 피드백: "초보에겐 자동이 더 좋다"). 실행 전 체크포인트가
      // 안전망이고, 적용 사실은 결과 화면에 명시한다. 실패 시 기존 prepare + 수동 버튼 폴백.
      if (result.verdict === "prepare" && hasAnchorRecommendation(result.recommendations)) {
        try {
          const fix = await runVib(["anchor", "--auto"], projectDir);
          if (fix.ok) {
            setAnchorAutoApplied(true);
            result = await vibGuard(projectDir, { strict: true });
          }
        } catch {
          /* 자동 앵커 실패 — 첫 guard 결과 유지, 수동 버튼이 폴백 */
        }
      }
      setGuardResult(result);
      // 가이드 신호는 3단 verdict 기준 — 위생 누적(prepare)은 사이클 진행을 막지 않는다.
      onGuardResult?.(result.verdict === "stop" ? "issue" : "ok");
    } catch {
      setGuardError("자동 검사를 끝내지 못했어요 — 홈의 '상태 확인'으로 직접 검사해 주세요.");
    } finally {
      setPhase("finished");
    }
  }

  /** 시퀀스 1단계: 실행 전 체크포인트 자동 저장. 실패 시 실행 중단이 기본(기획안 §7). */
  async function startSequence() {
    setErrorMsg(null);
    setCheckpointError(null);
    setPhase("checkpointing");
    try {
      await checkpointCreate(projectDir, `작업방 실행 전: ${noteSummary(planningPrompt)}`);
    } catch (e: unknown) {
      setCheckpointError(e instanceof Error ? e.message : String(e));
      setPhase("checkpoint-blocked");
      return;
    }
    await launchRun();
  }

  /** 시퀀스 2단계: CLI 헤드리스 실행. */
  async function launchRun() {
    if (!effectiveInstruction) return;
    setErrorMsg(null);
    setItems([]);
    setLastLog(null);
    setRunOutcome(null);
    setGuardResult(null);
    setGuardError(null);
    setSaveState("idle");
    setPhase("running");
    try {
      const runId = await invoke<number>("work_run", {
        provider: selectedProvider,
        instruction: effectiveInstruction,
        cwd: projectDir,
        planPath: planningOutputPath,
      });
      setActiveRunId(runId);
      activeRunIdRef.current = runId;
    } catch (e: unknown) {
      setPhase("idle");
      setErrorMsg(String(e));
    }
  }

  /** 준비 항목(앵커 부재)을 그 자리에서 해결 — 사용자 추가 행동을 원클릭으로(2026-06-12 피드백). */
  async function autoFixAnchors() {
    setAnchorFixState("running");
    try {
      const res = await runVib(["anchor", "--auto"], projectDir);
      if (!res.ok) throw new Error(res.stderr || `exit ${res.exit_code}`);
      setAnchorFixState("idle");
      setPhase("verifying");
      await verifyAfterRun(); // 재검사 — 앵커가 채워지면 verdict 가 pass 로 올라간다
    } catch {
      setAnchorFixState("error");
    }
  }

  async function saveFinalCheckpoint() {
    setSaveState("saving");
    try {
      await checkpointCreate(projectDir, `작업방 완료: ${noteSummary(planningPrompt)}`);
      setSaveState("saved");
    } catch {
      setSaveState("error");
    }
  }

  function resetForNextRun() {
    setPhase("idle");
    setRunOutcome(null);
    setGuardResult(null);
    setGuardError(null);
    setErrorMsg(null);
    setCheckpointError(null);
    setSaveState("idle");
    setAnchorFixState("idle");
    setAnchorAutoApplied(false);
    setHandoff(null);
  }

  const visibleItems = items.filter((i) => activeRunId === null || i.runId === activeRunId);
  const restoredLines = useMemo(
    () => (lastLog ? lastLog.lines.flatMap((l) => formatWorkOutputLine(l.line)) : []),
    [lastLog],
  );
  const showRestored = phase !== "running" && visibleItems.length === 0 && restoredLines.length > 0;
  const displayLines: WorkDisplayLine[] = showRestored ? restoredLines : visibleItems.map((i) => i.line);
  // 3단 verdict(2026-06-12): pass(통과)·prepare(범위 안 + 준비 항목)·stop(실제 위반).
  // prepare 는 위반이 없으므로 완료 체크포인트 저장을 막지 않는다.
  const guardVerdict = guardResult?.verdict ?? null;
  const guardSafe = guardVerdict === "pass" || guardVerdict === "prepare";

  return (
    // App 페이지 영역(App.tsx)은 overflow:hidden 인데 display:flex 가 없어서 page-content
    // 의 flex:1 이 높이를 못 받는다 → height:100% 로 부모(flex item, definite height) 높이를
    // 직접 받아 overflow-y:auto 스크롤을 살린다. 전역 box-sizing:border-box 라 padding 포함.
    // 이게 없으면 긴 결과/지난 실행 보고서가 잘리고 스크롤도 안 된다(알람앱 트라이얼 발견).
    <div className="page-content" style={{ height: "100%" }}>
      <div style={{ display: "grid", gap: 12, maxWidth: 860 }}>
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div className="page-title">작업방</div>
      </div>

      {/* 기준 기획안 — 자유 요청은 MVP 비허용(기획안 §9): guard 의 약속 범위 기준점 유지.
          단 실행해보기 핸드오프(workHandoff: error/improve)면 핸드오프 배너가 이 자리를 대체한다(§4·§6). */}
      {handoff != null ? (
        <section className="card" style={{ display: "grid", gap: 6, padding: 12, background: "#FDECEA", border: "2px solid #1A1A1A" }}>
          <div style={{ fontSize: 12, fontWeight: 900, color: "#b42318" }}>
            {handoff.kind === "error" ? "실행 에러를 고칠게요" : "요청하신 개선을 작업할게요"}
          </div>
          <div style={{ fontSize: 12, color: "#444", lineHeight: 1.6 }}>
            {handoff.kind === "error"
              ? "실행해보기에서 앱이 켜지지 않았어요 — 아래 실행 출력을 AI 에게 넘겨 원인을 찾아 고칩니다."
              : "미리보기에서 부족했던 점을 AI 에게 넘겨 다듬습니다."}
            {planningOutputPath ? " 기획안 범위 안에서 작업해요." : ""}
          </div>
          <pre style={{ margin: 0, maxHeight: 140, overflowY: "auto", background: "#1A1A1A", color: "#FCA5A5", padding: 8, borderRadius: 4, fontFamily: "IBM Plex Mono, monospace", fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {handoff.text || (handoff.kind === "error"
              ? "(캡처된 실행 출력이 없어요 — AI 가 코드·설정에서 시작 실패 원인을 추정해요)"
              : "(구체적 요청이 없어요 — AI 가 완성도 낮은 부분을 한 가지 골라 개선해요)")}
          </pre>
        </section>
      ) : instruction ? (
        <section className="card" style={{ display: "grid", gap: 6, padding: 12, background: "#F5F1E3" }}>
          <div style={{ fontSize: 13, fontWeight: 900 }}>작업 기준 기획안</div>
          <div style={{ fontSize: 14, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {planningPrompt}
          </div>
          <div style={{ fontSize: 13, color: "#666", fontWeight: 700, overflowWrap: "anywhere" }}>{planningOutputPath}</div>
          {planningDocStale && (
            <div style={{ fontSize: 13, color: "#B45309", background: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 4, padding: "6px 8px", fontWeight: 700 }}>
              ⚠ 기획방 대화가 이 기획안 저장 이후 더 진행됐어요 — 기획방에서 다시 저장한 뒤 실행하는 걸 권장해요.
            </div>
          )}
        </section>
      ) : (
        <section className="card" style={{ display: "grid", gap: 8, padding: 16 }}>
          <div style={{ fontSize: 14, fontWeight: 800 }}>확정된 기획안이 아직 없어요</div>
          <div style={{ fontSize: 13, color: "#555", lineHeight: 1.6 }}>
            작업방은 기획안을 약속(목표·범위)으로 삼아 AI에게 일을 시킵니다. 먼저 기획방에서 기획안을 확정해 주세요.
          </div>
          <div>
            <button className="btn btn-sm" onClick={() => onNavigate("planning")}>
              기획하러 가기 →
            </button>
          </div>
        </section>
      )}

      {/* 실행 카드 — 체크포인트 → 실행 → 자동 검사 시퀀스 */}
      <section className="card" style={{ display: "grid", gap: 10, padding: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: 900 }}>실행 CLI</span>
          {providers === null && <span style={{ fontSize: 13, fontWeight: 700 }}>확인 중…</span>}
          {providers !== null &&
            PROVIDER_DEFS.map((def) => {
              const detected = isDetected(def.id);
              const selected = selectedProvider === def.id;
              return (
                <button
                  key={def.id}
                  className="btn btn-ghost btn-sm"
                  type="button"
                  disabled={!detected || phase !== "idle"}
                  aria-pressed={selected}
                  onClick={() => setSelectedProvider(def.id)}
                  style={{
                    fontSize: 12,
                    border: "2px solid #1A1A1A",
                    background: selected ? "#1A1A1A" : undefined,
                    color: selected ? "#fff" : undefined,
                    opacity: detected ? 1 : 0.4,
                  }}
                  title={detected ? undefined : "설치돼 있지 않거나 찾지 못했어요"}
                >
                  {def.label}
                  {detected ? " ✓" : ""}
                </button>
              );
            })}
          {providers !== null && !anyDetected && (
            <button className="btn btn-ghost btn-sm" onClick={onOpenSettings} style={{ fontSize: 12 }}>
              AI 도구 설치 도움받기 →
            </button>
          )}
        </div>

        {phase === "idle" && (
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            <button className="btn" disabled={!effectiveInstruction || !ready} onClick={() => setPhase("confirm")}>
              {handoff != null ? (handoff.kind === "error" ? "이 에러 고치기" : "이 개선 작업하기") : "AI에게 작업 시키기"}
            </button>
            <span style={{ fontSize: 13, color: "#666", fontWeight: 700 }}>
              체크포인트 저장 → 실행 → 검사가 자동으로 이어져요 · 외부 도구는 코드탐색의 "작업 지시 복사"
            </span>
          </div>
        )}

        {phase === "confirm" && (
          <div style={{ display: "grid", gap: 8, border: "2px solid #1A1A1A", padding: 12, background: "#FFF3D0" }}>
            <div style={{ fontSize: 13, fontWeight: 800 }}>실행 전 확인</div>
            {lastLog?.status === "done" && lastLog.planPath !== null && lastLog.planPath === planningOutputPath && (
              <div style={{ fontSize: 12, color: "#92400E", fontWeight: 700, background: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 4, padding: "6px 8px", lineHeight: 1.6 }}>
                ℹ 이 기획안은 이미 실행을 마쳤어요 — 다시 실행하면 같은 내용을 검토부터 다시 합니다(토큰 소모).
                새 작업이라면 기획방에서 기획안을 갱신한 뒤 실행하는 걸 권장해요.
              </div>
            )}
            <div style={{ fontSize: 12, color: "#444", lineHeight: 1.7 }}>
              · 실행하면 <b>① 체크포인트 자동 저장 → ② AI 실행 → ③ 끝나면 자동 검사</b>로 이어집니다
              <br />· 사용자 본인의 <b>{PROVIDER_DEFS.find((d) => d.id === selectedProvider)?.label ?? "AI CLI"} 계정·요금제</b>로 실행됩니다 (토큰이 소모돼요)
              <br />· 에이전트가 이 프로젝트의 파일을 실제로 수정해요 — 잘못되면 ①의 체크포인트로 되돌릴 수 있어요
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn" onClick={() => void startSequence()}>
                실행
              </button>
              <button className="btn btn-ghost" onClick={() => setPhase("idle")}>
                취소
              </button>
            </div>
          </div>
        )}

        {phase === "checkpointing" && (
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span className="spinner" />
            <span style={{ fontSize: 13, fontWeight: 800 }}>실행 전 체크포인트를 저장하는 중…</span>
          </div>
        )}

        {phase === "checkpoint-blocked" && (
          <div style={{ display: "grid", gap: 8, border: "2px solid #b42318", padding: 12, background: "#FDECEA" }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: "#b42318" }}>체크포인트 저장에 실패해서 실행을 멈췄어요</div>
            <div style={{ fontSize: 12, color: "#444", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
              {checkpointError}
              {"\n"}안전 저장 없이 실행하면 잘못됐을 때 되돌릴 지점이 없어요.
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("backups")} style={{ fontSize: 12 }}>
                백업 탭에서 확인 →
              </button>
              <button className="btn btn-danger btn-sm" onClick={() => void launchRun()} style={{ fontSize: 12 }}>
                위험을 알고 그래도 실행
              </button>
              <button className="btn btn-ghost btn-sm" onClick={resetForNextRun} style={{ fontSize: 12 }}>
                취소
              </button>
            </div>
          </div>
        )}

        {phase === "running" && (
          <div style={{ display: "grid", gap: 6 }}>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="spinner" />
              <span style={{ fontSize: 13, fontWeight: 800 }}>AI가 작업 중이에요…</span>
              <button className="btn btn-danger btn-sm" onClick={() => void invoke<boolean>("work_cancel")}>
                작업 취소
              </button>
            </div>
            {idleHint && (
              <div style={{ fontSize: 12, color: "#92400E", fontWeight: 700, background: "#FFF3D0", border: "1px solid #1A1A1A", padding: "6px 8px" }}>
                한동안 출력이 없어요 — 큰 작업 중일 수도 있지만, 멈춘 것 같으면 취소 후 다시 시도하세요.
              </div>
            )}
          </div>
        )}

        {phase === "verifying" && (
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span className="spinner" />
            <span style={{ fontSize: 13, fontWeight: 800 }}>
              {runOutcome ? OUTCOME_LABEL[runOutcome].text : ""} — 약속 범위를 검사하는 중…
            </span>
          </div>
        )}

        {phase === "finished" && runOutcome && (
          <div style={{ display: "grid", gap: 8 }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: OUTCOME_LABEL[runOutcome].color }}>
              {OUTCOME_LABEL[runOutcome].text}
            </div>

            {guardResult && (
              <div
                style={{
                  border: "1px solid #1A1A1A",
                  padding: "8px 10px",
                  background: guardVerdict === "pass" ? "#E8F6EC" : guardVerdict === "prepare" ? "#FEF3C7" : "#FDECEA",
                  display: "grid",
                  gap: 6,
                }}
              >
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 800,
                    color: guardVerdict === "pass" ? "#166534" : guardVerdict === "prepare" ? "#92400E" : "#b42318",
                  }}
                >
                  {guardVerdict === "pass"
                    ? "🛡 검사 통과 — AI가 약속 범위 안에서 작업했어요"
                    : guardVerdict === "prepare"
                      ? "🛡 이번 작업은 약속 범위 안 ✓ — 다음 실행 전에 준비하면 좋은 항목이 있어요"
                      : "🛡 멈출 사유를 찾았어요 — 아래 항목을 먼저 확인하세요"}
                </div>
                {anchorAutoApplied && (
                  <div style={{ fontSize: 12, color: "#166534", fontWeight: 700 }}>
                    🛡 안전 구역(앵커)을 자동으로 추가해뒀어요 — 다음 AI 작업부터 더 안전하게 적용돼요
                  </div>
                )}
                {guardVerdict === "stop" &&
                  guardResult.issues.slice(0, 3).map((issue, idx) => (
                    <div key={idx} style={{ fontSize: 12, color: "#444", lineHeight: 1.5 }}>
                      · {issue.found} <span style={{ color: "#888" }}>→ {issue.next_step}</span>
                    </div>
                  ))}
                {/* prepare 의 행동 항목, 그리고 stop 인데 이슈 목록이 빈 경우의 폴백은
                    recommendations 가 담고 있다 — 빈 화면 대신 다음 행동을 보여준다. */}
                {guardVerdict !== "pass" &&
                  (guardVerdict === "prepare" || guardResult.issues.length === 0) &&
                  guardResult.recommendations.slice(0, 3).map((rec, idx) => (
                    <div key={idx} style={{ fontSize: 12, color: "#444", lineHeight: 1.5 }}>
                      · {rec}
                    </div>
                  ))}
              </div>
            )}
            {guardError && (
              <div style={{ fontSize: 12, color: "#92400E", fontWeight: 700, background: "#FFF3D0", border: "1px solid #1A1A1A", padding: "8px 10px" }}>
                {guardError}
              </div>
            )}

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {guardVerdict === "prepare" &&
                guardResult?.recommendations.some((r) => r.includes("앵커") || r.toLowerCase().includes("anchor")) && (
                  <button
                    className="btn btn-sm"
                    disabled={anchorFixState === "running"}
                    onClick={() => void autoFixAnchors()}
                  >
                    {anchorFixState === "running" ? "앵커 추가 중…" : "🛡 앵커 자동 추가하고 다시 검사"}
                  </button>
                )}
              {anchorFixState === "error" && (
                <span style={{ fontSize: 12, fontWeight: 800, color: "#b42318", alignSelf: "center" }}>
                  앵커 추가 실패 — 코드탐색에서 직접 시도해 주세요
                </span>
              )}
              {guardSafe && saveState !== "saved" && (
                <button className="btn btn-sm" disabled={saveState === "saving"} onClick={() => void saveFinalCheckpoint()}>
                  {saveState === "saving" ? "저장 중…" : "✓ 이 상태를 체크포인트로 저장"}
                </button>
              )}
              {saveState === "saved" && (
                <span style={{ fontSize: 12, fontWeight: 800, color: "#166534", alignSelf: "center" }}>저장했어요 — 한 사이클 완료!</span>
              )}
              {saveState === "error" && (
                <span style={{ fontSize: 12, fontWeight: 800, color: "#b42318", alignSelf: "center" }}>저장 실패 — 백업 탭에서 시도해 주세요</span>
              )}
              {guardVerdict === "stop" && (
                <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("backups")} style={{ fontSize: 12 }}>
                  백업에서 되돌리기 →
                </button>
              )}
              {guardSafe && (
                <button className="btn btn-sm" onClick={() => onNavigate("run")}>
                  ▶ 실행해보기 →
                </button>
              )}
              <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("home")} style={{ fontSize: 12 }}>
                홈에서 상태 확인 →
              </button>
              <button className="btn btn-ghost btn-sm" onClick={resetForNextRun} style={{ fontSize: 12 }}>
                다시 실행 준비
              </button>
            </div>
          </div>
        )}

        {errorMsg && (
          <div style={{ fontSize: 12, color: "#b42318", fontWeight: 700, whiteSpace: "pre-wrap" }}>{errorMsg}</div>
        )}
      </section>

      {/* 스트리밍 출력 — 실행 중엔 라이브, 그 외엔 영속된 지난 실행 기록을 복원 표시 */}
      {(displayLines.length > 0 || phase === "running") && (
        <section className="card" style={{ padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, marginBottom: 8 }}>
            {showRestored ? "지난 실행 기록" : "진행 내용"}
          </div>
          {showRestored && lastLog && (
            <div style={{ fontSize: 12, color: "#777", fontWeight: 700, marginBottom: 6 }}>
              {lastLog.finishedAt ? new Date(lastLog.finishedAt * 1000).toLocaleString() : ""}
              {lastLog.provider
                ? ` · ${PROVIDER_DEFS.find((d) => d.id === lastLog.provider)?.label ?? lastLog.provider}`
                : ""}
              {lastLog.status ? ` · ${RESTORED_STATUS_LABEL[lastLog.status] ?? lastLog.status}` : ""}
            </div>
          )}
          <div
            ref={outputRef}
            // 실행 중엔 뷰포트 비례 높이 + 내부 스크롤로 최신 라인을 자동 추적하고,
            // 완료·복원 표시 땐 박스를 풀어 자연 높이로 흐르게 한다 — 긴 보고서를 380px
            // 안에 가두지 않고 바깥 page-content 스크롤로 전체를 본다(트라이얼 발견).
            style={{
              ...(phase === "running" ? { maxHeight: "55vh", overflowY: "auto" as const } : {}),
              display: "grid",
              gap: 6,
              border: "1px solid #D6D2C4",
              padding: 10,
              background: "#fff",
            }}
          >
            {displayLines.length === 0 && <div style={{ fontSize: 12, color: "#888" }}>출력을 기다리는 중…</div>}
            {displayLines.map((line, idx) => (
              <div key={idx} style={LINE_STYLE[line.kind]}>
                {line.text}
              </div>
            ))}
          </div>
        </section>
      )}
      </div>
    </div>
  );
}
// === ANCHOR: WORKROOM_END ===
