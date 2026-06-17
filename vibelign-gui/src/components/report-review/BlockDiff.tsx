// === ANCHOR: BLOCK_DIFF_START ===
import type { CSSProperties, ReactElement } from "react";
import type { Decision, GuardRecord, RModelBlock, VagueWarning } from "../../lib/vib/reportModel";

interface Props {
  heading: string;
  base: RModelBlock;
  polished: RModelBlock;
  decision: Decision;
  guard?: GuardRecord;
  vague?: VagueWarning[];
  onAccept: () => void;
  onReject: () => void;
}

function guardTitle(g: GuardRecord): string {
  if (g.reason === "number_added") return "다듬기가 원문에 없던 숫자를 넣으려 해서 원문을 유지했어요";
  return `보존된 수치: ${g.missing.join(", ")}`;
}

// lint 의 offset(파이썬 코드포인트)을 신뢰하지 않고 GUI 에서 term 을 직접 재탐색한다(non-BMP 안전).
function highlight(text: string, vague: VagueWarning[]) {
  const terms = [...new Set(vague.map((w) => w.term))];
  if (!terms.length) return text;
  const hits: { start: number; len: number }[] = [];
  for (const term of terms) {
    let i = text.indexOf(term);
    while (i !== -1) { hits.push({ start: i, len: term.length }); i = text.indexOf(term, i + 1); }
  }
  hits.sort((a, b) => a.start - b.start);
  const out: (string | ReactElement)[] = [];
  let cur = 0;
  hits.forEach((h, idx) => {
    if (h.start < cur) return;
    out.push(text.slice(cur, h.start));
    out.push(<mark key={idx} style={{ background: "#ffe08a" }}>{text.slice(h.start, h.start + h.len)}</mark>);
    cur = h.start + h.len;
  });
  out.push(text.slice(cur));
  return out;
}

export function BlockDiff({ heading, base, polished, decision, guard, vague, onAccept, onReject }: Props) {
  const changed = base.text !== polished.text;
  return (
    <div style={box}>
      <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 6 }}>
        {heading}
        {guard && <span style={badge} title={guardTitle(guard)}>숫자 보존됨</span>}
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <div style={col}><div style={label}>원본</div><div>{base.text}</div></div>
        <div style={col}>
          <div style={label}>다듬</div>
          <div style={{ color: changed ? "#1A1A1A" : "#999" }}>{highlight(polished.text, vague ?? [])}</div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        <button type="button" onClick={onAccept} style={decision === "accept" ? onBtn : offBtn}>수락</button>
        <button type="button" onClick={onReject} style={decision === "reject" ? onBtn : offBtn}>거부</button>
      </div>
    </div>
  );
}

const box: CSSProperties = { border: "1px solid #e5e0d0", borderRadius: 6, padding: 10, marginBottom: 8 };
const col: CSSProperties = { flex: 1, fontSize: 13, lineHeight: 1.6 };
const label: CSSProperties = { fontSize: 11, color: "#888", marginBottom: 2 };
const badge: CSSProperties = { marginLeft: 8, fontSize: 10, background: "#eef", color: "#225", padding: "1px 6px", borderRadius: 8 };
const onBtn: CSSProperties = { background: "#1A1A1A", color: "#fff", border: "none", padding: "4px 12px", borderRadius: 5, cursor: "pointer" };
const offBtn: CSSProperties = { background: "#e5e0d0", color: "#1A1A1A", border: "none", padding: "4px 12px", borderRadius: 5, cursor: "pointer" };
// === ANCHOR: BLOCK_DIFF_END ===
