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

// Ensure localStorage has all methods
const store: { [key: string]: string } = {};
Object.defineProperty(globalThis, 'localStorage', {
  value: {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach(key => delete store[key]); },
    key: (index: number) => Object.keys(store)[index] ?? null,
    get length() { return Object.keys(store).length; },
  },
});
// === ANCHOR: SETUP_END ===
