// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_START ===
import type { PlanningChatMessage } from "../../lib/vib";
import { PlanningPersonaAvatar } from "./PlanningPersonaAvatar";
import { planningPersonaLabel } from "./PlanningPersonas";
import { planningPersonaStatusBackground, planningPersonaStatusColor, planningPersonaStatusDisplay } from "./PlanningPersonaStatusLabel";

interface PlanningPersonaResponseSummaryProps {
  readonly messages: readonly PlanningChatMessage[];
}

interface PersonaSummary {
  readonly personaId: string;
  readonly name: string;
  readonly status: string;
  readonly content: string;
}

// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_PLANNINGPERSONARESPONSESUMMARY_START ===
export function PlanningPersonaResponseSummary({ messages }: PlanningPersonaResponseSummaryProps) {
  const summaries = personaSummaries(messages);
  if (summaries.length === 0) {
    return null;
  }
  return (
    <section
      role="region"
      aria-label="페르소나 응답 요약"
      style={{
        border: "2px solid #1A1A1A",
        background: "#FFFFFF",
        padding: 10,
        display: "grid",
        gap: 8,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 900 }}>페르소나 응답 요약</div>
      <div style={{ display: "grid", gap: 6 }}>
        {summaries.map((summary) => (
          <PersonaSummaryCard key={summary.personaId} summary={summary} />
        ))}
      </div>
    </section>
  );
}
// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_PLANNINGPERSONARESPONSESUMMARY_END ===

// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_PERSONASUMMARYCARD_START ===
function PersonaSummaryCard({ summary }: { readonly summary: PersonaSummary }) {
  const display = planningPersonaStatusDisplay(summary.status);
  return (
    <div
      style={{
        border: "1px solid #1A1A1A",
        background: planningPersonaStatusBackground(display.tone),
        padding: 8,
        display: "grid",
        gap: 4,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, fontWeight: 900 }}>
        <PlanningPersonaAvatar personaId={summary.personaId} label={summary.name} decorative size={18} />
        <span>
          {summary.name} {display.label}
        </span>
      </div>
      <div style={{ fontSize: 12, color: planningPersonaStatusColor(display.tone), lineHeight: 1.45 }}>{summarySnippet(summary.content)}</div>
    </div>
  );
}
// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_PERSONASUMMARYCARD_END ===

// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_PERSONASUMMARIES_START ===
function personaSummaries(messages: readonly PlanningChatMessage[]): readonly PersonaSummary[] {
  const latestByPersona = new Map<string, PlanningChatMessage>();
  for (const message of messages) {
    if (message.role !== "assistant" || !message.personaId) {
      continue;
    }
    latestByPersona.set(message.personaId, message);
  }
  return Array.from(latestByPersona.entries()).map(([personaId, message]) => ({
    personaId,
    name: planningPersonaLabel(personaId),
    status: message.status,
    content: message.content,
  }));
}
// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_PERSONASUMMARIES_END ===

// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_SUMMARYSNIPPET_START ===
function summarySnippet(content: string): string {
  const normalized = content.trim().split(/\s+/).join(" ");
  if (normalized.length <= 96) {
    return normalized;
  }
  return `${normalized.slice(0, 96)}...`;
}
// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_SUMMARYSNIPPET_END ===
// === ANCHOR: PLANNINGPERSONARESPONSESUMMARY_END ===
