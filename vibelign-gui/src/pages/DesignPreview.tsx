import { useEffect, useState } from "react";
import { DESIGN_STYLES, type StyleSpec, type MotionSpec } from "../lib/design-preview/styles";
import { generateDesignMockup, saveDesignMockup, synthesizeStyle, listCustomStyles, saveCustomStyle, deleteCustomStyle } from "../lib/vib/design";
import { EXAMPLE_CHIPS, mergeStyleLists, tokensToCssVars, replaceRootBlock } from "../lib/design-preview/customStyles";

export interface DesignBinding {
  readonly mockupPath: string;
  readonly tokens: StyleSpec["tokens"];
  readonly motion?: MotionSpec;
}

interface Props {
  readonly projectDir: string;
  readonly planPath: string;
  /** 웹 UI로 보이는 프로젝트인지(웹 게이트). false면 경고 배너(비차단). */
  readonly isLikelyWeb: boolean;
  readonly onBack: () => void;
  readonly onConfirm: (binding: DesignBinding) => void;
}

export default function DesignPreview({ projectDir, planPath, isLikelyWeb, onBack, onConfirm }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [html, setHtml] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [describe, setDescribe] = useState("");
  const [synth, setSynth] = useState<StyleSpec | null>(null);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [custom, setCustom] = useState<StyleSpec[]>([]);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  useEffect(() => {
    listCustomStyles(projectDir).then(setCustom).catch(() => setCustom([]));
  }, [projectDir]);
  const allStyles = mergeStyleLists(DESIGN_STYLES, custom);
  const customIds = new Set(custom.map((s) => s.id));
  const selected = selectedId ? allStyles.find((s) => s.id === selectedId) : undefined;

  async function createFromDescription(baseStyle?: StyleSpec) {
    const desc = describe.trim();
    if (!desc && !baseStyle) return;
    setLoading(true);
    setError(null);
    setSavedMsg(null);
    setLoadingMsg("① 클로드가 스타일을 구상하는 중…");
    try {
      const spec = await synthesizeStyle({ projectDir, planPath, description: desc, baseStyle });
      setSynth(spec);
      setLoadingMsg("② 화면 목업을 그리는 중… (최대 1~2분 걸려요)");
      const res = await generateDesignMockup({ projectDir, planPath, style: spec });
      setHtml(res.html);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  async function generate(useFeedback: boolean) {
    const style = synth ?? selected;
    if (!style) return;
    setLoading(true);
    setError(null);
    setLoadingMsg("디자인을 그리는 중… (최대 1~2분 걸려요)");
    try {
      const res = await generateDesignMockup({
        projectDir, planPath, style,
        feedback: useFeedback ? feedback.trim() : undefined,
        previousHtml: useFeedback ? (html ?? undefined) : undefined,
      });
      setHtml(res.html);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  // 합성 스타일의 색 토큰을 즉시 바꾼다 — LLM 재호출 없이 목업 HTML 의 :root 변수만 갈아끼움.
  function recolor(key: "bg" | "surface" | "primary" | "accent" | "text", value: string) {
    if (!synth) return;
    const tokens = { ...synth.tokens, [key]: value };
    const updated = { ...synth, tokens };
    setSynth(updated);
    if (html) setHtml(replaceRootBlock(html, tokensToCssVars(tokens, updated.motion)));
  }

  async function confirm() {
    const style = synth ?? selected;
    if (!style || !html) return;
    try {
      const mockupPath = await saveDesignMockup({ projectDir, styleId: style.id, html });
      onConfirm({ mockupPath, tokens: style.tokens, motion: style.motion });
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="page-content" style={{ height: "100%" }}>
      <button onClick={onBack}>← 뒤로</button>
      <h2>디자인 미리보기</h2>
      {!isLikelyWeb && (
        <p role="alert" style={{ background: "#FFF7E6", border: "1px solid #FFD591", padding: 8 }}>
          웹 UI 프로젝트가 아닐 수 있어요 — 디자인 미리보기는 웹 화면 기준입니다. 계속할 수 있어요.
        </p>
      )}
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {allStyles.map((s) => (
          <button key={s.id} onClick={() => { setSelectedId(s.id); setSynth(null); }} aria-pressed={selectedId === s.id}
            style={{ border: selectedId === s.id ? "2px solid #111" : "1px solid #ccc", padding: 12 }}>
            <strong>{s.name}</strong>
            <div>{s.description}</div>
            {customIds.has(s.id) && (
              <span
                role="button"
                aria-label={`${s.name} 삭제`}
                onClick={(e) => {
                  e.stopPropagation();
                  void deleteCustomStyle({ projectDir, styleId: s.id }).then(() =>
                    listCustomStyles(projectDir).then(setCustom),
                  );
                }}
                style={{ fontSize: 11, color: "#b42318", fontWeight: 800, cursor: "pointer" }}
              >
                ✕ 삭제
              </span>
            )}
          </button>
        ))}
      </div>
      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "2px solid #1A1A1A", display: "grid", gap: 8 }}>
        <div style={{ fontSize: 13, fontWeight: 900 }}>✏️ 직접 만들기 — 원하는 느낌을 그냥 말로 적어보세요</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {EXAMPLE_CHIPS.map((chip) => (
            <button key={chip} type="button" onClick={() => setDescribe(chip)}
              style={{ fontSize: 12, padding: "4px 10px", border: "2px solid #1A1A1A", background: "#fff", borderRadius: 999 }}>
              {chip}
            </button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <input aria-label="디자인 묘사" value={describe} onChange={(e) => setDescribe(e.target.value)}
            placeholder="예: 귀엽고 파스텔톤으로"
            style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
          <button className="btn" disabled={!describe.trim() || loading} onClick={() => void createFromDescription()}
            style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}>
            {loading ? "클로드가 그리는 중…" : "✦ 클로드에게 그려달라기"}
          </button>
        </div>
      </div>
      <button disabled={(!selected && !synth) || loading} onClick={() => void generate(false)}>
        {loading ? "그리는 중…" : "이 스타일로 그려보기"}
      </button>
      {selected && !synth && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          <input aria-label="스타일 변형" value={describe} onChange={(e) => setDescribe(e.target.value)}
            placeholder={`예: "${selected.name}" 에서 더 밝게 / 더 미니멀하게`}
            style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
          <button className="btn" disabled={!describe.trim() || loading} onClick={() => void createFromDescription(selected)}>
            ✦ 이 스타일 변형하기
          </button>
        </div>
      )}
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {loading && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10, padding: "12px 14px", border: "2px solid #1A1A1A", background: "#F5F1E3" }}>
          <span className="spinner" />
          <div>
            <div style={{ fontSize: 13, fontWeight: 900 }}>{loadingMsg || "클로드가 작업 중…"}</div>
            <div style={{ fontSize: 12, color: "#666" }}>⏳ 멈춘 게 아니에요 — 클로드가 디자인을 만들고 있어요.</div>
          </div>
        </div>
      )}
      {html && (
        <>
          {synth && (
            <div style={{ border: "2px solid #1A1A1A", padding: "10px 12px", marginBottom: 8, background: "#F5F1E3", display: "grid", gap: 6 }}>
              <div style={{ fontSize: 13, fontWeight: 900 }}>✦ 이런 스타일을 만들었어요 — {synth.name}</div>
              <div style={{ fontSize: 12, color: "#444" }}>{synth.description}</div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                {([
                  { key: "bg", label: "배경" },
                  { key: "surface", label: "표면" },
                  { key: "primary", label: "주요" },
                  { key: "accent", label: "강조" },
                  { key: "text", label: "글자" },
                ] as const).map(({ key, label }) => {
                  const c = synth.tokens[key];
                  const hex = /^#[0-9a-fA-F]{6}$/.test(c) ? c : "#ffffff";
                  return (
                    <label key={key} title={`${label} — 클릭해 색 바꾸기 (${c})`}
                      style={{ position: "relative", width: 28, height: 28, display: "inline-block", cursor: "pointer" }}>
                      <span style={{ display: "block", width: 28, height: 28, background: c, border: "1px solid #1A1A1A", borderRadius: 4 }} />
                      <input type="color" aria-label={`${label} 색 바꾸기`} value={hex}
                        onChange={(e) => recolor(key, e.target.value)}
                        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0, border: 0, padding: 0, cursor: "pointer" }} />
                    </label>
                  );
                })}
                <span style={{ fontSize: 11, color: "#888" }}>✎ 색을 클릭해 바꿔보세요</span>
              </div>
              {synth.motion && <div style={{ fontSize: 11, color: "#666" }}>모션: {synth.motion.recipe}</div>}
            </div>
          )}
          <iframe title="디자인 목업" srcDoc={html} sandbox="" style={{ width: "100%", height: 600, border: "1px solid #ddd" }} />
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 12, paddingTop: 12, borderTop: "2px solid #1A1A1A" }}>
            <input aria-label="수정 요청" value={feedback} onChange={(e) => setFeedback(e.target.value)}
              placeholder="예: 여긴 빨강, 버튼 크게"
              style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
            <button className="btn" disabled={loading || !feedback.trim()} onClick={() => void generate(true)}
              style={{ fontWeight: 800 }}>
              ↻ 다시 그리기
            </button>
            <button className="btn" onClick={() => void confirm()}
              style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}>
              ✓ 이 디자인으로 만들기
            </button>
            {synth && (
              <button className="btn" disabled={loading} onClick={() => {
                void saveCustomStyle({ projectDir, style: synth })
                  .then(() => listCustomStyles(projectDir).then(setCustom))
                  .then(() => setSavedMsg("스타일을 저장했어요 — 목록에서 다시 쓸 수 있어요"))
                  .catch((e) => setError(String(e)));
              }}>
                ＋ 이 스타일 저장하기
              </button>
            )}
            {savedMsg && <span style={{ fontSize: 12, fontWeight: 800, color: "#166534", alignSelf: "center" }}>{savedMsg}</span>}
          </div>
        </>
      )}
    </div>
  );
}
