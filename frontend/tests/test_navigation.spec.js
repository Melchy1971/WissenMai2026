import { test, expect } from '@playwright/test';

const ROUTES = [
  ['/dashboard', 'dashboard-page'],
  ['/tools', 'tool-center-page'],
  ['/memory', 'memory-center-page'],
  ['/tasks', 'task-center-page'],
  ['/projects', 'project-center-page'],
  ['/rag', 'rag-center-page'],
  ['/agents', 'agent-center-page'],
  ['/collaboration', 'collaboration-center-page'],
  ['/governance', 'governance-center-page'],
  ['/settings', 'settings-page'],
];

for (const [path, testId] of ROUTES) {
  test(`Route ${path} lädt Seite ${testId}`, async ({ page }) => {
    // Stub alle API-Calls mit leeren Responses
    await page.route('**/api/v1/**', route =>
      route.fulfill({ json: { items: [], ok: true } })
    );
    await page.goto(path);
    await expect(page.getByTestId(testId)).toBeVisible({ timeout: 5000 });
  });
}
