// === ANCHOR: ONBOARDINGINPUTBAR_START ===
import type { RefObject } from "react";
import { OnboardingPromptTextarea } from "./OnboardingPromptTextarea";

interface OnboardingInputBarProps {
  readonly promptText: string;
  readonly selectedDirName: string;
  readonly folderHint: string | null;
  readonly claudeSetupOpen: boolean;
  readonly inputRef?: RefObject<HTMLTextAreaElement | null>;
  readonly onPromptChange: (value: string) => void;
  readonly onPickFolder: () => void;
  readonly onSubmit: () => void;
  readonly onToggleClaudeSetup: () => void;
}

// === ANCHOR: ONBOARDINGINPUTBAR_ONBOARDINGINPUTBAR_START ===
export function OnboardingInputBar({
  promptText,
  selectedDirName,
  folderHint,
  claudeSetupOpen,
  inputRef,
  onPromptChange,
  onPickFolder,
  onSubmit,
  onToggleClaudeSetup,
}: OnboardingInputBarProps) {
  return (
    <div style={{ width: "100%", maxWidth: 720 }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "44px minmax(0, 1fr) auto 44px",
          alignItems: "center",
          gap: 8,
          border: "2px solid #1A1A1A",
          background: "#fff",
          padding: 8,
          boxShadow: "4px 4px 0 #1A1A1A",
        }}
      >
        <button
          type="button"
          aria-label="프로젝트 폴더 선택"
          onClick={onPickFolder}
          style={{ width: 34, height: 34, border: "2px solid #1A1A1A", background: "#fff", fontSize: 20, fontWeight: 900, cursor: "pointer" }}
        >
          +
        </button>
        <OnboardingPromptTextarea inputRef={inputRef} value={promptText} onChange={onPromptChange} onSubmit={onSubmit} />
        <button
          type="button"
          aria-label="AI 선택"
          style={{ border: "1px solid #DDD", background: "#F7F7F7", fontSize: 11, fontWeight: 800, padding: "7px 10px", color: "#333" }}
        >
          Instant
        </button>
        <button
          type="button"
          aria-label="전송"
          onClick={onSubmit}
          style={{ width: 34, height: 34, border: "2px solid #1A1A1A", borderRadius: 999, background: "#1A1A1A", color: "#fff", fontSize: 12, fontWeight: 900, cursor: "pointer" }}
        >
          ●
        </button>
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center", marginTop: 10, fontSize: 11, color: "#555" }}>
        <button
          type="button"
          aria-expanded={claudeSetupOpen}
          onClick={onToggleClaudeSetup}
          style={{ display: "inline-flex", alignItems: "center", gap: 6, fontWeight: 700, fontSize: 11, padding: "4px 10px", border: "2px solid #1A1A1A", background: claudeSetupOpen ? "#1A1A1A" : "#fff", color: claudeSetupOpen ? "#fff" : "#1A1A1A", cursor: "pointer" }}
        >
          {claudeSetupOpen ? "▾" : "▸"} Claude Code 준비하기
        </button>
        {selectedDirName && (
          <span style={{ fontWeight: 700, color: "#1A1A1A" }}>
            선택한 폴더: {selectedDirName}
          </span>
        )}
      </div>

      {folderHint && (
        <div role="status" style={{ marginTop: 10, fontSize: 12, fontWeight: 700, color: "#A14B00" }}>
          {folderHint}
        </div>
      )}
    </div>
  );
}
// === ANCHOR: ONBOARDINGINPUTBAR_ONBOARDINGINPUTBAR_END ===
// === ANCHOR: ONBOARDINGINPUTBAR_END ===
