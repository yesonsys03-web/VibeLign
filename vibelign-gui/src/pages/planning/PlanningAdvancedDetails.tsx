// === ANCHOR: PLANNINGADVANCEDDETAILS_START ===
import { useState } from "react";

interface PlanningAdvancedDetailsProps {
  readonly details: string | null | undefined;
}

// === ANCHOR: PLANNINGADVANCEDDETAILS_PLANNINGADVANCEDDETAILS_START ===
export function PlanningAdvancedDetails({ details }: PlanningAdvancedDetailsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const trimmedDetails = details?.trim();

  if (!trimmedDetails) {
    return null;
  }

  return (
    <section
      aria-label="고급 상세"
      style={{
        border: "2px solid #1A1A1A",
        background: "#FFFFFF",
        padding: 12,
        display: "grid",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
        <div style={{ display: "grid", gap: 2 }}>
          <div style={{ fontSize: 12, fontWeight: 900 }}>고급 상세</div>
          <div style={{ fontSize: 12, color: "#555", fontWeight: 700 }}>문제 원인을 확인할 때만 펼쳐보세요.</div>
        </div>
        <button
          className="btn btn-ghost btn-sm"
          type="button"
          aria-expanded={isExpanded}
          onClick={() => setIsExpanded((expanded) => !expanded)}
          style={{ fontSize: 12 }}
        >
          {isExpanded ? "고급 상세 숨기기" : "고급 상세 보기"}
        </button>
      </div>
      {isExpanded && (
        <pre
          style={{
            margin: 0,
            border: "1px solid #1A1A1A",
            background: "#F7F0DF",
            padding: 10,
            maxHeight: 220,
            overflow: "auto",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontSize: 11,
            lineHeight: 1.5,
          }}
        >
          {trimmedDetails}
        </pre>
      )}
    </section>
  );
}
// === ANCHOR: PLANNINGADVANCEDDETAILS_PLANNINGADVANCEDDETAILS_END ===
// === ANCHOR: PLANNINGADVANCEDDETAILS_END ===
