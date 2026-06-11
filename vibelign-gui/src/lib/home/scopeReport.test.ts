import { describe, expect, it } from "vitest";

import { scopeReport } from "./scopeReport";
import type { ContractScopeEntry } from "../vib/types";

const SCOPE: ContractScopeEntry[] = [
  { path: "src/pages/Home.tsx", kind: "file", reason: "" },
  { path: "src/components/nav/", kind: "dir", reason: "" },
];

describe("scopeReport", () => {
  it("파일은 완전일치, 디렉터리는 prefix로 안/밖을 가른다", () => {
    const report = scopeReport(SCOPE, [
      "src/pages/Home.tsx",            // 안 (file 일치)
      "src/components/nav/Guide.tsx",  // 안 (dir prefix)
      "src/pages/Settings.tsx",        // 밖
    ]);
    expect(report.inScope).toBe(2);
    expect(report.outOfScope).toEqual(["src/pages/Settings.tsx"]);
  });

  it("도구 메타데이터 경로만 있으면 null — 실질 변경 0건 (.vibelign/.omc/.git 제외)", () => {
    expect(scopeReport(SCOPE, [".vibelign/report.md", ".omc/state.json", ".git/HEAD"])).toBeNull();
  });

  it("scope가 비면 null — 리포트 자체가 성립 안 함 (spec §7-2)", () => {
    expect(scopeReport([], ["src/a.ts"])).toBeNull();
  });

  it("변경이 없으면 null — '범위 안 0건'은 성공처럼 읽히는 무정보. 비-git(항상 빈 목록)도 이 규칙으로 미노출 (spec §6·§7-1, 외부 리뷰 M2)", () => {
    expect(scopeReport(SCOPE, [])).toBeNull();
  });

  it("dir 경로는 끝 '/' 보장돼 들어오지만, 유사 prefix 오탐은 없어야 한다", () => {
    // "src/components/nav/"가 "src/components/navbar.tsx"에 매칭되면 안 됨
    const report = scopeReport(SCOPE, ["src/components/navbar.tsx"]);
    expect(report?.outOfScope).toEqual(["src/components/navbar.tsx"]);
  });
});
