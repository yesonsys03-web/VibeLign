// === ANCHOR: SETUP_START ===
import "@testing-library/jest-dom/vitest";

// === ANCHOR: SETUP_RESIZEOBSERVERSTUB_START ===
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
// === ANCHOR: SETUP_RESIZEOBSERVERSTUB_END ===

// === ANCHOR: SETUP_INTERSECTIONOBSERVERSTUB_START ===
class IntersectionObserverStub {
  root = null;
  rootMargin = "0px";
  thresholds = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
}
// === ANCHOR: SETUP_INTERSECTIONOBSERVERSTUB_END ===

globalThis.ResizeObserver = ResizeObserverStub as typeof ResizeObserver;
globalThis.IntersectionObserver = IntersectionObserverStub as unknown as typeof IntersectionObserver;
// === ANCHOR: SETUP_END ===
