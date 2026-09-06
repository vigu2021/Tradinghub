import { defineConfig, devices } from "@playwright/test";

// Must match FRONTEND_ORIGIN in the backend's .env, or CORS rejects every request and the whole
// suite fails with "still on /register" rather than anything about origins.
const BASE_URL = "http://localhost:3210";

/**
 * The backend is not started here on purpose: it needs Postgres, and a test run that silently
 * boots infrastructure hides which half is broken. Bring it up with `make api` first.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
