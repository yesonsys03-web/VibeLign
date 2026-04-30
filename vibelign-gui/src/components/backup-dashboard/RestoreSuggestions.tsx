import type { RestoreSuggestion } from "./model";

interface RestoreSuggestionsProps {
  suggestions: RestoreSuggestion[];
  onSelect: (id: string) => void;
}

export default function RestoreSuggestions({ suggestions, onSelect }: RestoreSuggestionsProps) {
  return (
    <section className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: "#FFE5E5", padding: "12px 14px" }}>
        <div className="feature-card-icon" style={{ background: "#FF4D4D", borderColor: "#1A1A1A", color: "#fff" }}>↩</div>
        <div>
          <div style={{ fontWeight: 900, fontSize: 17 }}>추천 되돌리기</div>
          <div style={{ fontSize: 11, color: "#555" }}>많이 고르기 쉬운 저장본을 먼저 보여 줘요.</div>
        </div>
      </div>
      <div className="feature-card-body" style={{ display: "grid", gap: 8 }}>
        {suggestions.map((item) => (
          <button key={item.id} className="btn btn-ghost btn-sm" style={{ textAlign: "left", justifyContent: "flex-start" }} onClick={() => onSelect(item.id)}>
            <span style={{ display: "grid", gap: 2 }}>
              <strong>{item.title}</strong>
              <small>{item.detail}</small>
            </span>
          </button>
        ))}
        {suggestions.length === 0 && <div style={{ fontSize: 12, color: "#666" }}>아직 추천할 저장본이 없어요.</div>}
      </div>
    </section>
  );
}
