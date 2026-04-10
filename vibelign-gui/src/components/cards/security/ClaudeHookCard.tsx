// === ANCHOR: CLAUDE_HOOK_CARD_START ===
import { useCallback, useEffect, useState } from "react";
import { runVib } from "../../../lib/vib";
import type { GenericCommandCardProps } from "../GenericCommandCard";

type ClaudeHookCardProps = Omit<GenericCommandCardProps, "cmd">;

interface HookStatus {
  detected: boolean;
  installed: boolean;
  enabled: boolean;
}

const COLOR = "#FFD166";

function parseStatus(text: string): HookStatus | null {
  const flag = (label: string): boolean | null => {
    const re = new RegExp(`${label}\\s*:\\s*(예|아니오)`);
    const m = re.exec(text);
    if (!m) return null;
    return m[1] === "예";
  };
  const detected = flag("Claude 프로젝트 감지");
  const installed = flag("Hook 설치됨");
  const enabled = flag("Enforcement enabled");
  if (detected === null || installed === null || enabled === null) return null;
  return { detected, installed, enabled };
}

export default function ClaudeHookCard({ projectDir }: ClaudeHookCardProps) {
  const [status, setStatus] = useState<HookStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<"enable" | "disable" | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await runVib(["claude-hook", "status"], projectDir);
      const combined = [r.stderr.trim(), r.stdout.trim()].filter(Boolean).join("\n");
      if (!r.ok) {
        setError(combined || `exit ${r.exit_code}`);
        return;
      }
      const parsed = parseStatus(combined);
      if (!parsed) {
        setError("상태 파싱 실패");
        return;
      }
      setStatus(parsed);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [projectDir]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleToggle(next: boolean) {
    const action = next ? "enable" : "disable";
    setToggling(action);
    setError(null);
    try {
      const r = await runVib(["claude-hook", action], projectDir);
      if (!r.ok) {
        const combined = [r.stderr.trim(), r.stdout.trim()].filter(Boolean).join("\n");
        setError(combined || `exit ${r.exit_code}`);
        return;
      }
      await refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setToggling(null);
    }
  }

  const enabled = status?.enabled ?? false;
  const installed = status?.installed ?? false;
  const detected = status?.detected ?? false;
  const busy = loading || toggling !== null;

  return (
    <div className="feature-card" style={{ cursor: "default" }}>
      <div className="feature-card-header" style={{ background: COLOR + "18", padding: "8px 12px" }}>
        <div className="feature-card-icon" style={{
          background: COLOR, color: "#fff", borderColor: COLOR,
          width: 22, height: 22, fontSize: 11, fontWeight: 900,
        }}>🪝</div>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
          <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>클로드 훅</span>
          <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>
            Claude가 저장 전에 검사하게 만들기
          </span>
        </div>
        {status && enabled && (
          <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>켜짐</span>
        )}
        {status && !enabled && (
          <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#ddd", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>꺼짐</span>
        )}
        {error && (
          <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>
        )}
      </div>
      <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
        <div style={{ fontSize: 9, color: "#666", marginBottom: 6, lineHeight: 1.5, minHeight: 14 }}>
          {loading && !status && "상태 확인 중…"}
          {status && !error && (
            <>감지: {detected ? "예" : "아니오"} · 설치됨: {installed ? "예" : "아니오"} · 활성: {enabled ? "예" : "아니오"}</>
          )}
          {error && <span style={{ color: "#FF4D4D" }}>{error}</span>}
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            className="btn btn-sm"
            style={{
              flex: 1,
              background: enabled ? "#1A1A1A" : COLOR,
              color: enabled ? "#fff" : "#1A1A1A",
              border: "2px solid #1A1A1A",
              fontSize: 10,
              opacity: enabled ? 0.55 : 1,
            }}
            disabled={enabled || busy}
            onClick={() => handleToggle(true)}
          >
            {toggling === "enable" ? <span className="spinner" /> : "ENABLE ▶"}
          </button>
          <button
            className="btn btn-sm"
            style={{
              flex: 1,
              background: !enabled && status ? "#1A1A1A" : "#fff",
              color: !enabled && status ? "#fff" : "#1A1A1A",
              border: "2px solid #1A1A1A",
              fontSize: 10,
              opacity: !enabled && status ? 0.55 : 1,
            }}
            disabled={(!enabled && status !== null) || busy}
            onClick={() => handleToggle(false)}
          >
            {toggling === "disable" ? <span className="spinner" /> : "DISABLE ■"}
          </button>
          <button
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 11, border: "2px solid #1A1A1A", flexShrink: 0, padding: "0 8px" }}
            disabled={busy}
            onClick={() => void refresh()}
            title="상태 새로고침"
          >
            ↻
          </button>
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: CLAUDE_HOOK_CARD_END ===
