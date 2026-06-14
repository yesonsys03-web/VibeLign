import { useEffect, useState } from "react";
import { DESIGN_STYLES, type StyleSpec, type MotionSpec } from "../lib/design-preview/styles";
import { generateDesignMockup, saveDesignMockup, synthesizeStyle, listCustomStyles, saveCustomStyle, deleteCustomStyle } from "../lib/vib/design";
import { EXAMPLE_CHIPS, mergeStyleLists } from "../lib/design-preview/customStyles";

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
    try {
      const spec = await synthesizeStyle({ projectDir, planPath, description: desc, baseStyle });
      setSynth(spec);
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
      {html && (
        <>
          {synth && (
            <div style={{ border: "2px solid #1A1A1A", padding: "10px 12px", marginBottom: 8, background: "#F5F1E3", display: "grid", gap: 6 }}>
              <div style={{ fontSize: 13, fontWeight: 900 }}>✦ 이런 스타일을 만들었어요 — {synth.name}</div>
              <div style={{ fontSize: 12, color: "#444" }}>{synth.description}</div>
              <div style={{ display: "flex", gap: 6 }}>
                {[synth.tokens.bg, synth.tokens.surface, synth.tokens.primary, synth.tokens.accent, synth.tokens.text].map((c, i) => (
                  <span key={i} title={c} style={{ width: 28, height: 28, background: c, border: "1px solid #1A1A1A", borderRadius: 4 }} />
                ))}
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
