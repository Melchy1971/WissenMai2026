import { test, expect } from '@playwright/test';

test('Approval-Queue zeigt offene Freigaben', async ({ page }) => {
  await page.route('**/api/v1/approvals*', route =>
    route.fulfill({ json: { items: [{ id: 'a1', action: 'TOOL_RUN', risk: 'HIGH', status: 'pending' }] } })
  );
  await page.route('**/api/v1/status', route =>
    route.fulfill({ json: { privacy_mode: false, gates: [] } })
  );
  await page.route('**/api/v1/audit*', route =>
    route.fulfill({ json: { items: [] } })
  );
  await page.goto('/dashboard');
  await expect(page.getByTestId('approval-queue')).toBeVisible();
});

test('HIGH/CRITICAL Tools zeigen Approval-Hinweis statt direkten Start', async ({ page }) => {
  await page.route('**/api/v1/tools', route =>
    route.fulfill({ json: { items: [{ id: 't1', name: 'DangerTool', risk_level: 'CRITICAL', enabled: false }] } })
  );
  await page.route('**/api/v1/approvals*', route =>
    route.fulfill({ json: { items: [] } })
  );
  await page.goto('/tools');
  await expect(page.getByText('Approval erforderlich')).toBeVisible();
});
