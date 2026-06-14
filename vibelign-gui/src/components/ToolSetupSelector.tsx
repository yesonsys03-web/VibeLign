// === ANCHOR: TOOLSETUPSELECTOR_START ===
import { useState, type ReactElement } from "react";
import { ToolInstallPanel } from "./tools/ToolInstallPanel";

// vib start --tools 가 받는 키와 1:1 (vibelign/commands/vib_start_cmd.py START_TOOL_CHOICES).
// autoInstall: true = VibeLign이 자동 설치해 줌 / false = 직접 설치 필요.
//   - claude: 기존 온보딩 설치 플로(OnboardingClaudeSetup)로 자동 설치.
//   - opencode/codex/antigravity: 아래 ToolInstallPanel(AUTO_INSTALL_PANEL_ID)로 자동 설치.
//   - claude_desktop/cursor: 자동 설치 미지원(직접 설치).
const SETUP_TOOLS: readonly { readonly key: string; readonly label: string; readonly autoInstall: boolean }[] = [
  { key: "claude", label: "Claude Code", autoInstall: true },
  { key: "claude_desktop", label: "Claude Desktop", autoInstall: false },
  { key: "cursor", label: "Cursor", autoInstall: false },
  { key: "codex", label: "Codex", autoInstall: true },
  { key: "opencode", label: "OpenCode", autoInstall: true },
  { key: "antigravity", label: "Antigravity", autoInstall: true },
];

// 자동설치 패널을 지원하는 도구 키 → installerRegistry id 매핑
// (antigravity 선택 키 ≠ agy 레지스트리 id)
const AUTO_INSTALL_PANEL_ID: Readonly<Record<string, string>> = {
  opencode: "opencode",
  codex: "codex",
  antigravity: "agy",
};

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
  // 자동 설치 패널 확장 상태 — key: 도구 key, 기본 닫힘
  const [expandedPanel, setExpandedPanel] = useState<string | null>(null);

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
        const panelId = AUTO_INSTALL_PANEL_ID[tool.key];
        const panelOpen = expandedPanel === tool.key;
        return (
          <div key={tool.key} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <button
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
                {tool.autoInstall ? (
                  <span
                    title="VibeLign이 자동으로 설치해 드려요"
                    style={{
                      marginLeft: 4,
                      fontSize: 9,
                      fontWeight: 800,
                      padding: "1px 4px",
                      background: active ? "rgba(255,255,255,0.25)" : "#D1FAE5",
                      color: active ? "#fff" : "#065F46",
                      borderRadius: 3,
                      verticalAlign: "middle",
                    }}
                  >
                    자동설치
                  </span>
                ) : (
                  <span
                    title="직접 설치가 필요해요"
                    style={{
                      marginLeft: 4,
                      fontSize: 9,
                      fontWeight: 700,
                      padding: "1px 4px",
                      background: active ? "rgba(255,255,255,0.15)" : "#F3F4F6",
                      color: active ? "rgba(255,255,255,0.8)" : "#9CA3AF",
                      borderRadius: 3,
                      verticalAlign: "middle",
                    }}
                  >
                    직접설치
                  </span>
                )}
              </button>
              {panelId != null && !disabled && (
                <button
                  type="button"
                  title="자동 설치 패널 열기/닫기"
                  aria-expanded={panelOpen}
                  onClick={() => setExpandedPanel(panelOpen ? null : tool.key)}
                  style={{
                    fontSize: 9,
                    fontWeight: 800,
                    padding: "2px 5px",
                    border: "1px solid #1A1A1A",
                    background: panelOpen ? "#1A1A1A" : "transparent",
                    color: panelOpen ? "#fff" : "#1A1A1A",
                    cursor: "pointer",
                    lineHeight: 1.2,
                  }}
                >
                  자동 설치
                </button>
              )}
            </div>
            {panelId != null && panelOpen && (
              <ToolInstallPanel
                id={panelId}
                onDone={() => setExpandedPanel(null)}
              />
            )}
          </div>
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
