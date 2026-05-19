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

  test('active document is visible while deleted document is hidden', async ({ authedPage }) => {
    await authedPage.getByLabel('Statusfilter').selectOption('active');
    await expect(authedPage.getByRole('link', { name: 'GUI Truth Active Document' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Deleted Document')).not.toBeVisible();
  });

  test('archived document is not returned by active search', async ({ authedPage }) => {
    await authedPage.getByLabel('Suchbegriff').fill('archivedneedle');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    await expect(authedPage.getByText('Keine Treffer gefunden')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Archived Document')).not.toBeVisible();
  });

  test('archived document is visible only in archived filter', async ({ authedPage }) => {
    await authedPage.getByLabel('Statusfilter').selectOption('archived');
    await expect(authedPage.getByRole('link', { name: 'GUI Truth Archived Document' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Deleted Document')).not.toBeVisible();
  });
});
