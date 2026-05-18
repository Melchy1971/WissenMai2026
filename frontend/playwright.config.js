import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.GUI_TRUTH_BASE_URL || 'http://127.0.0.1:7474';

export default defineConfig({
  testDir: './tests/gui_truth',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL,
    headless: true,
    viewport: { width: 1280, height: 800 },
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: process.env.GUI_TRUTH_EXTERNAL_FRONTEND === '1'
    ? undefined
    : {
        command: 'npm run dev -- --host 127.0.0.1 --port 7474',
        url: baseURL,
        reuseExistingServer: false,
        timeout: 30_000,
      },
});
