// === ANCHOR: CHECKPOINT_CARD_START ===
import { useState } from "react";
import BackupCard from "../../backup-dashboard/BackupCard";
import { checkpointCreate } from "../../../lib/vib";
import { CardState } from "../../../lib/commands";

interface CheckpointCardProps {
  projectDir: string;
  onNavigate: (page: "backups") => void;
}

export default function CheckpointCard({ projectDir, onNavigate }: CheckpointCardProps) {
  const [cpMsg, setCpMsg] = useState("");
  const [st, setSt] = useState<CardState>("idle");

  async function handleCheckpoint() {
    if (!cpMsg.trim()) return;
    setSt("loading");
    try {
      await checkpointCreate(projectDir, cpMsg.trim());
      setCpMsg("");
      setSt("done");
      setTimeout(() => setSt("idle"), 2000);
    } catch {
      setSt("error");
    }
  }

  return (
    <BackupCard
      icon="💾"
      title="백업"
      subtitle="지금 코드 모습을 저장해 두면 나중에 그때로 되돌릴 수 있어요. 커밋 후 자동 백업은 Settings에서 켜고 끌 수 있어요."
      headerStyle={{ background: "#7B4DFF18", padding: "10px 14px" }}
      iconStyle={{ background: "#7B4DFF", color: "#fff", borderColor: "#7B4DFF", width: 28, height: 28, fontSize: 12, fontWeight: 900 }}
      bodyStyle={{ padding: "8px 14px 10px" }}
      actions={st === "done" ? <span style={{ fontSize: 9, fontWeight: 700, padding: "2px 6px", background: "#4DFF91", color: "#1A1A1A", border: "1px solid #1A1A1A" }}>저장됨</span> : null}
    >
      <input
        className="input-field"
        value={cpMsg}
        onChange={(e) => setCpMsg(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleCheckpoint()}
        placeholder="메시지 입력..."
        style={{ width: "100%", marginBottom: 6, fontSize: 11, padding: "4px 8px", boxSizing: "border-box" }}
      />
      <div style={{ display: "flex", gap: 6 }}>
        <button className="btn btn-sm" style={{ flex: 1, background: "#7B4DFF", color: "#fff", border: "2px solid #1A1A1A" }}
          disabled={st === "loading" || !cpMsg.trim()} onClick={handleCheckpoint}>
          {st === "loading" ? <span className="spinner" /> : "저장 ▶"}
        </button>
        <button className="btn btn-ghost btn-sm" style={{ fontSize: 10, border: "2px solid #1A1A1A" }}
          onClick={() => onNavigate("backups")}>목록</button>
      </div>
      <div style={{ marginTop: 8, fontSize: 10, color: "#666", lineHeight: 1.5 }}>
        BACKUPS의 <b>백업 범위</b>는 복원 가능한 원본 크기의 합계이고, 실제 디스크 사용량은 <b>Backup DB Viewer</b>에서 확인합니다.
      </div>
    </BackupCard>
  );
}
// === ANCHOR: CHECKPOINT_CARD_END ===
