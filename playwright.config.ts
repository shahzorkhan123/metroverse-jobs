import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/playwright",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:3001",
  },
  webServer: {
    command: "node tests/playwright/serve-build.js 3001",
    url: "http://localhost:3001/metroverse-jobs/",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
