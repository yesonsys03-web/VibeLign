// === ANCHOR: PLANNINGPERSONACOMPOSER_START ===
import { useState } from "react";

import { appendPlanningChatTurn, type PlanningChatSessionResponse } from "../../lib/vib";
import { DEFAULT_PLANNING_MODE, type PlanningModeOption } from "./PlanningModes";
import { PlanningModeSelector } from "./PlanningModeSelector";
import { allPlanningPersonaIds, PLANNING_PERSONAS } from "./PlanningPersonas";
import {
  appendMention,
  isSaveCommand,
  markAgentFailed,
  matchingSlashCommands,
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
  readonly onSlashSave: () => void;
}

// === ANCHOR: PLANNINGPERSONACOMPOSER_PLANNINGPERSONACOMPOSER_START ===
export function PlanningPersonaComposer({ projectDir, result, sessionId, onResultChange, onSlashSave }: PlanningPersonaComposerProps) {
  const [selectedModeId, setSelectedModeId] = useState<PlanningModeOption["id"]>(DEFAULT_PLANNING_MODE.id);
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<readonly string[]>(DEFAULT_PLANNING_MODE.personaIds);
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const canSubmit = message.trim().length > 0 && selectedPersonaIds.length > 0 && Boolean(sessionId) && !isSubmitting;
  const slashHints = matchingSlashCommands(message);

  // === ANCHOR: PLANNINGPERSONACOMPOSER_HANDLESUBMIT_START ===
  async function handleSubmit() {
    if (isSubmitting) {
      return;
    }
    // 결정적 저장 입구: 정확히 "/저장"이면 페르소나 호출 없이 통제 저장으로 위임한다.
    // (canSubmit/페르소나 선택보다 먼저 — 페르소나 미선택이어도 저장은 가능해야 한다.)
    if (isSaveCommand(message)) {
      setMessage("");
      onSlashSave();
      return;
    }
    if (!canSubmit || !sessionId) {
      return;
    }
    const prompt = message.trim();
    const agents = [...selectedPersonaIds];
    const createdAt = new Date().toISOString();
    setIsSubmitting(true);
    setMessage("");
    let latest = withPendingTurn(result, prompt, agents, createdAt);
    onResultChange(latest);

    // 한 페르소나가 하드 에러로 실패해도 break 하지 않고 나머지 페르소나를 계속 진행한다.
    // includeUserMessage 는 "성공해서 사용자 메시지가 실제 저장됐는가"로 판단한다(인덱스 0 고정 금지).
    let userPersisted = false;
    for (const [index, agent] of agents.entries()) {
      const nextResult = await appendPlanningChatTurn({
        projectDir,
        sessionId,
        prompt,
        agents: [agent],
        includeUserMessage: !userPersisted,
        extractCards: index === agents.length - 1,
      });
      const remaining = agents.slice(index + 1);
      if (nextResult.ok) {
        userPersisted = true;
        latest = withPendingAgents(nextResult, remaining, createdAt);
      } else {
        latest = markAgentFailed(latest, agent, createdAt);
      }
      onResultChange(latest);
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
              fontSize: 12,
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
            fontSize: 12,
            fontWeight: 900,
            cursor: "pointer",
          }}
        >
          모두
        </button>
      </div>
      {slashHints.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          {slashHints.map((hint) => (
            <button
              key={hint.command}
              type="button"
              // onMouseDown + preventDefault: 클릭으로 textarea 포커스가 풀리기 전에 값을 채운다.
              onMouseDown={(event) => {
                event.preventDefault();
                setMessage(hint.command);
              }}
              style={{
                display: "flex",
                gap: 6,
                alignItems: "center",
                border: "2px solid #1A1A1A",
                background: "#F7F0DF",
                padding: "4px 8px",
                fontSize: 12,
                fontWeight: 800,
                cursor: "pointer",
              }}
            >
              <span style={{ fontFamily: "IBM Plex Mono, monospace" }}>{hint.command}</span>
              <span style={{ opacity: 0.7 }}>{hint.label}</span>
            </button>
          ))}
          <span style={{ fontSize: 12, opacity: 0.6 }}>Tab 키로 완성</span>
        </div>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) 72px", gap: 8, alignItems: "end" }}>
        <textarea
          className="input-field"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={(event) => {
            // 슬래시 커맨드 힌트가 떠 있으면 Tab 으로 첫 제안을 자동완성한다.
            // IME 조합 중(Windows 한글 등)에는 끼어들지 않는다 — 조합 버퍼가 setMessage 와
            // 충돌해 "/저장저" 같은 깨진 입력이 생기는 걸 막는다. ("/" 단독 발견 경로는 조합이 없어 즉시 동작.)
            if (
              event.key === "Tab" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing &&
              slashHints.length > 0
            ) {
              event.preventDefault();
              setMessage(slashHints[0].command);
              return;
            }
            // 한글/일본어 IME 조합 중 Enter 는 조합 확정용이므로 전송하지 않는다.
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
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
