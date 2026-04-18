// === ANCHOR: GENERIC_COMMAND_CARD_START ===
import { useRef, useState } from "react";
import { runVib, pickFile, buildGuiAiEnv } from "../../lib/vib";
import GuiCliOutputBlock from "../GuiCliOutputBlock";
import { CardState, FlagDef, buildCmdArgs } from "../../lib/commands";

export interface GenericCmdDef {
  name: string;
  icon: string;
  color: string;
  title: string;
  short: string;
  flags?: FlagDef[];
}

export interface GenericCommandCardProps {
  cmd: GenericCmdDef;
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  hasAnyAiKey?: boolean;
  aiKeyStatusLoaded?: boolean;
  onOpenSettings?: (reason?: string) => void;
}

export default function GenericCommandCard({
  cmd,
  projectDir,
  apiKey,
  providerKeys,
  hasAnyAiKey = false,
  aiKeyStatusLoaded = false,
  onOpenSettings,
}: GenericCommandCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [out, setOut] = useState("");
  const [hasWarning, setHasWarning] = useState(false);
  const [flagValues, setFlagValues] = useState<Record<string, string | boolean>>({});
  const [showModal, setShowModal] = useState(false);
  const idleTimer = useRef<number | undefined>(undefined);

  async function handleRun() {
    const args = buildCmdArgs(cmd.name, { [cmd.name]: flagValues });
    if (!args) {
      setSt("error");
      setOut("필수 항목을 입력해주세요");
      return;
    }
    if (args.includes("--ai") && aiKeyStatusLoaded && !hasAnyAiKey) {
      setSt("error");
      setOut("API 키를 먼저 설정해주세요");
      if (onOpenSettings) onOpenSettings("AI 기능을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      return;
    }
    setSt("loading");
    setOut("");
    if (idleTimer.current !== undefined) {
      window.clearTimeout(idleTimer.current);
      idleTimer.current = undefined;
    }
    try {
      const env = args.includes("--ai") ? buildGuiAiEnv(providerKeys, apiKey) : undefined;
      const r = await runVib(args, projectDir, env);
      const stdoutContent = r.stdout.trim();
      const stderrContent = r.stderr.trim();
      const combined = [stderrContent, stdoutContent].filter(Boolean).join("\n\n");
      const output = combined || (r.ok ? "완료" : `exit ${r.exit_code}`);
      const warn = Boolean(stderrContent);
      setSt(r.ok ? "done" : "error");
      setOut(output);
      setHasWarning(warn);
      if (!r.ok || warn) setShowModal(true);
      if (r.ok && !warn) {
        idleTimer.current = window.setTimeout(() => {
          setSt("idle");
          idleTimer.current = undefined;
        }, 3000);
      }
    } catch (e) {
      setSt("error");
      setOut(String(e));
      setHasWarning(false);
    }
  }

  const hasTextOrSelect = cmd.flags?.some((f) => f.type === "text" || f.type === "select") ?? false;
  const textColor = cmd.color === "#FFD166" || cmd.color === "#FFE44D" ? "#1A1A1A" : "#fff";

  return (
    <>
      {showModal && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setShowModal(false)}
        >
          <div
            style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 480, maxHeight: "70vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ background: "#1A1A1A", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 12, color: "#fff", letterSpacing: 2 }}>{cmd.name.toUpperCase()} 결과</span>
              <button onClick={() => setShowModal(false)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 16 }}>✕</button>
            </div>
            <pre style={{ margin: 0, padding: 16, overflowY: "auto", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word", color: st === "error" ? "#FF4D4D" : "#1A1A1A" }}>
              {out}
            </pre>
          </div>
        </div>
      )}
      <div className="feature-card" style={{ cursor: "default" }}>
        <div className="feature-card-header" style={{ background: cmd.color + "18", padding: "8px 12px" }}>
          <div className="feature-card-icon" style={{
            background: cmd.color, color: "#fff", borderColor: cmd.color,
            width: 22, height: 22, fontSize: 11, fontWeight: 900,
          }}>{cmd.icon}</div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
            <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>{cmd.title}</span>
            <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>{cmd.short}</span>
          </div>
          {(st === "done" || (st === "idle" && out)) && !hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>}
          {hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>}
          {st === "error" && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
        </div>
        <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
          {!hasTextOrSelect && (
            <GuiCliOutputBlock text={out} placeholder={cmd.short} variant={st === "error" ? "error" : hasWarning ? "warn" : "default"} />
          )}
          {cmd.flags?.map((fd, fi) => {
            const val: string | boolean = flagValues[fd.key] ?? (fd.type === "bool" ? false : fd.type === "select" && fd.options.length > 0 ? fd.options[0].v : "");
            if (fd.type === "bool") return (
              <button key={fi} onClick={() => setFlagValues((m) => ({ ...m, [fd.key]: !val }))} style={{
                fontSize: 9, fontWeight: 700, padding: "2px 6px", marginRight: 4, marginBottom: 4,
                border: "2px solid #1A1A1A",
                background: val ? "#1A1A1A" : "#fff",
                color: val ? "#fff" : "#1A1A1A", cursor: "pointer",
              }}>{fd.label}</button>
            );
            if (fd.type === "text") return (
              <div key={fi} style={{ display: "flex", gap: 4, marginBottom: 4 }}>
                <input value={String(val)} onChange={(e) => setFlagValues((m) => ({ ...m, [fd.key]: e.target.value }))} placeholder={(fd as any).placeholder} style={{
                  flex: 1, fontSize: 10, padding: "3px 6px",
                  border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                  fontFamily: "IBM Plex Mono, monospace", background: "#fff", minWidth: 0,
                }} />
                {fd.key === "_file" && (
                  <button onClick={async () => {
                    const picked = await pickFile(projectDir);
                    if (picked) {
                      const rel = picked.startsWith(projectDir + "/") ? picked.slice(projectDir.length + 1) : picked;
                      setFlagValues((m) => ({ ...m, [fd.key]: rel }));
                    }
                  }} style={{ padding: "2px 6px", border: "2px solid #1A1A1A", background: "#fff", cursor: "pointer", fontSize: 13, flexShrink: 0 }}>📁</button>
                )}
              </div>
            );
            if (fd.type === "select") return (
              <select key={fi} value={String(val)} onChange={(e) => setFlagValues((m) => ({ ...m, [fd.key]: e.target.value }))} style={{
                width: "100%", fontSize: 10, padding: "3px 6px", marginBottom: 4,
                border: "2px solid #1A1A1A", boxSizing: "border-box" as const,
                fontFamily: "IBM Plex Mono, monospace", cursor: "pointer", background: "#fff",
              }}>
                {fd.options.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
              </select>
            );
            return null;
          })}
          {out && hasTextOrSelect && (
            <GuiCliOutputBlock text={out} placeholder="" variant={st === "error" ? "error" : hasWarning ? "warn" : "default"} />
          )}
          <div style={{ display: "flex", gap: 4 }}>
            <button
              className="btn btn-sm"
              style={{ flex: 1, background: cmd.color, color: textColor, border: "2px solid #1A1A1A", fontSize: 10 }}
              disabled={st === "loading"}
              onClick={handleRun}
            >
              {st === "loading" ? <span className="spinner" /> : `${cmd.name.toUpperCase()} ▶`}
            </button>
            {out && (
              <button className="btn btn-ghost btn-sm" style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                onClick={() => setShowModal(true)}>결과</button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
// === ANCHOR: GENERIC_COMMAND_CARD_END ===
