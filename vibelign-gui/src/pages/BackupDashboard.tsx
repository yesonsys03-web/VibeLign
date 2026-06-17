// === ANCHOR: BACKUP_DASHBOARD_PAGE_START ===
import { useCallback, useEffect, useState } from "react";
import { confirm as tauriConfirm } from "@tauri-apps/plugin-dialog";
import BackupDashboardView from "../components/backup-dashboard/BackupDashboard";
import RecoveryOptionsCard from "../components/agent-memory/RecoveryOptionsCard";
import type { BackupEntry } from "../lib/vib";
import { backupCreate, backupList, backupRestore, getCachedBackupList } from "../lib/vib";

interface BackupDashboardPageProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  /** 저장본 생성·복원 직후 호출 — App이 가이드 신호(체크포인트·변경 수)를 즉시 재조회한다. */
  onBackupsChanged?: () => void;
}

export default function BackupDashboardPage({ projectDir, apiKey, providerKeys, onBackupsChanged }: BackupDashboardPageProps) {
  const cached = getCachedBackupList(projectDir);
  const [entries, setEntries] = useState<BackupEntry[]>(cached?.backups ?? []);
  const [loading, setLoading] = useState(!cached);
  const [saving, setSaving] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [newNote, setNewNote] = useState("");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(cached?.backups[0]?.id ?? null);
  const [activeChildView, setActiveChildView] = useState<"list" | "db-viewer">("list");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (force = false) => {
    setLoading(true);
    setError(null);
    try {
      const result = await backupList(projectDir, { force });
      setEntries(result.backups);
      setSelectedId((current) => {
        if (current && result.backups.some((entry) => entry.id === current)) return current;
        return result.backups[0]?.id ?? null;
      });
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [projectDir]);

  useEffect(() => {
    void load(true);
  }, [load]);

  async function handleSave() {
    const note = newNote.trim() || "작업 저장";
    setSaving(true);
    setError(null);
    try {
      await backupCreate(projectDir, note);
      setNewNote("");
      setNotice("새 저장본을 만들었어요.");
      setSelectedId(null);
      await load(true);
      onBackupsChanged?.();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleRestore(id: string) {
    if (!(await tauriConfirm("이 저장본으로 되돌릴까요? 지금 상태도 먼저 안전하게 보관됩니다.", { title: "되돌리기", kind: "warning" }))) return;
    setRestoring(true);
    setError(null);
    try {
      await backupRestore(projectDir, id);
      setNotice("선택한 저장본으로 되돌렸어요.");
      await load(true);
      onBackupsChanged?.();
    } catch (err) {
      setError(String(err));
    } finally {
      setRestoring(false);
    }
  }

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header">
        <span className="page-title">BACKUPS</span>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input className="input-field" value={newNote} onChange={(event) => setNewNote(event.target.value)} onKeyDown={(event) => event.key === "Enter" && handleSave()} placeholder="저장 메모" style={{ width: 220, fontSize: 12 }} />
          <button className="btn btn-sm" onClick={handleSave} disabled={saving}>{saving ? <span className="spinner" /> : "지금 저장"}</button>
        </div>
      </div>
      <div style={{ padding: "12px 20px 0", display: "grid", gap: 8 }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>코드 상태를 안전하게 보관하고, 필요할 때 쉽게 되돌려요.</div>
        {error && <div className="alert alert-error">{error}</div>}
        {notice && <div className="alert alert-success">{notice}</div>}
      </div>
      <div className="page-content" style={{ overflowY: "auto" }}>
        <div style={{ padding: "12px 20px 0" }}>
          <RecoveryOptionsCard projectDir={projectDir} apiKey={apiKey} providerKeys={providerKeys} />
        </div>
        <BackupDashboardView entries={entries} loading={loading} query={query} selectedId={selectedId} restoring={restoring} projectDir={projectDir} activeChildView={activeChildView} onRefresh={() => void load(true)} onQueryChange={setQuery} onSelect={setSelectedId} onRestore={handleRestore} onActiveChildViewChange={setActiveChildView} />
      </div>
    </div>
  );
}
// === ANCHOR: BACKUP_DASHBOARD_PAGE_END ===
