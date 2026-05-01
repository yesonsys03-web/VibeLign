import { useCallback, useEffect, useMemo, useState } from "react";
import type { BackupDbViewerInspectResult } from "../../lib/vib";
import { backupDbViewerInspect } from "../../lib/vib";
import BackupCard from "./BackupCard";
import BackupDbDetailPanel from "./BackupDbDetailPanel";
import BackupDbRowList from "./BackupDbRowList";
import BackupDbSummaryCards from "./BackupDbSummaryCards";
import { filterBackupDbRows } from "./backupDbModel";

interface BackupDbViewerProps {
  projectDir: string;
}

export default function BackupDbViewer({ projectDir }: BackupDbViewerProps) {
  const [report, setReport] = useState<BackupDbViewerInspectResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await backupDbViewerInspect(projectDir);
      setReport(next);
      setSelectedId((current) => {
        if (current && next.checkpoints.some((row) => row.checkpointId === current)) return current;
        return next.checkpoints[0]?.checkpointId ?? null;
      });
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [projectDir]);

  useEffect(() => {
    load();
  }, [load]);

  const rows = useMemo(() => filterBackupDbRows(report?.checkpoints ?? [], query), [report, query]);
  const selected = report?.checkpoints.find((row) => row.checkpointId === selectedId) ?? null;
  const showMaintenanceHint = (report?.dbFile.totalBytes ?? 0) >= 64 * 1024 * 1024;

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="alert alert-success" style={{ margin: 0 }}>읽기 전용입니다. 복원에 쓰이는 값은 수정하지 않습니다.</div>
      {showMaintenanceHint && (
        <div className="alert" style={{ margin: 0 }}>
          DB 파일이 커졌어요. 터미널에서 <code>vib backup-db-maintenance --json</code>으로 먼저 계획을 확인하고, 필요할 때만 <code>--apply</code>를 붙여 정리하세요.
        </div>
      )}
      {error && <div className="alert alert-error" style={{ margin: 0 }}>{error}</div>}
      {report?.warnings.map((warning) => <div key={warning} className="alert" style={{ margin: 0 }}>{warning}</div>)}
      {report ? <BackupDbSummaryCards report={report} /> : null}
      <BackupCard
        icon="🗄️"
        title={report?.dbExists ? "백업 DB rows" : "백업 DB 없음"}
        subtitle={report?.dbExists ? "검색 가능한 목록으로 DB row를 확인해요." : "아직 Rust 백업 DB가 없어요. 백업을 먼저 만들어 주세요."}
        headerStyle={{ background: "#F7F7F7", padding: "12px 14px" }}
        iconStyle={{ background: "#1A1A1A", borderColor: "#1A1A1A", color: "#fff" }}
        bodyStyle={{ display: "grid", gap: 8 }}
        actions={
          <>
            <input className="input-field" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="DB row 검색" style={{ width: 160, fontSize: 11 }} />
            <button type="button" className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>{loading ? <span className="spinner" /> : "새로고침"}</button>
          </>
        }
      >
        {report ? <BackupDbRowList rows={rows} selectedId={selectedId} onSelect={setSelectedId} /> : <div style={{ fontSize: 12, color: "#666" }}>백업 관리 DB를 읽는 중입니다.</div>}
      </BackupCard>
      {report ? <BackupDbDetailPanel report={report} row={selected} /> : null}
    </div>
  );
}
