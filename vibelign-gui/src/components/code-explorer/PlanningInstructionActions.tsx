// === ANCHOR: PLANNINGINSTRUCTIONACTIONS_START ===
import { useState } from "react";

import { buildPlanningWorkInstruction, type PlanningWorkPersona } from "../../lib/code-explorer/planningInstruction";
import { planningPersonaLabel } from "../../pages/planning/PlanningPersonas";

interface PlanningInstructionActionsProps {
  readonly prompt: string;
  readonly outputPath: string;
}

type CopyStatus = "idle" | "copied" | "error";

const PERSONA_COPY_ACTIONS: readonly { readonly label: string; readonly persona: PlanningWorkPersona }[] = [
  { label: `${planningPersonaLabel("chloe")} Claude`, persona: "chloe" },
  { label: `${planningPersonaLabel("gio")} Codex`, persona: "gio" },
  { label: `${planningPersonaLabel("mina")} Antigravity`, persona: "mina" },
];

const PERSONA_PREVIEW_ACTIONS: readonly { readonly label: string; readonly persona: PlanningWorkPersona }[] = [
  { label: `${planningPersonaLabel("chloe")} 미리보기`, persona: "chloe" },
  { label: `${planningPersonaLabel("gio")} 미리보기`, persona: "gio" },
  { label: `${planningPersonaLabel("mina")} 미리보기`, persona: "mina" },
];

const PREVIEW_TARGET_LABELS: Record<PlanningWorkPersona, string> = {
  chloe: `${planningPersonaLabel("chloe")} Claude`,
  gio: `${planningPersonaLabel("gio")} Codex`,
  mina: `${planningPersonaLabel("mina")} Antigravity`,
};

// === ANCHOR: PLANNINGINSTRUCTIONACTIONS_PLANNINGINSTRUCTIONACTIONS_START ===
export function PlanningInstructionActions({ prompt, outputPath }: PlanningInstructionActionsProps) {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const [fallbackInstruction, setFallbackInstruction] = useState("");
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewPersona, setPreviewPersona] = useState<PlanningWorkPersona | undefined>(undefined);
  const previewInstruction = fallbackInstruction || buildPlanningWorkInstruction({ prompt, outputPath, persona: previewPersona });
  const previewTargetLabel = previewPersona ? PREVIEW_TARGET_LABELS[previewPersona] : "공통";
  const isCommonPreviewSelected = previewPersona === undefined;

  // === ANCHOR: PLANNINGINSTRUCTIONACTIONS_HANDLECOPYINSTRUCTION_START ===
  async function handleCopyInstruction(persona?: PlanningWorkPersona) {
    const instruction = buildPlanningWorkInstruction({ prompt, outputPath, persona });
    try {
      await navigator.clipboard.writeText(instruction);
      setCopyStatus("copied");
      setFallbackInstruction("");
    } catch (error: unknown) {
      if (!(error instanceof Error)) {
        throw error;
      }
      setCopyStatus("error");
      setFallbackInstruction(instruction);
      setIsPreviewOpen(true);
    }
  }
  // === ANCHOR: PLANNINGINSTRUCTIONACTIONS_HANDLECOPYINSTRUCTION_END ===

  // === ANCHOR: PLANNINGINSTRUCTIONACTIONS_HANDLECOPYPREVIEWINSTRUCTION_START ===
  async function handleCopyPreviewInstruction() {
    try {
      await navigator.clipboard.writeText(previewInstruction);
      setCopyStatus("copied");
      setFallbackInstruction("");
    } catch (error: unknown) {
      if (!(error instanceof Error)) {
        throw error;
      }
      setCopyStatus("error");
      setFallbackInstruction(previewInstruction);
      setIsPreviewOpen(true);
    }
  }
  // === ANCHOR: PLANNINGINSTRUCTIONACTIONS_HANDLECOPYPREVIEWINSTRUCTION_END ===

  return (
    <>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <button className="btn btn-black btn-sm" type="button" onClick={() => void handleCopyInstruction()} style={{ fontSize: 11 }}>
          작업 지시 복사
        </button>
        <button
          className="btn btn-secondary btn-sm"
          type="button"
          onClick={() => setIsPreviewOpen((current) => !current)}
          style={{ fontSize: 11 }}
        >
          {isPreviewOpen ? "미리보기 닫기" : "작업 지시 미리보기"}
        </button>
      </div>
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
      <div style={{ fontSize: 10, color: "#888", fontWeight: 700, lineHeight: 1.5 }}>
        VibeLign MCP가 연결된 도구(Claude Code·Cursor 등)에서는 복사 없이 그 도구에 <b>“VibeLign 기획안 구현해”</b> 라고만 입력해도 됩니다.
      </div>
      {copyStatus === "copied" && (
        <div style={{ fontSize: 11, color: "#2f6f46", fontWeight: 800 }}>복사했어요. 사용하는 AI CLI에 붙여넣어 시작하세요.</div>
      )}
      {copyStatus === "error" && (
        <div style={{ fontSize: 11, color: "#b42318", fontWeight: 800 }}>자동 복사에 실패해서 아래에 작업 지시를 표시했어요.</div>
      )}
      {isPreviewOpen && (
        <div style={{ display: "grid", gap: 6 }}>
          <h3 style={{ margin: 0, fontSize: 11, fontWeight: 900 }}>작업 지시 미리보기</h3>
          <div style={{ fontSize: 11, color: "#555", fontWeight: 800 }}>현재 미리보기: {previewTargetLabel}</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <button className="btn btn-black btn-sm" type="button" onClick={() => void handleCopyPreviewInstruction()} style={{ fontSize: 10 }}>
              현재 미리보기 복사
            </button>
            <button
              className="btn btn-ghost btn-sm"
              type="button"
              aria-pressed={isCommonPreviewSelected}
              onClick={() => setPreviewPersona(undefined)}
              style={{
                fontSize: 10,
                border: "2px solid #1A1A1A",
                background: isCommonPreviewSelected ? "#1A1A1A" : undefined,
                color: isCommonPreviewSelected ? "#fff" : undefined,
              }}
            >
              공통 미리보기
            </button>
            {PERSONA_PREVIEW_ACTIONS.map((action) => {
              const isSelected = previewPersona === action.persona;
              return (
                <button
                  key={action.persona}
                  className="btn btn-ghost btn-sm"
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setPreviewPersona(action.persona)}
                  style={{
                    fontSize: 10,
                    border: "2px solid #1A1A1A",
                    background: isSelected ? "#1A1A1A" : undefined,
                    color: isSelected ? "#fff" : undefined,
                  }}
                >
                  {action.label}
                </button>
              );
            })}
          </div>
          <pre style={{ margin: 0, padding: 10, border: "2px solid #1A1A1A", background: "#fff", whiteSpace: "pre-wrap", fontSize: 11 }}>
            {previewInstruction}
          </pre>
        </div>
// === ANCHOR: PLANNINGINSTRUCTIONACTIONS_PLANNINGINSTRUCTIONACTIONS_END ===
      )}
    </>
  );
}
// === ANCHOR: PLANNINGINSTRUCTIONACTIONS_END ===
