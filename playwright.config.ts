import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests drive the real stack. Start it first (see README):
 *   docker compose -f docker-compose.dev.yml up -d
 *   (cd api && uv run alembic upgrade head && uv run uvicorn peopleforce.main:app_factory --factory --port 8000)
 *   npx next dev -p 3100
 * The API must run with EMAIL_PROVIDER=console and PUBLIC_BASE_URL equal to E2E_BASE_URL, so the
 * sign-in link is shown on the page instead of being emailed.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1360, height: 900 } } }],
});
