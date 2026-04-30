// === ANCHOR: ESLINT_CONFIG_START ===
// 단일 파일 비대화 완화. 일반 소스 800줄, 레거시 Home.tsx는 2000줄까지(넘으면 에러).
import eslint from "@eslint/js";
import tseslint from "typescript-eslint";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  {
    // 이 프로젝트는 우선 파일 크기(max-lines) 위주로 막는다. any 정리는 별도 작업.
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    ignores: ["dist/**", "node_modules/**", "src-tauri/**"],
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "max-lines": [
        "error",
        { max: 800, skipBlankLines: true, skipComments: true },
      ],
    },
  },
  {
    files: ["src/pages/Home.tsx"],
    rules: {
      "max-lines": [
        "error",
        { max: 2000, skipBlankLines: true, skipComments: true },
      ],
    },
  },
  {
    files: ["src/pages/Onboarding.tsx"],
    rules: {
      "max-lines": [
        "error",
        { max: 1200, skipBlankLines: true, skipComments: true },
      ],
    },
  },
  {
    files: ["scripts/*.mjs"],
    languageOptions: {
      globals: {
        console: "readonly",
        process: "readonly",
        URL: "readonly",
      },
    },
  }
);
// === ANCHOR: ESLINT_CONFIG_END ===
