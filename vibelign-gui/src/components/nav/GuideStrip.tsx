// === ANCHOR: GUIDE_STRIP_START ===
import { useState } from "react";
import { journeyStep, type ActiveGuideStep } from "../../lib/nav/guide";
import { PAGE_LABELS, type Page } from "../../lib/nav/stages";

interface GuideStripProps {
  enabled: boolean;
  /** null = 신호 로딩 전 — 가이드 부분 미렌더(spec §4-4) */
  step: ActiveGuideStep | null;
  /** 현재 탭 — 이미 단계 목적지에 있으면 "~으로 이동 →" 버튼을 숨긴다. */
  currentPage?: Page | null;
  hasCheckpoint: boolean;
  planningPending: boolean;
  /** AI 도구 0개 "확정 탐지" 시에만 true — 탐지 실패·미완은 false(분기 미노출, spec §3.2) */
  aiToolMissing?: boolean;
  /** 첫 사이클 완주 축하 표시 중 — App이 6️⃣→4️⃣ 전환에서 1회 켠다(spec §3.2) */
  celebrating?: boolean;
  onNavigate: (page: Page) => void;
  onStepChange: (next: ActiveGuideStep) => void;
  onDisable: () => void;
  /** 도구 미보유 분기의 "설치 도움받기" 목적지 — 설정('AI 도구 설정') */
  onOpenSettings?: () => void;
  onCelebrateDismiss?: () => void;
}

// 접힘 존의 정사각 아이콘 버튼(‹ › ×) — 크기·간격 통일이 정돈의 핵심.
const iconBtnStyle = {
  fontSize: 14,
  width: 26,
  height: 26,
  padding: 0,
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  color: "#4A4A4A",
  borderRight: "none",
};

// 의미 그룹(정보 | 비상구 | 컨트롤) 사이 세로 구분선.
const dividerStyle = { width: 1, height: 14, background: "rgba(0, 0, 0, 0.25)" };

// 접힘 선호는 전역 UI 설정(프로젝트 무관) — 한 번 접으면 계속 접힌 채 유지(답답함 해소).
const GUIDE_COLLAPSED_KEY = "vibelign:guide-collapsed";
function readCollapsed(): boolean {
  try {
    const v = localStorage.getItem(GUIDE_COLLAPSED_KEY);
    return v === null ? true : v === "1"; // 기본은 컴팩트(한 줄) — 저장된 선호가 있으면 따른다
  } catch {
    return true;
  }
}
function writeCollapsed(v: boolean) {
  try {
    localStorage.setItem(GUIDE_COLLAPSED_KEY, v ? "1" : "0");
  } catch {
    /* localStorage 불가 환경 — 세션 내 상태만 유지 */
  }
}

/**
 * 탭바 아래 안내 줄 — 좌측 가이드(지금 할 일) + 우측 기존 상태 신호. A안 상태 스트립을 대체·통합.
 * 시인성(spec §3.2): 가이드 활성 시 15px·진한 웜 그레이 배경(#CFCABB)에 #7C2D12 강조, off 시 얇은 줄(3px·13px).
 * 배경을 다크가 아닌 라이트 톤으로 두는 이유 — 앱 전체가 크림(#FEFBF0) 테마라 블랙 스트립은 이질적 섬이 된다.
 * 작업 탭 안에서 초보자에게 보이는 유일한 안내 표면이라 두 탭바 아래에서 묻히면 안 된다.
 */
export function GuideStrip({
  enabled,
  step,
  currentPage = null,
  hasCheckpoint,
  planningPending,
  aiToolMissing = false,
  celebrating = false,
  onNavigate,
  onStepChange,
  onDisable,
  onOpenSettings,
  onCelebrateDismiss,
}: GuideStripProps) {
  const def = enabled && step ? journeyStep(step) : null;
  // 점진적 노출 게이트 — 한 시점에 행동 버튼 하나만. 목적지 탭 밖에선 "~하러 가기"만,
  // 도착하면 그게 사라지고 후속 버튼("다 했어요" 등)이 나타난다. "복사 완료" 같은 행위
  // 신호가 아니라 탭 위치 기준인 이유: 행위 감지는 놓치면 다음 버튼이 영영 안 떠서 갇히지만,
  // 탭 이동은 항상 가능해 갇힘이 구조적으로 불가능하다.
  const onTarget = def?.targetPage != null && def.targetPage === currentPage;
  // 유틸리티(되돌리기·‹ › ×·상태 신호) 접힘 — 기본 화면을 "안내문 + 행동 버튼 1개"로 유지.
  // 비상구(되돌리기)가 접힘 뒤로 숨는 트레이드오프는 토글 라벨("문제 있나요?")이 길 안내를 대신한다.
  const [utilOpen, setUtilOpen] = useState(false);
  // 접힘(컴팩트 한 줄) 토글 — 기본 컴팩트, ▾자세히로 펼침. 답답함 해소(2026-06-12 사용자 요청).
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const toggleCollapsed = () =>
    setCollapsed((v) => {
      writeCollapsed(!v);
      return !v;
    });
  if (celebrating) {
    // 첫 사이클 완주 축하(spec §3.2) — 이 순간만큼은 가이드 줄 대신 완료 마디를 보여준다.
    return (
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 12,
          padding: "10px 14px",
          fontSize: 15,
          color: "#166534",
          background: "#E8F6EC",
          borderBottom: "2px solid #1A1A1A",
        }}
      >
        <span>
          🎉 <b>첫 사이클 완주!</b> 기획부터 저장까지 해냈어요 — 이 흐름 그대로 반복하면 돼요
        </span>
        <button
          className="nav-tab"
          style={{ fontSize: 14, padding: "5px 10px", color: "#4A4A4A", borderRight: "none" }}
          onClick={() => onCelebrateDismiss?.()}
        >
          ×
        </button>
      </div>
    );
  }
  if (def && step && collapsed) {
    // 컴팩트(기본) — 한 줄: 단계 라벨 + 주행동 버튼 + ▾자세히. 안내 기능은 유지하되 높이를 줄인다.
    return (
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 10,
          padding: "6px 14px",
          fontSize: 14,
          background: "#CFCABB",
          borderBottom: "2px solid #1A1A1A",
        }}
      >
        <span style={{ color: "#7C2D12", fontWeight: 700 }}>
          🧭 {def.icon} {def.label}
        </span>
        {def.targetPage && !onTarget && (
          <button
            className="nav-tab"
            style={{ fontSize: 13, padding: "4px 10px", background: "#FBBF24", color: "#1A1A1A", border: "1px solid #1A1A1A", borderRadius: 4 }}
            onClick={() => onNavigate(def.targetPage as Page)}
          >
            {def.goLabel ?? `${PAGE_LABELS[def.targetPage]}으로 이동 →`}
          </button>
        )}
        <div style={{ flex: 1 }} />
        <button
          className="nav-tab"
          style={{ fontSize: 13, padding: "4px 10px", color: "#4A4A4A", borderRight: "none" }}
          title="안내 자세히 보기"
          aria-expanded={false}
          onClick={toggleCollapsed}
        >
          ▾ 자세히
        </button>
      </div>
    );
  }
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: 16,
        padding: def ? "10px 14px" : "3px 12px",
        fontSize: 13,
        color: "#555",
        background: def ? "#CFCABB" : "var(--gray)",
        borderBottom: "2px solid #1A1A1A",
      }}
    >
      {def && step && (
        // 고정 2단 구조 — ①텍스트 행(자연 개행) ②버튼 행. 확대·창 폭에 따라 버튼이 텍스트
        // 옆/아래로 오가며 배치가 출렁이지 않도록 column으로 고정. 버튼 행만 좁을 때 보조적 wrap.
        <span style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 8, fontSize: 15, minWidth: 0, flex: "1 1 auto" }}>
          {/* 머리말(오버라인) 행 — 단계 제목과 분리해 "라벨 → 내용 → 행동" 3단 고정 위계 */}
          <span style={{ color: "#555", fontSize: 13, fontWeight: 700, letterSpacing: "0.04em" }}>🧭 지금 할 일:</span>
          <span style={{ color: "#1A1A1A", lineHeight: 1.6 }}>
            <span style={{ color: "#7C2D12", fontWeight: 700 }}>
              {def.icon} {def.label}
            </span>{" "}
            — {def.shortAction}
          </span>
          <span style={{ display: "flex", flexWrap: "wrap", alignItems: "center", columnGap: 10, rowGap: 8 }}>
            {def.targetPage && !onTarget && (
              <button
                // 가이드의 주행동 버튼 — 앰버 채움 + 검정 텍스트("지금 할 차례" 배지와 같은 톤)로 최상위 강조.
                className="nav-tab"
                style={{ fontSize: 14, padding: "5px 12px", background: "#FBBF24", color: "#1A1A1A", border: "1px solid #1A1A1A", borderRadius: 4 }}
                onClick={() => onNavigate(def.targetPage as Page)}
              >
                {def.goLabel ?? `${PAGE_LABELS[def.targetPage]}으로 이동 →`}
              </button>
            )}
            {/* 수동 출구는 외부 도구 폴백(코드탐색에서 복사) 전용 — 작업방 경유는 종료 감지가
                자동으로 검사·전환하므로 이 버튼이 필요 없다(작업방 기획안 §2). */}
            {step === 4 && currentPage === "code" && (
              <button
                className="nav-tab"
                style={{ fontSize: 14, padding: "5px 12px", color: "#7C2D12", background: "transparent", border: "1px solid #7C2D12", borderRadius: 4 }}
                title="AI 작업이 끝났어도, 중간에 멈췄어도 눌러요 — 확인 단계로 가요"
                onClick={() => {
                  // 외부 AI 작업 종료는 신호로 100% 감지 불가, 비-git 프로젝트는 변경이 항상
                  // 0으로 읽혀 자동 전환이 아예 없음 → 수동 출구(spec §3.2 affordance).
                  // 라벨은 상태 선언("다 했어요")으로 짧게 — 중도 중단 포용("멈췄어도")은 툴팁이 담당.
                  // override 후 5️⃣ 목적지로 이동.
                  onStepChange(5);
                  const verify = journeyStep(5);
                  if (verify.targetPage) onNavigate(verify.targetPage as Page);
                }}
              >
                ✓ 다 했어요 — 결과 확인
              </button>
            )}
            {/* 도구 미보유 분기도 폴백 동선에서만 — 작업방 화면은 자체 설치 안내 버튼을 가진다. */}
            {step === 4 && currentPage === "code" && aiToolMissing && onOpenSettings && (
              <button
                className="nav-tab"
                style={{ fontSize: 14, padding: "5px 12px", color: "#7C2D12", background: "transparent", border: "1px solid #7C2D12", borderRadius: 4 }}
                title="설정의 'AI 도구 설정'에서 설치를 도와드려요"
                onClick={onOpenSettings}
              >
                {/* 도구 미보유 입문자 분기(spec §3.2) — 4️⃣는 앱 밖으로 나가는 유일한 지점이라 최대 이탈 절벽 */}
                AI 도구가 없어요 — 설치 도움받기
              </button>
            )}
            <button
              className="nav-tab"
              style={{ fontSize: 13, padding: "5px 10px", color: "#4A4A4A", borderRight: "none" }}
              title="되돌리기·단계 이동·가이드 끄기·백업 상태"
              aria-expanded={utilOpen}
              onClick={() => setUtilOpen((v) => !v)}
            >
              {utilOpen ? "접기 ▴" : "문제 있나요? ▾"}
            </button>
            <button
              className="nav-tab"
              style={{ fontSize: 13, padding: "5px 10px", color: "#4A4A4A", borderRight: "none" }}
              title="가이드를 한 줄로 접기"
              onClick={toggleCollapsed}
            >
              ▴ 한 줄로
            </button>
          </span>
        </span>
      )}
      <div style={{ flex: 1 }} />
      {!def && (
        <>
          {planningPending && <span style={{ color: "#7C2D12", whiteSpace: "nowrap" }}>● 기획 진행 중</span>}
          <span style={{ color: hasCheckpoint ? "#333" : "#666", whiteSpace: "nowrap" }}>
            {hasCheckpoint ? "✓ 백업 데이터 있음" : "백업 데이터 없음"}
          </span>
        </>
      )}
      {def && step && utilOpen && (
        // 접힘 존 — "문제 있나요?" 토글이 펼치는 전체 폭 보조 행. 비상구 | ‹ › × | 상태 신호 순.
        <div style={{ flexBasis: "100%", display: "flex", alignItems: "center", gap: 8, whiteSpace: "nowrap" }}>
          {(step === 4 || step === 5) && (
            <>
              <button
                className="nav-tab"
                style={{ fontSize: 14, padding: "5px 12px", color: "#4A4A4A", borderRight: "none" }}
                title="마지막으로 저장한 시점으로 코드를 되돌릴 수 있어요"
                onClick={() => onNavigate("backups")}
              >
                {/* 포기 비상구(spec §3.2) — 접힘 뒤에 있지만 토글 라벨("문제 있나요?")이 입구를 안내한다. */}
                잘 안 되면: 되돌리기
              </button>
              <span style={dividerStyle} />
            </>
          )}
          <span style={{ display: "flex", alignItems: "center", gap: 2 }}>
            <button
              className="nav-tab"
              style={iconBtnStyle}
              title="이전 단계"
              disabled={step === 2}
              onClick={() => step > 2 && onStepChange((step - 1) as ActiveGuideStep)}
            >
              ‹
            </button>
            <button
              className="nav-tab"
              style={iconBtnStyle}
              title="다음 단계"
              disabled={step === 6}
              onClick={() => step < 6 && onStepChange((step + 1) as ActiveGuideStep)}
            >
              ›
            </button>
            <button
              className="nav-tab"
              style={iconBtnStyle}
              title="가이드 끄기 (설정에서 다시 켤 수 있어요)"
              onClick={onDisable}
            >
              ×
            </button>
          </span>
          <span style={dividerStyle} />
          <span style={{ color: hasCheckpoint ? "#333" : "#666" }}>
            {hasCheckpoint ? "✓ 백업 데이터 있음" : "백업 데이터 없음"}
          </span>
          {planningPending && <span style={{ color: "#7C2D12" }}>● 기획 진행 중</span>}
        </div>
      )}
    </div>
  );
}
// === ANCHOR: GUIDE_STRIP_END ===
