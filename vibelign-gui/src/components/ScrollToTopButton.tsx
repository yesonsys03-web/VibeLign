import { useEffect, useState } from "react";

const SCROLL_THRESHOLD = 300;

export default function ScrollToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > SCROLL_THRESHOLD);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      type="button"
      aria-label="페이지 최상단으로 이동"
      title="최상단으로"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
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
