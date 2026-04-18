// === ANCHOR: ANCHOR_CARD_START ===
import { useEffect, useMemo, useRef, useState } from "react";
import {
  AnchorAutoIntentResult,
  AnchorMetaEntry,
  anchorAutoIntentJson,
  anchorListMeta,
  anchorSetIntent,
  buildGuiAiEnv,
  getAiEnhancement,
  runVib,
} from "../../../lib/vib";
import { CardState } from "../../../lib/commands";
import GuiCliOutputBlock from "../../GuiCliOutputBlock";

interface AnchorCardProps {
  projectDir: string;
  apiKey?: string | null;
  providerKeys?: Record<string, string>;
  hasAnyAiKey?: boolean;
  aiKeyStatusLoaded?: boolean;
  onOpenSettings?: (reason?: string) => void;
}

type RunMode = "run" | "autoIntent" | "loadMeta" | "save";

const COLOR = "#4D9FFF";

export default function AnchorCard({
  projectDir,
  apiKey,
  providerKeys,
  hasAnyAiKey = false,
  aiKeyStatusLoaded = false,
  onOpenSettings,
}: AnchorCardProps) {
  const [st, setSt] = useState<CardState>("idle");
  const [runMode, setRunMode] = useState<RunMode | null>(null);
  const [out, setOut] = useState("");
  const [hasWarning, setHasWarning] = useState(false);
  const [showResultModal, setShowResultModal] = useState(false);

  const [force, setForce] = useState(false);
  const [useWithAi, setUseWithAi] = useState(false);
  const [aiProgress, setAiProgress] = useState<{ done: number; total: number; cached: number; toCall: number } | null>(null);
  const [lastAuto, setLastAuto] = useState<AnchorAutoIntentResult | null>(null);

  useEffect(() => {
    if (!projectDir) return;
    getAiEnhancement(projectDir).then(setUseWithAi).catch(() => {});
  }, [projectDir]);

  const [showEditor, setShowEditor] = useState(false);
  const [meta, setMeta] = useState<Record<string, AnchorMetaEntry>>({});
  const [selected, setSelected] = useState<string>("");
  const [filter, setFilter] = useState("");
  const [form, setForm] = useState<{
    intent: string;
    description: string;
    aliases: string;
    warning: string;
    connects: string;
  }>({ intent: "", description: "", aliases: "", warning: "", connects: "" });
  const [saveMsg, setSaveMsg] = useState("");

  const idleTimer = useRef<number | undefined>(undefined);

  function setOutputWarn(text: string, warn: boolean, error = false) {
    setOut(text);
    setHasWarning(warn);
    setSt(error ? "error" : warn ? "done" : "done");
    if (error || warn) setShowResultModal(true);
    if (!error && !warn) {
      if (idleTimer.current !== undefined) window.clearTimeout(idleTimer.current);
      idleTimer.current = window.setTimeout(() => {
        setSt("idle");
        idleTimer.current = undefined;
      }, 3000);
    }
  }

  async function handleBaseAnchor() {
    setRunMode("run");
    setSt("loading");
    setOut("");
    setHasWarning(false);
    try {
      const r = await runVib(["anchor"], projectDir);
      const stdout = r.stdout.trim();
      const stderr = r.stderr.trim();
      const combined = [stderr, stdout].filter(Boolean).join("\n\n");
      const text = combined || (r.ok ? "완료" : `exit ${r.exit_code}`);
      setOutputWarn(text, Boolean(stderr) && r.ok, !r.ok);
    } catch (e) {
      setOutputWarn(String(e), false, true);
    } finally {
      setRunMode(null);
    }
  }

  async function handleAutoIntent() {
    if (useWithAi && aiKeyStatusLoaded && !hasAnyAiKey) {
      setOutputWarn("API 키를 먼저 설정해주세요", false, true);
      if (onOpenSettings) onOpenSettings("AI intent 보강을 쓰려면 먼저 설정에서 API 키를 입력해주세요.");
      return;
    }
    setRunMode("autoIntent");
    setSt("loading");
    setOut("");
    setHasWarning(false);
    setAiProgress(null);
    try {
      const aiEnv = buildGuiAiEnv(providerKeys, apiKey);
      const { data, stderrLog } = await anchorAutoIntentJson(projectDir, {
        force,
        aiEnv,
        withAi: useWithAi,
        onProgress: useWithAi
          ? (ev) => {
              if (ev.step === "ai-cache") {
                setAiProgress({
                  done: 0,
                  total: ev.batches ?? 0,
                  cached: ev.cached ?? 0,
                  toCall: ev.to_call ?? 0,
                });
              } else if (ev.step === "ai-batch") {
                setAiProgress((prev) => ({
                  done: ev.done ?? 0,
                  total: ev.total ?? prev?.total ?? 0,
                  cached: prev?.cached ?? 0,
                  toCall: prev?.toCall ?? 0,
                }));
              }
            }
          : undefined,
      });
      setLastAuto(data);
      const header =
        data.total_anchors === 0
          ? "앵커가 있는 파일이 없습니다"
          : `✅ code_count=${data.code_count}  ai_count=${data.ai_count}  total=${data.total_anchors}`;
      const tail = !useWithAi
        ? "(AI 재생성 OFF → 코드 기반만)"
        : data.ai_available
        ? data.forced
          ? "(force 재생성)"
          : ""
        : "(AI 키 없음 → 코드 기반만 적용)";
      const log = stderrLog ? `${stderrLog}\n\n${header} ${tail}`.trim() : `${header} ${tail}`.trim();
      const warn = useWithAi && data.total_anchors > 0 && !data.ai_available && data.ai_count === 0;
      setOutputWarn(log, warn, false);
    } catch (e) {
      setOutputWarn(String(e), false, true);
    } finally {
      setRunMode(null);
      setAiProgress(null);
    }
  }

  async function openEditor() {
    setShowEditor(true);
    setRunMode("loadMeta");
    setSaveMsg("");
    try {
      const data = await anchorListMeta(projectDir);
      setMeta(data);
      const firstKey = selected && data[selected] ? selected : Object.keys(data)[0] ?? "";
      setSelected(firstKey);
      prefill(firstKey, data);
    } catch (e) {
      setSaveMsg(`메타 로드 실패: ${e}`);
    } finally {
      setRunMode(null);
    }
  }

  function prefill(name: string, source: Record<string, AnchorMetaEntry> = meta) {
    const entry = source[name] ?? {};
    setForm({
      intent: entry.intent ?? "",
      description: entry.description ?? "",
      aliases: (entry.aliases ?? []).join(", "),
      warning: entry.warning ?? "",
      connects: (entry.connects ?? []).join(", "),
    });
  }

  async function handleSave() {
    if (!selected) {
      setSaveMsg("앵커를 먼저 선택해주세요");
      return;
    }
    if (!form.intent.trim()) {
      setSaveMsg("intent를 입력해주세요");
      return;
    }
    setRunMode("save");
    setSaveMsg("");
    try {
      const res = await anchorSetIntent(projectDir, selected, form.intent.trim(), {
        aliases: form.aliases.split(",").map((s) => s.trim()).filter(Boolean),
        description: form.description.trim() || undefined,
        warning: form.warning.trim() || undefined,
        connects: form.connects.split(",").map((s) => s.trim()).filter(Boolean),
      });
      setMeta((m) => ({ ...m, [selected]: res.entry }));
      setSaveMsg(`✅ 저장 완료 (_source=${res.entry._source ?? "?"})`);
    } catch (e) {
      setSaveMsg(`저장 실패: ${e}`);
    } finally {
      setRunMode(null);
    }
  }

  const anchorNames = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    const keys = Object.keys(meta).sort();
    if (!needle) return keys;
    return keys.filter((k) => {
      if (k.toLowerCase().includes(needle)) return true;
      const e = meta[k] ?? {};
      const hay = [e.intent, e.description, ...(e.aliases ?? [])]
        .filter((v): v is string => Boolean(v))
        .join(" ")
        .toLowerCase();
      return hay.includes(needle);
    });
  }, [meta, filter]);

  const selectedEntry = selected ? meta[selected] ?? {} : {};
  const selectedSource = selectedEntry._source ?? "—";

  return (
    <>
      {showResultModal && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setShowResultModal(false)}
        >
          <div
            style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 560, maxHeight: "72vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ background: "#1A1A1A", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 12, color: "#fff", letterSpacing: 2 }}>ANCHOR 결과</span>
              <button onClick={() => setShowResultModal(false)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 16 }}>✕</button>
            </div>
            <pre style={{ margin: 0, padding: 16, overflowY: "auto", fontFamily: "IBM Plex Mono, monospace", fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap", wordBreak: "break-word", color: st === "error" ? "#FF4D4D" : "#1A1A1A" }}>
              {out}
            </pre>
          </div>
        </div>
      )}

      {showEditor && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}
          onClick={() => setShowEditor(false)}
        >
          <div
            style={{ background: "#FEFBF0", border: "3px solid #1A1A1A", boxShadow: "8px 8px 0 #1A1A1A", width: "100%", maxWidth: 720, maxHeight: "82vh", display: "flex", flexDirection: "column" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ background: "#1A1A1A", padding: "10px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontFamily: "IBM Plex Mono, monospace", fontWeight: 700, fontSize: 12, color: "#fff", letterSpacing: 2 }}>앵커 intent 수동 편집</span>
              <button onClick={() => setShowEditor(false)} style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", fontSize: 16 }}>✕</button>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 0, flex: 1, minHeight: 0 }}>
              <div style={{ borderRight: "2px solid #1A1A1A", display: "flex", flexDirection: "column", minHeight: 0 }}>
                <input
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  placeholder="검색..."
                  style={{ margin: 8, fontSize: 11, padding: "4px 6px", border: "2px solid #1A1A1A", fontFamily: "IBM Plex Mono, monospace" }}
                />
                <div style={{ overflowY: "auto", flex: 1, padding: "0 4px 8px" }}>
                  {runMode === "loadMeta" && <div style={{ padding: 8, fontSize: 11, color: "#666" }}>로딩 중…</div>}
                  {runMode !== "loadMeta" && anchorNames.length === 0 && (
                    <div style={{ padding: 8, fontSize: 11, color: "#666" }}>
                      {Object.keys(meta).length === 0 ? "anchor_meta.json이 비어 있습니다" : "일치하는 앵커가 없습니다"}
                    </div>
                  )}
                  {anchorNames.map((name) => {
                    const e = meta[name] ?? {};
                    const src = e._source ?? "";
                    const isSel = name === selected;
                    return (
                      <button
                        key={name}
                        onClick={() => { setSelected(name); prefill(name); setSaveMsg(""); }}
                        style={{
                          display: "block", width: "100%", textAlign: "left",
                          padding: "4px 6px", marginBottom: 2,
                          background: isSel ? "#1A1A1A" : "#fff",
                          color: isSel ? "#fff" : "#1A1A1A",
                          border: "1px solid #1A1A1A",
                          cursor: "pointer",
                          fontFamily: "IBM Plex Mono, monospace",
                          fontSize: 10,
                        }}
                      >
                        <div style={{ fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</div>
                        <div style={{ fontSize: 9, opacity: 0.7 }}>
                          {src && <span style={{ marginRight: 6 }}>_source={src}</span>}
                          {e.intent ? e.intent.slice(0, 40) : "(intent 없음)"}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
              <div style={{ padding: 12, overflowY: "auto", minHeight: 0 }}>
                {!selected && <div style={{ fontSize: 12, color: "#666" }}>좌측에서 앵커를 선택하세요</div>}
                {selected && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <div style={{ fontSize: 11, fontWeight: 700 }}>
                      {selected} <span style={{ fontWeight: 500, color: "#666" }}>(_source={selectedSource})</span>
                    </div>
                    <EditorField label="intent *" value={form.intent} onChange={(v) => setForm((f) => ({ ...f, intent: v }))} />
                    <EditorField label="description" value={form.description} onChange={(v) => setForm((f) => ({ ...f, description: v }))} multiline />
                    <EditorField label="aliases (쉼표 구분)" value={form.aliases} onChange={(v) => setForm((f) => ({ ...f, aliases: v }))} />
                    <EditorField label="warning" value={form.warning} onChange={(v) => setForm((f) => ({ ...f, warning: v }))} />
                    <EditorField label="connects (쉼표 구분)" value={form.connects} onChange={(v) => setForm((f) => ({ ...f, connects: v }))} />
                    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                      <button
                        disabled={runMode === "save"}
                        onClick={handleSave}
                        className="btn btn-sm"
                        style={{ background: COLOR, color: "#fff", border: "2px solid #1A1A1A", fontSize: 11, padding: "4px 10px" }}
                      >
                        {runMode === "save" ? <span className="spinner" /> : "저장"}
                      </button>
                      <button
                        onClick={() => prefill(selected)}
                        className="btn btn-ghost btn-sm"
                        style={{ border: "2px solid #1A1A1A", fontSize: 11, padding: "4px 10px" }}
                      >
                        되돌리기
                      </button>
                      {saveMsg && (
                        <span style={{ fontSize: 10, color: saveMsg.startsWith("✅") ? "#1A1A1A" : "#A05A00" }}>{saveMsg}</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="feature-card" style={{ cursor: "default" }}>
        <div className="feature-card-header" style={{ background: COLOR + "18", padding: "8px 12px" }}>
          <div className="feature-card-icon" style={{
            background: COLOR, color: "#fff", borderColor: COLOR,
            width: 22, height: 22, fontSize: 11, fontWeight: 900,
          }}>⚓</div>
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
            <span style={{ fontWeight: 700, fontSize: 16.5, flexShrink: 0 }}>앵커</span>
            <span style={{ fontSize: 9, fontWeight: 500, color: "#666", lineHeight: 1.25 }}>AI가 건드려도 되는 구역 표시</span>
          </div>
          {st === "done" && !hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>완료</span>}
          {hasWarning && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FFD166", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>주의</span>}
          {st === "error" && <span style={{ fontSize: 8, fontWeight: 700, padding: "1px 5px", background: "#FF4D4D", color: "#fff", border: "1px solid #1A1A1A" }}>오류</span>}
        </div>
        <div className="feature-card-body" style={{ padding: "6px 12px 8px" }}>
          <GuiCliOutputBlock
            text={out}
            placeholder="코드가 바뀐 뒤 앵커의 intent/aliases를 재생성합니다."
            variant={st === "error" ? "error" : hasWarning ? "warn" : "default"}
          />
          <div style={{ display: "flex", gap: 4, marginBottom: 4 }}>
            <button
              className="btn btn-sm"
              style={{ flex: 1, background: COLOR, color: "#fff", border: "2px solid #1A1A1A", fontSize: 10 }}
              disabled={st === "loading"}
              onClick={handleBaseAnchor}
            >
              {runMode === "run" ? <span className="spinner" /> : "ANCHOR ▶"}
            </button>
            {out && (
              <button
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 9, border: "2px solid #1A1A1A", flexShrink: 0 }}
                onClick={() => setShowResultModal(true)}
              >결과</button>
            )}
          </div>
          <div style={{ display: "flex", gap: 4, marginBottom: 4, alignItems: "center" }}>
            <button
              onClick={() => setForce((v) => !v)}
              style={{
                fontSize: 9, fontWeight: 700, padding: "2px 6px",
                border: "2px solid #1A1A1A",
                background: force ? "#1A1A1A" : "#fff",
                color: force ? "#fff" : "#1A1A1A", cursor: "pointer",
              }}
            >--force</button>
            <button
              onClick={() => setUseWithAi((v) => !v)}
              title="OFF: 코드 기반으로만 재생성. ON: AI로 재생성 (API 호출)."
              style={{
                fontSize: 9, fontWeight: 700, padding: "2px 6px",
                border: "2px solid #1A1A1A",
                background: useWithAi ? "#1E2216" : "#fff",
                color: useWithAi ? "#4DFF91" : "#1A1A1A", cursor: "pointer",
              }}
            >AI 재생성 {useWithAi ? "ON" : "OFF"}</button>
            <button
              className="btn btn-sm"
              style={{ flex: 1, background: "#fff", color: "#1A1A1A", border: "2px solid #1A1A1A", fontSize: 10 }}
              disabled={st === "loading"}
              onClick={handleAutoIntent}
              title={useWithAi ? "AI로 모든 앵커 intent/aliases 재생성 (기존 AI 결과는 --force 시 덮어씀)" : "코드 기반으로만 재생성 (AI 호출 없음)"}
            >
              {runMode === "autoIntent" ? <span className="spinner" /> : useWithAi ? "AI intent 재생성" : "코드 기반 재생성"}
            </button>
          </div>
          {runMode === "autoIntent" && useWithAi && aiProgress && aiProgress.total > 0 && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
              <div style={{
                flex: 1, height: 5, background: "#cfd8dc", border: "1px solid #1A1A1A", overflow: "hidden",
              }}>
                <div style={{
                  width: `${Math.min(100, (aiProgress.done / aiProgress.total) * 100)}%`,
                  height: "100%", background: "#4DFF91", transition: "width 0.2s ease",
                }} />
              </div>
              <span style={{ fontSize: 9, color: "#555", minWidth: 56, textAlign: "right" }}>
                {aiProgress.done}/{aiProgress.total} 배치
              </span>
            </div>
          )}
          {lastAuto && (
            <div style={{ fontSize: 9, color: "#666", marginBottom: 4 }}>
              최근: code={lastAuto.code_count} / ai={lastAuto.ai_count} / total={lastAuto.total_anchors}
              {(lastAuto.ai_cached_hit ?? 0) ? ` · 캐시 ${lastAuto.ai_cached_hit}` : ""}
              {(lastAuto.ai_retried ?? 0) ? ` · 재시도 ${lastAuto.ai_retried}` : ""}
              {(lastAuto.ai_failed ?? 0) ? ` · 실패 ${lastAuto.ai_failed}` : ""}
              {lastAuto.ai_available ? "" : " · AI 키 없음"}
            </div>
          )}
          <button
            className="btn btn-sm"
            style={{ width: "100%", background: "#fff", color: "#1A1A1A", border: "2px solid #1A1A1A", fontSize: 10 }}
            onClick={openEditor}
          >
            수동 편집…
          </button>
        </div>
      </div>
    </>
  );
}

function EditorField({
  label, value, onChange, multiline = false,
}: { label: string; value: string; onChange: (v: string) => void; multiline?: boolean }) {
  return (
    <label style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <span style={{ fontSize: 10, fontWeight: 700 }}>{label}</span>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          style={{ fontSize: 11, padding: "4px 6px", border: "2px solid #1A1A1A", fontFamily: "IBM Plex Mono, monospace", resize: "vertical" }}
        />
      ) : (
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          style={{ fontSize: 11, padding: "4px 6px", border: "2px solid #1A1A1A", fontFamily: "IBM Plex Mono, monospace" }}
        />
      )}
    </label>
  );
}
// === ANCHOR: ANCHOR_CARD_END ===
