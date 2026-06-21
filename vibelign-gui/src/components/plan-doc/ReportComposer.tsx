// === ANCHOR: REPORTCOMPOSER_START ===
import { useEffect, useMemo, useState } from "react";
import { probePlanningProviders } from "../../lib/vib/planning-personas";
import { pickFolder } from "../../lib/vib/system";
import {
  copyReportTo,
  getReportExportDir,
  setReportExportDir,
  type ReportType,
} from "../../lib/vib/report";
import type { ReportFontSizes } from "../../lib/vib/reportFontSizes";
import type { ReportFonts } from "../../lib/vib/reportFonts";
import { ReportQualityPanel } from "./ReportQualityPanel";
import { ReportComposerControls, REPORT_TYPES } from "./ReportComposerControls";
import { ReportComposerExportBox } from "./ReportComposerExportBox";
import { ReportComposerLayout } from "./ReportComposerLayout";
import { ReportVisualCardsCompanion } from "./ReportVisualCardsCompanion";
import {
  firstInstalledAiProvider,
  reportAssistProviderOptions,
  type ReportAssistProviderId,
} from "./reportAssistProviders";
import {
  useReportComposerGeneration,
  type ReportComposerFormat,
  type ReportComposerReviewRequest,
} from "./useReportComposerGeneration";

async function rememberReportExportDir(dir: string): Promise<void> {
  try {
    await setReportExportDir(dir);
  } catch (error) {
    if (!(error instanceof Error)) throw error;
  }
}

type Format = ReportComposerFormat;

export interface ReportComposerProps {
  planPath: string;
  cwd: string;
  /** "modal": 오버레이 박스(헤더+푸터) 형태. "inline": 좌측 옵션 + 우측 큰 프리뷰 2-pane. */
  layout: "modal" | "inline";
  /** modal: 모달 닫기. inline: 목록으로 돌아가기. */
  onClose: () => void;
  /** 제공되고 'AI 다듬기'가 켜져 있으면, 인라인 생성 대신 블록 diff 검토 화면으로 보낸다. */
  onReviewRequest?: ReportComposerReviewRequest;
  /** 처음 선택될 보고서 종류(문서 우클릭 진입 시 "doc"). 기본 "work". */
  defaultType?: ReportType;
}

// === ANCHOR: REPORTCOMPOSER_REPORTCOMPOSER_START ===
export function ReportComposer({ planPath, cwd, layout, onClose, onReviewRequest, defaultType }: ReportComposerProps) {
  const [reportType, setReportType] = useState<ReportType>(defaultType ?? "work");
  const [workspaceTab, setWorkspaceTab] = useState<"report" | "cards">("report");
  const [format, setFormat] = useState<Format>("html");
  const [polish, setPolish] = useState(false);
  const [theme, setTheme] = useState<string>(() => {
    try {
      return localStorage.getItem("vibelign_report_theme") || "classic";
    } catch {
      return "classic";
    }
  });
  const [author, setAuthor] = useState<string>(() => {
    try {
      return localStorage.getItem("vibelign_report_author") || "";
    } catch {
      return "";
    }
  });
  const [fontSizes, setFontSizes] = useState<ReportFontSizes>({});
  const [fonts, setFonts] = useState<ReportFonts>({});
  const [pageNumbers, setPageNumbers] = useState(true);
  const [installedAssistProviders, setInstalledAssistProviders] = useState<readonly string[]>([]);
  const [assistProvider, setAssistProvider] = useState<ReportAssistProviderId>("local");
  const [openErr, setOpenErr] = useState<string | null>(null);
  // 사용자에게 전달된 최종 저장 위치(.vibelign/reports 내부 사본과 별개로 복사한 곳).
  const [exportedPath, setExportedPath] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportErr, setExportErr] = useState<string | null>(null);

  const inline = layout === "inline";

  // 생성된 보고서를 지정 폴더로 복사한다. dir 가 없으면 기본 폴더(설정값→OS 문서 폴더)를 쓴다.
  // === ANCHOR: REPORTCOMPOSER_EXPORTTO_START ===
  const exportTo = async (src: string, dir?: string) => {
    setExporting(true);
    setExportErr(null);
    try {
      const target = dir ?? (await getReportExportDir());
      const dest = await copyReportTo(src, target);
      setExportedPath(dest);
    } catch (error) {
      if (error instanceof Error) {
        setExportErr(`저장 위치로 복사하지 못했어요: ${error.message}`);
        return;
      }
      throw error;
    } finally {
      setExporting(false);
    }
  };
  // === ANCHOR: REPORTCOMPOSER_EXPORTTO_END ===

  // "다른 위치에 저장": 폴더 선택 → 복사 → 그 폴더를 다음 기본값으로 기억.
  // === ANCHOR: REPORTCOMPOSER_HANDLECHOOSELOCATION_START ===
  const handleChooseLocation = async () => {
    if (!result || !result.ok) return;
    let dir: string | null = null;
    try {
      dir = await pickFolder();
    } catch (error) {
      if (!(error instanceof Error)) throw error;
    }
    if (!dir) return;
    await exportTo(result.path, dir);
    void rememberReportExportDir(dir);
  };
  // === ANCHOR: REPORTCOMPOSER_HANDLECHOOSELOCATION_END ===

  const resetGeneratedArtifacts = () => {
    setOpenErr(null);
    setExportedPath(null);
    setExportErr(null);
  };

  const {
    generating,
    result,
    qualityReview,
    requestAssistance,
    handleQualityProceed,
    handleGenerate,
    cancelQualityReview,
  } = useReportComposerGeneration({
    planPath,
    cwd,
    reportType,
    format,
    polish,
    theme,
    author,
    pageNumbers,
    fontSizes,
    fonts,
    assistProvider,
    reportTypeLabel: REPORT_TYPES.find((t) => t.id === reportType)?.label ?? reportType,
    onClose,
    onReportTypeChange: setReportType,
    onResetGeneratedArtifacts: resetGeneratedArtifacts,
    onExportReady: (path) => void exportTo(path),
    ...(onReviewRequest === undefined ? {} : { onReviewRequest }),
  });

  const reviewActive = qualityReview !== null;
  useEffect(() => {
    if (!reviewActive) return;
    let active = true;
    void probePlanningProviders()
      .then((providers) => {
        if (!active) return;
        setInstalledAssistProviders(providers);
        setAssistProvider((current) => {
          if (current !== "local") return current;
          return firstInstalledAiProvider(providers) ?? "local";
        });
      })
      .catch(() => {
        if (active) setInstalledAssistProviders([]);
      });
    return () => {
      active = false;
    };
  }, [reviewActive]);

  const assistProviderOptions = useMemo(
    () => reportAssistProviderOptions(installedAssistProviders),
    [installedAssistProviders],
  );

  // === ANCHOR: REPORTCOMPOSER_OPTIONS_START ===
  const options = (
    <>
      <ReportComposerControls
        reportType={reportType}
        format={format}
        theme={theme}
        author={author}
        fontSizes={fontSizes}
        fonts={fonts}
        pageNumbers={pageNumbers}
        polish={polish}
        generating={generating}
        result={result}
        onReportTypeChange={setReportType}
        onFormatChange={setFormat}
        onThemeChange={setTheme}
        onAuthorChange={setAuthor}
        onFontSizesChange={setFontSizes}
        onFontsChange={setFonts}
        onPageNumbersChange={setPageNumbers}
        onPolishChange={setPolish}
        onGenerate={() => {
          setWorkspaceTab("report");
          handleGenerate();
        }}
      />
    </>
  );
  // === ANCHOR: REPORTCOMPOSER_OPTIONS_END ===

  const composerControls = qualityReview === null ? (
    options
  ) : (
    <ReportQualityPanel
      quality={qualityReview.quality}
      assistance={qualityReview.assistance}
      sourceLabel="기획안"
      longSource={qualityReview.longSource}
      onRequestAssistance={requestAssistance}
      assistProvider={assistProvider}
      assistProviderOptions={assistProviderOptions}
      onAssistProviderChange={setAssistProvider}
      onProceed={handleQualityProceed}
      onCancel={cancelQualityReview}
    />
  );

  // === ANCHOR: REPORTCOMPOSER_EXPORTBOX_START ===
  const exportBoxEl = (
    <ReportComposerExportBox
      result={result}
      inline={inline}
      exporting={exporting}
      exportedPath={exportedPath}
      exportErr={exportErr}
      openErr={openErr}
      onOpenErr={setOpenErr}
      onChooseLocation={() => void handleChooseLocation()}
    />
  );
  // === ANCHOR: REPORTCOMPOSER_EXPORTBOX_END ===

  return (
    <ReportComposerLayout
      cwd={cwd}
      inline={inline}
      controls={composerControls}
      qualityReviewActive={qualityReview !== null}
      workspaceTab={workspaceTab}
      onWorkspaceTabChange={setWorkspaceTab}
      companion={<ReportVisualCardsCompanion cwd={cwd} planPath={planPath} reportType={reportType} />}
      exportBox={exportBoxEl}
      result={result}
      exportedPath={exportedPath}
      openErr={openErr}
      onOpenErr={setOpenErr}
      onClose={onClose}
    />
  );
}
// === ANCHOR: REPORTCOMPOSER_REPORTCOMPOSER_END ===
// === ANCHOR: REPORTCOMPOSER_END ===
