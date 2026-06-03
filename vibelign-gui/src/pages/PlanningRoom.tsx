import { useState } from "react";

import { openFolder, savePlanningChatAsMarkdown, type PlanningChatSessionResponse } from "../lib/vib";
import { PlanningActionBar } from "./planning/PlanningActionBar";
import { PlanningAdvancedDetails } from "./planning/PlanningAdvancedDetails";
import { PlanningMarkdownView } from "./planning/PlanningMarkdownView";
import { PlanningMessages } from "./planning/PlanningMessages";
import { PlanningPersonaComposer } from "./planning/PlanningPersonaComposer";
import { PlanningPersonaProgressSummary } from "./planning/PlanningPersonaProgressSummary";
import { PlanningPersonaResponseSummary } from "./planning/PlanningPersonaResponseSummary";

interface PlanningRoomProps {
  readonly projectDir: string;
  readonly result: PlanningChatSessionResponse;
  readonly onBack: () => void;
  readonly onStartWork?: () => void;
  readonly onResultChange: (result: PlanningChatSessionResponse) => void;
}

export default function PlanningRoom({ projectDir, result, onBack, onStartWork, onResultChange }: PlanningRoomProps) {
  const [showMarkdown, setShowMarkdown] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const markdown = result.markdown ?? "";
  const isPending = result.messages.some((message) => message.status === "pending");
  const savedPlanOpenPath = getSavedPlanOpenPath(projectDir, result);
  const hasSavedPlan = Boolean(savedPlanOpenPath);
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

  async function handleOpenSavedPlan() {
    if (!savedPlanOpenPath) {
      return;
    }
    try {
      await openFolder(savedPlanOpenPath);
    } catch (error) {
      onResultChange({
        ...result,
        ok: false,
        message: "저장된 기획안 파일을 열지 못했어요.",
        details: error instanceof Error ? error.message : String(error),
      });
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
            <PlanningPersonaProgressSummary messages={result.messages} />
            <PlanningPersonaResponseSummary messages={result.messages} />
            <PlanningMessages messages={result.messages} outputPath={result.outputPath ?? null} />
            <PlanningPersonaComposer projectDir={projectDir} result={result} sessionId={result.sessionId ?? null} onResultChange={onResultChange} />
            <PlanningActionBar
              canSave={canSave}
              canView={canView}
              hasSavedPlan={hasSavedPlan}
              isSaving={isSaving}
              onOpenSavedPlan={() => void handleOpenSavedPlan()}
              onSave={handleSavePlan}
              onStartWork={onStartWork ?? onBack}
              onToggleMarkdown={() => setShowMarkdown((visible) => !visible)}
            />
            <PlanningAdvancedDetails details={result.details} />
            {showMarkdown && <PlanningMarkdownView markdown={markdown} />}
          </>
        ) : (
          <>
            <div role="alert" className="alert alert-error" style={{ padding: 14, fontSize: 12 }}>
              {result.message ?? "기획안을 만들지 못했어요."}
            </div>
            <PlanningAdvancedDetails details={result.details} />
          </>
        )}
      </div>
    </main>
  );
}

function getSavedPlanOpenPath(projectDir: string, result: PlanningChatSessionResponse): string | null {
  const absoluteOutputPath = result.absoluteOutputPath?.trim();
  if (absoluteOutputPath) {
    return absoluteOutputPath;
  }
  const outputPath = result.outputPath?.trim();
  if (!outputPath) {
    return null;
  }
  if (isAbsolutePath(outputPath)) {
    return outputPath;
  }
  return `${projectDir.replace(/[\\/]$/, "")}/${outputPath.replace(/^[\\/]/, "")}`;
}

function isAbsolutePath(path: string): boolean {
  return path.startsWith("/") || /^[A-Z]:[\\/]/i.test(path);
}
