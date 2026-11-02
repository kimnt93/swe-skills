import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The API base URL comes from VITE_API_BASE_URL at build time (see .env.example).
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 3000, strictPort: true },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/setupTests.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
