import { useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { openUrl } from "@tauri-apps/plugin-opener";
import {
  installTool,
  toolInstallStatus,
  getInstaller,
  shouldGuideManual,
  type ToolInstallResult,
} from "../../lib/tools/installerRegistry";

interface Props {
  readonly id: string;
  readonly onDone?: () => void;
}

export function ToolInstallPanel({ id, onDone }: Props) {
  const meta = getInstaller(id);
  const [phase, setPhase] = useState<"idle" | "installing" | "done" | "manual">("idle");
  const [lines, setLines] = useState<string[]>([]);
  const [result, setResult] = useState<ToolInstallResult | null>(null);
  const [installed, setInstalled] = useState(false);
  const outRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    toolInstallStatus(id).then(setInstalled).catch(() => setInstalled(false));
  }, [id]);

  useEffect(() => {
    const un = listen<{ id: string; stream: string; line: string }>(
      "tool-install-output",
      (e) => {
        if (e.payload.id === id) setLines((p) => [...p, e.payload.line]);
      },
    );
    return () => {
      void un.then((f) => f());
    };
  }, [id]);

  useEffect(() => {
    outRef.current?.scrollTo(0, outRef.current.scrollHeight);
  }, [lines]);

  if (!meta) return null;

  async function start() {
    setPhase("installing");
    setLines([]);
    try {
      const r = await installTool(id);
      setResult(r);
      if (shouldGuideManual(r)) {
        setPhase("manual");
      } else {
        setInstalled(true);
        setPhase("done");
        onDone?.();
      }
    } catch {
      setPhase("manual");
    }
  }

  return (
    <div
      style={{
        border: "2px solid #1A1A1A",
        padding: 12,
        display: "grid",
        gap: 8,
        background: "#F5F1E3",
      }}
    >
      <div style={{ fontWeight: 900, fontSize: 14 }}>
        {meta.displayName} {installed ? "✓ 설치됨" : ""}
        {meta.recommendedForBeginner && !installed ? " — 무료·키 불필요 (추천)" : ""}
      </div>

      {phase === "idle" && !installed && (
        <button
          className="btn"
          onClick={() => void start()}
          style={{
            background: "#1A1A1A",
            color: "#fff",
            border: "2px solid #1A1A1A",
            fontWeight: 900,
            justifySelf: "start",
          }}
        >
          ⬇ 자동 설치
        </button>
      )}

      {phase === "installing" && (
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="spinner" />
          <span style={{ fontWeight: 800, fontSize: 13 }}>설치 중… (수십 초~몇 분)</span>
        </div>
      )}

      {(phase === "installing" || lines.length > 0) && (
        <div
          ref={outRef}
          style={{
            maxHeight: 160,
            overflowY: "auto",
            background: "#fff",
            border: "1px solid #D6D2C4",
            padding: 8,
            fontFamily: "IBM Plex Mono, monospace",
            fontSize: 11,
            whiteSpace: "pre-wrap",
          }}
        >
          {lines.map((l, i) => (
            <div key={i}>{l}</div>
          ))}
        </div>
      )}

      {phase === "done" && result && (
        <div style={{ fontSize: 12, color: "#166534", fontWeight: 700 }}>
          ✓ 설치 완료!
          {result.auth === "login"
            ? ` ${result.authHint}`
            : ` ${result.authHint ?? ""}`}
        </div>
      )}

      {phase === "manual" && (
        <div style={{ fontSize: 12, color: "#92400E", display: "grid", gap: 6 }}>
          <div style={{ fontWeight: 800 }}>자동 설치가 안 됐어요 — 직접 설치해 주세요.</div>
          {result?.manualUrl && (
            <button
              className="btn btn-sm"
              onClick={() => {
                if (result.manualUrl) void openUrl(result.manualUrl).catch(() => {});
              }}
              style={{ justifySelf: "start" }}
            >
              설치 페이지 열기 →
            </button>
          )}
          <button
            className="btn btn-sm"
            onClick={() =>
              void toolInstallStatus(id).then((ok) => {
                setInstalled(ok);
                if (ok) setPhase("done");
              })
            }
            style={{ justifySelf: "start" }}
          >
            설치 후 다시 확인
          </button>
        </div>
      )}
    </div>
  );
}
