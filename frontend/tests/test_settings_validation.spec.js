import { test, expect } from '@playwright/test';

test('Settings: Timeout außerhalb 1–300 wird blockiert', async ({ page }) => {
  await page.route('**/api/v1/settings', route =>
    route.fulfill({ json: { provider: { timeout_seconds: 30, max_retries: 3 } } })
  );
  await page.goto('/settings');
  const timeoutInput = page.locator('input[type="number"]').first();
  await timeoutInput.fill('999');
  await page.getByRole('button', { name: /speichern/i }).first().click();
  await expect(page.getByText('1–300 s')).toBeVisible();
});

test('Settings: RAG chunk_overlap >= chunk_size wird blockiert', async ({ page }) => {
  await page.route('**/api/v1/settings', route =>
    route.fulfill({ json: { rag: { chunk_size: 500, chunk_overlap: 600, min_score: 0.7, max_chunks: 5 } } })
  );
  await page.goto('/settings');
  // overlap >= chunk_size Fehler soll angezeigt werden
  await page.getByRole('button', { name: /speichern/i }).nth(4).click();
  await expect(page.getByText('Overlap < chunk_size')).toBeVisible();
});
