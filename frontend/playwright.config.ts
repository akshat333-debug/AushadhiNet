import { defineConfig } from "@playwright/test";

// E2E_BASE_URL=https://<deployed frontend> runs the same suite against a deployment
// (no local servers started; free hosting can be slow, so timeouts are longer).
const remote = process.env.E2E_BASE_URL;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: remote ? 120_000 : 30_000,
  expect: { timeout: remote ? 60_000 : 5_000 },
  use: {
    baseURL: remote ?? "http://localhost:3000",
  },
  webServer: remote ? undefined : [
    {
      command: "cd .. && AUSHADHI_MODE=local uv run uvicorn backend.app:app --port 8000",
      url: "http://localhost:8000/public/district-summary",
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
});
