import type { DayBucket } from "./model";

interface DateGraphProps {
  buckets: DayBucket[];
}

export default function DateGraph({ buckets }: DateGraphProps) {
  const max = Math.max(1, ...buckets.map((item) => item.count));
  return (
    <section className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#E7F0FF", padding: "12px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#3D7DFF", borderColor: "#1A1A1A", color: "#fff" }}>📅</div>
        <div>
          <div style={{ fontWeight: 900, fontSize: 17 }}>날짜별 저장</div>
          <div style={{ fontSize: 11, color: "#555" }}>어느 날에 많이 저장했는지 보여 줘요.</div>
        </div>
      </div>
      <div className="feature-card-body" style={{ display: "flex", alignItems: "end", gap: 8, minHeight: 120 }}>
        {buckets.length === 0 ? <span style={{ fontSize: 12, color: "#666" }}>아직 그릴 내용이 없어요.</span> : buckets.map((item) => (
          <div key={item.label} style={{ flex: 1, textAlign: "center" }}>
            <div style={{ height: `${Math.max(18, (item.count / max) * 86)}px`, background: "#3D7DFF", border: "2px solid #1A1A1A", boxShadow: "3px 3px 0 #1A1A1A" }} />
            <div style={{ marginTop: 6, fontSize: 10, fontWeight: 800 }}>{item.label}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
