interface HomePlanningEntryProps {
  readonly prompt: string;
  readonly outputPath: string | null;
  readonly isPending: boolean;
  readonly onOpen: () => void;
}

export function HomePlanningEntry({ prompt, outputPath, isPending, onOpen }: HomePlanningEntryProps) {
  return (
    <section
      style={{
        border: "2px solid #1A1A1A",
        background: "#F5F1E3",
        padding: 10,
        marginBottom: 12,
        display: "flex",
        gap: 10,
        alignItems: "center",
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 11, fontWeight: 900, marginBottom: 3 }}>현재 기획안</div>
        <div style={{ fontSize: 13, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {prompt}
        </div>
        <div style={{ fontSize: 10, color: "#666", fontWeight: 700, marginTop: 3 }}>
          {isPending ? "기획안을 만드는 중..." : outputPath ? `저장 위치: ${outputPath}` : "기획방에서 이어서 볼 수 있어요."}
        </div>
      </div>
      <button className="btn btn-black btn-sm" type="button" onClick={onOpen} style={{ fontSize: 11, flexShrink: 0 }}>
        기획방으로 돌아가기
      </button>
    </section>
  );
}
