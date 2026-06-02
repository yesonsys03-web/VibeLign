interface PlanningMessagesProps {
  readonly prompt: string;
  readonly outputPath: string | null;
}

export function PlanningMessages({ prompt, outputPath }: PlanningMessagesProps) {
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div
        style={{
          justifySelf: "end",
          maxWidth: 680,
          border: "2px solid #1A1A1A",
          background: "#FFFFFF",
          padding: 12,
          fontSize: 13,
          fontWeight: 700,
          lineHeight: 1.5,
        }}
      >
        {prompt}
      </div>
      <div
        style={{
          justifySelf: "start",
          maxWidth: 720,
          border: "2px solid #1A1A1A",
          background: "#F5F1E3",
          padding: 14,
          fontSize: 13,
          lineHeight: 1.6,
        }}
      >
        <div style={{ fontWeight: 900, marginBottom: 6 }}>VibeLign 정리</div>
        <div>첫 기획안을 템플릿으로 정리했어요.</div>
        {outputPath && (
          <div style={{ marginTop: 6, fontSize: 12, color: "#555", fontWeight: 700 }}>
            저장 위치: {outputPath}
          </div>
        )}
      </div>
    </div>
  );
}
