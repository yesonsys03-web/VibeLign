import type { DocsHtmlReadResult, DocsVisualReadResult, ReadFileResult } from "../../lib/vib";

export type DocsTrustState = "source-only" | "enhanced-synced" | "enhanced-stale" | "enhanced-failed";
export type CanvasStatus = "not_generated" | "ready" | "stale" | "generating" | "failed" | "unsupported";

export interface CanvasTrustResult {
  status: Exclude<CanvasStatus, "generating" | "failed">;
  trustState: DocsTrustState;
  reason: string;
}

function normalizePath(path: string): string {
  return path.replaceAll("\\", "/").replace(/\/+$/, "");
}

function sourcePathMatchesArtifact(artifactSourcePath: string, relativePath: string): boolean {
  const artifactPath = normalizePath(artifactSourcePath);
  const rel = normalizePath(relativePath).replace(/^\/+/, "");
  return artifactPath === rel || artifactPath.endsWith(`/${rel}`);
}

export function evaluateCanvasArtifactTrust(
  visual: DocsVisualReadResult | DocsHtmlReadResult | null,
  doc: ReadFileResult | null,
): CanvasTrustResult {
  if (!visual || !doc) {
    return {
      status: "not_generated",
      trustState: "source-only",
      reason: "Canvas artifact가 아직 없어 원문 문서만 표시합니다.",
    };
  }

  const { artifact, contract } = visual;
  if (artifact.schema_version > contract.schema_version) {
    return {
      status: "unsupported",
      trustState: "enhanced-stale",
      reason: `앱보다 새로운 Canvas schema_version입니다: artifact ${artifact.schema_version} / app ${contract.schema_version}`,
    };
  }
  if (artifact.schema_version !== contract.schema_version) {
    return {
      status: "stale",
      trustState: "enhanced-stale",
      reason: `schema_version 불일치: artifact ${artifact.schema_version} / contract ${contract.schema_version}`,
    };
  }
  if (artifact.generator_version !== contract.generator_version) {
    return {
      status: "stale",
      trustState: "enhanced-stale",
      reason: `generator_version 불일치: artifact ${artifact.generator_version} / contract ${contract.generator_version}`,
    };
  }
  if (artifact.source_hash !== doc.source_hash) {
    return {
      status: "stale",
      trustState: "enhanced-stale",
      reason: "원문 source_hash와 Canvas artifact hash가 달라 STALE 상태입니다.",
    };
  }
  if (!sourcePathMatchesArtifact(artifact.source_path, visual.path)) {
    return {
      status: "stale",
      trustState: "enhanced-stale",
      reason: "Canvas artifact source_path가 현재 문서 경로와 달라 신뢰하지 않습니다.",
    };
  }

  return {
    status: "ready",
    trustState: "enhanced-synced",
    reason: "source_path, source_hash, schema_version, generator_version 검증을 통과했습니다.",
  };
}
