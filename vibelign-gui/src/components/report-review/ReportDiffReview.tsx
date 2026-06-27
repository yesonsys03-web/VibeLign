// === ANCHOR: REPORT_DIFF_REVIEW_START ===
import { useReviewState } from "./useReviewState";
import { BlockDiff } from "./BlockDiff";
import {
  blockKey, isPolishable,
  type EmitPayload, type GuardRecord, type VagueWarning,
} from "../../lib/vib/reportModel";

interface Props {
  payload: EmitPayload;
  onConfirm: (reject: [number, number][]) => void;
  onCancel: () => void;
}

export function ReportDiffReview({ payload, onConfirm, onCancel }: Props) {
  const { decisions, set, setAll, reject } = useReviewState(payload);

  const guardByKey = new Map<string, GuardRecord>(
    payload.guards.map((g) => [blockKey(g.section, g.block), g]),
  );
  const vagueByKey = new Map<string, VagueWarning[]>();
  payload.vague_warnings.forEach((w) => {
    const k = blockKey(w.section, w.block);
    vagueByKey.set(k, [...(vagueByKey.get(k) ?? []), w]);
  });

  const diffs = payload.base.sections.flatMap((sec, si) =>
    sec.blocks
      .map((blk, bi) => ({ si, bi, sec, blk }))
      .filter((x) => isPolishable(x.blk)),
  );

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button type="button" onClick={() => setAll("accept")}>모두 수락</button>
        <button type="button" onClick={() => setAll("reject")}>모두 원본</button>
      </div>
      {diffs.length === 0 &&
        (payload.base.sections.length === 0 && payload.report_type !== "doc" ? (
          <p style={{ color: "#9B1B1B", lineHeight: 1.6 }}>
            이 문서에는 선택한 보고서 양식 항목이 없어요. <b>취소</b> 후 보고서 종류를{" "}
            <b>‘문서 그대로’</b>로 바꿔 다시 만들어 주세요.
          </p>
        ) : (
          <p style={{ color: "#888" }}>다듬을 항목이 없어요. 바로 내보낼 수 있어요.</p>
        ))}
      {diffs.map(({ si, bi, sec }) => (
        <BlockDiff
          key={`${si}:${bi}`}
          heading={sec.heading}
          base={payload.base.sections[si].blocks[bi]}
          polished={payload.polished.sections[si].blocks[bi]}
          decision={decisions[blockKey(si, bi)] ?? "accept"}
          guard={guardByKey.get(blockKey(si, bi))}
          vague={vagueByKey.get(blockKey(si, bi))}
          onAccept={() => set(si, bi, "accept")}
          onReject={() => set(si, bi, "reject")}
        />
      ))}
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button
          type="button"
          onClick={() => onConfirm(reject())}
          style={{ background: "#9B1B1B", color: "#fff", border: "none", padding: "8px 16px", borderRadius: 6, cursor: "pointer", fontWeight: 700 }}
        >
          저장 / 내보내기
        </button>
        <button type="button" onClick={onCancel}>취소</button>
      </div>
    </div>
  );
}
// === ANCHOR: REPORT_DIFF_REVIEW_END ===
