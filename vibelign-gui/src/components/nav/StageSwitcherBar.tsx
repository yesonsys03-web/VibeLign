// === ANCHOR: STAGE_SWITCHER_BAR_START ===
import { STAGE_DEFS, stageOf, pagesForStage, PAGE_DESCRIPTIONS, STAGE_DESCRIPTIONS, type Page } from "../../lib/nav/stages";

interface StageSwitcherBarProps {
  page: Page;
  projectDir: string;
  onHome: () => void;
  onNavigate: (page: Page) => void;
  onOpenManual: () => void;
  onOpenFolder: () => void;
  onExitProject: () => void;
}

export function StageSwitcherBar({
  page,
  projectDir,
  onHome,
  onNavigate,
  onOpenManual,
  onOpenFolder,
  onExitProject,
}: StageSwitcherBarProps) {
  const activeStage = stageOf(page);
  return (
    <div className="nav-tabs" style={{ paddingLeft: 8 }}>
      <button className={`nav-tab ${page === "home" ? "active" : ""}`} title={PAGE_DESCRIPTIONS.home} onClick={onHome}>
        홈
      </button>
      {STAGE_DEFS.map((def) => (
        <button
          key={def.key}
          className={`nav-tab ${activeStage === def.key ? "active" : ""}`}
          title={STAGE_DESCRIPTIONS[def.key]}
          onClick={() => onNavigate(pagesForStage(def.key)[0])}
        >
          {def.icon} {def.label}
        </button>
      ))}
      <div style={{ flex: 1 }} />
      <button className={`nav-tab ${page === "manual" ? "active" : ""}`} title={PAGE_DESCRIPTIONS.manual} onClick={onOpenManual}>
        사용법
      </button>
      <button className="nav-tab" title="탐색기로 열기" onClick={onOpenFolder}>
        폴더열기
      </button>
      <button
        className="nav-tab"
        style={{
          borderRight: "none",
          fontSize: 13,
          color: "#777",
          maxWidth: 260,
          overflow: "hidden",
          textOverflow: "ellipsis",
          display: "block",
        }}
        title={projectDir}
        onClick={onExitProject}
      >
        {projectDir.replace(/\\/g, "/").split("/").filter(Boolean).slice(-1)[0] || projectDir} ↩
      </button>
    </div>
  );
}
// === ANCHOR: STAGE_SWITCHER_BAR_END ===
