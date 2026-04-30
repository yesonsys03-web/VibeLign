import type { BackupDashboardStats } from "./model";
import { formatBytes } from "./model";
import type { BackupEntry } from "../../lib/vib";
import BackupCard from "./BackupCard";
import StorageRadialMap from "./StorageRadialMap";

interface StorageSavingsProps {
  stats: BackupDashboardStats;
  entries: BackupEntry[];
}

export default function StorageSavings({ stats, entries }: StorageSavingsProps) {
  return (
    <BackupCard
      icon="📦"
      title="공간 사용"
      subtitle="같은 내용은 한 번만 보관해서 낭비를 줄여요."
      headerStyle={{ background: "#FFF1B8", padding: "12px 14px" }}
      iconStyle={{ background: "#FFB000", borderColor: "#1A1A1A" }}
    >
      <div style={{ fontSize: 28, fontWeight: 900 }}>{formatBytes(stats.storedBytes)}</div>
      <div style={{ fontSize: 12, color: "#555" }}>{stats.manualCount}개는 직접 저장했고, {stats.autoCount}개는 자동으로 보관했어요.</div>
      <div style={{ marginTop: 12 }}>
        <StorageRadialMap entries={entries} />
      </div>
    </BackupCard>
  );
}
