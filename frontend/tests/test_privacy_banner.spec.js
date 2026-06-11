import { test, expect } from '@playwright/test';

test('PrivacyModeBanner erscheint wenn Privacy Mode aktiv', async ({ page }) => {
  await page.route('**/api/v1/status', route =>
    route.fulfill({ json: { privacy_mode: true, gates: [] } })
  );
  await page.goto('/dashboard');
  await expect(page.getByTestId('privacy-mode-banner')).toBeVisible();
});

test('PrivacyModeBanner fehlt ohne Privacy Mode', async ({ page }) => {
  await page.route('**/api/v1/status', route =>
    route.fulfill({ json: { privacy_mode: false, gates: [] } })
  );
  await page.goto('/dashboard');
  await expect(page.getByTestId('privacy-mode-banner')).not.toBeVisible();
});
