// === ANCHOR: BACKUPDBVIEWER_START ===
import { useCallback, useEffect, useMemo, useState } from "react";
import type { BackupDbMaintenanceResult, BackupDbViewerInspectResult } from "../../lib/vib";
import { backupCleanup, backupDbMaintenance, backupDbViewerInspect, getCachedBackupDbViewerInspect } from "../../lib/vib";
import BackupCard from "./BackupCard";
import BackupDbDetailPanel from "./BackupDbDetailPanel";
import BackupDbRowList from "./BackupDbRowList";
import BackupDbSummaryCards from "./BackupDbSummaryCards";
import { filterBackupDbRows } from "./backupDbModel";
import { formatBytes } from "./model";

interface BackupDbViewerProps {
  projectDir: string;
}

const DB_SIZE_WARNING_BYTES = 64 * 1024 * 1024;
const DB_SIZE_CRITICAL_BYTES = 256 * 1024 * 1024;

export default function BackupDbViewer({ projectDir }: BackupDbViewerProps) {
  const cachedReport = getCachedBackupDbViewerInspect(projectDir);
  const [report, setReport] = useState<BackupDbViewerInspectResult | null>(cachedReport ?? null);
  const [loading, setLoading] = useState(!cachedReport);
  const [maintenanceLoading, setMaintenanceLoading] = useState(false);
  const [maintenancePlan, setMaintenancePlan] = useState<BackupDbMaintenanceResult | null>(null);
  const [maintenanceMessage, setMaintenanceMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const load = useCallback(async (force = false) => {
    const cached = getCachedBackupDbViewerInspect(projectDir);
    if (!force && cached) {
      setReport(cached);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const next = await backupDbViewerInspect(projectDir, { force });
      setReport(next);
      if (next.dbFile.totalBytes >= DB_SIZE_WARNING_BYTES) {
        try {
          setMaintenancePlan(await backupDbMaintenance(projectDir, false));
        } catch {
          setMaintenancePlan(null);
        }
      } else {
        setMaintenancePlan(null);
      }
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

  const runMaintenance = useCallback(async () => {
    setMaintenanceLoading(true);
    setMaintenanceMessage(null);
    setError(null);
    try {
      const isCritical = (report?.dbFile.totalBytes ?? 0) >= DB_SIZE_CRITICAL_BYTES;
      const cleanupResult = isCritical ? await backupCleanup(projectDir) : null;
      const result = cleanupResult?.maintenance ?? await backupDbMaintenance(projectDir, true);
      if (result.blockers.length > 0) {
        setMaintenanceMessage(`정리를 건너뛰었어요: ${result.blockers.join(", ")}`);
      } else if (result.plannedAction === "noop") {
        const pruned = cleanupResult?.retention.count ?? 0;
        setMaintenanceMessage(isCritical ? `오래된 백업 ${pruned}개를 정리했고, DB 파일은 이미 추가 압축할 내용이 없어요.` : "이미 정리할 내용이 없어요.");
      } else {
        const pruned = cleanupResult?.retention.count ?? 0;
        const prefix = isCritical ? `오래된 백업 ${pruned}개를 정리하고 ` : "";
        setMaintenanceMessage(`${prefix}DB 정리를 완료했어요. 회수한 공간: ${formatBytes(result.reclaimedBytes)}`);
      }
      await load(true);
    } catch (err) {
      setError(String(err));
    } finally {
      setMaintenanceLoading(false);
    }
  }, [load, projectDir, report?.dbFile.totalBytes]);

  const rows = useMemo(() => filterBackupDbRows(report?.checkpoints ?? [], query), [report, query]);
  const selected = report?.checkpoints.find((row) => row.checkpointId === selectedId) ?? null;
  // === ANCHOR: BACKUPDBVIEWER_SHOWMAINTENANCEHINT_START ===
  const dbTotalBytes = report?.dbFile.totalBytes ?? 0;
  const showMaintenanceHint = dbTotalBytes >= DB_SIZE_WARNING_BYTES;
  const showCriticalMaintenance = dbTotalBytes >= DB_SIZE_CRITICAL_BYTES;
  const canRunMaintenance = showMaintenanceHint && (maintenancePlan === null || maintenancePlan.blockers.length === 0);
  const visibleWarnings = (report?.warnings ?? []).filter((warning) => !warning.includes("백업 관리 DB 파일이 64MB") && !warning.includes("백업 관리 DB 파일이 256MB"));
  // === ANCHOR: BACKUPDBVIEWER_SHOWMAINTENANCEHINT_END ===

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="alert alert-success" style={{ margin: 0 }}>읽기 전용입니다. 복원에 쓰이는 값은 수정하지 않습니다.</div>
      {showMaintenanceHint && (
        <div className="alert" style={{ alignItems: "center", display: "flex", gap: 10, justifyContent: "space-between", margin: 0 }}>
          <span>
            {showCriticalMaintenance
              ? "백업 DB가 256MB를 넘었어요. 오래된 백업을 정리하고 DB 파일을 최적화할 수 있습니다."
              : maintenancePlan !== null && maintenancePlan.plannedAction !== "noop"
              ? "DB 파일이 커졌어요. 정리하면 DB 백업을 만든 뒤 WAL 정리와 필요한 압축을 실행합니다."
              : "DB 파일이 64MB를 넘었어요. 버튼을 눌러 정리 상태를 확인하거나 가능한 정리를 실행할 수 있습니다."}
          </span>
          {canRunMaintenance && (
            <button type="button" className="btn btn-primary btn-sm" onClick={runMaintenance} disabled={maintenanceLoading || loading}>
              {maintenanceLoading ? <span className="spinner" /> : "DB 정리 실행"}
            </button>
          )}
        </div>
      )}
      {maintenanceMessage && <div className="alert alert-success" style={{ margin: 0 }}>{maintenanceMessage}</div>}
      {error && <div className="alert alert-error" style={{ margin: 0 }}>{error}</div>}
      {visibleWarnings.map((warning) => <div key={warning} className="alert" style={{ margin: 0 }}>{warning}</div>)}
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
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => load(true)} disabled={loading}>{loading ? <span className="spinner" /> : "새로고침"}</button>
          </>
        }
      >
        {report ? <BackupDbRowList rows={rows} selectedId={selectedId} onSelect={setSelectedId} /> : <div style={{ fontSize: 12, color: "#666" }}>백업 관리 DB를 읽는 중입니다.</div>}
      </BackupCard>
      {report ? <BackupDbDetailPanel report={report} row={selected} /> : null}
    </div>
  );
}
// === ANCHOR: BACKUPDBVIEWER_END ===
