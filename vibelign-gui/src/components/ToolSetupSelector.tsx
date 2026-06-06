// === ANCHOR: TOOLSETUPSELECTOR_START ===
import type { ReactElement } from "react";

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

  function toggle(key: string): void {
    const next = new Set(selected);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    onChange(next);
  }

  return (
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
              border: `2px solid ${active ? "#F5621E" : "#333"}`,
              background: active ? "#F5621E" : "transparent",
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
        onClick={() => onChange(allSelected ? new Set() : new Set(SETUP_TOOL_KEYS))}
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
  );
}
// === ANCHOR: TOOLSETUPSELECTOR_TOOLSETUPSELECTOR_END ===
// === ANCHOR: TOOLSETUPSELECTOR_END ===
