// === ANCHOR: SCROLLTOTOPBUTTON_START ===
import { useEffect, useState } from "react";

const SCROLL_THRESHOLD = 300;

// brutalism.css 의 app-layout 이 `height: 100vh; overflow: hidden` 이라 실제 scroll
// container 는 `.page-content` (flex: 1; overflow-y: auto). window.scrollY 는 항상 0
// 이라 그것에만 listener 달면 버튼 안 보임. document 의 capture-phase scroll listener
// 가 inner element 의 scroll 도 모두 잡음 (scroll 은 bubble 안 하지만 capture phase
// 에서 받음).
// === ANCHOR: SCROLLTOTOPBUTTON_GETACTIVESCROLLCONTAINER_START ===
function getActiveScrollContainer(): HTMLElement | null {
  return document.querySelector<HTMLElement>(".page-content");
}
// === ANCHOR: SCROLLTOTOPBUTTON_GETACTIVESCROLLCONTAINER_END ===

export default function ScrollToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // === ANCHOR: SCROLLTOTOPBUTTON_UPDATE_START ===
    const update = () => {
      const container = getActiveScrollContainer();
      const scrollTop = container?.scrollTop ?? window.scrollY;
      setVisible(scrollTop > SCROLL_THRESHOLD);
    };
    // === ANCHOR: SCROLLTOTOPBUTTON_UPDATE_END ===
    update();
    window.addEventListener("scroll", update, { passive: true });
    document.addEventListener("scroll", update, { passive: true, capture: true });
    return () => {
      window.removeEventListener("scroll", update);
      document.removeEventListener("scroll", update, { capture: true } as EventListenerOptions);
    };
  }, []);

  if (!visible) return null;

  // === ANCHOR: SCROLLTOTOPBUTTON_SCROLLTOTOP_START ===
  const scrollToTop = () => {
    const container = getActiveScrollContainer();
    if (container) {
      container.scrollTo({ top: 0, behavior: "smooth" });
    } else {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };
  // === ANCHOR: SCROLLTOTOPBUTTON_SCROLLTOTOP_END ===

  return (
    <button
      type="button"
      aria-label="페이지 최상단으로 이동"
      title="최상단으로"
      onClick={scrollToTop}
      style={{
        position: "fixed",
        right: 24,
        bottom: 24,
        width: 48,
        height: 48,
        border: "2px solid #1A1A1A",
        boxShadow: "4px 4px 0 #1A1A1A",
        background: "#FFE44D",
        cursor: "pointer",
        fontSize: 22,
        fontWeight: 900,
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        lineHeight: 1,
        padding: 0,
      }}
    >
      ↑
    </button>
  );
}
// === ANCHOR: SCROLLTOTOPBUTTON_END ===
