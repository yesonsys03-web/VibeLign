// === ANCHOR: WORKROOM_START ===
// 작업방 Tier 1 (plans/2026-06-12-작업방-tier1-design.md §5) — 기획안 기반 지시문을
// 사용자의 코딩 CLI(BYO, MVP=Claude Code)로 헤드리스 실행하고 출력을 스트리밍 표시.
// M2 범위: UI 셸 + 실행/취소/상태. 자동 체크포인트→guard 시퀀스·가이드 연동은 M3.
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

import { buildPlanningWorkInstruction } from "../lib/code-explorer/planningInstruction";
import { formatWorkOutputLine, type WorkDisplayLine } from "../lib/work-room/streamJson";
import type { PlanningContract } from "../lib/vib/types";
import type { Page } from "../lib/nav/stages";

interface WorkRoomProps {
  projectDir: string;
  planningPrompt: string;
  planningOutputPath: string | null;
  planningContract: PlanningContract | null;
  planningDocStale: boolean;
  onNavigate: (page: Page) => void;
  onOpenSettings: () => void;
}

type Phase = "idle" | "confirm" | "running" | "done" | "failed" | "cancelled";

interface WorkOutputEvent {
  runId: number;
  stream: "stdout" | "stderr";
  line: string;
}

interface WorkStatusEvent {
  runId: number;
  status: "done" | "failed" | "cancelled";
  exitCode: number | null;
}

interface WorkRoomStatusPayload {
  running: boolean;
  runId: number;
}

const LINE_STYLE: Record<WorkDisplayLine["kind"], CSSProperties> = {
  info: { fontFamily: "IBM Plex Mono, monospace", fontSize: 12, color: "#777" },
  text: { fontSize: 14, color: "#1A1A1A", whiteSpace: "pre-wrap", lineHeight: 1.6 },
  tool: { fontFamily: "IBM Plex Mono, monospace", fontSize: 12, color: "#555" },
  result: { fontSize: 14, color: "#166534", fontWeight: 700, whiteSpace: "pre-wrap" },
  error: { fontSize: 13, color: "#b42318", fontWeight: 700, whiteSpace: "pre-wrap" },
  raw: { fontFamily: "IBM Plex Mono, monospace", fontSize: 11, color: "#888", whiteSpace: "pre-wrap", wordBreak: "break-word" },
};

const PHASE_BANNER: Partial<Record<Phase, { text: string; color: string; bg: string }>> = {
  done: {
    text: "✅ 작업이 끝났어요 — 홈의 '상태 확인'으로 약속 범위를 검사하세요 (자동 검사는 다음 업데이트에서 이어집니다)",
    color: "#166534",
    bg: "#E8F6EC",
  },
  failed: { text: "❌ 작업이 실패했어요 — 출력 끝부분을 확인하세요. 코드가 바뀌었다면 백업 탭에서 되돌릴 수 있어요", color: "#b42318", bg: "#FDECEA" },
  cancelled: { text: "✋ 작업을 취소했어요 — 이미 바뀐 파일이 있을 수 있으니 백업 탭에서 확인하세요", color: "#92400E", bg: "#FFF3D0" },
};

export default function WorkRoom({
  projectDir,
  planningPrompt,
  planningOutputPath,
  planningContract,
  planningDocStale,
  onNavigate,
  onOpenSettings,
}: WorkRoomProps) {
  const [providers, setProviders] = useState<string[] | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [items, setItems] = useState<{ runId: number; line: WorkDisplayLine }[]>([]);
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const activeRunIdRef = useRef<number | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const outputRef = useRef<HTMLDivElement | null>(null);

  const claudeReady = providers?.includes("claude") ?? false;
  const instruction = planningOutputPath
    ? buildPlanningWorkInstruction({ prompt: planningPrompt, outputPath: planningOutputPath, contract: planningContract })
    : null;

  useEffect(() => {
    void invoke<string[]>("planning_provider_status")
      .then(setProviders)
      .catch(() => setProviders([]));
  }, []);

  // 탭 이탈 후 복귀 — 백그라운드에서 계속 도는 작업의 상태만 복원한다.
  // (이탈 중 흘러간 라인의 백버퍼는 M3+ — 지금은 "실행 중" 표시와 취소만 보장)
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

  useEffect(() => {
    let unOut: UnlistenFn | null = null;
    let unStatus: UnlistenFn | null = null;
    void listen<WorkOutputEvent>("work-output", (ev) => {
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
      setPhase(ev.payload.status);
    }).then((u) => {
      unStatus = u;
    });
    return () => {
      unOut?.();
      unStatus?.();
    };
  }, []);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
  }, [items, phase]);

  async function startRun() {
    if (!instruction) return;
    setErrorMsg(null);
    setItems([]);
    setPhase("running");
    try {
      const runId = await invoke<number>("work_run", {
        provider: "claude",
        instruction,
        cwd: projectDir,
      });
      setActiveRunId(runId);
      activeRunIdRef.current = runId;
    } catch (e: unknown) {
      setPhase("idle");
      setErrorMsg(String(e));
    }
  }

  const visibleItems = items.filter((i) => activeRunId === null || i.runId === activeRunId);
  const banner = PHASE_BANNER[phase];

  return (
    <div style={{ display: "grid", gap: 12, maxWidth: 860 }}>
      <div className="page-header" style={{ marginBottom: 0 }}>
        <div className="page-title">작업방</div>
      </div>

      {/* 기준 기획안 — 자유 요청은 MVP 비허용(기획안 §9): guard 의 약속 범위 기준점 유지 */}
      {instruction ? (
        <section className="card" style={{ display: "grid", gap: 6, padding: 12, background: "#F5F1E3" }}>
          <div style={{ fontSize: 12, fontWeight: 900 }}>작업 기준 기획안</div>
          <div style={{ fontSize: 13, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {planningPrompt}
          </div>
          <div style={{ fontSize: 11, color: "#666", fontWeight: 700, overflowWrap: "anywhere" }}>{planningOutputPath}</div>
          {planningDocStale && (
            <div style={{ fontSize: 11, color: "#B45309", background: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 4, padding: "6px 8px", fontWeight: 700 }}>
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

      {/* 실행 카드 */}
      <section className="card" style={{ display: "grid", gap: 10, padding: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 12, fontWeight: 900 }}>실행 CLI</span>
          <span style={{ fontSize: 13, fontWeight: 700 }}>
            Claude Code {providers === null ? "(확인 중…)" : claudeReady ? "✓ 사용 가능" : "— 찾지 못했어요"}
          </span>
          {providers !== null && !claudeReady && (
            <button className="btn btn-ghost btn-sm" onClick={onOpenSettings} style={{ fontSize: 11 }}>
              AI 도구 설치 도움받기 →
            </button>
          )}
        </div>

        {phase === "idle" && (
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn" disabled={!instruction || !claudeReady} onClick={() => setPhase("confirm")}>
              AI에게 작업 시키기
            </button>
            <span style={{ fontSize: 11, color: "#888", fontWeight: 700 }}>
              외부 도구에서 직접 실행하려면 코드탐색의 "작업 지시 복사"를 쓰세요
            </span>
          </div>
        )}

        {phase === "confirm" && (
          <div style={{ display: "grid", gap: 8, border: "2px solid #1A1A1A", padding: 12, background: "#FFF3D0" }}>
            <div style={{ fontSize: 13, fontWeight: 800 }}>실행 전 확인</div>
            <div style={{ fontSize: 12, color: "#444", lineHeight: 1.7 }}>
              · 사용자 본인의 <b>Claude Code 계정·요금제</b>로 실행됩니다 (토큰이 소모돼요)
              <br />· 에이전트가 이 프로젝트의 파일을 실제로 수정합니다 — 백업 탭에서 <b>체크포인트를 먼저 저장</b>했는지 확인하세요 (자동 저장은 다음 업데이트에서 이어집니다)
              <br />· 실행 중 언제든 취소할 수 있어요
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn" onClick={() => void startRun()}>
                실행
              </button>
              <button className="btn btn-ghost" onClick={() => setPhase("idle")}>
                취소
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("backups")} style={{ fontSize: 11 }}>
                백업 탭에서 체크포인트 저장 →
              </button>
            </div>
          </div>
        )}

        {phase === "running" && (
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span className="spinner" />
            <span style={{ fontSize: 13, fontWeight: 800 }}>AI가 작업 중이에요…</span>
            <button className="btn btn-danger btn-sm" onClick={() => void invoke<boolean>("work_cancel")}>
              작업 취소
            </button>
          </div>
        )}

        {banner && (
          <div style={{ fontSize: 13, fontWeight: 700, color: banner.color, background: banner.bg, border: "1px solid #1A1A1A", padding: "8px 10px", lineHeight: 1.6 }}>
            {banner.text}
          </div>
        )}
        {banner && (
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("home")} style={{ fontSize: 11 }}>
              홈에서 상태 확인 →
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => onNavigate("backups")} style={{ fontSize: 11 }}>
              백업 탭 →
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => setPhase("idle")} style={{ fontSize: 11 }}>
              다시 실행 준비
            </button>
          </div>
        )}

        {errorMsg && (
          <div style={{ fontSize: 12, color: "#b42318", fontWeight: 700, whiteSpace: "pre-wrap" }}>{errorMsg}</div>
        )}
      </section>

      {/* 스트리밍 출력 */}
      {(visibleItems.length > 0 || phase === "running") && (
        <section className="card" style={{ padding: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 900, marginBottom: 8 }}>진행 내용</div>
          <div
            ref={outputRef}
            style={{ maxHeight: 380, overflowY: "auto", display: "grid", gap: 6, border: "1px solid #D6D2C4", padding: 10, background: "#fff" }}
          >
            {visibleItems.length === 0 && <div style={{ fontSize: 12, color: "#888" }}>출력을 기다리는 중…</div>}
            {visibleItems.map((item, idx) => (
              <div key={idx} style={LINE_STYLE[item.line.kind]}>
                {item.line.text}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
// === ANCHOR: WORKROOM_END ===
