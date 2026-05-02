import type { BackupEntry } from "../../lib/vib";
import BackupFlow from "./BackupFlow";
import CleanupInsight from "./CleanupInsight";
import BackupDbViewer from "./BackupDbViewer";
import DateGraph from "./DateGraph";
import FileHistoryTable from "./FileHistoryTable";
import RestorePreviewPanel from "./RestorePreviewPanel";
import RestoreSuggestions from "./RestoreSuggestions";
import SafetySummary from "./SafetySummary";
import StorageSavings from "./StorageSavings";
import { buildRestoreSuggestions, buildStats, buildTimelinePoints } from "./model";

interface BackupDashboardProps {
  entries: BackupEntry[];
  loading: boolean;
  query: string;
  selectedId: string | null;
  restoring: boolean;
  projectDir: string;
  activeChildView: "list" | "db-viewer";
  onRefresh: () => void;
  onQueryChange: (query: string) => void;
  onSelect: (id: string) => void;
  onRestore: (id: string) => void;
  onActiveChildViewChange: (view: "list" | "db-viewer") => void;
}

export default function BackupDashboard({ entries, loading, query, selectedId, restoring, projectDir, activeChildView, onRefresh, onQueryChange, onSelect, onRestore, onActiveChildViewChange }: BackupDashboardProps) {
  const stats = buildStats(entries);
  const selected = entries.find((entry) => entry.id === selectedId) ?? null;
  function handleTimelineSelect(id: string) {
    onQueryChange("");
    onSelect(id);
  }
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="nav-tabs" aria-label="Backup child views">
        <button type="button" className={activeChildView === "list" ? "nav-tab active" : "nav-tab"} onClick={() => onActiveChildViewChange("list")}>백업 목록</button>
        <button type="button" className={activeChildView === "db-viewer" ? "nav-tab active" : "nav-tab"} onClick={() => onActiveChildViewChange("db-viewer")}>Backup DB Viewer</button>
      </div>
      {activeChildView === "db-viewer" ? <BackupDbViewer projectDir={projectDir} /> : (
        <>
      <SafetySummary stats={stats} loading={loading} onRefresh={onRefresh} />
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 14 }}>
        <StorageSavings stats={stats} entries={entries} />
        <DateGraph points={buildTimelinePoints(entries)} selectedId={selectedId} onSelect={handleTimelineSelect} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 14 }}>
        <BackupFlow entries={entries} />
        <RestoreSuggestions suggestions={buildRestoreSuggestions(entries)} onSelect={onSelect} />
      </div>
      <FileHistoryTable entries={entries} query={query} selectedId={selectedId} onQueryChange={onQueryChange} onSelect={onSelect} />
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 14 }}>
        <RestorePreviewPanel entry={selected} restoring={restoring} onRestore={onRestore} />
        <CleanupInsight stats={stats} />
      </div>
        </>
      )}
    </div>
  );
}
