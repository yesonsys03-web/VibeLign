import type { KeyboardEvent } from "react";

interface OnboardingPromptTextareaProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
}

export function OnboardingPromptTextarea({ value, onChange, onSubmit }: OnboardingPromptTextareaProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  }

  return (
    <textarea
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
  );
}
