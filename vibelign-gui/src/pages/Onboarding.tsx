// === ANCHOR: ONBOARDING_START ===
import { useState, useEffect } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { getVibPath, vibStart, saveApiKey } from "../lib/vib";

interface OnboardingProps {
  onComplete: (projectDir: string, apiKey: string | null) => void;
  onResume?: (dir: string) => void;
  recentDirs?: string[];
}

const FEATURE_CARDS = [
  { icon: "MAP", color: "#F5621E", title: "코드맵 생성",   desc: "AI가 구조 즉시 이해" },
  { icon: "♥",   color: "#FF4D8B", title: "AI 폭주 방지", desc: "실시간 감시 모드" },
  { icon: "↺",   color: "#7B4DFF", title: "원클릭 복구",  desc: "checkpoint + undo" },
  { icon: "⇄",   color: "#4D9FFF", title: "AI 이동 자유", desc: "Claude · Cursor 즉시" },
];

const TERMINAL_LINES = [
  { type: "prompt", text: "vibelign start" },
  { type: "check",  text: "프로젝트 구조 스캔 완료" },
  { type: "check",  text: "앵커 18개 자동 삽입" },
  { type: "check",  text: "코드맵 생성 → .vibelign/" },
  { type: "check",  text: "체크포인트 자동 백업" },
  { type: "check",  text: "AI에게 코드맵만 주세요!" },
];

export default function Onboarding({ onComplete, onResume, recentDirs = [] }: OnboardingProps) {
  const [vibFound, setVibFound] = useState<string | null>(null);
  const [vibChecking, setVibChecking] = useState(true);
  const [selectedDir, setSelectedDir] = useState("");
  const [starting, setStarting] = useState(false);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [apiKeyOpen, setApiKeyOpen] = useState(false);
  const [recentOpen, setRecentOpen] = useState(true);

  useEffect(() => {
    getVibPath().then((p) => { setVibFound(p); setVibChecking(false); });
  }, []);

  async function handleStart() {
    setStarting(true);
    await vibStart(selectedDir);
    let key: string | null = null;
    if (apiKeyInput.trim()) {
      try { await saveApiKey(apiKeyInput.trim()); key = apiKeyInput.trim(); } catch { /* 무시 */ }
    }
    setStarting(false);
    onComplete(selectedDir, key);
  }

  async function pickFolder() {
    const dir = await open({ directory: true, multiple: false, title: "프로젝트 폴더 선택" });
    if (typeof dir === "string") setSelectedDir(dir);
  }

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* ─── 상단: 스크롤 가능 영역 ──────────────────────────────── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "14px 20px 10px" }}>

        {/* RECENT 카드 — 최근 프로젝트 접이식 */}
        {recentDirs.length > 0 && onResume && (
          <div className="feature-card" style={{ marginBottom: 12 }}>
            {/* 헤더 (클릭 시 접기/펼치기) */}
            <div
              className="feature-card-header"
              style={{ background: "#4D9FFF18", padding: "8px 12px", cursor: "pointer" }}
              onClick={() => setRecentOpen((o) => !o)}
            >
              <div className="feature-card-icon"
                style={{ background: "#4D9FFF", color: "#fff", borderColor: "#4D9FFF", width: 24, height: 24, fontSize: 11, fontWeight: 900 }}>
                ⊞
              </div>
              <div style={{ fontWeight: 700, fontSize: 11, flex: 1 }}>최근 프로젝트</div>
              <div style={{ fontSize: 10, color: "#4D9FFF", fontWeight: 700, marginRight: 8 }}>{recentDirs.length}개</div>
              <div style={{ fontSize: 11, color: "#666" }}>{recentOpen ? "▲" : "▼"}</div>
            </div>
            {/* 목록 */}
            {recentOpen && (
              <div className="feature-card-body" style={{ padding: 0 }}>
                {recentDirs.map((dir, i) => (
                  <div
                    key={dir}
                    onClick={() => onResume(dir)}
                    style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "7px 12px", cursor: "pointer",
                      borderTop: i > 0 ? "1px solid #1A1A1A" : undefined,
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "#4D9FFF11")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "")}
                  >
                    <span style={{ fontWeight: 900, fontSize: 12, color: "#4D9FFF", flexShrink: 0, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>
                      {dir.split("/").filter(Boolean).at(-1)}
                    </span>
                    {i === 0 && (
                      <span style={{ fontSize: 9, fontWeight: 700, color: "#4D9FFF", background: "#4D9FFF22", padding: "1px 6px", flexShrink: 0, border: "1px solid #4D9FFF55" }}>
                        진행 중
                      </span>
                    )}
                    <span style={{ fontSize: 10, color: "#555", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {dir}
                    </span>
                    <span style={{ fontSize: 11, color: "#4D9FFF", fontWeight: 700, flexShrink: 0 }}>▶</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 배지 + 헤더 */}
        <div style={{ marginBottom: 12 }}>
          <div className="badge" style={{ marginBottom: 10, fontSize: 10 }}>
            ▶ PIP INSTALL VIBELIGN
          </div>

          <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            {/* 타이틀 */}
            <div style={{ flex: 1 }}>
              <div className="heading-xl" style={{ marginBottom: 6, fontSize: 22 }}>
                <span style={{ background: "#F5621E", color: "#fff", padding: "0 5px", lineHeight: 1.3 }}>
                  커맨드 하나로
                </span>
                <br />
                바이브코딩 안전망
              </div>
              <div style={{ fontSize: 12, color: "#555", fontWeight: 600 }}>
                코드 몰라도 AI가 폭주 안 합니다
              </div>
            </div>

            {/* 터미널 */}
            <div className="terminal" style={{ width: 240, flexShrink: 0, padding: "10px 14px" }}>
              <div className="terminal-header" style={{ marginBottom: 8 }}>
                <div className="terminal-dot red" />
                <div className="terminal-dot yellow" />
                <div className="terminal-dot green" />
              </div>
              {TERMINAL_LINES.map((line, i) => (
                <div key={i} style={{ lineHeight: 1.6 }}>
                  {line.type === "prompt"
                    ? <span><span className="terminal-prompt">$ </span>{line.text}</span>
                    : <span><span className="terminal-check">✓ </span>{line.text}</span>}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 기능 카드 그리드 */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
          {FEATURE_CARDS.map((card) => (
            <div className="feature-card" key={card.icon}>
              <div className="feature-card-header" style={{ background: card.color + "18", padding: "8px 12px" }}>
                <div className="feature-card-icon"
                  style={{ background: card.color, color: "#fff", borderColor: card.color, width: 24, height: 24, fontSize: 12 }}>
                  {card.icon}
                </div>
                <div style={{ fontWeight: 700, fontSize: 11 }}>{card.title}</div>
              </div>
              <div className="feature-card-body" style={{ padding: "6px 12px", fontSize: 11 }}>{card.desc}</div>
            </div>
          ))}
        </div>

        {/* API 키 카드 */}
        <div className="feature-card" style={{ cursor: "pointer" }}
          onClick={() => setApiKeyOpen((o) => !o)}>
          <div className="feature-card-header" style={{ background: "#FFE44D18", padding: "8px 12px" }}>
            <div className="feature-card-icon"
              style={{ background: "#FFE44D", color: "#1A1A1A", borderColor: "#FFE44D", width: 24, height: 24, fontSize: 12, fontWeight: 900 }}>
              KEY
            </div>
            <div style={{ fontWeight: 700, fontSize: 11, flex: 1 }}>Anthropic API Key</div>
            <div style={{ fontSize: 10, color: apiKeyInput.trim() ? "#4DFF91" : "#888", fontWeight: 700 }}>
              {apiKeyInput.trim() ? "설정됨 ✓" : "미설정 (선택)"}
            </div>
            <div style={{ fontSize: 11, color: "#666", marginLeft: 8 }}>{apiKeyOpen ? "▲" : "▼"}</div>
          </div>
          {apiKeyOpen && (
            <div className="feature-card-body"
              style={{ padding: "8px 12px" }}
              onClick={(e) => e.stopPropagation()}>
              <input
                type="password"
                className="input-field"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="sk-ant-api03-..."
                style={{ width: "100%", fontSize: 11, boxSizing: "border-box" }}
                autoFocus
              />
              <div style={{ fontSize: 10, color: "#666", marginTop: 4 }}>
                AI 기능(vib patch --ai 등)에 사용됩니다. 나중에 ⚙ 설정에서 변경 가능.
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ─── 하단: 항상 보이는 고정 영역 ────────────────────────── */}
      <div style={{ flexShrink: 0, borderTop: "2px solid #1A1A1A", padding: "12px 20px 14px", background: "var(--bg)" }}>
        {/* VIB 상태 + 폴더 선택 */}
        <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
          <span className="label" style={{ flexShrink: 0 }}>VIB CLI</span>
          {vibChecking ? (
            <span className="spinner" />
          ) : vibFound ? (
            <span className="badge" style={{ fontSize: 10, background: "#4DFF91", color: "#1A1A1A" }}>발견됨</span>
          ) : (
            <span className="badge" style={{ fontSize: 10, background: "#FF4D4D" }}>미설치 — pip install vibelign</span>
          )}
          <div style={{ flex: 1 }} />
          <input
            className="input-field"
            value={selectedDir}
            onChange={(e) => setSelectedDir(e.target.value)}
            placeholder="프로젝트 폴더 경로..."
            style={{ flex: 2, maxWidth: 320 }}
          />
          <button className="btn btn-ghost btn-sm" onClick={pickFolder} style={{ flexShrink: 0 }}>탐색</button>
        </div>

        <button
          className="btn btn-black"
          style={{ width: "100%", padding: "10px", fontSize: 13 }}
          disabled={!vibFound || !selectedDir || starting}
          onClick={handleStart}
        >
          {starting ? <><span className="spinner" style={{ marginRight: 8 }} />초기화 중...</> : "시작하기 ▶"}
        </button>
      </div>
    </div>
  );
}
// === ANCHOR: ONBOARDING_END ===
