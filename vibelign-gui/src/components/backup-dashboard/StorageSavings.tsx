// === ANCHOR: STORAGESAVINGS_START ===
import { useEffect, useState } from "react";
import type { BackupDashboardStats } from "./model";
import { formatBytes } from "./model";
import type { BackupEntry, BackupGraphNode, BackupDbViewerInspectResult } from "../../lib/vib";
import { backupGraphSummary, getCachedBackupGraphSummary, backupDbViewerInspect, getCachedBackupDbViewerInspect } from "../../lib/vib";
import BackupCard from "./BackupCard";
import StorageRadialMap from "./StorageRadialMap";

interface StorageSavingsProps {
  stats: BackupDashboardStats;
  entries: BackupEntry[];
  projectDir: string;
}

export default function StorageSavings({ stats, entries, projectDir }: StorageSavingsProps) {
  const cachedGraph = getCachedBackupGraphSummary(projectDir);
  const [graphRoot, setGraphRoot] = useState<BackupGraphNode | null>(cachedGraph?.root ?? null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [graphMessage, setGraphMessage] = useState<string | null>(cachedGraph?.warnings[0] ?? null);
  const hasFileDetails = entries.some((entry) => entry.files.length > 0);
  const hasGraphDetails = hasFileDetails || (graphRoot?.sizeBytes ?? 0) > 0;

  const cachedDb = getCachedBackupDbViewerInspect(projectDir);
  const [dbReport, setDbReport] = useState<BackupDbViewerInspectResult | null>(cachedDb ?? null);

  useEffect(() => {
    const cached = getCachedBackupDbViewerInspect(projectDir);
    if (cached) {
      setDbReport(cached);
      return;
    }
    let cancelled = false;
    backupDbViewerInspect(projectDir)
      .then((report) => {
        if (!cancelled) setDbReport(report);
      })
      .catch(() => {
        /* db viewer 실패 시 복원 크기 표시로 폴백 */
      });
    return () => {
      cancelled = true;
    };
  }, [projectDir]);

  // 실제 디스크 사용량 = 백업 DB 파일 + 중복제거·압축된 객체 저장 크기.
  // stats.storedBytes 는 "복원 가능한 원본 크기의 합계"(논리값)라 디스크와 크게 다르다.
  const realDiskBytes =
    dbReport !== null
      ? (dbReport.dbFile.totalBytes ?? 0) + (dbReport.totalStoredSizeBytes ?? 0)
      : null;

  // 폴더별 원본 크기 → 근사 실제 사용량 환산 배율(저장/원본). 폴더별 정확한 dedup 은
  // 알 수 없어 전역 압축비로 환산한다.
  const diskScale =
    dbReport !== null && (dbReport.totalOriginalSizeBytes ?? 0) > 0
      ? (dbReport.totalStoredSizeBytes ?? 0) / (dbReport.totalOriginalSizeBytes ?? 1)
      : 1;

  useEffect(() => {
    if (hasFileDetails) {
      setGraphRoot(null);
      setGraphMessage(null);
      setGraphLoading(false);
      return;
    }
    const cached = getCachedBackupGraphSummary(projectDir);
    if (cached) {
      setGraphRoot(cached.root);
      setGraphMessage(cached.warnings[0] ?? null);
      setGraphLoading(false);
      return;
    }
    let cancelled = false;
    setGraphLoading(true);
    setGraphMessage(null);
    backupGraphSummary(projectDir)
      .then((result) => {
        if (cancelled) return;
        setGraphRoot(result.root);
        setGraphMessage(result.warnings[0] ?? null);
      })
      .catch((error) => {
        if (!cancelled) setGraphMessage(String(error));
      })
      .finally(() => {
        if (!cancelled) setGraphLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [hasFileDetails, projectDir]);

  return (
    <BackupCard
      icon="📦"
      title="백업 용량"
      subtitle="백업이 실제로 차지하는 디스크 용량이에요. 아래 그래프의 폴더별 값은 압축·중복제거를 반영한 근사 실제 사용량입니다."
      headerStyle={{ background: "#FFF1B8", padding: "12px 14px" }}
      iconStyle={{ background: "#FFB000", borderColor: "#1A1A1A" }}
    >
      {realDiskBytes !== null ? (
        <>
          <div style={{ fontSize: 28, fontWeight: 900 }}>{formatBytes(realDiskBytes)}</div>
          <div style={{ fontSize: 12, color: "#555" }}>
            실제 디스크 사용량(중복·압축 후)이에요. 복원 크기로는 {formatBytes(stats.storedBytes)}예요.
            {" "}{stats.manualCount}개는 직접 저장했고, {stats.autoCount}개는 자동으로 보관했어요.
          </div>
        </>
      ) : (
        <>
          <div style={{ fontSize: 28, fontWeight: 900 }}>{formatBytes(stats.storedBytes)}</div>
          <div style={{ fontSize: 12, color: "#555" }}>{stats.manualCount}개는 직접 저장했고, {stats.autoCount}개는 자동으로 보관했어요. 복원 가능한 원본 크기 합계라 실제 디스크와는 달라요.</div>
        </>
      )}
      {hasGraphDetails ? (
        <div style={{ marginTop: 12 }}>
          <StorageRadialMap entries={entries} root={hasFileDetails ? null : graphRoot} sizeScale={diskScale} />
        </div>
      ) : (
        <div style={{ marginTop: 12, fontSize: 12, color: "#666" }}>
          {graphLoading ? "백업 범위 그래프 요약을 불러오는 중입니다." : graphMessage ?? "파일별 그래프 데이터가 아직 없어요."}
        </div>
      )}
    </BackupCard>
  );
}
// === ANCHOR: STORAGESAVINGS_END ===
