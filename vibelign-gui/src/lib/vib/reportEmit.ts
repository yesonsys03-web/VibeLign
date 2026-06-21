// === ANCHOR: REPORTEMIT_START ===
import { runVib } from "./core";
import type { PlanningProviderId } from "./planning-personas";
import { parseReportAssistPayload, type ReportAssistPayload } from "./reportAssist";
import type { ReportType } from "./report";
import type { EmitPayload, GuardRecord, RModel, RModelBlock, RModelSection, VagueWarning } from "./reportModel";
import { parseReportQualityPayload, type ReportQualityPayload } from "./reportQuality";

export type EmitResult = { ok: true; payload: EmitPayload } | { ok: false; error: string };

export type ReportAssistanceRequest = {
  readonly cwd: string;
  readonly planPath: string;
  readonly reportType: ReportType;
  readonly author?: string;
  readonly assistProvider?: "local" | PlanningProviderId;
};

export type ReportAssistancePayload = {
  readonly ok: true;
  readonly report_type: string;
  readonly quality: ReportQualityPayload;
  readonly assistance: ReportAssistPayload;
};

export type ReportAssistanceResult = { ok: true; payload: ReportAssistancePayload } | { ok: false; error: string };

const EMPTY_RECORD: Readonly<Record<string, unknown>> = {};

// === ANCHOR: REPORTEMIT_ISRECORD_START ===
function isRecord(value: unknown): value is Readonly<Record<string, unknown>> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
// === ANCHOR: REPORTEMIT_ISRECORD_END ===

// === ANCHOR: REPORTEMIT_STRINGVALUE_START ===
function stringValue(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}
// === ANCHOR: REPORTEMIT_STRINGVALUE_END ===

// === ANCHOR: REPORTEMIT_NUMBERVALUE_START ===
function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
// === ANCHOR: REPORTEMIT_NUMBERVALUE_END ===

// === ANCHOR: REPORTEMIT_STRINGARRAY_START ===
function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string");
}
// === ANCHOR: REPORTEMIT_STRINGARRAY_END ===

// === ANCHOR: REPORTEMIT_RECORDARRAY_START ===
function recordArray(value: unknown): readonly Readonly<Record<string, unknown>>[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isRecord);
}
// === ANCHOR: REPORTEMIT_RECORDARRAY_END ===

// === ANCHOR: REPORTEMIT_PARSEBLOCKKIND_START ===
function parseBlockKind(value: unknown): RModelBlock["kind"] {
  switch (value) {
    case "paragraph":
    case "bullets":
    case "summary":
      return value;
    default:
      return "paragraph";
  }
}
// === ANCHOR: REPORTEMIT_PARSEBLOCKKIND_END ===

// === ANCHOR: REPORTEMIT_PARSERMODELBLOCK_START ===
function parseRModelBlock(value: unknown): RModelBlock {
  const record = isRecord(value) ? value : EMPTY_RECORD;
  return {
    kind: parseBlockKind(record.kind),
    text: stringValue(record.text) ?? "",
    items: stringArray(record.items),
  };
}
// === ANCHOR: REPORTEMIT_PARSERMODELBLOCK_END ===

// === ANCHOR: REPORTEMIT_PARSERMODELSECTION_START ===
function parseRModelSection(value: unknown): RModelSection {
  const record = isRecord(value) ? value : EMPTY_RECORD;
  return {
    heading: stringValue(record.heading) ?? "",
    blocks: Array.isArray(record.blocks) ? record.blocks.map(parseRModelBlock) : [],
  };
}
// === ANCHOR: REPORTEMIT_PARSERMODELSECTION_END ===

// === ANCHOR: REPORTEMIT_PARSERMODEL_START ===
function parseRModel(value: unknown): RModel {
  const record = isRecord(value) ? value : EMPTY_RECORD;
  return {
    title: stringValue(record.title) ?? "",
    report_type: stringValue(record.report_type) ?? "",
    date: stringValue(record.date) ?? "",
    source_plan_path: stringValue(record.source_plan_path) ?? "",
    sections: Array.isArray(record.sections) ? record.sections.map(parseRModelSection) : [],
  };
}
// === ANCHOR: REPORTEMIT_PARSERMODEL_END ===

// === ANCHOR: REPORTEMIT_PARSEGUARDRECORD_START ===
function parseGuardRecord(value: unknown): GuardRecord {
  const record = isRecord(value) ? value : EMPTY_RECORD;
  return {
    section: numberValue(record.section),
    block: numberValue(record.block),
    reason: stringValue(record.reason) ?? "",
    missing: stringArray(record.missing),
  };
}
// === ANCHOR: REPORTEMIT_PARSEGUARDRECORD_END ===

// === ANCHOR: REPORTEMIT_PARSEVAGUEWARNING_START ===
function parseVagueWarning(value: unknown): VagueWarning {
  const record = isRecord(value) ? value : EMPTY_RECORD;
  return {
    section: numberValue(record.section),
    block: numberValue(record.block),
    term: stringValue(record.term) ?? "",
    offset: numberValue(record.offset),
  };
}
// === ANCHOR: REPORTEMIT_PARSEVAGUEWARNING_END ===

// === ANCHOR: REPORTEMIT_PARSEEMITPAYLOAD_START ===
function parseEmitPayload(value: unknown): EmitPayload | null {
  if (!isRecord(value) || value.ok !== true) return null;
  return {
    ok: true,
    report_type: stringValue(value.report_type) ?? "",
    slug: stringValue(value.slug) ?? "",
    key: stringValue(value.key) ?? "",
    base: parseRModel(value.base),
    polished: parseRModel(value.polished),
    guards: recordArray(value.guards).map(parseGuardRecord),
    vague_warnings: recordArray(value.vague_warnings).map(parseVagueWarning),
    quality: parseReportQualityPayload(value.quality),
    assistance: parseReportAssistPayload(value.assistance),
  };
}
// === ANCHOR: REPORTEMIT_PARSEEMITPAYLOAD_END ===

// === ANCHOR: REPORTEMIT_PARSEREPORTASSISTANCERESPONSE_START ===
function parseReportAssistanceResponse(value: unknown): ReportAssistancePayload | null {
  if (!isRecord(value) || value.ok !== true) return null;
  return {
    ok: true,
    report_type: stringValue(value.report_type) ?? "",
    quality: parseReportQualityPayload(value.quality),
    assistance: parseReportAssistPayload(value.assistance),
  };
}
// === ANCHOR: REPORTEMIT_PARSEREPORTASSISTANCERESPONSE_END ===

// === ANCHOR: REPORTEMIT_EMITREPORTMODEL_START ===
export async function emitReportModel(
  cwd: string,
  planPath: string,
  reportType: ReportType,
  polish: boolean,
  author = "",
): Promise<EmitResult> {
  const args = [
    "report", planPath, "--type", reportType, "--emit-model", "--author", author, "--json",
    ...(polish ? ["--polish"] : []),
  ];
  const res = await runVib(args, cwd);
  try {
    const raw: unknown = JSON.parse(res.stdout.trim());
    const payload = parseEmitPayload(raw);
    if (payload === null) {
      const error = isRecord(raw) ? stringValue(raw.error) : null;
      return { ok: false, error: error ?? "모델 생성 실패" };
    }
    return { ok: true, payload };
  } catch {
    return { ok: false, error: res.stderr.trim() || "모델 생성 실패" };
  }
}
// === ANCHOR: REPORTEMIT_EMITREPORTMODEL_END ===

// === ANCHOR: REPORTEMIT_REQUESTREPORTASSISTANCE_START ===
export async function requestReportAssistance(request: ReportAssistanceRequest): Promise<ReportAssistanceResult> {
  const res = await runVib(
    [
      "report",
      request.planPath,
      "--type",
      request.reportType,
      "--assist-missing",
      ...(request.assistProvider !== undefined && request.assistProvider !== "local" ? ["--cli", request.assistProvider] : []),
      "--author",
      request.author ?? "",
      "--json",
    ],
    request.cwd,
  );
  try {
    const raw: unknown = JSON.parse(res.stdout.trim());
    const payload = parseReportAssistanceResponse(raw);
    if (payload === null) {
      const error = isRecord(raw) ? stringValue(raw.error) : null;
      return { ok: false, error: error ?? "보완 제안 생성 실패" };
    }
    return { ok: true, payload };
  } catch {
    return { ok: false, error: res.stderr.trim() || "보완 제안 생성 실패" };
  }
}
// === ANCHOR: REPORTEMIT_REQUESTREPORTASSISTANCE_END ===
// === ANCHOR: REPORTEMIT_END ===
