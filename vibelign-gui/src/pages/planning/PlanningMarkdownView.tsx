// === ANCHOR: PLANNINGMARKDOWNVIEW_START ===
import { useRef } from "react";

import MarkdownPane from "../../components/docs/MarkdownPane";

interface PlanningMarkdownViewProps {
  readonly markdown: string;
}

// === ANCHOR: PLANNINGMARKDOWNVIEW_PLANNINGMARKDOWNVIEW_START ===
export function PlanningMarkdownView({ markdown }: PlanningMarkdownViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  return (
    <div style={{ minHeight: 360, border: "2px solid #1A1A1A" }}>
      <MarkdownPane content={markdown} containerRef={containerRef} />
    </div>
  );
}
// === ANCHOR: PLANNINGMARKDOWNVIEW_PLANNINGMARKDOWNVIEW_END ===
// === ANCHOR: PLANNINGMARKDOWNVIEW_END ===
