// === ANCHOR: NAV_GUIDE_START ===
// 강 PD 가이드 레이어 — 초보자 여정(6단계)의 단일 소스. 순수 데이터/함수.
// 근거: plans/2026-06-10-강PD-가이드레이어-design.md
import type { Page, Stage } from "./stages";

export type GuideStep = 1 | 2 | 3 | 4 | 5 | 6;
/** inferStep 반환 범위 — 1️⃣(프로젝트 열기)은 가이드가 뜨는 시점엔 항상 완료라 제외. */
export type ActiveGuideStep = 2 | 3 | 4 | 5 | 6;

export interface JourneyStep {
  step: GuideStep;
  icon: string;
  label: string;
  /** 스트립·카드에 보이는 행동 한 줄 */
  shortAction: string;
  /** 사용법 따라하기 아코디언의 상세 하우투 */
  howto: string[];
  /** "이동 →" 목적지. 1️⃣은 자동 단계라 null. */
  targetPage: Page | null;
  /** 스트립 주행동 버튼 라벨 — 목적지 탭 이름("코드탐색으로 이동")이 아니라 안내문의 행동 동사를
   *  그대로 받는다("지시문 복사하러 가기"). 초보가 내부 탭 이름을 해석할 필요를 없앤다. null=주행동 없음. */
  goLabel: string | null;
  /** 이 단계가 속한 홈 허브 카드. 1️⃣은 카드 밖(null). */
  cardStage: Stage | null;
}

export const JOURNEY_STEPS: JourneyStep[] = [
  {
    step: 1,
    icon: "1️⃣",
    label: "프로젝트 열기",
    shortAction: "폴더를 고르면 준비 끝 — 감시가 자동으로 켜져요",
    howto: [
      "① 첫 화면에서 프로젝트 폴더를 선택해요",
      "② 코드맵과 앵커가 자동으로 준비돼요",
      "③ 감시(watch)가 자동으로 켜져요 — 코드 변경을 지켜보다 위반을 알려줘요 (백업은 아니에요)",
    ],
    targetPage: null,
    goLabel: null,
    cardStage: null,
  },
  {
    step: 2,
    icon: "2️⃣",
    label: "기획하기",
    shortAction: "기획방에서 AI와 대화하며 기획안을 확정하세요",
    howto: [
      "① 기획 탭(기획방)으로 가요",
      "② \"무엇을 만들고 싶은지\" 한 줄로 적어요",
      "③ AI 페르소나들과 대화하며 생각을 다듬어요",
      // 계약 프레임(v6 카피 보강): 기획안은 문서가 아니라 다음 단계 AI 작업의 기준점.
      "④ 기획안이 마음에 들면 확정(저장)해요 — 이 문서가 다음 단계 AI 작업의 약속(목표·범위)이 돼요",
    ],
    targetPage: "planning",
    goLabel: "기획하러 가기 →",
    cardStage: "planning",
  },
  {
    step: 3,
    icon: "3️⃣",
    label: "체크포인트 저장",
    shortAction: "AI에게 시키기 전에 안전 저장 — 망쳐도 되돌아올 수 있게",
    howto: [
      "① 유지보수 → 백업 탭으로 가요",
      "② \"체크포인트 저장\" 버튼을 눌러요",
      "③ 무슨 작업 전인지 설명을 짧게 적으면 끝!",
    ],
    targetPage: "backups",
    goLabel: "체크포인트 저장하러 가기 →",
    cardStage: "maintain",
  },
  {
    step: 4,
    icon: "4️⃣",
    label: "AI에게 작업 시키기",
    // 작업방 Tier 1(plans/2026-06-12-작업방-tier1-design.md §2): 기본 동선은 앱 내 작업방 —
    // 체크포인트→실행→guard 가 자동으로 이어진다. 외부 도구 복사 동선은 폴백으로 유지.
    shortAction: "작업방에서 AI에게 시키세요 — 체크포인트 저장과 검사가 자동으로 따라붙어요",
    howto: [
      "① 개발 → 작업방 탭으로 가요",
      "② 'AI에게 작업 시키기'를 누르면 체크포인트 저장 → AI 실행 → 자동 검사가 한 번에 이어져요",
      "③ 외부 도구(터미널)를 쓰고 싶다면? 코드탐색의 '작업 지시 복사'로 붙여넣어 실행해도 돼요",
      "④ 아직 AI 도구가 없나요? 설정의 'AI 도구 설정'에서 설치를 도와드려요",
    ],
    targetPage: "work",
    goLabel: "작업방에서 시키기 →",
    cardStage: "develop",
  },
  {
    step: 5,
    icon: "5️⃣",
    label: "결과 검증",
    // 사용자 노출 카피에 "guard" 영문 노출 금지 — UI 버튼 라벨('상태 확인')과 동일 어휘 사용 (북극성 점검 #3)
    shortAction: "홈의 '상태 확인'으로 AI가 약속한 범위만 고쳤는지 확인하세요",
    howto: [
      "① 홈으로 가요",
      "② '상태 확인' 버튼을 눌러요 — AI가 약속한 범위만 고쳤는지 검사해줘요",
      "③ 문제가 있으면 진단으로 안내돼요 — 고치는 길을 알려줘요",
      "④ 결과가 마음에 안 들면? 검사 없이 백업 탭에서 '되돌리기'로 3️⃣ 시점으로 돌아가도 돼요",
    ],
    // guard 버튼은 진단 탭에 없고 홈에만 있다(Home.tsx handleRunGuard) — spec §2 정정.
    targetPage: "home",
    goLabel: "상태 확인하러 가기 →",
    cardStage: null,
  },
  {
    step: 6,
    icon: "6️⃣",
    label: "저장 또는 되돌리기",
    shortAction: "잘 됐으면 체크포인트 저장, 망쳤으면 되돌리기",
    howto: [
      "① 결과가 마음에 들면 → 백업에서 체크포인트를 저장해요",
      "② 망쳤으면 → '되돌리기'로 3️⃣ 시점으로 돌아가요 — 없던 일로 만들 수 있어요",
      "③ 다음 작업이 있으면 4️⃣로 돌아가 반복!",
    ],
    targetPage: "backups",
    goLabel: "마무리하러 가기 →",
    cardStage: "maintain",
  },
];

export function journeyStep(step: GuideStep): JourneyStep {
  return JOURNEY_STEPS[step - 1];
}

export interface GuideSignals {
  /** 확정 기획안 존재 (App: planningResult?.outputPath 기준) */
  hasPlanDoc: boolean;
  /** 기획 대화 진행 중(pending 메시지 존재) */
  planningPending: boolean;
  hasCheckpoint: boolean;
  /**
   * 마지막 체크포인트 이후 달라진 파일 수 — git changed-set을 체크포인트 시점
   * baseline과 변경 지문 단위로 비교(countChangesSinceBaseline, v6): 경로 대칭차에 더해
   * 같은 경로의 재수정(지문 변화)도 센다. git HEAD 절대 기준 아님.
   * null = 조회가 예외로 실패한 경우만 → 보수적 생략(spec §4-5).
   * 주의: 비-git 프로젝트는 null이 아니라 0 — git_status가 빈 목록을 반환(에러 아님)해
   * 자동 5️⃣ 전환이 없고, 4️⃣ affordance가 유일한 검증 진입로(spec §3.1).
   */
  changedFileCount: number | null;
  /**
   * 마지막 변경 이후 guard 결과(홈 '상태 확인' 콜백). guard가 검사한 시점의 changed-set
   * 지문과 현재 지문이 달라지면 App이 null로 리셋(spec §3.1, 외부 리뷰 H2) — count 기준이
   * 아니라서 같은 파일 재수정·동수 집합 교체에서도 stale pass가 남지 않는다.
   */
  guardStatus: "ok" | "issue" | null;
}

/** 신호 → 현재 단계 추론. 충돌 시 뒤 단계 우선(spec §4-1). 1️⃣은 반환하지 않음. */
export function inferStep(s: GuideSignals): ActiveGuideStep {
  let step: ActiveGuideStep = !s.hasPlanDoc || s.planningPending ? 2 : !s.hasCheckpoint ? 3 : 4;
  if (s.hasCheckpoint && s.changedFileCount !== null && s.changedFileCount > 0) {
    step = s.guardStatus === "ok" ? 6 : 5;
  }
  return step;
}

export interface GuideOverride {
  step: ActiveGuideStep;
  /** override 기록 시점의 추론값 — 추론이 바뀌면 자동 해제(spec §4-2) */
  baseInferred: ActiveGuideStep;
}

/** 수동 보정 적용: 추론이 기록 시점과 같을 때만 override 유지. */
export function resolveOverride(
  override: GuideOverride | null,
  inferred: ActiveGuideStep,
): ActiveGuideStep {
  if (override && override.baseInferred === inferred) return override.step;
  return inferred;
}

export type CardStepState = "now" | "done" | "upcoming";

/** 홈 허브 카드(3장)가 현재 여정에서 갖는 상태. 기획=[2], 개발=[4], 유지보수=[3,6]. 5️⃣은 홈 행동이라 카드 밖. */
export function cardStepState(stage: Stage, currentStep: ActiveGuideStep): CardStepState {
  const steps = JOURNEY_STEPS.filter((j) => j.cardStage === stage).map((j) => j.step);
  if (steps.includes(currentStep)) return "now";
  if (steps.every((st) => st < currentStep)) return "done";
  return "upcoming";
}

/** 홈 허브 카드 클릭 목적지 — "지금 할 차례" 카드는 현재 단계의 목적지로 보낸다
 *  (예: 3️⃣ 체크포인트 저장에서 유지보수 카드 → 진단이 아니라 백업 탭).
 *  평상시(now 아님)엔 fallback(단계 첫 탭) 그대로. */
export function hubCardTarget(stage: Stage, currentStep: ActiveGuideStep | null, fallback: Page): Page {
  if (currentStep && cardStepState(stage, currentStep) === "now") {
    const target = journeyStep(currentStep).targetPage;
    if (target) return target;
  }
  return fallback;
}

// ── 신호 배선 보조 (App.tsx가 사용, 순수) ──────────────────────────────────

/** backupList 결과에서 최신 체크포인트 id. 응답 정렬 순서를 가정하지 않는다. */
export function latestCheckpointId(
  backups: Array<{ id: string; createdAt?: string }>,
): string | null {
  if (backups.length === 0) return null;
  return [...backups].sort((a, b) => (b.createdAt ?? "").localeCompare(a.createdAt ?? ""))[0].id;
}

/**
 * 변경 entry 하나의 최소 구조 — `lib/vib`의 `ChangedEntry`와 구조적 호환(직접 import하지 않아
 * 이 모듈의 순수성 유지). mtime_ms+size가 같으면 같은 내용으로 간주하는 **근사 지문**(spec §4-9):
 * 동일 ms·동일 크기 재작성은 미감지(4️⃣ affordance가 안전망), touch 오탐은 5️⃣(재검증) 방향이라 안전.
 */
export interface GuideChangedEntry {
  path: string;
  status: string;
  mtime_ms: number;
  size: number;
}

/** 변경 entry 하나의 지문 — 경로+상태+mtime+size (외부 리뷰 H1·H2의 공통 기준 단위).
 *  구분자는 경로에 못 들어가는 제어문자 — 공백 포함 경로의 결합 모호성 방지. */
export function entryFingerprint(e: GuideChangedEntry): string {
  return `${e.path}\u0000${e.status}\u0000${e.mtime_ms}\u0000${e.size}`;
}

/** changed-set 전체의 지문 — 정렬 후 결합(순서 무관). guard 리셋 비교의 단일 기준(spec §3.1). */
export function changedSetFingerprint(entries: GuideChangedEntry[]): string {
  return entries.map(entryFingerprint).sort().join("\u0001");
}

/**
 * 체크포인트 시점 baseline과 현재 changed-set의 달라진 파일 수 — 경로 대칭차에 더해,
 * **같은 경로라도 지문이 다르면 변경으로 센다**(외부 리뷰 H1: 체크포인트 시점에 이미 dirty였던
 * 파일을 AI가 재수정하는 케이스 — 커밋 안 하는 초보자에겐 2사이클차부터의 일상).
 */
export function countChangesSinceBaseline(
  baseline: GuideChangedEntry[],
  current: GuideChangedEntry[],
): number {
  const b = new Map(baseline.map((e) => [e.path, entryFingerprint(e)]));
  const c = new Map(current.map((e) => [e.path, entryFingerprint(e)]));
  let n = 0;
  for (const [p, fp] of c) if (b.get(p) !== fp) n += 1; // 신규 경로 또는 재수정(지문 변화)
  for (const p of b.keys()) if (!c.has(p)) n += 1; // baseline에만 있던 변경이 사라짐
  return n;
}

const GUIDE_IGNORED_PREFIXES = [".vibelign/", ".omc/", ".git/", "plans/", "vibelign_exports/"];

/** 도구 메타데이터·기획 산출물 경로 제외 — guard 리포트·체크포인트 메타 churn은 물론, 기획안 저장
 *  (plans/*.md)·규칙 내보내기(vibelign_exports/)를 "AI가 코드를 고침"(4️⃣→5️⃣ 신호)으로 오인하지 않게.
 *  .DS_Store는 어느 폴더에나 생기는 OS 메타라 prefix가 아니라 파일명으로 거른다. */
export function guideRelevantEntries<T extends { path: string }>(entries: T[]): T[] {
  return entries.filter(
    (e) =>
      !GUIDE_IGNORED_PREFIXES.some((pre) => e.path.startsWith(pre)) &&
      !e.path.endsWith(".DS_Store"),
  );
}

/** vib start가 자동 생성하는 초기 체크포인트의 note 마커 — CLI(hook_setup.py)가 중복 방지 검사에
 *  쓰는 문자열과 동일해야 한다. */
const AUTO_INIT_BACKUP_MARKER = "vib start 초기 저장";

export function isAutoInitBackup(note: string | undefined): boolean {
  return (note ?? "").includes(AUTO_INIT_BACKUP_MARKER);
}

/** 가이드 3️⃣(AI 작업 전 수동 체크포인트) 신호 — vib start 자동 초기 저장은 사용자가 만든 안전
 *  저장이 아니므로 제외한다. 이걸 세면 프로젝트를 열기만 해도 3️⃣이 완료 처리되고, 기획안 파일
 *  생성과 결합해 개발(4️⃣)까지 "완료"로 건너뛰는 오표시가 난다. */
export function hasManualCheckpoint(backups: Array<{ note?: string }>): boolean {
  return backups.some((b) => !isAutoInitBackup(b.note));
}

/** 가이드 ON/OFF — 전역 1개 (숙련도는 프로젝트와 무관, spec §4) */
export const GUIDE_ENABLED_KEY = "vibelign.guide.enabled";

/** 수동 보정 — 프로젝트 경로별 (진행 위치가 프로젝트 간 새면 안 됨, spec §4) */
export function guideOverrideKey(projectDir: string): string {
  return `vibelign.guide.override.${projectDir}`;
}

/** 변경 감지 기준점 — 프로젝트 경로별. { checkpointId, entries[] } JSON (spec §3.1, v6 지문 entry) */
export function guideBaselineKey(projectDir: string): string {
  return `vibelign.guide.baseline.${projectDir}`;
}

/** 첫 사이클 완주 축하 1회성 플래그 — 프로젝트 경로별 (spec §3.2) */
export function guideCelebratedKey(projectDir: string): string {
  return `vibelign.guide.celebrated.${projectDir}`;
}

/**
 * 첫 사이클 완주 축하 발화 조건(spec §3.2) — 6️⃣→4️⃣ 전환(저장으로 루프가 닫힌 순간)에
 * 프로젝트당 1회. 앱 시작 직후(prev=null)·신호 로딩 전엔 발화 금지(오발 방지).
 */
export function shouldCelebrate(
  prev: ActiveGuideStep | null,
  next: ActiveGuideStep | null,
  alreadyCelebrated: boolean,
): boolean {
  return prev === 6 && next === 4 && !alreadyCelebrated;
}

/** guideBaselineKey 값의 형태 — entry 지문 목록(v6). 경로 목록이 아니라서 재수정도 감지된다. */
export interface GuideBaseline {
  checkpointId: string;
  entries: GuideChangedEntry[];
}
// === ANCHOR: NAV_GUIDE_END ===
