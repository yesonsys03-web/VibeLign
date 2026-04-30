import type { BackupDashboardStats } from "./model";
import BackupCard from "./BackupCard";

interface SafetySummaryProps {
  stats: BackupDashboardStats;
  loading: boolean;
  onRefresh: () => void;
}

export default function SafetySummary({ stats, loading, onRefresh }: SafetySummaryProps) {
  const mood = stats.totalCount > 0 ? "안전하게 보관 중" : "첫 저장이 필요해요";
  return (
    <BackupCard
      icon="🛡"
      title={mood}
      subtitle={`최근 저장: ${stats.lastSavedLabel}`}
      headerStyle={{ background: "#DFFFE8", padding: "14px 16px" }}
      iconStyle={{ background: "#26A65B", borderColor: "#1A1A1A", color: "#fff" }}
      sectionStyle={{ borderWidth: 3 }}
      bodyStyle={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}
      actions={
        <button className="btn btn-ghost btn-sm" onClick={onRefresh} disabled={loading}>
          {loading ? <span className="spinner" /> : "새로 보기"}
        </button>
      }
    >
      <strong>{stats.totalCount}개 저장본</strong>
      <strong>{stats.autoCount}개 자동 보관</strong>
      <strong>{stats.totalFiles}개 파일</strong>
    </BackupCard>
  );
}
