import { defineConfig } from "@playwright/test";

// Builds and starts the production server on :3000, then drives it like a user.
// API_BASE_URL points at a port nothing listens on, so the page must degrade, not crash.
export default defineConfig({
  testDir: "e2e",
  use: { baseURL: "http://127.0.0.1:3000" },
  webServer: {
    command: "npm run build && npm run start",
    url: "http://127.0.0.1:3000/healthz",
    reuseExistingServer: !process.env.CI,
    timeout: 240_000,
    env: { API_BASE_URL: "http://127.0.0.1:1", SERVICE_NAME: "web", ENV_NAME: "local" },
  },
});
