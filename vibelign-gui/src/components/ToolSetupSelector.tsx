// === ANCHOR: TOOLSETUPSELECTOR_START ===
import { useState, type ReactElement } from "react";

// vib start --tools 가 받는 키와 1:1 (vibelign/commands/vib_start_cmd.py START_TOOL_CHOICES).
const SETUP_TOOLS: readonly { readonly key: string; readonly label: string }[] = [
  { key: "claude", label: "Claude Code" },
  { key: "claude_desktop", label: "Claude Desktop" },
  { key: "cursor", label: "Cursor" },
  { key: "codex", label: "Codex" },
  { key: "opencode", label: "OpenCode" },
  { key: "antigravity", label: "Antigravity" },
];

export const SETUP_TOOL_KEYS: readonly string[] = SETUP_TOOLS.map((t) => t.key);

interface ToolSetupSelectorProps {
  readonly detected: readonly string[] | null;
  readonly selected: ReadonlySet<string>;
  readonly onChange: (next: Set<string>) => void;
  readonly disabled?: boolean;
}

// === ANCHOR: TOOLSETUPSELECTOR_TOOLSETUPSELECTOR_START ===
export function ToolSetupSelector({ detected, selected, onChange, disabled = false }: ToolSetupSelectorProps): ReactElement {
  const allSelected = SETUP_TOOLS.every((t) => selected.has(t.key));
  // MCP 설명 말풍선(W4) — "전체 선택" 클릭 시 등장, "전체 해제" 시 숨김. 컴포넌트 내부에 캡슐화.
  const [mcpTip, setMcpTip] = useState(false);

  function toggle(key: string): void {
    const next = new Set(selected);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    onChange(next);
  }

  function toggleAll(): void {
    onChange(allSelected ? new Set() : new Set(SETUP_TOOL_KEYS));
    setMcpTip(!allSelected); // 전체 선택 → 설명, 전체 해제 → 숨김
  }

  return (
    <>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {SETUP_TOOLS.map((tool) => {
        const active = selected.has(tool.key);
        const isDetected = detected?.includes(tool.key) ?? false;
        return (
          <button
            key={tool.key}
            type="button"
            disabled={disabled}
            aria-pressed={active}
            onClick={() => toggle(tool.key)}
            style={{
              fontSize: 11,
              fontWeight: 700,
              padding: "4px 10px",
              border: `2px solid ${active ? "#2D9CDB" : "#333"}`,
              background: active ? "#2D9CDB" : "transparent",
              color: active ? "#fff" : "#888",
              cursor: disabled ? "default" : "pointer",
            }}
          >
            {tool.label}
            {isDetected ? " MCP" : ""}
          </button>
        );
      })}
      <button
        type="button"
        disabled={disabled}
        onClick={toggleAll}
        style={{
          fontSize: 11,
          fontWeight: 700,
          padding: "4px 10px",
          border: `2px solid ${allSelected ? "#4DFF91" : "#333"}`,
          background: allSelected ? "#4DFF91" : "transparent",
          color: allSelected ? "#1A1A1A" : "#888",
          cursor: disabled ? "default" : "pointer",
        }}
      >
        {allSelected ? "전체 해제" : "전체 선택"}
      </button>
    </div>
    {mcpTip && (
      <div className="tip-bubble">
        <span className="ic">🔌</span>
        <span>
          <b>MCP가 뭐냐면</b> — 고른 AI 도구에 바이브라인의 <b>코드맵·앵커·검사·백업</b>을 &apos;연결&apos;하는 거예요.
          그러면 Claude 같은 도구가 이 기능들을 직접 쓰면서 더 똑똑하게 작업해요. 설치된 도구는 자동으로 골라뒀으니 그대로 둬도 돼요!
        </span>
        <button type="button" className="x" aria-label="설명 닫기" onClick={() => setMcpTip(false)}>
          ×
        </button>
      </div>
    )}
    </>
  );
}
// === ANCHOR: TOOLSETUPSELECTOR_TOOLSETUPSELECTOR_END ===
// === ANCHOR: TOOLSETUPSELECTOR_END ===
