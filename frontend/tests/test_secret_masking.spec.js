import { test, expect } from '@playwright/test';

test('SecretInput zeigt keine Klartextwerte', async ({ page }) => {
  await page.route('**/api/v1/settings', route =>
    route.fulfill({ json: { provider: { api_key: 'sk-secret-123', timeout_seconds: 30 } } })
  );
  await page.goto('/settings');
  const secretInputs = page.getByTestId('secret-input');
  const count = await secretInputs.count();
  for (let i = 0; i < count; i++) {
    const text = await secretInputs.nth(i).textContent();
    expect(text).not.toContain('sk-secret-123');
  }
});
