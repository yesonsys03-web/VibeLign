// === ANCHOR: PLANNINGROOM_START ===
import { useState } from "react";
import { confirm as tauriConfirm } from "@tauri-apps/plugin-dialog";

import {
  openFolder,
  retryPlanningPersona,
  savePlanningChatAsMarkdown,
  type PlanningChatMessage,
  type PlanningChatSessionResponse,
} from "../lib/vib";
import { PlanningActionBar } from "./planning/PlanningActionBar";
import { markMessagePending } from "./planning/PlanningPersonaComposerState";
import { PlanningAdvancedDetails } from "./planning/PlanningAdvancedDetails";
import { PlanningMarkdownView } from "./planning/PlanningMarkdownView";
import { PlanningMessages } from "./planning/PlanningMessages";
import { PlanningPersonaComposer } from "./planning/PlanningPersonaComposer";
import { PlanningPersonaProgressSummary } from "./planning/PlanningPersonaProgressSummary";
import { PlanningPersonaResponseSummary } from "./planning/PlanningPersonaResponseSummary";
import { PlanningCardsPanel } from "./planning/PlanningCardsPanel";
import { PlanningReadinessPanel } from "./planning/PlanningReadinessPanel";
import { readinessSummary } from "./planning/PlanningReadiness";

interface PlanningRoomProps {
  readonly projectDir: string;
  readonly result: PlanningChatSessionResponse;
  readonly sourcePath?: string | null;
  readonly onBack: () => void;
  readonly onStartWork?: () => void;
  readonly onDesignPreview?: (planPath: string) => void;
  readonly onResultChange: (result: PlanningChatSessionResponse) => void;
  /** 저장 후 백그라운드 보강(준비상태·계약 분석) 진행 중 — "분석 중" 표시(App 소유). */
  readonly isEnriching?: boolean;
  /** 즉시 저장 직후 백그라운드 보강을 시작시킨다(App 이 navigation 너머까지 소유). */
  readonly onEnrich?: (sessionId: string) => void;
}

export default function PlanningRoom({ projectDir, result, sourcePath, onBack, onStartWork, onDesignPreview, onResultChange, isEnriching = false, onEnrich }: PlanningRoomProps) {
  const [showMarkdown, setShowMarkdown] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [pendingSaveSource, setPendingSaveSource] = useState<"button" | "slash">("button");
  const markdown = result.markdown ?? "";
  const isPending = result.messages.some((message) => message.status === "pending");
  const savedPlanOpenPath = getSavedPlanOpenPath(projectDir, result);
  const hasSavedPlan = Boolean(savedPlanOpenPath);
  const canSave = result.ok && !isPending && !isSaving && Boolean(result.sessionId);
  const canView = !isPending && Boolean(markdown);
  // 특정 파일을 검토하며 시작한 세션이고 아직 저장 전이면 저장 위치를 묻는다.
  const usesSaveDialog = Boolean(sourcePath) && !result.outputPath;

  // === ANCHOR: PLANNINGROOM_HANDLESAVEPLAN_START ===
  async function savePlan(targetPath?: string, source: "button" | "slash" = "button") {
    const sessionId = result.sessionId;
    if (!sessionId || !canSave) {
      return;
    }
    setIsSaving(true);
    try {
      const next = await savePlanningChatAsMarkdown(
        targetPath ? { projectDir, sessionId, targetPath, source } : { projectDir, sessionId, source },
      );
      onResultChange(next);
      if (next.markdown) {
        setShowMarkdown(true);
      }
      // 즉시 저장은 끝 — 준비상태·계약 AI 분석은 백그라운드로(App 소유, navigation 생존).
      if (next.ok && next.sessionId) {
        onEnrich?.(next.sessionId);
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

  // 버튼·/저장 모두 같은 통제 저장 경로를 타되, 출처(source)만 다르게 기록한다.
  // 저장 위치를 묻는 세션이면 다이얼로그를 거치며, 그 출처를 보존해 확정 시 함께 넘긴다.
  function handleSavePlan(source: "button" | "slash" = "button") {
    if (usesSaveDialog) {
      setPendingSaveSource(source);
      setShowSaveDialog(true);
      return;
    }
    void savePlan(undefined, source);
  }
  // === ANCHOR: PLANNINGROOM_HANDLESAVEPLAN_END ===

  // === ANCHOR: PLANNINGROOM_HANDLEOPENSAVEDPLAN_START ===
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
  // === ANCHOR: PLANNINGROOM_HANDLEOPENSAVEDPLAN_END ===

  // === ANCHOR: PLANNINGROOM_HANDLERETRYPERSONA_START ===
  async function handleRetryPersona(message: PlanningChatMessage) {
    const sessionId = result.sessionId;
    if (!sessionId || isPending) {
      return;
    }
    onResultChange(markMessagePending(result, message.id));
    try {
      const next = await retryPlanningPersona({ projectDir, sessionId, messageId: message.id });
      // 백엔드가 실패(ok:false)면 대화를 지우지 말고 이전 상태로 되돌린다.
      onResultChange(next.ok ? next : result);
    } catch {
      onResultChange(result);
    }
  }
  // === ANCHOR: PLANNINGROOM_HANDLERETRYPERSONA_END ===

  // === ANCHOR: PLANNINGROOM_HANDLESTARTWORK_START ===
  async function handleStartWork() {
    const proceed = onStartWork ?? onBack;
    // 저장 이후 대화가 더 진행됐으면 기획안·계약이 구버전 — 그대로 시작하면 지시문이 옛 기준이 된다.
    if (result.docStale && hasSavedPlan) {
      const ok = await tauriConfirm(
        "저장된 기획안·작업 계약이 마지막 대화를 반영하지 않았어요.\n'기획안 다시 저장'을 먼저 누르는 걸 권장합니다.\n저장하지 않고 작업을 시작할까요?",
        { title: "작업 시작", kind: "warning" },
      );
      if (!ok) {
        return;
      }
    }
    const summary = readinessSummary(result.readiness);
    if (!summary.canStartWork) {
      const ok = await tauriConfirm(
        `핵심 항목 ${summary.coreRedCount}개가 명세에 비어 있어 구현 도구가 임의로 채웁니다.\n그래도 작업을 시작할까요?`,
        { title: "작업 시작", kind: "warning" },
      );
      if (!ok) {
        return;
      }
    }
    proceed();
  }
  // === ANCHOR: PLANNINGROOM_HANDLESTARTWORK_END ===

  return (
    <>
    <main className="page-content" style={{ height: "100%", overflow: "auto", background: "var(--bg)", padding: 0 }}>
      <div style={{ width: "min(920px, calc(100% - 32px))", margin: "0 auto", padding: "28px 0", display: "grid", gap: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn btn-ghost btn-sm" type="button" onClick={onBack} style={{ fontSize: 12 }}>
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
            <PlanningMessages messages={result.messages} outputPath={result.outputPath ?? null} onRetry={(message) => void handleRetryPersona(message)} />
            <PlanningReadinessPanel report={result.readiness} />
            <PlanningCardsPanel
              cards={result.cards}
              projectDir={projectDir}
              sessionId={result.sessionId ?? null}
              onCardsChange={(cards) => onResultChange({ ...result, cards })}
            />
            <PlanningPersonaComposer projectDir={projectDir} result={result} sessionId={result.sessionId ?? null} onResultChange={onResultChange} onSlashSave={() => handleSavePlan("slash")} />
            {result.docStale && hasSavedPlan && !isPending && (
              <div style={{ fontSize: 12, color: "#B45309", background: "#FEF3C7", border: "1px solid #FDE68A", borderRadius: 6, padding: "8px 12px" }}>
                저장된 기획안 이후 대화가 더 진행됐어요 — ‘기획안 다시 저장’을 누르면 최신 내용이 반영됩니다.
              </div>
            )}
            <PlanningActionBar
              canSave={canSave}
              canView={canView}
              hasSavedPlan={hasSavedPlan}
              isSaving={isSaving}
              isEnriching={isEnriching}
              onOpenSavedPlan={() => void handleOpenSavedPlan()}
              onSave={() => handleSavePlan("button")}
              onStartWork={handleStartWork}
              onToggleMarkdown={() => setShowMarkdown((visible) => !visible)}
              onDesignPreview={result.outputPath && onDesignPreview ? () => onDesignPreview(result.outputPath!) : undefined}
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
    {showSaveDialog && sourcePath && (
      <PlanSaveDialog
        sourcePath={sourcePath}
        onCancel={() => setShowSaveDialog(false)}
        onConfirm={(targetPath) => {
          setShowSaveDialog(false);
          void savePlan(targetPath, pendingSaveSource);
        }}
      />
    )}
    </>
  );
}

// === ANCHOR: PLANNINGROOM_GETSAVEDPLANOPENPATH_START ===
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
// === ANCHOR: PLANNINGROOM_GETSAVEDPLANOPENPATH_END ===

// === ANCHOR: PLANNINGROOM_ISABSOLUTEPATH_START ===
function isAbsolutePath(path: string): boolean {
  return path.startsWith("/") || /^[A-Z]:[\\/]/i.test(path);
}
// === ANCHOR: PLANNINGROOM_ISABSOLUTEPATH_END ===

// === ANCHOR: PLANNINGROOM_PLANSAVEDIALOG_START ===
interface PlanSaveDialogProps {
  readonly sourcePath: string;
  readonly onCancel: () => void;
  readonly onConfirm: (targetPath: string) => void;
}

function PlanSaveDialog({ sourcePath, onCancel, onConfirm }: PlanSaveDialogProps) {
  const { dir, basename, stem } = splitSourcePath(sourcePath);
  const defaultName = `${stem}-review.md`;
  const [fileName, setFileName] = useState(defaultName);
  const [overwrite, setOverwrite] = useState(false);

  function handleConfirm() {
    if (overwrite) {
      onConfirm(sourcePath);
      return;
    }
    let name = fileName.trim() || defaultName;
    if (!name.endsWith(".md")) {
      name = `${name}.md`;
    }
    onConfirm(dir ? `${dir}/${name}` : name);
  }

  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
      onClick={onCancel}
    >
      <div
        style={{ background: "#FEFBF0", border: "2px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 440, display: "flex", flexDirection: "column" }}
        onClick={(event) => event.stopPropagation()}
      >
        <div style={{ background: "#1A1A1A", padding: "12px 18px" }}>
          <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 13, color: "#fff", letterSpacing: 1 }}>기획안 저장</span>
        </div>
        <div style={{ padding: "18px", display: "grid", gap: 14 }}>
          <div style={{ fontSize: 12, color: "#1A1A1A" }}>저장 폴더: {dir || "."}</div>
          <label style={{ display: "grid", gap: 6, fontSize: 12, fontWeight: 700, opacity: overwrite ? 0.5 : 1 }}>
            파일 이름
            <input
              type="text"
              value={fileName}
              disabled={overwrite}
              onChange={(event) => setFileName(event.target.value)}
              style={{ padding: "8px 10px", border: "2px solid #1A1A1A", fontSize: 13, background: "#fff" }}
            />
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, fontWeight: 700 }}>
            <input type="checkbox" checked={overwrite} onChange={(event) => setOverwrite(event.target.checked)} />
            원본 파일({basename}) 덮어쓰기
          </label>
        </div>
        <div style={{ padding: "12px 18px", borderTop: "2px solid #1A1A1A", display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="btn btn-ghost btn-sm" type="button" onClick={onCancel}>취소</button>
          <button className="btn btn-sm" style={{ background: "#FF4D8B" }} type="button" onClick={handleConfirm}>저장</button>
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: PLANNINGROOM_PLANSAVEDIALOG_END ===

// === ANCHOR: PLANNINGROOM_SPLITSOURCEPATH_START ===
function splitSourcePath(sourcePath: string): { dir: string; basename: string; stem: string } {
  const normalized = sourcePath.replace(/\\/g, "/");
  const lastSlash = normalized.lastIndexOf("/");
  const dir = lastSlash >= 0 ? normalized.slice(0, lastSlash) : "";
  const basename = lastSlash >= 0 ? normalized.slice(lastSlash + 1) : normalized;
  const lastDot = basename.lastIndexOf(".");
  const stem = lastDot > 0 ? basename.slice(0, lastDot) : basename;
  return { dir, basename, stem };
}
// === ANCHOR: PLANNINGROOM_SPLITSOURCEPATH_END ===
// === ANCHOR: PLANNINGROOM_END ===
