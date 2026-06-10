// === ANCHOR: PLAN_DOC_VIEW_START ===
import { useEffect, useState } from "react";
import DocumentPane from "../components/docs/DocumentPane";
import { loadDoc } from "../lib/docs";
import { deletePlanningChatSession, listPlanningChatSessions, type ReadFileResult } from "../lib/vib";
import type { PlanningSessionSummary } from "../lib/vib/types";

interface PlanDocViewProps {
  projectDir: string;
  /** 현재 활성 세션 id. 목록의 기본 선택으로 사용. */
  activeSessionId?: string | null;
  /** 저장된 기획안이 하나도 없을 때 기획 시작으로 이동. */
  onStart?: () => void;
  /** 한 기획안(세션)이 삭제된 뒤 호출(예: 활성 세션이면 호출부가 정리). */
  onDeleted?: (sessionId: string) => void;
}

function fileName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const slash = normalized.lastIndexOf("/");
  return slash >= 0 ? normalized.slice(slash + 1) : normalized;
}

/**
 * 기획 단계 '기획안' 서브탭. 저장된 기획안(세션별 outputPath) 전체를 왼쪽 목록으로,
 * 선택한 기획안 본문을 오른쪽에 문서 탭과 동일한 마크다운 렌더로 보여준다.
 * 항목마다 삭제할 수 있어 쌓인 기획안을 이 화면에서 바로 정리한다.
 */
export default function PlanDocView({ projectDir, activeSessionId, onStart, onDeleted }: PlanDocViewProps) {
  const [plans, setPlans] = useState<PlanningSessionSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [doc, setDoc] = useState<ReadFileResult | null>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // 목록 로드: 저장된(outputPath 있는) 세션만. 기본 선택 = 활성 세션 또는 첫 항목.
  useEffect(() => {
    let cancelled = false;
    listPlanningChatSessions(projectDir)
      .then((rows) => {
        if (cancelled) return;
        const saved = rows.filter((row) => Boolean(row.outputPath));
        setPlans(saved);
        setSelectedId((current) => {
          if (current && saved.some((p) => p.sessionId === current)) return current;
          if (activeSessionId && saved.some((p) => p.sessionId === activeSessionId)) return activeSessionId;
          return saved[0]?.sessionId ?? null;
        });
      })
      .catch(() => {
        if (!cancelled) setPlans([]);
      });
    return () => {
      cancelled = true;
    };
  }, [projectDir, activeSessionId]);

  const selected = plans?.find((p) => p.sessionId === selectedId) ?? null;
  const selectedPath = selected?.outputPath ?? null;

  // 선택한 기획안 본문 로드.
  useEffect(() => {
    if (!selectedPath) {
      setDoc(null);
      setDocError(null);
      return;
    }
    let cancelled = false;
    setDocLoading(true);
    setDocError(null);
    loadDoc(projectDir, selectedPath)
      .then((result) => {
        if (!cancelled) setDoc(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setDocError(err instanceof Error ? err.message : typeof err === "string" ? err : "기획안을 불러오지 못했어요.");
          setDoc(null);
        }
      })
      .finally(() => {
        if (!cancelled) setDocLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectDir, selectedPath]);

  async function handleDelete(sessionId: string) {
    setConfirmingId(null);
    setDeleteError(null);
    setDeletingId(sessionId);
    try {
      await deletePlanningChatSession(projectDir, sessionId);
      const remaining = (plans ?? []).filter((row) => row.sessionId !== sessionId);
      setPlans(remaining);
      if (selectedId === sessionId) {
        setSelectedId(remaining[0]?.sessionId ?? null);
      }
      onDeleted?.(sessionId);
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : typeof err === "string" ? err : "삭제하지 못했어요.");
    } finally {
      setDeletingId(null);
    }
  }

  // 저장된 기획안이 하나도 없을 때.
  if (plans !== null && plans.length === 0) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 12, color: "#888" }}>
        <div style={{ fontSize: 32 }}>📋</div>
        <div style={{ fontSize: 14 }}>아직 저장된 기획안이 없어요.</div>
        <div style={{ fontSize: 12, color: "#666" }}>기획방에서 대화로 기획안을 만들면 여기에 쌓입니다.</div>
        {onStart && (
          <button className="nav-tab" style={{ marginTop: 4 }} onClick={onStart}>
            기획 시작하기 →
          </button>
        )}
      </div>
    );
  }

  return (
    <div style={{ height: "100%", display: "flex" }}>
      <div style={{ width: 240, flexShrink: 0, borderRight: "1px solid #1A1A1A", display: "flex", flexDirection: "column", overflow: "auto" }}>
        <div style={{ padding: "6px 10px", fontSize: 11, fontWeight: 700, color: "#888", borderBottom: "1px solid #1A1A1A" }}>
          기획안 {plans ? `(${plans.length})` : ""}
        </div>
        {deleteError && <div style={{ padding: "4px 10px", fontSize: 11, color: "#B91C1C", fontWeight: 700 }}>삭제 오류: {deleteError}</div>}
        {plans === null && <div style={{ padding: 10, fontSize: 12, color: "#888" }}>불러오는 중…</div>}
        {plans?.map((plan) => {
          const active = plan.sessionId === selectedId;
          return (
            <div key={plan.sessionId} style={{ display: "flex", alignItems: "stretch", borderBottom: "1px solid #EEE", background: active ? "#1A1A1A" : "transparent" }}>
              <button
                type="button"
                onClick={() => setSelectedId(plan.sessionId)}
                disabled={deletingId === plan.sessionId}
                title={plan.outputPath ?? undefined}
                style={{ flex: 1, textAlign: "left", border: "none", background: "transparent", color: active ? "#fff" : "#333", padding: "8px 10px", cursor: "pointer", overflow: "hidden", opacity: deletingId === plan.sessionId ? 0.5 : 1 }}
              >
                <div style={{ fontSize: 12, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{plan.title || "(제목 없음)"}</div>
                <div style={{ fontSize: 10, opacity: 0.7, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{plan.outputPath ? fileName(plan.outputPath) : ""}</div>
              </button>
              {confirmingId === plan.sessionId ? (
                <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 2, padding: "0 4px" }}>
                  <button type="button" onClick={() => void handleDelete(plan.sessionId)} title="이 기획을 영구 삭제" style={{ border: "none", background: "#B91C1C", color: "#fff", fontSize: 10, fontWeight: 800, padding: "2px 6px", cursor: "pointer" }}>삭제</button>
                  <button type="button" onClick={() => setConfirmingId(null)} style={{ border: "1px solid #888", background: "#fff", fontSize: 10, padding: "2px 6px", cursor: "pointer" }}>취소</button>
                </div>
              ) : (
                <button type="button" onClick={() => setConfirmingId(plan.sessionId)} disabled={deletingId === plan.sessionId} title="이 기획안 삭제" style={{ border: "none", background: "transparent", color: active ? "#fff" : "#888", fontSize: 13, padding: "0 8px", cursor: "pointer" }}>🗑</button>
              )}
            </div>
          );
        })}
      </div>
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {selectedPath && (
          <div style={{ padding: "6px 12px", fontSize: 12, color: "#555", borderBottom: "1px solid #1A1A1A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {selectedPath}
          </div>
        )}
        <div style={{ flex: 1, overflow: "hidden" }}>
          {docLoading ? (
            <div style={{ padding: 24, color: "#888", fontSize: 13 }}>기획안을 불러오는 중…</div>
          ) : docError ? (
            <div style={{ padding: 24, color: "#F87171", fontSize: 13 }}>오류: {docError}</div>
          ) : doc ? (
            <DocumentPane path={doc.path} content={doc.content} />
          ) : (
            <div style={{ padding: 24, color: "#888", fontSize: 13 }}>왼쪽에서 기획안을 선택하세요.</div>
          )}
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: PLAN_DOC_VIEW_END ===
