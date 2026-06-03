import { useState } from "react";

import { buildPlanningWorkInstruction, type PlanningWorkPersona } from "../../lib/code-explorer/planningInstruction";

interface CodeExplorerPlanningContextProps {
  readonly prompt: string;
  readonly outputPath: string;
}

type CopyStatus = "idle" | "copied" | "error";

const PERSONA_COPY_ACTIONS: readonly { readonly label: string; readonly persona: PlanningWorkPersona }[] = [
  { label: "클로이 Claude", persona: "chloe" },
  { label: "지오 Codex", persona: "gio" },
  { label: "미나 Antigravity", persona: "mina" },
];

export default function CodeExplorerPlanningContext({ prompt, outputPath }: CodeExplorerPlanningContextProps) {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const [instructionPreview, setInstructionPreview] = useState("");

  async function handleCopyInstruction(persona?: PlanningWorkPersona) {
    const instruction = buildPlanningWorkInstruction({ prompt, outputPath, persona });
    try {
      await navigator.clipboard.writeText(instruction);
      setCopyStatus("copied");
      setInstructionPreview("");
    } catch (error: unknown) {
      if (!(error instanceof Error)) {
        throw error;
      }
      setCopyStatus("error");
      setInstructionPreview(instruction);
    }
  }

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
        <button className="btn btn-black btn-sm" type="button" onClick={() => void handleCopyInstruction()} style={{ fontSize: 11, flexShrink: 0 }}>
          작업 지시 복사
        </button>
      </div>
      <div style={{ fontSize: 11, color: "#666", fontWeight: 700, overflowWrap: "anywhere" }}>{outputPath}</div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {PERSONA_COPY_ACTIONS.map((action) => (
          <button
            key={action.persona}
            className="btn btn-ghost btn-sm"
            type="button"
            onClick={() => void handleCopyInstruction(action.persona)}
            style={{ fontSize: 10, border: "2px solid #1A1A1A" }}
          >
            {action.label}
          </button>
        ))}
      </div>
      {copyStatus === "copied" && (
        <div style={{ fontSize: 11, color: "#2f6f46", fontWeight: 800 }}>복사했어요. 사용하는 AI CLI에 붙여넣어 시작하세요.</div>
      )}
      {copyStatus === "error" && (
        <div style={{ display: "grid", gap: 6 }}>
          <div style={{ fontSize: 11, color: "#b42318", fontWeight: 800 }}>자동 복사에 실패해서 아래에 작업 지시를 표시했어요.</div>
          <pre style={{ margin: 0, padding: 10, border: "2px solid #1A1A1A", background: "#fff", whiteSpace: "pre-wrap", fontSize: 11 }}>
            {instructionPreview}
          </pre>
        </div>
      )}
    </section>
  );
}
