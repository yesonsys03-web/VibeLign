import { runVib } from "./core";
import { loadDoc } from "../docs";

export type ReportType = "work" | "proposal" | "result";

export type ReportResult =
  | { ok: true; path: string; reportType: string; html: string }
  | { ok: false; error: string };

/** 절대 보고서 경로를 프로젝트 루트 기준 상대경로로 변환한다.
 *  read_file(loadDoc) 가 root-상대 경로를 기대하기 때문. 루트 밖이면 원본 유지. */
export function toProjectRelative(cwd: string, absPath: string): string {
  const norm = (p: string) => p.replace(/\\/g, "/").replace(/\/+$/, "");
  const root = norm(cwd);
  const p = norm(absPath);
  if (p === root) return "";
  if (p.startsWith(root + "/")) return p.slice(root.length + 1);
  return absPath;
}

export async function generatePlanningReport(
  cwd: string,
  planPath: string,
  reportType: ReportType,
): Promise<ReportResult> {
  const res = await runVib(
    ["report", planPath, "--type", reportType, "--format", "html", "--json"],
    cwd,
  );

  let parsed: { ok?: boolean; path?: string; report_type?: string; error?: string };
  try {
    parsed = JSON.parse(res.stdout.trim());
  } catch {
    return {
      ok: false,
      error: res.stderr.trim() || res.stdout.trim() || "보고서 생성에 실패했어요.",
    };
  }

  if (!parsed.ok || !parsed.path) {
    return { ok: false, error: String(parsed.error ?? "보고서 생성에 실패했어요.") };
  }

  const rel = toProjectRelative(cwd, parsed.path);
  try {
    const doc = await loadDoc(cwd, rel);
    return {
      ok: true,
      path: parsed.path,
      reportType: String(parsed.report_type ?? reportType),
      html: doc.content,
    };
  } catch (e) {
    // CLI 는 성공했지만 생성된 파일 읽기가 실패(권한/삭제/락) → 모달이 멈추지 않도록
    // 래퍼의 {ok:false} 계약을 유지한다.
    return { ok: false, error: `보고서 파일을 읽지 못했어요: ${String(e)}` };
  }
}
