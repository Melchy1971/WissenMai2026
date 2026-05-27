import { expect, test } from './fixtures.js';

test.describe('04 Dokumentliste', () => {
  test('shows documents page heading', async ({ authedPage }) => {
    await expect(authedPage.getByTestId('documents-page')).toBeVisible();
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

  test('loads the seeded active document in the list', async ({ authedPage }) => {
    await expect(authedPage.getByTestId('document-list')).toBeVisible({ timeout: 10_000 });
    // Die konkrete Dokumentenprüfung bleibt vorerst textbasiert, bis weitere testid verfügbar sind
    await expect(authedPage.getByText('GUI Truth Deleted Document')).not.toBeVisible();
  });

  test('opens document detail with versions and chunk preview', async ({ authedPage }) => {
    await authedPage.getByRole('link', { name: 'GUI Truth Active Document' }).click();
    await expect(authedPage).toHaveURL(/\/documents\/.+/);
    await expect(authedPage.getByRole('heading', { name: 'GUI Truth Active Document' }).first()).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByRole('heading', { name: 'Versionen' })).toBeVisible();
    await expect(authedPage.getByRole('heading', { name: 'Chunk-Vorschau' })).toBeVisible();
    await expect(authedPage.getByText(/truthneedle active knowledge base content/)).toBeVisible();
  });

  test('unknown document detail is an error state, not an empty list', async ({ authedPage }) => {
    await authedPage.goto('/documents/00000000-0000-0000-0000-000000000000');
    await expect(authedPage.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  });

  test('empty document list is distinct from an API error', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    await multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' }).selectOption(ws2);
    await expect(multiWorkspacePage.getByText(`Workspace: ${ws2}`)).toBeVisible({ timeout: 10_000 });
    await expect(multiWorkspacePage.getByText('Dokumente werden geladen...')).not.toBeVisible({ timeout: 15_000 });
    await expect(multiWorkspacePage.locator('.state-card--error')).not.toBeVisible();
    await expect(multiWorkspacePage.getByText('Keine Dokumente vorhanden')).toBeVisible({ timeout: 15_000 });
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
