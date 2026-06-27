// === ANCHOR: USE_REPORT_EXPORT_START ===
import { useState } from "react";
import { copyReportTo, getReportExportDir } from "../../lib/vib/report";

/** 생성된 보고서 경로를 기본 폴더(설정값→OS 문서 폴더)로 복사하는 공용 훅. */
export function useReportExport() {
  const [exportedPath, setExportedPath] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);
  async function exportTo(src: string, dir?: string) {
    setExporting(true);
    setExportErr(null);
    try {
      const target = dir ?? (await getReportExportDir());
      setExportedPath(await copyReportTo(src, target));
    } catch (e) {
      setExportErr(`저장 위치로 복사하지 못했어요: ${String(e)}`);
    } finally {
      setExporting(false);
    }
  }
  return { exportedPath, exporting, exportErr, exportTo, reset: () => setExportedPath(null) };
}
// === ANCHOR: USE_REPORT_EXPORT_END ===
