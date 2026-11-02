import { defineConfig } from "@playwright/test";

// Builds and serves the production bundle on :3000, then drives it like a user.
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://127.0.0.1:3000" },
  webServer: {
    command: "npm run build && npm run preview",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
