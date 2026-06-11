// === ANCHOR: SCOPE_REPORT_START ===
// 작업 계약 scope vs 실제 changed-set 비교 — 판정이 아니라 리포트(spec §6 불개입 원칙).
import type { ContractScopeEntry } from "../vib/types";

export interface ScopeReportResult {
  inScope: number;
  outOfScope: string[];
}

// 가이드 v6 guideRelevantEntries와 같은 목록 — 미구현 모듈 의존 금지로 자체 보유(spec §6).
const META_PREFIXES = [".vibelign/", ".omc/", ".git/"];

/**
 * scope가 비거나 실질 변경이 0건이면 null(리포트 성립 불가 — 표시하지 않는다).
 * "약속 범위 안 0건"은 성공처럼 읽히는 무정보이고, 비-git(항상 빈 changed-set)도
 * 이 규칙으로 자연 미노출된다(spec §6·§7-1, 외부 리뷰 M2).
 * 매칭: kind "file" = 완전일치, kind "dir" = prefix(검증 단계에서 끝 '/' 보장됨 — 유사 prefix 오탐 없음).
 */
export function scopeReport(
  scope: ContractScopeEntry[],
  changedPaths: string[],
): ScopeReportResult | null {
  if (scope.length === 0) return null;
  const relevant = changedPaths.filter(
    (path) => !META_PREFIXES.some((prefix) => path.startsWith(prefix)),
  );
  if (relevant.length === 0) return null;
  const inScopeOf = (path: string): boolean =>
    scope.some((entry) =>
      entry.kind === "file" ? entry.path === path : path.startsWith(entry.path),
    );
  const outOfScope = relevant.filter((path) => !inScopeOf(path));
  return { inScope: relevant.length - outOfScope.length, outOfScope };
}
// === ANCHOR: SCOPE_REPORT_END ===
