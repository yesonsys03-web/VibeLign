import type { BackupDashboardStats } from "./model";
import BackupCard from "./BackupCard";
import { formatBytes } from "./model";

interface CleanupInsightProps {
  stats: BackupDashboardStats;
}

export default function CleanupInsight({ stats }: CleanupInsightProps) {
  return (
    <BackupCard
      icon="🧹"
      title="정리 안내"
      subtitle="너무 오래된 저장본은 규칙에 따라 정리돼요."
      headerStyle={{ background: "#F2F2F2", padding: "12px 14px" }}
      iconStyle={{ background: "#555", borderColor: "#1A1A1A", color: "#fff" }}
      bodyStyle={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 8, fontSize: 12 }}
    >
      <span>기본 보관: 최근 저장본 20개</span>
      <span>보관 중인 크기: {formatBytes(stats.storedBytes)}</span>
      <span>보호 중: 최근 저장본과 월별 대표</span>
      <span>마지막 정리: 저장할 때 자동 확인</span>
    </BackupCard>
  );
}
