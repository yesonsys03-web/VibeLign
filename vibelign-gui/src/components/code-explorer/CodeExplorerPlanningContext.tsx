// === ANCHOR: CODEEXPLORERPLANNINGCONTEXT_START ===
import { PlanningInstructionActions } from "./PlanningInstructionActions";

interface CodeExplorerPlanningContextProps {
  readonly prompt: string;
  readonly outputPath: string;
}

export default function CodeExplorerPlanningContext({ prompt, outputPath }: CodeExplorerPlanningContextProps) {
  return (
    <section
      className="card"
      style={{
        display: "grid",
        gap: 6,
        padding: 12,
        borderColor: "#1A1A1A",
        background: "#F5F1E3",
      }}
    >
      <div style={{ display: "flex", gap: 10, alignItems: "center", minWidth: 0, flexWrap: "wrap" }}>
        <div style={{ flex: 1, display: "flex", gap: 10, alignItems: "center", minWidth: 220 }}>
          <div style={{ fontSize: 12, fontWeight: 900, flexShrink: 0 }}>작업 기준 기획안</div>
          <div style={{ fontSize: 13, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {prompt}
          </div>
        </div>
      </div>
      <div style={{ fontSize: 11, color: "#666", fontWeight: 700, overflowWrap: "anywhere" }}>{outputPath}</div>
      <PlanningInstructionActions prompt={prompt} outputPath={outputPath} />
    </section>
  );
}
// === ANCHOR: CODEEXPLORERPLANNINGCONTEXT_END ===
