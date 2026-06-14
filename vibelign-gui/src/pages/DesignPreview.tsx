import { useEffect, useState } from "react";
import { DESIGN_STYLES, type StyleSpec, type MotionSpec } from "../lib/design-preview/styles";
import { saveDesignMockup, listCustomStyles, saveCustomStyle, deleteCustomStyle } from "../lib/vib/design";
import { EXAMPLE_CHIPS, mergeStyleLists } from "../lib/design-preview/customStyles";
import type { DesignJob } from "../lib/design-preview/useDesignJob";

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
  /** App 레벨 생성 잡(탭 이동에도 살아남음). */
  readonly job: DesignJob;
  readonly onBack: () => void;
  readonly onConfirm: (binding: DesignBinding) => void;
}

export default function DesignPreview({ projectDir, planPath, isLikelyWeb, job, onBack, onConfirm }: Props) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [describe, setDescribe] = useState("");
  const [custom, setCustom] = useState<StyleSpec[]>([]);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);
  useEffect(() => {
    listCustomStyles(projectDir).then(setCustom).catch(() => setCustom([]));
  }, [projectDir]);
  const allStyles = mergeStyleLists(DESIGN_STYLES, custom);
  const customIds = new Set(custom.map((s) => s.id));
  const selected = selectedId ? allStyles.find((s) => s.id === selectedId) : undefined;
  const running = job.status === "running";

  function createFromDescription(baseStyle?: StyleSpec) {
    const desc = describe.trim();
    if (!desc && !baseStyle) return;
    setSavedMsg(null);
    setConfirmError(null);
    job.run({ kind: "describe", description: desc, baseStyle }, planPath);
  }

  function generate(useFeedback: boolean) {
    const style = job.synth ?? selected;
    if (!style) return;
    setConfirmError(null);
    job.run(
      {
        kind: "style",
        style,
        feedback: useFeedback ? feedback.trim() : undefined,
        previousHtml: useFeedback ? (job.html ?? undefined) : undefined,
      },
      planPath,
    );
  }

  async function confirm() {
    const style = job.synth ?? selected;
    if (!style || !job.html) return;
    try {
      const mockupPath = await saveDesignMockup({ projectDir, styleId: style.id, html: job.html });
      onConfirm({ mockupPath, tokens: style.tokens, motion: style.motion });
      job.reset(); // 디자인 확정 후 잡 소비 — 잔여 "완성" 칩 방지
    } catch (e) {
      setConfirmError(String(e));
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
          <button key={s.id} onClick={() => { setSelectedId(s.id); }} aria-pressed={selectedId === s.id}
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
          <button className="btn" disabled={!describe.trim() || running} onClick={() => createFromDescription()}
            style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}>
            {running ? "클로드가 그리는 중…" : "✦ 클로드에게 그려달라기"}
          </button>
        </div>
      </div>
      <button disabled={(!selected && !job.synth) || running} onClick={() => generate(false)}>
        {running ? "그리는 중…" : "이 스타일로 그려보기"}
      </button>
      {selected && !job.synth && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
          <input aria-label="스타일 변형" value={describe} onChange={(e) => setDescribe(e.target.value)}
            placeholder={`예: "${selected.name}" 에서 더 밝게 / 더 미니멀하게`}
            style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
          <button className="btn" disabled={!describe.trim() || running} onClick={() => createFromDescription(selected)}>
            ✦ 이 스타일 변형하기
          </button>
        </div>
      )}
      {(job.error || confirmError) && <p style={{ color: "crimson" }}>{job.error || confirmError}</p>}
      {running && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10, padding: "12px 14px", border: "2px solid #1A1A1A", background: "#F5F1E3" }}>
          <span className="spinner" />
          <div>
            <div style={{ fontSize: 13, fontWeight: 900 }}>{job.phaseMsg || "클로드가 작업 중…"}</div>
            <div style={{ fontSize: 12, color: "#666" }}>⏳ 멈춘 게 아니에요 — 다른 탭을 써도 돼요. 끝나면 알려드려요.</div>
          </div>
        </div>
      )}
      {job.html && (
        <>
          {job.synth && (
            <div style={{ border: "2px solid #1A1A1A", padding: "10px 12px", marginBottom: 8, background: "#F5F1E3", display: "grid", gap: 6 }}>
              <div style={{ fontSize: 13, fontWeight: 900 }}>✦ 이런 스타일을 만들었어요 — {job.synth.name}</div>
              <div style={{ fontSize: 12, color: "#444" }}>{job.synth.description}</div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                {([
                  { key: "bg", label: "배경" },
                  { key: "surface", label: "표면" },
                  { key: "primary", label: "주요" },
                  { key: "accent", label: "강조" },
                  { key: "text", label: "글자" },
                ] as const).map(({ key, label }) => {
                  const c = job.synth!.tokens[key];
                  const hex = /^#[0-9a-fA-F]{6}$/.test(c) ? c : "#ffffff";
                  return (
                    <label key={key} title={`${label} — 클릭해 색 바꾸기 (${c})`}
                      style={{ position: "relative", width: 28, height: 28, display: "inline-block", cursor: "pointer" }}>
                      <span style={{ display: "block", width: 28, height: 28, background: c, border: "1px solid #1A1A1A", borderRadius: 4 }} />
                      <input type="color" aria-label={`${label} 색 바꾸기`} value={hex}
                        onChange={(e) => job.recolor(key, e.target.value)}
                        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0, border: 0, padding: 0, cursor: "pointer" }} />
                    </label>
                  );
                })}
                <span style={{ fontSize: 11, color: "#888" }}>✎ 색을 클릭해 바꿔보세요</span>
              </div>
              {job.synth.motion && <div style={{ fontSize: 11, color: "#666" }}>모션: {job.synth.motion.recipe}</div>}
            </div>
          )}
          <iframe title="디자인 목업" srcDoc={job.html} sandbox="" style={{ width: "100%", height: 600, border: "1px solid #ddd" }} />
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginTop: 12, paddingTop: 12, borderTop: "2px solid #1A1A1A" }}>
            <input aria-label="수정 요청" value={feedback} onChange={(e) => setFeedback(e.target.value)}
              placeholder="예: 여긴 빨강, 버튼 크게"
              style={{ flex: 1, minWidth: 220, padding: "9px 12px", border: "2px solid #1A1A1A", fontSize: 14 }} />
            <button className="btn" disabled={running || !feedback.trim()} onClick={() => generate(true)}
              style={{ fontWeight: 800 }}>
              ↻ 다시 그리기
            </button>
            <button className="btn" onClick={() => void confirm()}
              style={{ background: "#1A1A1A", color: "#fff", border: "2px solid #1A1A1A", fontWeight: 900 }}>
              ✓ 이 디자인으로 만들기
            </button>
            {job.synth && (
              <button className="btn" disabled={running} onClick={() => {
                void saveCustomStyle({ projectDir, style: job.synth! })
                  .then(() => listCustomStyles(projectDir).then(setCustom))
                  .then(() => setSavedMsg("스타일을 저장했어요 — 목록에서 다시 쓸 수 있어요"))
                  .catch((e) => setConfirmError(String(e)));
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
