import { describe, it, expect } from "vitest";
import {
  JOURNEY_STEPS,
  journeyStep,
  inferStep,
  resolveOverride,
  cardStepState,
  guideOverrideKey,
  guideBaselineKey,
  guideCelebratedKey,
  latestCheckpointId,
  changedSetFingerprint,
  countChangesSinceBaseline,
  guideRelevantEntries,
  shouldCelebrate,
  type GuideChangedEntry,
  type GuideSignals,
} from "./guide";

const base: GuideSignals = {
  hasPlanDoc: false,
  planningPending: false,
  hasCheckpoint: false,
  changedFileCount: null,
  guardStatus: null,
};

/** 테스트용 변경 entry — 기본 지문(mtime_ms=1, size=10) */
const ent = (path: string, mtime_ms = 1, size = 10): GuideChangedEntry => ({
  path,
  status: "modified",
  mtime_ms,
  size,
});

describe("JOURNEY_STEPS", () => {
  it("6단계가 순서대로", () => {
    expect(JOURNEY_STEPS.map((j) => j.step)).toEqual([1, 2, 3, 4, 5, 6]);
  });
  it("journeyStep은 step 번호로 조회", () => {
    expect(journeyStep(3).label).toBe("체크포인트 저장");
    expect(journeyStep(4).targetPage).toBe("code");
  });
  it("5️⃣ 목적지는 홈 — guard 버튼은 진단 탭에 없음 (spec §2 정정)", () => {
    expect(journeyStep(5).targetPage).toBe("home");
  });
  it("1️⃣은 자동 단계 — 이동 목적지 없음", () => {
    expect(journeyStep(1).targetPage).toBeNull();
    expect(journeyStep(1).cardStage).toBeNull();
  });
});

describe("inferStep", () => {
  it("기획안 없으면 2", () => {
    expect(inferStep(base)).toBe(2);
  });
  it("기획 진행 중이면 기획안 있어도 2", () => {
    expect(inferStep({ ...base, hasPlanDoc: true, planningPending: true })).toBe(2);
  });
  it("기획안 있고 체크포인트 없으면 3", () => {
    expect(inferStep({ ...base, hasPlanDoc: true })).toBe(3);
  });
  it("기획안+체크포인트, 추가 신호 없으면 4", () => {
    expect(inferStep({ ...base, hasPlanDoc: true, hasCheckpoint: true })).toBe(4);
  });
  it("변경 감지되면 5 (뒤 단계 우선 — spec §4-1)", () => {
    expect(inferStep({ ...base, hasPlanDoc: true, hasCheckpoint: true, changedFileCount: 3 })).toBe(5);
  });
  it("변경 + guard 통과면 6", () => {
    expect(
      inferStep({ ...base, hasPlanDoc: true, hasCheckpoint: true, changedFileCount: 3, guardStatus: "ok" }),
    ).toBe(6);
  });
  it("체크포인트 없으면 변경 감지돼도 5로 점프하지 않음", () => {
    expect(inferStep({ ...base, hasPlanDoc: true, changedFileCount: 3 })).toBe(3);
  });
  it("신호 사용 불가(null=조회 예외)는 보수적 생략 — 4 유지 (spec §4-5)", () => {
    expect(
      inferStep({ ...base, hasPlanDoc: true, hasCheckpoint: true, changedFileCount: null, guardStatus: null }),
    ).toBe(4);
  });
  it("변경 0도 4 유지 — 비-git 프로젝트는 항상 이 값(null 아님, spec §3.1)", () => {
    expect(
      inferStep({ ...base, hasPlanDoc: true, hasCheckpoint: true, changedFileCount: 0, guardStatus: null }),
    ).toBe(4);
  });
});

describe("resolveOverride", () => {
  it("override 없으면 추론값", () => {
    expect(resolveOverride(null, 3)).toBe(3);
  });
  it("추론이 기록 시점과 같으면 override 유지", () => {
    expect(resolveOverride({ step: 5, baseInferred: 3 }, 3)).toBe(5);
  });
  it("추론이 바뀌면 override 자동 해제 (spec §4-2)", () => {
    expect(resolveOverride({ step: 5, baseInferred: 3 }, 4)).toBe(4);
  });
});

describe("cardStepState", () => {
  it("현재 단계가 속한 카드는 now", () => {
    expect(cardStepState("planning", 2)).toBe("now");
    expect(cardStepState("maintain", 3)).toBe("now");
    expect(cardStepState("develop", 4)).toBe("now");
    expect(cardStepState("maintain", 6)).toBe("now");
  });
  it("5️⃣은 홈에서 하는 행동이라 카드 밖 — 어느 카드도 now가 아님", () => {
    expect(cardStepState("planning", 5)).toBe("done");
    expect(cardStepState("develop", 5)).toBe("done");
    expect(cardStepState("maintain", 5)).toBe("upcoming"); // 6️⃣이 남아 있음
  });
  it("카드의 모든 단계가 지났으면 done", () => {
    expect(cardStepState("planning", 3)).toBe("done");
  });
  it("남은 단계가 있으면 upcoming (유지보수 카드=3·6이라 4에서도 upcoming)", () => {
    expect(cardStepState("develop", 3)).toBe("upcoming");
    expect(cardStepState("maintain", 4)).toBe("upcoming");
  });
});

describe("guideOverrideKey / guideBaselineKey", () => {
  it("프로젝트 경로별로 다른 키 (spec §4 진행 분리)", () => {
    expect(guideOverrideKey("/a")).not.toBe(guideOverrideKey("/b"));
    expect(guideBaselineKey("/a")).not.toBe(guideBaselineKey("/b"));
    expect(guideOverrideKey("/a")).not.toBe(guideBaselineKey("/a"));
  });
});

describe("latestCheckpointId", () => {
  it("createdAt 내림차순 최신 — backupList 정렬 순서를 가정하지 않음", () => {
    expect(
      latestCheckpointId([
        { id: "old", createdAt: "2026-06-01T10:00:00Z" },
        { id: "new", createdAt: "2026-06-10T10:00:00Z" },
      ]),
    ).toBe("new");
  });
  it("빈 목록이면 null, createdAt 없는 항목은 뒤로", () => {
    expect(latestCheckpointId([])).toBeNull();
    expect(
      latestCheckpointId([{ id: "noDate" }, { id: "dated", createdAt: "2026-06-10T10:00:00Z" }]),
    ).toBe("dated");
  });
});

describe("countChangesSinceBaseline", () => {
  it("경로 대칭차 — 추가·사라짐 모두 변경으로 센다", () => {
    expect(countChangesSinceBaseline([ent("a.ts")], [ent("a.ts")])).toBe(0);
    expect(countChangesSinceBaseline([ent("a.ts")], [ent("a.ts"), ent("b.ts")])).toBe(1); // AI가 b.ts 변경
    expect(countChangesSinceBaseline([ent("a.ts")], [])).toBe(1); // baseline에 있던 변경이 사라짐 = 체크포인트 시점과 달라진 것
    expect(countChangesSinceBaseline([], [ent("x.ts"), ent("y.ts")])).toBe(2);
  });
  it("같은 경로라도 지문(mtime/size)이 다르면 변경 — 이미 dirty였던 파일의 재수정 감지 (외부 리뷰 H1)", () => {
    expect(countChangesSinceBaseline([ent("a.ts", 1, 10)], [ent("a.ts", 2, 10)])).toBe(1); // mtime 변화
    expect(countChangesSinceBaseline([ent("a.ts", 1, 10)], [ent("a.ts", 1, 11)])).toBe(1); // size 변화
  });
  it("undo로 체크포인트 시점과 동일해지면 0 (baseline 자체가 그 시점 changed-set)", () => {
    expect(countChangesSinceBaseline([ent("a.ts"), ent("b.ts")], [ent("b.ts"), ent("a.ts")])).toBe(0); // 순서 무관
  });
});

describe("changedSetFingerprint", () => {
  it("순서 무관 — 동일 집합은 같은 지문", () => {
    expect(changedSetFingerprint([ent("a.ts"), ent("b.ts")])).toBe(
      changedSetFingerprint([ent("b.ts"), ent("a.ts")]),
    );
  });
  it("내용 변화(mtime)·동수 집합 교체는 다른 지문 — guard stale pass 차단 기준 (외부 리뷰 H2)", () => {
    expect(changedSetFingerprint([ent("a.ts", 1)])).not.toBe(changedSetFingerprint([ent("a.ts", 2)]));
    // 변경 '수'는 같아도(2개) 집합이 다르면 지문이 다르다 — count 기준의 사각지대
    expect(changedSetFingerprint([ent("a.ts"), ent("b.ts")])).not.toBe(
      changedSetFingerprint([ent("c.ts"), ent("d.ts")]),
    );
  });
});

describe("guideRelevantEntries", () => {
  it("vibelign/omc/git 메타데이터 경로 제외 — guard 리포트·체크포인트 churn 오인 방지", () => {
    expect(
      guideRelevantEntries([
        ent(".vibelign/report.md"),
        ent(".omc/state/x.json"),
        ent(".git/HEAD"),
        ent("src/app.ts"),
      ]).map((e) => e.path),
    ).toEqual(["src/app.ts"]);
  });
});

describe("shouldCelebrate", () => {
  it("6→4 전환(저장으로 루프 닫힘) + 미축하일 때만 true", () => {
    expect(shouldCelebrate(6, 4, false)).toBe(true);
    expect(shouldCelebrate(6, 4, true)).toBe(false); // 프로젝트당 1회
    expect(shouldCelebrate(5, 4, false)).toBe(false);
    expect(shouldCelebrate(6, 5, false)).toBe(false);
  });
  it("앱 시작 직후(prev=null)·신호 로딩 전(next=null)엔 발화 금지", () => {
    expect(shouldCelebrate(null, 4, false)).toBe(false);
    expect(shouldCelebrate(6, null, false)).toBe(false);
  });
  it("guideCelebratedKey는 프로젝트 경로별", () => {
    expect(guideCelebratedKey("/a")).not.toBe(guideCelebratedKey("/b"));
  });
});
