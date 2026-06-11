import { test, expect } from '@playwright/test';

test('Audit-Log filtert SECRET-Einträge heraus', async ({ page }) => {
  await page.route('**/api/v1/audit*', route =>
    route.fulfill({ json: { items: [
      { id: 'e1', action: 'READ', classification: 'PUBLIC', actor: 'user1', timestamp: '2026-06-01T10:00:00Z' },
      { id: 'e2', action: 'WRITE', classification: 'SECRET', actor: 'user2', timestamp: '2026-06-01T11:00:00Z' },
    ] } })
  );
  await page.route('**/api/v1/**', route =>
    route.fulfill({ json: { items: [] } })
  );
  await page.goto('/governance');
  await expect(page.getByTestId('audit-log-table')).toBeVisible();
  // SECRET-Zeile darf nicht sichtbar sein
  await expect(page.getByText('user2')).not.toBeVisible();
});
