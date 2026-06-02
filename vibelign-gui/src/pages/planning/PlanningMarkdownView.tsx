import { useRef } from "react";

import MarkdownPane from "../../components/docs/MarkdownPane";

interface PlanningMarkdownViewProps {
  readonly markdown: string;
}

export function PlanningMarkdownView({ markdown }: PlanningMarkdownViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  return (
    <div style={{ minHeight: 360, border: "2px solid #1A1A1A" }}>
      <MarkdownPane content={markdown} containerRef={containerRef} />
    </div>
  );
}
