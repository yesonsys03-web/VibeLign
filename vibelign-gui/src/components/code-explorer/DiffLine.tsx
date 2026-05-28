import type { DiffLine as DiffLineType } from "../../lib/vib/types";

interface Props {
  line: DiffLineType;
}

const BG: Record<DiffLineType["kind"], string> = {
  context: "transparent",
  added: "rgba(46, 160, 67, 0.18)",   // 녹색 배경
  removed: "rgba(248, 81, 73, 0.18)", // 빨강 배경
};

const MARK: Record<DiffLineType["kind"], string> = {
  context: " ",
  added: "+",
  removed: "-",
};

export default function DiffLine({ line }: Props) {
  const oldNo = line.old_no === null ? "" : String(line.old_no);
  const newNo = line.new_no === null ? "" : String(line.new_no);
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "44px 44px 18px 1fr",
        fontFamily: "ui-monospace, Menlo, Consolas, monospace",
        background: BG[line.kind],
        whiteSpace: "pre",
      }}
    >
      <span style={{ textAlign: "right", paddingRight: 6, color: "#888" }}>{oldNo}</span>
      <span style={{ textAlign: "right", paddingRight: 6, color: "#888" }}>{newNo}</span>
      <span style={{ textAlign: "center", color: line.kind === "added" ? "#2ea043" : line.kind === "removed" ? "#f85149" : "#888" }}>
        {MARK[line.kind]}
      </span>
      <span>{line.text || " "}</span>
    </div>
  );
}
