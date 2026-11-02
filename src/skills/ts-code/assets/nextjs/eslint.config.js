import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: [".next", "next-env.d.ts", "playwright-report", "test-results", "lib/schema.d.ts"] },
  js.configs.recommended,
  ...tseslint.configs.strict,
  reactHooks.configs.flat.recommended,
  {
    rules: {
      "no-console": "error",
      "@typescript-eslint/no-explicit-any": "error",
      "@typescript-eslint/ban-ts-comment": ["error", { "ts-expect-error": "allow-with-description" }],
    },
  },
);
