import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/playwright",
  timeout: 30_000,
  use: {
    baseURL: "http://localhost:3001",
  },
  webServer: {
    command: "npx serve build -l 3001 --no-clipboard",
    url: "http://localhost:3001/metroverse-jobs/",
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
