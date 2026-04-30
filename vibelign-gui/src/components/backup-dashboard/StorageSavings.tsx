import type { BackupDashboardStats } from "./model";
import { formatBytes } from "./model";

interface StorageSavingsProps {
  stats: BackupDashboardStats;
}

export default function StorageSavings({ stats }: StorageSavingsProps) {
  return (
    <section className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#FFF1B8", padding: "12px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#FFB000", borderColor: "#1A1A1A" }}>📦</div>
        <div>
          <div style={{ fontWeight: 900, fontSize: 17 }}>공간 사용</div>
          <div style={{ fontSize: 11, color: "#555" }}>같은 내용은 한 번만 보관해서 낭비를 줄여요.</div>
        </div>
      </div>
      <div className="feature-card-body">
        <div style={{ fontSize: 28, fontWeight: 900 }}>{formatBytes(stats.storedBytes)}</div>
        <div style={{ fontSize: 12, color: "#555" }}>{stats.manualCount}개는 직접 저장했고, {stats.autoCount}개는 자동으로 보관했어요.</div>
      </div>
    </section>
  );
}
