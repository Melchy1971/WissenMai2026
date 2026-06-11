import { test, expect } from '@playwright/test';

test('Rollback-Punkte nur für Admins sichtbar', async ({ page }) => {
  await page.route('**/api/v1/governance/status', route =>
    route.fulfill({ json: { current_user_is_admin: false, privacy_mode: false } })
  );
  await page.route('**/api/v1/approvals', route => route.fulfill({ json: { items: [] } }));
  await page.route('**/api/v1/governance/**', route => route.fulfill({ json: { items: [] } }));
  await page.route('**/api/v1/audit', route => route.fulfill({ json: { items: [] } }));
  await page.goto('/governance');
  await expect(page.getByTestId('rollback-point-list')).not.toBeVisible();
});

test('Rollback-Punkte für Admins sichtbar', async ({ page }) => {
  await page.route('**/api/v1/governance/status', route =>
    route.fulfill({ json: { current_user_is_admin: true, privacy_mode: false } })
  );
  await page.route('**/api/v1/approvals', route => route.fulfill({ json: { items: [] } }));
  await page.route('**/api/v1/governance/rollback-points', route =>
    route.fulfill({ json: { items: [{ id: 'r1', label: 'v1.0', created_at: '2026-06-01' }] } })
  );
  await page.route('**/api/v1/governance/**', route => route.fulfill({ json: { items: [] } }));
  await page.route('**/api/v1/audit', route => route.fulfill({ json: { items: [] } }));
  await page.goto('/governance');
  await expect(page.getByTestId('rollback-point-list')).toBeVisible();
});
