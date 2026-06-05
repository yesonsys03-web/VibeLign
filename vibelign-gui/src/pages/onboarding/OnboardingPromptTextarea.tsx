// === ANCHOR: ONBOARDINGPROMPTTEXTAREA_START ===
import type { KeyboardEvent, RefObject } from "react";

interface OnboardingPromptTextareaProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
  readonly inputRef?: RefObject<HTMLTextAreaElement | null>;
}

// === ANCHOR: ONBOARDINGPROMPTTEXTAREA_ONBOARDINGPROMPTTEXTAREA_START ===
export function OnboardingPromptTextarea({ value, onChange, onSubmit, inputRef }: OnboardingPromptTextareaProps) {
  // === ANCHOR: ONBOARDINGPROMPTTEXTAREA_HANDLEKEYDOWN_START ===
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }
  // === ANCHOR: ONBOARDINGPROMPTTEXTAREA_HANDLEKEYDOWN_END ===

  return (
    <textarea
      ref={inputRef}
      className="input-field"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      onKeyDown={handleKeyDown}
      placeholder="무엇을 만들고 싶나요?"
      rows={1}
      style={{
        border: "none",
        minWidth: 0,
        minHeight: 34,
        maxHeight: 96,
        fontSize: 14,
        lineHeight: "20px",
        boxShadow: "none",
        resize: "none",
        overflowY: "auto",
        paddingTop: 7,
        paddingBottom: 7,
      }}
    />
// === ANCHOR: ONBOARDINGPROMPTTEXTAREA_ONBOARDINGPROMPTTEXTAREA_END ===
  );
}
// === ANCHOR: ONBOARDINGPROMPTTEXTAREA_END ===
