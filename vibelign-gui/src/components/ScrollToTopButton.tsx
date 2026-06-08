// === ANCHOR: SCROLLTOTOPBUTTON_START ===
import { useEffect, useState, type CSSProperties } from "react";

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

// === ANCHOR: SCROLLTOTOPBUTTON_SCROLLNAVVISIBILITY_START ===
/** 스크롤 위치로 위(↑)·아래(↓) 버튼 표시 여부를 계산하는 순수 함수. */
export function scrollNavVisibility(
  scrollTop: number,
  clientHeight: number,
  scrollHeight: number,
  threshold: number = SCROLL_THRESHOLD,
): { showTop: boolean; showBottom: boolean } {
  return {
    showTop: scrollTop > threshold,
    showBottom: scrollHeight - scrollTop - clientHeight > threshold,
  };
}
// === ANCHOR: SCROLLTOTOPBUTTON_SCROLLNAVVISIBILITY_END ===

export default function ScrollToTopButton() {
  const [nav, setNav] = useState({ showTop: false, showBottom: false });

  useEffect(() => {
    // === ANCHOR: SCROLLTOTOPBUTTON_UPDATE_START ===
    const update = () => {
      const container = getActiveScrollContainer();
      const scrollTop = container?.scrollTop ?? window.scrollY;
      const clientHeight = container?.clientHeight ?? window.innerHeight;
      const scrollHeight = container?.scrollHeight ?? document.documentElement.scrollHeight;
      setNav(scrollNavVisibility(scrollTop, clientHeight, scrollHeight));
    };
    // === ANCHOR: SCROLLTOTOPBUTTON_UPDATE_END ===
    update();
    window.addEventListener("scroll", update, { passive: true });
    document.addEventListener("scroll", update, { passive: true, capture: true });
    // 대화가 길어지면(메시지 추가로 내용 높이 변화) 버튼 표시가 갱신되도록 resize 도 청취.
    window.addEventListener("resize", update, { passive: true });
    return () => {
      window.removeEventListener("scroll", update);
      document.removeEventListener("scroll", update, { capture: true } as EventListenerOptions);
      window.removeEventListener("resize", update);
    };
  }, []);

  if (!nav.showTop && !nav.showBottom) return null;

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

  // === ANCHOR: SCROLLTOTOPBUTTON_SCROLLTOBOTTOM_START ===
  const scrollToBottom = () => {
    const container = getActiveScrollContainer();
    if (container) {
      container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
    } else {
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" });
    }
  };
  // === ANCHOR: SCROLLTOTOPBUTTON_SCROLLTOBOTTOM_END ===

  const buttonStyle: CSSProperties = {
    width: 48,
    height: 48,
    border: "2px solid #1A1A1A",
    boxShadow: "4px 4px 0 #1A1A1A",
    background: "#FFE44D",
    cursor: "pointer",
    fontSize: 22,
    fontWeight: 900,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    lineHeight: 1,
    padding: 0,
  };

  // 컨테이너를 bottom-right 에 고정해 자식이 아래부터 쌓이게 한다. 둘 중 하나만
  // 보일 땐 그 버튼이 코너(bottom:24)에 붙어 빈틈이 없고, 둘 다 보이면 ↓ 위 ↑ 아래로
  // 쌓여 기존 ↑ 위치(코너)가 유지된다.
  return (
    <div
      style={{
        position: "fixed",
        right: 24,
        bottom: 24,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
    >
      {nav.showBottom && (
        <button
          type="button"
          aria-label="대화 최하단으로 이동"
          title="최하단으로"
          onClick={scrollToBottom}
          style={buttonStyle}
        >
          ↓
        </button>
      )}
      {nav.showTop && (
        <button
          type="button"
          aria-label="페이지 최상단으로 이동"
          title="최상단으로"
          onClick={scrollToTop}
          style={buttonStyle}
        >
          ↑
        </button>
      )}
    </div>
  );
}
// === ANCHOR: SCROLLTOTOPBUTTON_END ===
