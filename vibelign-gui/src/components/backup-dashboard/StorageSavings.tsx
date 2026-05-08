// === ANCHOR: STORAGESAVINGS_START ===
import { useEffect, useState } from "react";
import type { BackupDashboardStats } from "./model";
import { formatBytes } from "./model";
import type { BackupEntry, BackupGraphNode } from "../../lib/vib";
import { backupGraphSummary } from "../../lib/vib";
import BackupCard from "./BackupCard";
import StorageRadialMap from "./StorageRadialMap";

interface StorageSavingsProps {
  stats: BackupDashboardStats;
  entries: BackupEntry[];
  projectDir: string;
}

export default function StorageSavings({ stats, entries, projectDir }: StorageSavingsProps) {
  const [graphRoot, setGraphRoot] = useState<BackupGraphNode | null>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphMessage, setGraphMessage] = useState<string | null>(null);
  const hasFileDetails = entries.some((entry) => entry.files.length > 0);
  const hasGraphDetails = hasFileDetails || (graphRoot?.sizeBytes ?? 0) > 0;

  useEffect(() => {
    if (hasFileDetails) {
      setGraphRoot(null);
      setGraphMessage(null);
      setGraphLoading(false);
      return;
    }
    let cancelled = false;
    setGraphLoading(true);
    setGraphMessage(null);
    backupGraphSummary(projectDir)
      .then((result) => {
        if (cancelled) return;
        setGraphRoot(result.root);
        setGraphMessage(result.warnings[0] ?? null);
      })
      .catch((error) => {
        if (!cancelled) setGraphMessage(String(error));
      })
      .finally(() => {
        if (!cancelled) setGraphLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hasFileDetails, projectDir]);

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
      {hasGraphDetails ? (
        <div style={{ marginTop: 12 }}>
          <StorageRadialMap entries={entries} root={hasFileDetails ? null : graphRoot} />
        </div>
      ) : (
        <div style={{ marginTop: 12, fontSize: 12, color: "#666" }}>
          {graphLoading ? "백업 범위 그래프 요약을 불러오는 중입니다." : graphMessage ?? "파일별 그래프 데이터가 아직 없어요."}
        </div>
      )}
    </BackupCard>
  );
}
// === ANCHOR: STORAGESAVINGS_END ===
