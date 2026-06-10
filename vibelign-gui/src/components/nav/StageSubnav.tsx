// === ANCHOR: STAGE_SUBNAV_START ===
import { stageOf, pagesForStage, PAGE_LABELS, type Page } from "../../lib/nav/stages";

interface StageSubnavProps {
  page: Page;
  onNavigate: (page: Page) => void;
}

/** 현재 단계의 서브탭. 단계에 페이지가 2개 이상일 때만 렌더(기획 단계는 숨김). */
export function StageSubnav({ page, onNavigate }: StageSubnavProps) {
  const stage = stageOf(page);
  if (!stage) return null;
  const pages = pagesForStage(stage);
  if (pages.length < 2) return null;
  return (
    <div style={{ display: "flex", gap: 4, padding: "4px 12px", borderBottom: "1px solid #1A1A1A" }}>
      {pages.map((p) => (
        <button
          key={p}
          className={`nav-tab ${page === p ? "active" : ""}`}
          style={{ fontSize: 12, padding: "2px 10px" }}
          onClick={() => onNavigate(p)}
        >
          {PAGE_LABELS[p]}
        </button>
      ))}
    </div>
  );
}
// === ANCHOR: STAGE_SUBNAV_END ===
