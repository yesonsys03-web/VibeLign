// === ANCHOR: ONBOARDINGINPUTBAR_START ===
import type { CSSProperties, RefObject } from "react";
import { OnboardingPromptTextarea } from "./OnboardingPromptTextarea";

/** 코치마크 단계 — "folder"(폴더 고르기) → "prompt"(한 줄 적고 시작) → null(종료). */
export type OnboardingCoach = "folder" | "prompt" | null;

interface OnboardingInputBarProps {
  readonly promptText: string;
  readonly selectedDirName: string;
  readonly folderHint: string | null;
  readonly inputRef?: RefObject<HTMLTextAreaElement | null>;
  readonly onPromptChange: (value: string) => void;
  readonly onPickFolder: () => void;
  readonly onSubmit: () => void;
  /** 게임형 코치마크 단계(W3) — 없으면 말풍선/펄스링 미표시. */
  readonly coach?: OnboardingCoach;
  readonly onDismissCoach?: () => void;
}

// === ANCHOR: ONBOARDINGINPUTBAR_ONBOARDINGINPUTBAR_START ===
export function OnboardingInputBar({
  promptText,
  selectedDirName,
  folderHint,
  inputRef,
  onPromptChange,
  onPickFolder,
  onSubmit,
  coach = null,
  onDismissCoach,
}: OnboardingInputBarProps) {
  // 코치 말풍선이 바 "위"에 떠도 제목/안내문과 겹치지 않도록 여백 확보(목업 .coach-on).
  const barStyle: CSSProperties = {
    position: "relative",
    display: "grid",
    gridTemplateColumns: "44px minmax(0, 1fr) auto 44px",
    alignItems: "center",
    gap: 8,
    border: "2px solid #1A1A1A",
    background: "#fff",
    padding: 8,
    boxShadow: "4px 4px 0 #1A1A1A",
    marginTop: coach ? 140 : 0,
  };
  return (
    <div style={{ width: "100%", maxWidth: 720 }}>
      <div style={barStyle}>
        {coach && (
          <div
            className={`coach-bubble${coach === "prompt" ? " at-prompt" : ""}`}
            style={{ ["--tailx" as string]: coach === "prompt" ? "20px" : "24px" } as CSSProperties}
          >
            <button type="button" className="x" aria-label="안내 닫기" onClick={() => onDismissCoach?.()}>
              ×
            </button>
            {coach === "folder" ? (
              <>
                <span className="em">👋</span> 안녕! 먼저 <b>＋</b>를 눌러 프로젝트 폴더를 골라줘.
                <br />
                비어 있는 새 폴더를 만들어도 좋아요 — 거기서부터 시작할게요!
              </>
            ) : (
              <>
                <span className="em">✍️</span> 좋았어! 이제 <b>만들고 싶은 걸 한 줄</b> 적고
                <br />
                오른쪽 <b>●</b>를 누르면 시작! 나머진 내가 정렬해 둘게 🚀
              </>
            )}
          </div>
        )}
        <span className="onb-plus-wrap">
          <button
            type="button"
            aria-label="프로젝트 폴더 선택"
            onClick={onPickFolder}
            className={coach === "folder" ? "guide-attract" : undefined}
            style={{ width: 34, height: 34, border: "2px solid #1A1A1A", background: "#fff", fontSize: 20, fontWeight: 900, cursor: "pointer" }}
          >
            +
          </button>
          <span className="coach-hovertip">
            ➕ 여기 눌러서 프로젝트 폴더 고르기!
            <br />
            새 폴더 만들어도 돼요 👌
          </span>
        </span>
        <OnboardingPromptTextarea inputRef={inputRef} value={promptText} onChange={onPromptChange} onSubmit={onSubmit} />
        <button
          type="button"
          aria-label="AI 선택"
          style={{ border: "1px solid #DDD", background: "#F7F7F7", fontSize: 11, fontWeight: 800, padding: "7px 10px", color: "#333" }}
        >
          Instant
        </button>
        <button
          type="button"
          aria-label="전송"
          onClick={onSubmit}
          style={{ width: 34, height: 34, border: "2px solid #1A1A1A", borderRadius: 999, background: "#1A1A1A", color: "#fff", fontSize: 12, fontWeight: 900, cursor: "pointer" }}
        >
          ●
        </button>
      </div>

      {selectedDirName && (
        <div style={{ marginTop: 10, fontSize: 11, fontWeight: 700, color: "#1A1A1A" }}>
          선택한 폴더: {selectedDirName}
        </div>
      )}

      {folderHint && (
        <div role="status" style={{ marginTop: 10, fontSize: 12, fontWeight: 700, color: "#A14B00" }}>
          {folderHint}
        </div>
      )}
    </div>
  );
}
// === ANCHOR: ONBOARDINGINPUTBAR_ONBOARDINGINPUTBAR_END ===
// === ANCHOR: ONBOARDINGINPUTBAR_END ===
