import "@testing-library/jest-dom/vitest";

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

class IntersectionObserverStub {
  root = null;
  rootMargin = "0px";
  thresholds = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() { return []; }
}

globalThis.ResizeObserver = ResizeObserverStub as typeof ResizeObserver;
globalThis.IntersectionObserver = IntersectionObserverStub as unknown as typeof IntersectionObserver;
