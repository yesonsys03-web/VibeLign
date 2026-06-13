// === ANCHOR: PLANNINGINSTRUCTIONACTIONS_START ===
import { useState } from "react";

import { buildPlanningWorkInstruction, type PlanningWorkPersona } from "../../lib/code-explorer/planningInstruction";
import { planningPersonaLabel } from "../../pages/planning/PlanningPersonas";
import type { PlanningContract } from "../../lib/vib/types";

interface PlanningInstructionActionsProps {
  readonly prompt: string;
  readonly outputPath: string;
  readonly contract?: PlanningContract | null;
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
  deepseek: `${planningPersonaLabel("deepseek")} OpenCode`,
};

// === ANCHOR: PLANNINGINSTRUCTIONACTIONS_PLANNINGINSTRUCTIONACTIONS_START ===
export function PlanningInstructionActions({ prompt, outputPath, contract = null }: PlanningInstructionActionsProps) {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>("idle");
  const [fallbackInstruction, setFallbackInstruction] = useState("");
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [previewPersona, setPreviewPersona] = useState<PlanningWorkPersona | undefined>(undefined);
  const previewInstruction = fallbackInstruction || buildPlanningWorkInstruction({ prompt, outputPath, persona: previewPersona, contract });
  const previewTargetLabel = previewPersona ? PREVIEW_TARGET_LABELS[previewPersona] : "공통";
  const isCommonPreviewSelected = previewPersona === undefined;

  // === ANCHOR: PLANNINGINSTRUCTIONACTIONS_HANDLECOPYINSTRUCTION_START ===
  async function handleCopyInstruction(persona?: PlanningWorkPersona) {
    const instruction = buildPlanningWorkInstruction({ prompt, outputPath, persona, contract });
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
      {/* 동선 봉합 후 역할 명확화 — 기본 경로는 작업방(앱 내 자동 실행)이고, 이 복사 영역은
          "내 외부 도구에 직접 붙여넣어 쓰는 경우"용임을 초보자에게 분명히 한다(두 길이 안 헷갈리게). */}
      <div style={{ fontSize: 14, fontWeight: 900, color: "#1A1A1A" }}>
        외부 AI 도구에 직접 붙여넣어 쓰는 경우 — 작업 지시 복사
      </div>
      <div style={{ fontSize: 12.5, color: "#555", fontWeight: 700, lineHeight: 1.6 }}>
        기본은 <b>작업방</b>이 앱 안에서 자동으로 실행해요. Claude Code·Cursor 등 <b>내 도구에 직접</b> 시킬 때만 복사하면 돼요.
      </div>
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
      <div style={{ fontSize: 12.5, color: "#555", fontWeight: 700, lineHeight: 1.6 }}>
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
