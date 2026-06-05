// === ANCHOR: HOMEPLANNINGSTART_START ===
import { useState } from "react";

interface HomePlanningStartProps {
  readonly onStart: (idea: string) => void;
}

// === ANCHOR: HOMEPLANNINGSTART_HOMEPLANNINGSTART_START ===
export function HomePlanningStart({ onStart }: HomePlanningStartProps) {
  const [idea, setIdea] = useState("");

  function submit() {
    const trimmed = idea.trim();
    if (!trimmed) return;
    onStart(trimmed);
  }

  return (
    <section
      style={{
        border: "2px solid #1A1A1A",
        background: "#F5F1E3",
        padding: 10,
        marginBottom: 12,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 900, marginBottom: 3 }}>기획방 시작하기</div>
      <div style={{ fontSize: 10, color: "#666", fontWeight: 700, marginBottom: 8 }}>
        아이디어를 입력하면 기획방에서 구체화할 수 있어요.
      </div>
      <textarea
        value={idea}
        onChange={(e) => setIdea(e.target.value.slice(0, 4000))}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="무엇을 만들고 싶나요?"
        rows={3}
        style={{ width: "100%", boxSizing: "border-box", resize: "vertical", fontSize: 12, padding: 8, border: "2px solid #1A1A1A", background: "#fff" }}
      />
      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
        <button className="btn btn-black btn-sm" type="button" onClick={submit} style={{ fontSize: 11 }}>
          시작
        </button>
      </div>
    </section>
  );
}
// === ANCHOR: HOMEPLANNINGSTART_HOMEPLANNINGSTART_END ===
// === ANCHOR: HOMEPLANNINGSTART_END ===
