import type { CanvasStatus } from "./canvasArtifactTrust";

interface CanvasGenerateButtonProps {
  status: CanvasStatus;
  disabled?: boolean;
  onGenerate: () => void;
  onCancel: () => void;
}

export default function CanvasGenerateButton({ status, disabled = false, onGenerate, onCancel }: CanvasGenerateButtonProps) {
  if (status === "unsupported") {
    return <span style={{ fontSize: 11, opacity: 0.8 }}>이 경로는 Canvas 생성 대상이 아닙니다.</span>;
  }
  if (status === "generating") {
    return (
      <button type="button" className="btn btn-ghost btn-sm" onClick={onCancel}>
        Cancel
      </button>
    );
  }
  const label = status === "stale" ? "Refresh Canvas" : status === "ready" ? "Regenerate Canvas" : "Generate Canvas";
  return (
    <button type="button" className="btn btn-ghost btn-sm" onClick={onGenerate} disabled={disabled}>
      {label}
    </button>
  );
}
