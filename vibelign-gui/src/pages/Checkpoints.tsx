// === ANCHOR: CHECKPOINTS_START ===
import { useState, useEffect, useCallback } from "react";
import { checkpointList, checkpointCreate, undoCheckpoint } from "../lib/vib";

interface Checkpoint {
  checkpoint_id: string;
  message: string;
  created_at?: string;
  file_count?: number;
}

interface CheckpointsProps {
  projectDir: string;
}

export default function Checkpoints({ projectDir }: CheckpointsProps) {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [newMsg, setNewMsg] = useState("");
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await checkpointList(projectDir) as { checkpoints?: Checkpoint[] };
      setCheckpoints(data.checkpoints ?? []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectDir]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate() {
    if (!newMsg.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await checkpointCreate(projectDir, newMsg.trim());
      setNewMsg("");
      setSuccessMsg("체크포인트 저장됨");
      setTimeout(() => setSuccessMsg(null), 2000);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setCreating(false);
    }
  }

  async function handleRestore(id: string) {
    if (!confirm(`[${id.slice(0, 12)}...] 으로 복원할까요?`)) return;
    setRestoring(id);
    setError(null);
    try {
      await undoCheckpoint(projectDir, id);
      setSuccessMsg("복원 완료!");
      setTimeout(() => setSuccessMsg(null), 2000);
      load();
    } catch (e) {
      setError(String(e));
    } finally {
      setRestoring(null);
    }
  }

  function formatDate(dateStr?: string) {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleString("ko-KR", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return dateStr.slice(0, 16);
    }
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header">
        <span className="page-title">CHECKPOINTS</span>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          {loading ? <span className="spinner" /> : "새로고침"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {successMsg && <div className="alert alert-success">{successMsg}</div>}

      {/* 새 체크포인트 생성 */}
      <div style={{ padding: "0 20px 16px", borderBottom: "2px solid #000" }}>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            className="input-field"
            value={newMsg}
            onChange={(e) => setNewMsg(e.target.value)}
            placeholder="체크포인트 메시지..."
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            style={{ flex: 1 }}
          />
          <button className="btn btn-sm" onClick={handleCreate} disabled={creating || !newMsg.trim()}>
            {creating ? <span className="spinner" /> : "+ 저장"}
          </button>
        </div>
      </div>

      {/* 목록 */}
      <div className="page-content">
        {checkpoints.length === 0 && !loading ? (
          <div className="card" style={{ textAlign: "center", padding: 32 }}>
            <div style={{ fontWeight: 700 }}>체크포인트가 없어요.</div>
          </div>
        ) : (
          checkpoints.map((cp) => (
            <div className="checkpoint-item" key={cp.checkpoint_id}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, flex: 1, minWidth: 0 }}>
                <span className="checkpoint-dot" />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 13 }}>{cp.message || "(메시지 없음)"}</div>
                  <div style={{ display: "flex", gap: 12, marginTop: 2 }}>
                    {cp.created_at && (
                      <code style={{ fontSize: 11, color: "#555" }}>{formatDate(cp.created_at)}</code>
                    )}
                    {cp.file_count != null && (
                      <code style={{ fontSize: 11, color: "#555" }}>{cp.file_count}개 파일</code>
                    )}
                  </div>
                </div>
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => handleRestore(cp.checkpoint_id)}
                disabled={restoring === cp.checkpoint_id}
              >
                {restoring === cp.checkpoint_id ? <span className="spinner" /> : "복원"}
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
// === ANCHOR: CHECKPOINTS_END ===
