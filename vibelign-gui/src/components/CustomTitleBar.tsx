// === ANCHOR: CUSTOM_TITLEBAR_START ===
import { getCurrentWindow } from "@tauri-apps/api/window";

interface CustomTitleBarProps {
  projectDir?: string | null;
  onSettings?: () => void;
}

export default function CustomTitleBar({ projectDir, onSettings }: CustomTitleBarProps) {
  const win = getCurrentWindow();
  const projectName = projectDir ? projectDir.split("/").filter(Boolean).at(-1) : null;

  async function handleMouseDown(e: React.MouseEvent) {
    // 버튼 클릭은 드래그 제외
    if ((e.target as HTMLElement).closest("button")) return;
    if (e.button !== 0) return;
    await win.startDragging();
  }

  return (
    <div className="title-bar" onMouseDown={handleMouseDown}>
      <span className="app-name">VIBELIGN</span>
      {projectName && (
        <span className="title-center mono">~ /{projectName}</span>
      )}
      <div className="window-controls" onMouseDown={(e) => e.stopPropagation()}>
        {onSettings && (
          <button onClick={onSettings} title="설정" style={{ fontSize: 13 }}>⚙</button>
        )}
        <button onClick={() => win.minimize()} title="최소화">─</button>
        <button onClick={() => win.close()} title="닫기">✕</button>
      </div>
    </div>
  );
}
// === ANCHOR: CUSTOM_TITLEBAR_END ===
