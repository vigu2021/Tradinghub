import { defineConfig, devices } from "@playwright/test";

// Must match FRONTEND_ORIGIN in the backend's .env, or CORS rejects every request and the whole
// suite fails with "still on /register" rather than anything about origins.
export const BASE_URL = "http://localhost:3210";

/**
 * The backend is not started here on purpose: it needs Postgres, and a test run that silently
 * boots infrastructure hides which half is broken. Bring it up with `make api` first.
 */
export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? "github" : "list",
  // A fixed pixel allowance, not a ratio: a ratio forgives more on a bigger page, and 0.1% of a
  // full desktop page is enough to hide a whole input outline. 50 absorbs anti-aliasing noise.
  expect: { toHaveScreenshot: { maxDiffPixels: 50 } },
  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
  },
  projects: [
    // Signs one user in through the API and saves the session for the signed-in tests.
    { name: "setup", testMatch: /\.setup\.ts$/ },
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
      dependencies: ["setup"],
    },
    // A real phone profile: touch, a 2.6x screen, a mobile user agent. The width checks and
    // snapshots set their own viewport and stay on desktop.
    {
      name: "mobile-chrome",
      use: { ...devices["Pixel 7"] },
      testMatch: /(entry|app)\.spec\.ts/,
      grepInvert: /width|keyboard/,
      dependencies: ["setup"],
    },
  ],
  webServer: {
    command: "npm run dev",
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
