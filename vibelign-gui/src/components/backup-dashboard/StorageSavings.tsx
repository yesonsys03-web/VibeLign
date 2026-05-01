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
      title="백업 범위"
      subtitle="각 저장본이 복원할 수 있는 원본 파일 크기의 합계예요. 실제 디스크 사용량은 Backup DB Viewer에서 확인하세요."
      headerStyle={{ background: "#FFF1B8", padding: "12px 14px" }}
      iconStyle={{ background: "#FFB000", borderColor: "#1A1A1A" }}
    >
      <div style={{ fontSize: 28, fontWeight: 900 }}>{formatBytes(stats.storedBytes)}</div>
      <div style={{ fontSize: 12, color: "#555" }}>{stats.manualCount}개는 직접 저장했고, {stats.autoCount}개는 자동으로 보관했어요. 중복·압축 후 실제 용량과는 다릅니다.</div>
      <div style={{ marginTop: 12 }}>
        <StorageRadialMap entries={entries} />
      </div>
    </BackupCard>
  );
}
