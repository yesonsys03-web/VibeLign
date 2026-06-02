import { useState } from "react";

import type { CreatePlanningTemplateResponse } from "../lib/vib";
import { PlanningMarkdownView } from "./planning/PlanningMarkdownView";
import { PlanningMessages } from "./planning/PlanningMessages";
import { PlanningPersonaComposer } from "./planning/PlanningPersonaComposer";
import { PlanningPersonaStatus } from "./planning/PlanningPersonaStatus";

interface PlanningRoomProps {
  readonly projectDir: string;
  readonly prompt: string;
  readonly result: CreatePlanningTemplateResponse;
  readonly onBack: () => void;
  readonly onResultChange: (result: CreatePlanningTemplateResponse) => void;
}

export default function PlanningRoom({ projectDir, prompt, result, onBack, onResultChange }: PlanningRoomProps) {
  const [showMarkdown, setShowMarkdown] = useState(false);
  const markdown = result.markdown ?? "";
  const isPending = result.llmStatus === "pending";

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
            <PlanningPersonaStatus result={result} />
            <PlanningMessages prompt={prompt} outputPath={result.outputPath ?? null} />
            <PlanningPersonaComposer projectDir={projectDir} outputPath={result.outputPath ?? null} onResultChange={onResultChange} />
            <div>
              <button
                className="btn btn-black"
                type="button"
                onClick={() => setShowMarkdown((visible) => !visible)}
                disabled={isPending || !markdown}
                style={{ fontSize: 12, opacity: isPending || !markdown ? 0.5 : 1 }}
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
