// === ANCHOR: JOURNEY_HOWTO_START ===
import { useEffect, useState } from "react";
import { JOURNEY_STEPS, type ActiveGuideStep, type GuideStep } from "../../lib/nav/guide";
import { PAGE_LABELS, type Page } from "../../lib/nav/stages";

interface JourneyHowtoProps {
  /** 현재 단계(가이드 추론). null이면 강조 없이 전부 접힘. */
  currentStep: ActiveGuideStep | null;
  onNavigate: (page: Page) => void;
}

/** 사용법 탭 상단 "순서대로 따라하기" 아코디언. 현재 단계가 자동으로 펼쳐진다(spec §3.4). */
export function JourneyHowto({ currentStep, onNavigate }: JourneyHowtoProps) {
  const [open, setOpen] = useState<GuideStep | null>(currentStep);
  useEffect(() => setOpen(currentStep), [currentStep]);
  return (
    <div style={{ padding: "16px 20px 4px" }}>
      <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 8 }}>📖 순서대로 따라하기</div>
      {JOURNEY_STEPS.map((def) => {
        const isOpen = open === def.step;
        const isCurrent = currentStep === def.step;
        return (
          <div
            key={def.step}
            style={{
              border: isCurrent ? "1px solid #FBBF24" : "1px solid #2A2A2A",
              background: isCurrent ? "#1a1813" : "#141414",
              borderRadius: 6,
              marginBottom: 4,
            }}
          >
            <button
              onClick={() => setOpen(isOpen ? null : def.step)}
              style={{
                width: "100%",
                textAlign: "left",
                padding: "8px 12px",
                background: "transparent",
                border: "none",
                color: "#ddd",
                cursor: "pointer",
                fontSize: 15,
              }}
            >
              {def.icon} <b>{def.label}</b> — <span style={{ color: "#888" }}>{def.shortAction}</span>
              <span style={{ float: "right", color: "#666" }}>{isOpen ? "▾" : "▸"}</span>
            </button>
            {isOpen && (
              <div style={{ padding: "0 12px 10px", fontSize: 14, color: "#aaa", lineHeight: 1.8 }}>
                {def.howto.map((line) => (
                  <div key={line}>{line}</div>
                ))}
                {def.targetPage && (
                  <button
                    className="nav-tab"
                    style={{ fontSize: 14, marginTop: 6 }}
                    onClick={() => onNavigate(def.targetPage as Page)}
                  >
                    지금 하러 가기 → {PAGE_LABELS[def.targetPage]}
                  </button>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
// === ANCHOR: JOURNEY_HOWTO_END ===
