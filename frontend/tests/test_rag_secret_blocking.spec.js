import { test, expect } from '@playwright/test';

test('SECRET-Dokumente in RAG zeigen gesperrt statt Reindex', async ({ page }) => {
  await page.route('**/api/v1/rag/documents', route =>
    route.fulfill({ json: { items: [
      { id: 'd1', title: 'Öffentlich', classification: 'PUBLIC', index_status: 'indexed' },
      { id: 'd2', title: 'Geheim', classification: 'SECRET', index_status: 'blocked' },
    ] } })
  );
  await page.route('**/api/v1/status', route =>
    route.fulfill({ json: { privacy_mode: false } })
  );
  await page.goto('/rag');
  await expect(page.getByText('gesperrt')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reindex' })).toHaveCount(1);
});
