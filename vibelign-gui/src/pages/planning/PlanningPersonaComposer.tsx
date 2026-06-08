// === ANCHOR: PLANNINGPERSONACOMPOSER_START ===
import { useState } from "react";

import { appendPlanningChatTurn, type PlanningChatSessionResponse } from "../../lib/vib";
import { DEFAULT_PLANNING_MODE, type PlanningModeOption } from "./PlanningModes";
import { PlanningModeSelector } from "./PlanningModeSelector";
import { allPlanningPersonaIds, PLANNING_PERSONAS } from "./PlanningPersonas";
import {
  appendMention,
  togglePersona,
  withPendingAgents,
  withPendingTurn,
} from "./PlanningPersonaComposerState";
import { PlanningPersonaAvatar } from "./PlanningPersonaAvatar";

interface PlanningPersonaComposerProps {
  readonly projectDir: string;
  readonly result: PlanningChatSessionResponse;
  readonly sessionId: string | null;
  readonly onResultChange: (result: PlanningChatSessionResponse) => void;
}

// === ANCHOR: PLANNINGPERSONACOMPOSER_PLANNINGPERSONACOMPOSER_START ===
export function PlanningPersonaComposer({ projectDir, result, sessionId, onResultChange }: PlanningPersonaComposerProps) {
  const [selectedModeId, setSelectedModeId] = useState<PlanningModeOption["id"]>(DEFAULT_PLANNING_MODE.id);
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<readonly string[]>(DEFAULT_PLANNING_MODE.personaIds);
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const canSubmit = message.trim().length > 0 && selectedPersonaIds.length > 0 && Boolean(sessionId) && !isSubmitting;

  // === ANCHOR: PLANNINGPERSONACOMPOSER_HANDLESUBMIT_START ===
  async function handleSubmit() {
    if (!canSubmit || !sessionId) {
      return;
    }
    const prompt = message.trim();
    const agents = [...selectedPersonaIds];
    const createdAt = new Date().toISOString();
    setIsSubmitting(true);
    setMessage("");
    onResultChange(withPendingTurn(result, prompt, agents, createdAt));

    for (const [index, agent] of agents.entries()) {
      const nextResult = await appendPlanningChatTurn({
        projectDir,
        sessionId,
        prompt,
        agents: [agent],
        includeUserMessage: index === 0,
        extractCards: index === agents.length - 1,
      });
      if (!nextResult.ok) {
        onResultChange(nextResult);
        break;
      }
      onResultChange(withPendingAgents(nextResult, agents.slice(index + 1), createdAt));
    }
    setIsSubmitting(false);
  }
  // === ANCHOR: PLANNINGPERSONACOMPOSER_HANDLESUBMIT_END ===

  return (
    <section
      style={{
        border: "2px solid #1A1A1A",
        background: "#FFFFFF",
        padding: 12,
        display: "grid",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <PlanningModeSelector
          value={selectedModeId}
          onChange={(option) => {
            setSelectedModeId(option.id);
            setSelectedPersonaIds(option.personaIds);
          }}
        />
        {PLANNING_PERSONAS.map((persona) => (
          <button
            key={persona.id}
            type="button"
            aria-pressed={selectedPersonaIds.includes(persona.id)}
            onClick={() => {
              setSelectedPersonaIds(togglePersona(selectedPersonaIds, persona.id));
              setMessage((current) => appendMention(current, persona.mention));
            }}
            style={{
              border: "2px solid #1A1A1A",
              background: selectedPersonaIds.includes(persona.id) ? "#1A1A1A" : "#F7F0DF",
              color: selectedPersonaIds.includes(persona.id) ? "#FFFFFF" : "#1A1A1A",
              padding: "7px 9px",
              fontSize: 11,
              fontWeight: 900,
              cursor: "pointer",
            }}
          >
            <PlanningPersonaAvatar personaId={persona.id} label={persona.label} decorative size={18} />
            {persona.label} {persona.role}
          </button>
        ))}
        <button
          type="button"
          aria-pressed={selectedPersonaIds.length === PLANNING_PERSONAS.length}
          onClick={() => {
            setSelectedPersonaIds(allPlanningPersonaIds());
            setMessage((current) => appendMention(current, "@모두"));
          }}
          style={{
            border: "2px solid #1A1A1A",
            background: selectedPersonaIds.length === PLANNING_PERSONAS.length ? "#1A1A1A" : "#FFFFFF",
            color: selectedPersonaIds.length === PLANNING_PERSONAS.length ? "#FFFFFF" : "#1A1A1A",
            padding: "7px 9px",
            fontSize: 11,
            fontWeight: 900,
            cursor: "pointer",
          }}
        >
          모두
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 72px", gap: 8, alignItems: "end" }}>
        <textarea
          className="input-field"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSubmit();
            }
          }}
          placeholder="기획안을 어떻게 더 다듬을까요?"
          rows={2}
          style={{
            border: "2px solid #1A1A1A",
            minHeight: 58,
            maxHeight: 120,
            fontSize: 13,
            lineHeight: "20px",
            resize: "vertical",
            boxShadow: "none",
          }}
        />
        <button
          className="btn btn-black"
          type="button"
          onClick={() => void handleSubmit()}
          disabled={!canSubmit}
          style={{ height: 42, fontSize: 12, opacity: canSubmit ? 1 : 0.5 }}
        >
          {isSubmitting ? "호출중" : "호출"}
        </button>
      </div>
    </section>
// === ANCHOR: PLANNINGPERSONACOMPOSER_PLANNINGPERSONACOMPOSER_END ===
  );
}
// === ANCHOR: PLANNINGPERSONACOMPOSER_END ===
