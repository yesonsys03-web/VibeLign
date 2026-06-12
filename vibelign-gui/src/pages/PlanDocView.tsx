// === ANCHOR: PLAN_DOC_VIEW_START ===
import { useEffect, useState } from "react";
import DocumentPane from "../components/docs/DocumentPane";
import { loadDoc } from "../lib/docs";
import {
  deletePlanningChatSession,
  emptyPlanningTrash,
  listPlanningChatSessions,
  listTrashedPlanningSessions,
  restorePlanningChatSession,
  type ReadFileResult,
} from "../lib/vib";
import type { PlanningSessionSummary, TrashedSessionSummary } from "../lib/vib/types";

interface PlanDocViewProps {
  projectDir: string;
  /** 현재 활성 세션 id. 목록의 기본 선택으로 사용. */
  activeSessionId?: string | null;
  /** 저장된 기획안이 하나도 없을 때 기획 시작으로 이동. */
  onStart?: () => void;
  /** 한 기획안(세션)이 삭제된 뒤 호출(예: 활성 세션이면 호출부가 정리). */
  onDeleted?: (sessionId: string) => void;
  /** 이 기획안을 기획방에서 이어서 수정(세션 재개). */
  onEdit?: (sessionId: string) => void;
}

function fileName(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const slash = normalized.lastIndexOf("/");
  return slash >= 0 ? normalized.slice(slash + 1) : normalized;
}

/**
 * 기획 단계 '기획안' 서브탭. 저장된 기획안 전체를 왼쪽 목록 + 오른쪽 본문(마크다운)으로
 * 보여주고, 항목마다 수정(기획방 재개)·삭제(휴지통)한다. 사이드바 하단 휴지통에서
 * 복구/비우기, 삭제 직후엔 실행취소 토스트. 휴지통은 30일 뒤 자동 정리된다.
 */
export default function PlanDocView({ projectDir, activeSessionId, onStart, onDeleted, onEdit }: PlanDocViewProps) {
  const [plans, setPlans] = useState<PlanningSessionSummary[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [doc, setDoc] = useState<ReadFileResult | null>(null);
  const [docLoading, setDocLoading] = useState(false);
  const [docError, setDocError] = useState<string | null>(null);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [trashed, setTrashed] = useState<TrashedSessionSummary[] | null>(null);
  const [trashOpen, setTrashOpen] = useState(false);
  const [restoringId, setRestoringId] = useState<string | null>(null);
  const [confirmEmpty, setConfirmEmpty] = useState(false);
  const [emptying, setEmptying] = useState(false);
  const [trashError, setTrashError] = useState<string | null>(null);
  const [undo, setUndo] = useState<{ sessionId: string; title: string } | null>(null);

  async function refreshPlans() {
    try {
      const rows = await listPlanningChatSessions(projectDir);
      const saved = rows.filter((row) => Boolean(row.outputPath));
      setPlans(saved);
      setSelectedId((current) => {
        if (current && saved.some((p) => p.sessionId === current)) return current;
        if (activeSessionId && saved.some((p) => p.sessionId === activeSessionId)) return activeSessionId;
        return saved[0]?.sessionId ?? null;
      });
    } catch {
      setPlans([]);
    }
  }

  async function refreshTrashed() {
    try {
      setTrashed(await listTrashedPlanningSessions(projectDir));
    } catch {
      setTrashed([]);
    }
  }

  useEffect(() => {
    void refreshPlans();
    void refreshTrashed();
  }, [projectDir, activeSessionId]);

  const selected = plans?.find((p) => p.sessionId === selectedId) ?? null;
  const selectedPath = selected?.outputPath ?? null;

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

  // 실행취소 토스트 6초 뒤 자동 사라짐.
  useEffect(() => {
    if (!undo) return;
    const timer = setTimeout(() => setUndo(null), 6000);
    return () => clearTimeout(timer);
  }, [undo]);

  async function handleDelete(plan: PlanningSessionSummary) {
    setConfirmingId(null);
    setDeleteError(null);
    setDeletingId(plan.sessionId);
    try {
      await deletePlanningChatSession(projectDir, plan.sessionId);
      await refreshPlans();
      await refreshTrashed();
      setUndo({ sessionId: plan.sessionId, title: plan.title || "기획안" });
      onDeleted?.(plan.sessionId);
    } catch (err: unknown) {
      setDeleteError(err instanceof Error ? err.message : typeof err === "string" ? err : "삭제하지 못했어요.");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleRestore(sessionId: string) {
    setTrashError(null);
    setRestoringId(sessionId);
    try {
      await restorePlanningChatSession(projectDir, sessionId);
      setUndo((current) => (current?.sessionId === sessionId ? null : current));
      await refreshPlans();
      await refreshTrashed();
    } catch (err: unknown) {
      setTrashError(err instanceof Error ? err.message : typeof err === "string" ? err : "복구하지 못했어요.");
    } finally {
      setRestoringId(null);
    }
  }

  async function handleEmpty() {
    setConfirmEmpty(false);
    setTrashError(null);
    setEmptying(true);
    try {
      await emptyPlanningTrash(projectDir);
      setUndo(null);
      await refreshTrashed();
    } catch (err: unknown) {
      setTrashError(err instanceof Error ? err.message : typeof err === "string" ? err : "비우지 못했어요.");
    } finally {
      setEmptying(false);
    }
  }

  const trashCount = trashed?.length ?? 0;

  // 저장된 기획안도, 휴지통도 비어 있을 때(둘 다 로딩 끝난 뒤에만 판단).
  if (plans !== null && plans.length === 0 && trashed !== null && trashCount === 0) {
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
    <div style={{ height: "100%", display: "flex", position: "relative" }}>
      <div style={{ width: 240, flexShrink: 0, borderRight: "1px solid #1A1A1A", display: "flex", flexDirection: "column", overflow: "auto" }}>
        <div style={{ padding: "6px 10px", fontSize: 12, fontWeight: 700, color: "#888", borderBottom: "1px solid #1A1A1A" }}>
          기획안 {plans ? `(${plans.length})` : ""}
        </div>
        {deleteError && <div style={{ padding: "4px 10px", fontSize: 12, color: "#B91C1C", fontWeight: 700 }}>삭제 오류: {deleteError}</div>}
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
                <div style={{ fontSize: 12, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {plan.title || "(제목 없음)"}
                  {plan.docStale && (
                    <span title="저장 후 대화가 더 진행됐어요. 기획방에서 다시 저장하면 반영됩니다." style={{ marginLeft: 6, fontSize: 12, fontWeight: 800, color: "#B45309", background: "#FEF3C7", padding: "1px 4px", borderRadius: 3, verticalAlign: "middle" }}>
                      다시 저장 필요
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 12, opacity: 0.7, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{plan.outputPath ? fileName(plan.outputPath) : ""}</div>
              </button>
              {confirmingId === plan.sessionId ? (
                <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", gap: 2, padding: "0 4px" }}>
                  <button type="button" onClick={() => void handleDelete(plan)} title="휴지통으로" style={{ border: "none", background: "#B91C1C", color: "#fff", fontSize: 12, fontWeight: 800, padding: "2px 6px", cursor: "pointer" }}>삭제</button>
                  <button type="button" onClick={() => setConfirmingId(null)} style={{ border: "1px solid #888", background: "#fff", fontSize: 12, padding: "2px 6px", cursor: "pointer" }}>취소</button>
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center" }}>
                  {onEdit && (
                    <button type="button" onClick={() => onEdit(plan.sessionId)} disabled={deletingId === plan.sessionId} title="기획방에서 이어서 수정" style={{ border: "none", background: "transparent", color: active ? "#fff" : "#888", fontSize: 12, fontWeight: 700, padding: "0 6px", cursor: "pointer", whiteSpace: "nowrap" }}>수정</button>
                  )}
                  <button type="button" onClick={() => setConfirmingId(plan.sessionId)} disabled={deletingId === plan.sessionId} title="이 기획안 삭제(휴지통)" style={{ border: "none", background: "transparent", color: active ? "#fff" : "#888", fontSize: 13, padding: "0 8px", cursor: "pointer" }}>🗑</button>
                </div>
              )}
            </div>
          );
        })}

        {/* 휴지통 */}
        <div style={{ marginTop: "auto", borderTop: "1px solid #1A1A1A" }}>
          <button
            type="button"
            onClick={() => setTrashOpen((open) => !open)}
            style={{ width: "100%", textAlign: "left", border: "none", background: "transparent", color: "#888", fontSize: 12, fontWeight: 700, padding: "6px 10px", cursor: "pointer" }}
          >
            {trashOpen ? "▾" : "▸"} 🗑 휴지통 ({trashCount})
          </button>
          {trashOpen && (
            <div style={{ padding: "0 6px 6px" }}>
              {trashError && <div style={{ fontSize: 12, color: "#B91C1C", fontWeight: 700, padding: "2px 4px" }}>{trashError}</div>}
              {trashCount === 0 && <div style={{ fontSize: 12, color: "#888", padding: "2px 4px" }}>비어 있음</div>}
              {trashed?.map((item) => (
                <div key={item.sessionId} style={{ display: "flex", alignItems: "center", gap: 4, padding: "3px 4px", borderBottom: "1px solid #EEE" }}>
                  <span style={{ flex: 1, fontSize: 12, color: "#666", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={item.outputPath ?? undefined}>
                    {item.title || (item.outputPath ? fileName(item.outputPath) : "(제목 없음)")}
                  </span>
                  <button type="button" onClick={() => void handleRestore(item.sessionId)} disabled={restoringId === item.sessionId} style={{ border: "1px solid #1A1A1A", background: "#fff", fontSize: 12, fontWeight: 700, padding: "1px 6px", cursor: "pointer", whiteSpace: "nowrap" }}>
                    {restoringId === item.sessionId ? "복구 중…" : "복구"}
                  </button>
                </div>
              ))}
              {trashCount > 0 && (
                confirmEmpty ? (
                  <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
                    <button type="button" onClick={() => void handleEmpty()} disabled={emptying} style={{ flex: 1, border: "2px solid #B91C1C", background: "#B91C1C", color: "#fff", fontSize: 12, fontWeight: 800, padding: "3px 6px", cursor: "pointer" }}>
                      {emptying ? "비우는 중…" : "영구 삭제"}
                    </button>
                    <button type="button" onClick={() => setConfirmEmpty(false)} style={{ flex: 1, border: "1px solid #888", background: "#fff", fontSize: 12, padding: "3px 6px", cursor: "pointer" }}>취소</button>
                  </div>
                ) : (
                  <button type="button" onClick={() => setConfirmEmpty(true)} style={{ width: "100%", marginTop: 6, border: "1px solid #B91C1C", background: "#fff", color: "#B91C1C", fontSize: 12, fontWeight: 700, padding: "3px 6px", cursor: "pointer" }}>휴지통 비우기</button>
                )
              )}
            </div>
          )}
        </div>
      </div>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {selectedPath && (
          <div style={{ padding: "6px 12px", fontSize: 12, color: "#555", borderBottom: "1px solid #1A1A1A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {selectedPath}
          </div>
        )}
        {selected?.docStale && (
          <div style={{ padding: "6px 12px", fontSize: 12, color: "#B45309", background: "#FEF3C7", borderBottom: "1px solid #1A1A1A" }}>
            저장 후 기획방 대화가 더 진행됐어요 — {onEdit ? "‘수정’으로 들어가 다시 저장하면" : "기획방에서 다시 저장하면"} 최신 내용이 반영됩니다.
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

      {undo && (
        <div style={{ position: "absolute", bottom: 16, left: "50%", transform: "translateX(-50%)", background: "#1A1A1A", color: "#fff", padding: "8px 14px", borderRadius: 6, display: "flex", alignItems: "center", gap: 12, boxShadow: "0 4px 12px rgba(0,0,0,0.4)", zIndex: 50, fontSize: 12 }}>
          <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>휴지통으로 보냈어요 · {undo.title}</span>
          <button type="button" onClick={() => void handleRestore(undo.sessionId)} style={{ border: "none", background: "transparent", color: "#7DD3FC", fontWeight: 800, fontSize: 12, cursor: "pointer", whiteSpace: "nowrap" }}>실행취소</button>
        </div>
      )}
    </div>
  );
}
// === ANCHOR: PLAN_DOC_VIEW_END ===
