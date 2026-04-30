import type { BackupDashboardStats } from "./model";

interface SafetySummaryProps {
  stats: BackupDashboardStats;
  loading: boolean;
  onRefresh: () => void;
}

export default function SafetySummary({ stats, loading, onRefresh }: SafetySummaryProps) {
  const mood = stats.totalCount > 0 ? "안전하게 보관 중" : "첫 저장이 필요해요";
  return (
    <section className="feature-card" style={{ cursor: "default", borderWidth: 3 }}>
      <div className="feature-card-header" style={{ background: "#DFFFE8", padding: "14px 16px" }}>
        <div className="feature-card-icon" style={{ background: "#26A65B", borderColor: "#1A1A1A", color: "#fff" }}>🛡</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 20, fontWeight: 900 }}>{mood}</div>
          <div style={{ fontSize: 12, color: "#3A3A3A" }}>최근 저장: {stats.lastSavedLabel}</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onRefresh} disabled={loading}>
          {loading ? <span className="spinner" /> : "새로 보기"}
        </button>
      </div>
      <div className="feature-card-body" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        <strong>{stats.totalCount}개 저장본</strong>
        <strong>{stats.autoCount}개 자동 보관</strong>
        <strong>{stats.totalFiles}개 파일</strong>
      </div>
    </section>
  );
}
