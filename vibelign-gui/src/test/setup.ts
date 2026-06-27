// === ANCHOR: SETUP_START ===
import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";

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

// Node.js 25+ exposes its own global localStorage (getter/setter) that vitest's
// jsdom populateGlobal cannot override.  Re-wire it to jsdom's proper Storage so
// that localStorage.clear/setItem/getItem work correctly in every test file.
// Each test file runs in its own forked process with a fresh JSDOM instance, so
// this is fully per-file isolated — no cross-test leakage.
Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  enumerable: true,
  get: () => (globalThis as any).jsdom?.window?.localStorage,
});

// Clear localStorage after every test so that no test leaves state for the next
// test within the same file (the component now correctly reads/writes Storage).
afterEach(() => {
  (globalThis as any).jsdom?.window?.localStorage?.clear();
});
// === ANCHOR: SETUP_END ===
