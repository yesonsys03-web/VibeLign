// === ANCHOR: BACKUP_DASHBOARD_PAGE_START ===
import { useCallback, useEffect, useState } from "react";
import BackupDashboardView from "../components/backup-dashboard/BackupDashboard";
import type { BackupEntry } from "../lib/vib";
import { backupCreate, backupList, backupRestore, getCachedBackupList } from "../lib/vib";

interface BackupDashboardPageProps {
  projectDir: string;
}

export default function BackupDashboardPage({ projectDir }: BackupDashboardPageProps) {
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

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await backupList(projectDir);
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
    load();
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
      await load();
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleRestore(id: string) {
    if (!window.confirm("이 저장본으로 되돌릴까요? 지금 상태도 먼저 안전하게 보관됩니다.")) return;
    setRestoring(true);
    setError(null);
    try {
      await backupRestore(projectDir, id);
      setNotice("선택한 저장본으로 되돌렸어요.");
      await load();
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
          <input className="input-field" value={newNote} onChange={(event) => setNewNote(event.target.value)} onKeyDown={(event) => event.key === "Enter" && handleSave()} placeholder="저장 메모" style={{ width: 220, fontSize: 11 }} />
          <button className="btn btn-sm" onClick={handleSave} disabled={saving}>{saving ? <span className="spinner" /> : "지금 저장"}</button>
        </div>
      </div>
      <div style={{ padding: "12px 20px 0", display: "grid", gap: 8 }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>코드 상태를 안전하게 보관하고, 필요할 때 쉽게 되돌려요.</div>
        {error && <div className="alert alert-error">{error}</div>}
        {notice && <div className="alert alert-success">{notice}</div>}
      </div>
      <div className="page-content" style={{ overflowY: "auto" }}>
        <BackupDashboardView entries={entries} loading={loading} query={query} selectedId={selectedId} restoring={restoring} projectDir={projectDir} activeChildView={activeChildView} onRefresh={load} onQueryChange={setQuery} onSelect={setSelectedId} onRestore={handleRestore} onActiveChildViewChange={setActiveChildView} />
      </div>
    </div>
  );
}
// === ANCHOR: BACKUP_DASHBOARD_PAGE_END ===
