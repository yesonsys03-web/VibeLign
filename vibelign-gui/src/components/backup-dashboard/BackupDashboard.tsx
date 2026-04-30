import type { BackupEntry } from "../../lib/vib";
import BackupFlow from "./BackupFlow";
import CleanupInsight from "./CleanupInsight";
import DateGraph from "./DateGraph";
import FileHistoryTable from "./FileHistoryTable";
import RestorePreviewPanel from "./RestorePreviewPanel";
import RestoreSuggestions from "./RestoreSuggestions";
import SafetySummary from "./SafetySummary";
import StorageSavings from "./StorageSavings";
import { buildDayBuckets, buildRestoreSuggestions, buildStats } from "./model";

interface BackupDashboardProps {
  entries: BackupEntry[];
  loading: boolean;
  query: string;
  selectedId: string | null;
  restoring: boolean;
  onRefresh: () => void;
  onQueryChange: (query: string) => void;
  onSelect: (id: string) => void;
  onRestore: (id: string) => void;
}

export default function BackupDashboard({ entries, loading, query, selectedId, restoring, onRefresh, onQueryChange, onSelect, onRestore }: BackupDashboardProps) {
  const stats = buildStats(entries);
  const selected = entries.find((entry) => entry.id === selectedId) ?? null;
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <SafetySummary stats={stats} loading={loading} onRefresh={onRefresh} />
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 14 }}>
        <StorageSavings stats={stats} />
        <DateGraph buckets={buildDayBuckets(entries)} />
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
    </div>
  );
}
