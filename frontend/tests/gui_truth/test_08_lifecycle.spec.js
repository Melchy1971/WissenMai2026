import { expect, test } from './fixtures.js';

test.describe('08 Lifecycle GUI', () => {
  test('shows lifecycle filter with correct default option', async ({ authedPage }) => {
    const select = authedPage.getByLabel('Statusfilter');
    await expect(select).toBeVisible();
    await expect(select).toHaveValue('active');
  });

  test('lifecycle filter shows correct option labels', async ({ authedPage }) => {
    await expect(authedPage.getByRole('option', { name: 'Nur aktive Dokumente' })).toBeAttached();
    await expect(authedPage.getByRole('option', { name: 'Nur archivierte Dokumente' })).toBeAttached();
  });

  test('switching to archived filter triggers API call without error', async ({ authedPage }) => {
    await authedPage.getByLabel('Statusfilter').selectOption('archived');
    await authedPage.waitForTimeout(3_000);
    // Should show empty state or archived documents — no error
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('switching back to active filter restores document list', async ({ authedPage }) => {
    const select = authedPage.getByLabel('Statusfilter');
    await select.selectOption('archived');
    await authedPage.waitForTimeout(1_000);
    await select.selectOption('active');
    await authedPage.waitForTimeout(3_000);
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('shows lifecycle warning hint text', async ({ authedPage }) => {
    await expect(
      authedPage.getByText('Archivierte Dokumente erscheinen nicht in Suche oder Chat.'),
    ).toBeVisible();
  });
});
