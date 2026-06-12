// === ANCHOR: MANUALCOMMANDDETAIL_START ===
import type { GuideStep } from "../../lib/commands";
import type { ManualCommand } from "./ManualCommandList";

interface ManualCommandDetailProps {
  readonly command: ManualCommand;
  readonly onBack: () => void;
}

// === ANCHOR: MANUALCOMMANDDETAIL_MANUALCOMMANDDETAIL_START ===
export function ManualCommandDetail({ command, onBack }: ManualCommandDetailProps) {
  const guide = "guide" in command && Array.isArray(command.guide) ? command.guide : null;
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="page-header" style={{ padding: "12px 20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn btn-ghost btn-sm" onClick={onBack} style={{ fontSize: 12 }} type="button">← 목록</button>
          <div style={{ width: 32, height: 32, background: command.color, border: "2px solid #1A1A1A", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16 }}>
            {command.icon}
          </div>
          <div>
            <div style={{ fontWeight: 900, fontSize: 14 }}>{command.title}</div>
            <div style={{ fontSize: 12, color: "#666" }}>{command.usage}</div>
          </div>
        </div>
      </div>

      <div className="page-content">
        <div style={{ background: `${command.color}22`, border: `2px solid ${command.color}`, padding: "10px 14px", marginBottom: 12, fontWeight: 700, fontSize: 12 }}>
          {command.short}
        </div>

        <div className="card" style={{ marginBottom: 12, padding: "14px 16px" }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>어떤 기능이에요?</div>
          <div style={{ fontSize: 13, lineHeight: 1.8, color: "#1A1A1A" }}>{command.desc}</div>
        </div>

        <div className="terminal" style={{ marginBottom: 12 }}>
          <div className="terminal-header">
            <div className="terminal-dot red" />
            <div className="terminal-dot yellow" />
            <div className="terminal-dot green" />
          </div>
          <div style={{ marginTop: 4 }}>
            <span className="terminal-prompt">$ </span>
            <span style={{ color: "#FFD166", fontWeight: 700 }}>{command.usage}</span>
          </div>
        </div>

        {guide ? <ManualCommandGuide commandColor={command.color} guide={guide} /> : <ManualCommandTips commandColor={command.color} tips={command.tips} />}

        {command.flags?.length ? (
          <div className="card" style={{ marginTop: 12, padding: "12px 14px" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#888", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>서브명령 / 옵션</div>
            <div style={{ display: "grid", gap: 6 }}>
              {command.flags.map((flag, index) => {
                if (flag.type === "select") {
                  return (
                    <div key={`${flag.label}:${index}`} style={{ display: "grid", gap: 4 }}>
                      <div style={{ fontSize: 12, fontWeight: 900, color: "#555" }}>{flag.label}</div>
                      {flag.options.map((option) => (
                        <div key={option.v} style={{ display: "flex", gap: 6, alignItems: "baseline", fontSize: 12, lineHeight: 1.45 }}>
                          <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 10, fontWeight: 800, color: command.color, minWidth: 150 }}>{option.v}</span>
                          <span style={{ color: "#444" }}>{option.l}</span>
                        </div>
                      ))}
                    </div>
                  );
                }
                return (
                  <div key={`${flag.label}:${index}`} style={{ display: "flex", gap: 6, alignItems: "baseline", fontSize: 12, lineHeight: 1.45 }}>
                    <span style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 10, fontWeight: 800, color: command.color, minWidth: 150 }}>{flag.label}</span>
                    <span style={{ color: "#444" }}>{flag.type === "bool" ? "켜고 끄는 옵션" : flag.placeholder ?? "값을 입력하는 옵션"}</span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
// === ANCHOR: MANUALCOMMANDDETAIL_MANUALCOMMANDDETAIL_END ===

// === ANCHOR: MANUALCOMMANDDETAIL_MANUALCOMMANDGUIDE_START ===
function ManualCommandGuide({ commandColor, guide }: { readonly commandColor: string; readonly guide: readonly GuideStep[] }) {
  return (
    <div>
      {guide.map((step, index) => (
        <div key={`${step.step}:${index}`} className="card" style={{ marginBottom: 8, padding: "12px 14px" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: step.subtitle ? 2 : 8 }}>
            <span style={{
              fontSize: 12,
              fontWeight: 900,
              padding: "2px 6px",
              background: step.optional ? "#444" : commandColor,
              color: step.optional ? "#aaa" : "#1A1A1A",
              border: "1.5px solid #1A1A1A",
              flexShrink: 0,
            }}>{step.step}</span>
            <span style={{ fontWeight: 800, fontSize: 12 }}>{step.title}</span>
          </div>
          {step.subtitle ? <div style={{ fontSize: 12, color: "#888", marginBottom: 8, marginLeft: 2 }}>{step.subtitle}</div> : null}
          {step.lines.map((line, lineIndex) => {
            if (line.t === "code") {
              return (
                <div key={`${line.t}:${lineIndex}`} style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 10, fontWeight: 700, background: "#1A1A1A", color: "#4DFF91", padding: "5px 10px", marginBottom: 4, overflowX: "auto", whiteSpace: "nowrap" }}>
                  {line.v}
                </div>
              );
            }
            if (line.t === "label") {
              return <div key={`${line.t}:${lineIndex}`} style={{ fontSize: 12, fontWeight: 800, color: "#888", marginTop: 6, marginBottom: 2 }}>{line.v}</div>;
            }
            if (line.t === "error") {
              return <div key={`${line.t}:${lineIndex}`} style={{ fontFamily: "IBM Plex Mono, monospace", fontSize: 10, fontWeight: 700, color: "#FF4D4D", marginTop: 8, marginBottom: 2 }}>{line.v}</div>;
            }
            return <div key={`${line.t}:${lineIndex}`} style={{ fontSize: 12, color: "#444", lineHeight: 1.6, marginBottom: 2 }}>{line.v}</div>;
          })}
          {step.warn ? (
            <div style={{ marginTop: 8, fontSize: 12, fontWeight: 700, color: "#FFD166", background: "#FFD16618", border: "1.5px solid #FFD16666", padding: "5px 10px" }}>⚠ {step.warn}</div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
// === ANCHOR: MANUALCOMMANDDETAIL_MANUALCOMMANDGUIDE_END ===

// === ANCHOR: MANUALCOMMANDDETAIL_MANUALCOMMANDTIPS_START ===
function ManualCommandTips({ commandColor, tips }: { readonly commandColor: string; readonly tips: readonly string[] }) {
  return (
    <div className="card" style={{ padding: "14px 16px" }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#888", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>💡 이렇게 써요</div>
      {tips.map((tip) => (
        <div key={tip} style={{ display: "flex", gap: 8, marginBottom: 6, fontSize: 12, lineHeight: 1.6 }}>
          <span style={{ color: commandColor, fontWeight: 900, flexShrink: 0 }}>▸</span>
          <span>{tip}</span>
        </div>
      ))}
    </div>
  );
}
// === ANCHOR: MANUALCOMMANDDETAIL_MANUALCOMMANDTIPS_END ===
// === ANCHOR: MANUALCOMMANDDETAIL_END ===
