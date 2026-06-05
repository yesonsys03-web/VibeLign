// === ANCHOR: HOMEHEADER_START ===
interface HomeHeaderProps {
  readonly version: string;
  readonly advancedOpen: boolean;
  readonly onResetOrder: () => void;
  readonly onShowSimple: () => void;
}

// === ANCHOR: HOMEHEADER_HOMEHEADER_START ===
export function HomeHeader({ version, advancedOpen, onResetOrder, onShowSimple }: HomeHeaderProps) {
  return (
    <div className="page-header" style={{ padding: "14px 20px 12px" }}>
      <span className="page-title">HOME</span>
      {advancedOpen ? (
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <button
            className="btn btn-ghost btn-sm"
            onClick={onShowSimple}
            style={{ fontSize: 10, padding: "2px 8px", border: "1.5px solid #1A1A1A" }}
            type="button"
          >
            간단히 보기
          </button>
          <button
            aria-label="카드 순서 초기화"
            className="btn btn-ghost btn-sm"
            onClick={onResetOrder}
            style={{ fontSize: 10, padding: "2px 8px", border: "1.5px solid #ccc", color: "#888" }}
            title="카드 순서 초기화"
            type="button"
          >
            ↺
          </button>
        </div>
      ) : null}
      <div
        className="terminal"
        style={{
          padding: "6px 10px",
          fontSize: 10,
          fontWeight: 700,
          lineHeight: 1.4,
          flexShrink: 0,
        }}
        title="VibeLign GUI 버전"
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: 8 }}>
          <div className="terminal-header" style={{ marginBottom: 0 }}>
            <div className="terminal-dot red" />
            <div className="terminal-dot yellow" />
            <div className="terminal-dot green" />
          </div>
          <span style={{ color: "#b8b4b0" }}>바이브라인</span>
          <span style={{ color: "#F5621E" }}>v{version}</span>
        </div>
      </div>
    </div>
  );
}
// === ANCHOR: HOMEHEADER_HOMEHEADER_END ===
// === ANCHOR: HOMEHEADER_END ===
