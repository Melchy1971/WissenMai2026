import { expect, test } from './fixtures.js';

test.describe('04 Dokumentliste', () => {
  test('shows documents page heading', async ({ authedPage }) => {
    await expect(authedPage.getByRole('heading', { name: 'Dokumente' })).toBeVisible();
  });

  test('shows empty state for workspace with no documents', async ({ authedPage }) => {
    // Truth workspace starts empty; if prior uploads exist, this may show a list instead
    const emptyState = authedPage.getByText('Keine Dokumente vorhanden');
    const hasEmpty = await emptyState.isVisible().catch(() => false);
    if (!hasEmpty) {
      // Workspace has documents — verify the list renders, not an error
      await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
    } else {
      await expect(emptyState).toBeVisible();
    }
  });

  test('shows lifecycle filter section', async ({ authedPage }) => {
    await expect(authedPage.getByText('Sichtbarkeit')).toBeVisible();
    await expect(authedPage.getByLabel('Statusfilter')).toBeVisible();
  });

  test('shows upload section', async ({ authedPage }) => {
    await expect(authedPage.getByRole('heading', { name: 'Dokument hochladen' })).toBeVisible();
    await expect(authedPage.getByLabel('Datei')).toBeVisible();
    await expect(authedPage.getByRole('button', { name: 'Dokument importieren' })).toBeVisible();
  });

  test('shows search section', async ({ authedPage }) => {
    await expect(authedPage.getByLabel('Suchbegriff')).toBeVisible();
    await expect(authedPage.getByRole('button', { name: 'Suchen' })).toBeVisible();
  });
});
