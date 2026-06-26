// ANCHOR: TUTORIAL_PICKER_START
import { TUTORIALS } from "../../lib/tutorial/scripts";
import type { TutorialId } from "../../lib/tutorial/types";

interface TutorialPickerProps {
  onPick: (id: TutorialId) => void;
  onClose: () => void;
}

export default function TutorialPicker({ onPick, onClose }: TutorialPickerProps) {
  return (
    <div className="tutpick-backdrop" role="dialog" aria-label="따라하며 만들기">
      <div className="tutpick-panel">
        <h2 className="tutpick-title">🧭 따라하며 앱 하나 만들어볼까요?</h2>
        <p className="tutpick-sub">버튼을 하나하나 눌러주는 대로 따라하면, 끝에 진짜 작동하는 앱이 남아요.</p>
        <div className="tutpick-cards">
          {TUTORIALS.map((t) => (
            <button key={t.id} className="tutpick-card" onClick={() => onPick(t.id)}>
              <span className="tutpick-emoji">{t.emoji}</span>
              <span className="tutpick-cardtitle">{t.title}</span>
              <span className="tutpick-goal">{t.goal}</span>
            </button>
          ))}
        </div>
        <button className="tour-skip" onClick={onClose}>나중에 할게요</button>
      </div>
    </div>
  );
}
// ANCHOR: TUTORIAL_PICKER_END
