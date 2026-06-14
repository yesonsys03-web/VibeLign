import { useState } from "react";
import { DESIGN_STYLES, getStyle, type StyleSpec, type MotionSpec } from "../lib/design-preview/styles";
import { generateDesignMockup, saveDesignMockup } from "../lib/vib/design";

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
  const selected = selectedId ? getStyle(selectedId) : undefined;

  async function generate(useFeedback: boolean) {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const res = await generateDesignMockup({
        projectDir, planPath, style: selected,
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
    if (!selected || !html) return;
    try {
      const mockupPath = await saveDesignMockup({ projectDir, styleId: selected.id, html });
      onConfirm({ mockupPath, tokens: selected.tokens, motion: selected.motion });
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
        {DESIGN_STYLES.map((s) => (
          <button key={s.id} onClick={() => setSelectedId(s.id)} aria-pressed={selectedId === s.id}
            style={{ border: selectedId === s.id ? "2px solid #111" : "1px solid #ccc", padding: 12 }}>
            <strong>{s.name}</strong>
            <div>{s.description}</div>
          </button>
        ))}
      </div>
      <button disabled={!selected || loading} onClick={() => void generate(false)}>
        {loading ? "그리는 중…" : "이 스타일로 그려보기"}
      </button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {html && (
        <>
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
          </div>
        </>
      )}
    </div>
  );
}
