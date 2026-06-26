// === ANCHOR: VITEST_CONFIG_START ===
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    environmentOptions: { jsdom: { url: "http://localhost/" } },
    setupFiles: "./src/test/setup.ts",
  },
});
// === ANCHOR: VITEST_CONFIG_END ===
