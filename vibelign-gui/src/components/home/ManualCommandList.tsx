import { COMMANDS } from "../../lib/commands";
import LegacyCommandBadge from "./LegacyCommandBadge";

export type ManualCommand = (typeof COMMANDS)[number];

interface ManualCommandListProps {
  readonly onBack: () => void;
  readonly onSelectCommand: (command: ManualCommand) => void;
}

export function ManualCommandList({ onBack, onSelectCommand }: ManualCommandListProps) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header" style={{ padding: "12px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn btn-ghost btn-sm" onClick={onBack} style={{ fontSize: 11 }} type="button">← 홈</button>
          <span className="page-title">MANUAL</span>
        </div>
        <div style={{ fontSize: 11, color: "#666", fontWeight: 600 }}>커맨드 {COMMANDS.length}개</div>
      </div>

      <div className="page-content">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          {COMMANDS.map((command) => (
            <div
              key={command.name}
              className="feature-card"
              style={{ cursor: "pointer" }}
              onClick={() => onSelectCommand(command)}
              onMouseEnter={(event) => {
                event.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseLeave={(event) => {
                event.currentTarget.style.transform = "";
              }}
            >
              <div className="feature-card-header" style={{ background: `${command.color}18`, padding: "8px 12px" }}>
                <div
                  className="feature-card-icon"
                  style={{ background: command.color, color: "#fff", borderColor: command.color, width: 26, height: 26, fontSize: 13, fontWeight: 900 }}
                >
                  {command.icon}
                </div>
                <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
                  <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{command.title}</span>
                  <LegacyCommandBadge visibility={command.visibility} />
                  <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{command.short}</span>
                </div>
              </div>
              <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
                <div style={{ fontSize: 15, color: "#555", lineHeight: 1.5 }}>{command.short}</div>
                <div style={{ marginTop: 4, fontSize: 13.5, fontFamily: "IBM Plex Mono, monospace", color: command.color, fontWeight: 700 }}>
                  {command.usage}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
