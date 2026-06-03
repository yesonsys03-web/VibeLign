import { useState } from "react";

import { savePlanningChatAsMarkdown, type PlanningChatSessionResponse } from "../lib/vib";
import { PlanningMarkdownView } from "./planning/PlanningMarkdownView";
import { PlanningMessages } from "./planning/PlanningMessages";
import { PlanningPersonaComposer } from "./planning/PlanningPersonaComposer";

interface PlanningRoomProps {
  readonly projectDir: string;
  readonly result: PlanningChatSessionResponse;
  readonly onBack: () => void;
  readonly onResultChange: (result: PlanningChatSessionResponse) => void;
}

export default function PlanningRoom({ projectDir, result, onBack, onResultChange }: PlanningRoomProps) {
  const [showMarkdown, setShowMarkdown] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const markdown = result.markdown ?? "";
  const isPending = result.messages.some((message) => message.status === "pending");
  const canSave = result.ok && !isPending && !isSaving && Boolean(result.sessionId);
  const canView = !isPending && Boolean(markdown);

  async function handleSavePlan() {
    const sessionId = result.sessionId;
    if (!sessionId || !canSave) {
      return;
    }
    setIsSaving(true);
    try {
      const next = await savePlanningChatAsMarkdown({ projectDir, sessionId });
      onResultChange(next);
      if (next.markdown) {
        setShowMarkdown(true);
      }
    } catch (error) {
      onResultChange({
        ok: false,
        sessionId,
        prompt: result.prompt ?? null,
        messages: result.messages,
        message: "기획안을 저장하지 못했어요.",
        details: error instanceof Error ? error.message : String(error),
      });
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main style={{ height: "100%", overflow: "auto", background: "var(--bg)" }}>
      <div style={{ width: "min(920px, calc(100% - 32px))", margin: "0 auto", padding: "28px 0", display: "grid", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn btn-ghost btn-sm" type="button" onClick={onBack} style={{ fontSize: 11 }}>
            ← 홈
          </button>
          <h1 className="heading-xl" style={{ fontSize: 22, margin: 0 }}>
            기획방
          </h1>
        </div>

        {result.ok ? (
          <>
            <PlanningMessages messages={result.messages} outputPath={result.outputPath ?? null} />
            <PlanningPersonaComposer projectDir={projectDir} result={result} sessionId={result.sessionId ?? null} onResultChange={onResultChange} />
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <button
                className="btn btn-black"
                type="button"
                onClick={handleSavePlan}
                disabled={!canSave}
                style={{ fontSize: 12, opacity: canSave ? 1 : 0.5 }}
              >
                {isSaving ? "저장중" : result.outputPath ? "기획안 다시 저장" : "기획안으로 저장"}
              </button>
              <button
                className="btn btn-black"
                type="button"
                onClick={() => setShowMarkdown((visible) => !visible)}
                disabled={!canView}
                style={{ fontSize: 12, opacity: canView ? 1 : 0.5 }}
              >
                기획안 보기
              </button>
            </div>
            {showMarkdown && <PlanningMarkdownView markdown={markdown} />}
          </>
        ) : (
          <div role="alert" className="alert alert-error" style={{ padding: 14, fontSize: 12 }}>
            {result.message ?? "기획안을 만들지 못했어요."}
          </div>
        )}
      </div>
    </main>
  );
}
