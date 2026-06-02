import { useState } from "react";

import { appendPlanningWithAgents, type CreatePlanningTemplateResponse } from "../../lib/vib";

interface PlanningPersonaComposerProps {
  readonly projectDir: string;
  readonly outputPath: string | null;
  readonly onResultChange: (result: CreatePlanningTemplateResponse) => void;
}

interface PersonaOption {
  readonly id: string;
  readonly label: string;
  readonly role: string;
}

const PERSONAS: readonly PersonaOption[] = [
  { id: "chloe", label: "클로이", role: "설계" },
  { id: "gio", label: "지오", role: "검토" },
  { id: "mina", label: "미나", role: "탐색" },
];

export function PlanningPersonaComposer({ projectDir, outputPath, onResultChange }: PlanningPersonaComposerProps) {
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<readonly string[]>(["gio"]);
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const canSubmit = message.trim().length > 0 && selectedPersonaIds.length > 0 && Boolean(outputPath) && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit || !outputPath) {
      return;
    }
    setIsSubmitting(true);
    const result = await appendPlanningWithAgents({
      projectDir,
      outputPath,
      prompt: message,
      cli: "auto",
      agents: selectedPersonaIds,
    });
    setIsSubmitting(false);
    if (result.ok) {
      setMessage("");
    }
    onResultChange(result);
  }

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
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {PERSONAS.map((persona) => (
          <button
            key={persona.id}
            type="button"
            aria-pressed={selectedPersonaIds.includes(persona.id)}
            onClick={() => setSelectedPersonaIds(togglePersona(selectedPersonaIds, persona.id))}
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
            {persona.label} {persona.role}
          </button>
        ))}
        <button
          type="button"
          aria-pressed={selectedPersonaIds.length === PERSONAS.length}
          onClick={() => setSelectedPersonaIds(PERSONAS.map((persona) => persona.id))}
          style={{
            border: "2px solid #1A1A1A",
            background: selectedPersonaIds.length === PERSONAS.length ? "#1A1A1A" : "#FFFFFF",
            color: selectedPersonaIds.length === PERSONAS.length ? "#FFFFFF" : "#1A1A1A",
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
  );
}

function togglePersona(current: readonly string[], personaId: string): readonly string[] {
  if (current.includes(personaId)) {
    return current.filter((id) => id !== personaId);
  }
  return [...current, personaId];
}
