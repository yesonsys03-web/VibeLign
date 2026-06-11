// === ANCHOR: CODEEXPLORERPLANNINGCONTEXT_START ===
import { PlanningInstructionActions } from "./PlanningInstructionActions";
import type { PlanningContract } from "../../lib/vib/types";

interface CodeExplorerPlanningContextProps {
  readonly prompt: string;
  readonly outputPath: string;
  readonly contract?: PlanningContract | null;
  /** 저장된 기획안·계약보다 기획방 대화가 더 진행됨 — 다시 저장 전엔 지시문이 구버전 기준. */
  readonly docStale?: boolean;
}

export default function CodeExplorerPlanningContext({ prompt, outputPath, contract, docStale = false }: CodeExplorerPlanningContextProps) {
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
      {docStale && (
        <div style={{ fontSize: 11, color: "#B45309", background: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 4, padding: "6px 8px", fontWeight: 700 }}>
          ⚠ 기획방 대화가 이 기획안 저장 이후 더 진행됐어요 — 지시문이 이전 버전 기준입니다. 기획방에서 다시 저장한 뒤 복사하는 걸 권장해요.
        </div>
      )}
      <PlanningInstructionActions prompt={prompt} outputPath={outputPath} contract={contract} />
    </section>
  );
}
// === ANCHOR: CODEEXPLORERPLANNINGCONTEXT_END ===
