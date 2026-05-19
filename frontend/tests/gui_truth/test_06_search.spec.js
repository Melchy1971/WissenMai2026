import { expect, test } from './fixtures.js';

test.describe('06 Search flow', () => {
  test('shows search form elements', async ({ authedPage }) => {
    await expect(authedPage.getByLabel('Suchbegriff')).toBeVisible();
    await expect(authedPage.getByRole('button', { name: 'Suchen' })).toBeVisible();
  });

  test('submitting empty search term shows idle state without error', async ({ authedPage }) => {
    await authedPage.getByRole('button', { name: 'Suchen' }).click();
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('query with hits returns the seeded truth document', async ({ authedPage }) => {
    await authedPage.getByLabel('Suchbegriff').fill('truthneedle');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
    await expect(authedPage.getByRole('heading', { name: /Treffer fuer/ })).toBeVisible({ timeout: 10_000 });
    await expect(
      authedPage.locator('.search-result-card').getByRole('link', { name: 'GUI Truth Active Document' }),
    ).toBeVisible();
  });

  test('query with no hits renders empty search state', async ({ authedPage }) => {
    await authedPage.getByLabel('Suchbegriff').fill('nohitneedle-frontend-truth');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    await expect(authedPage.getByText('Keine Treffer gefunden')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('search with workspace context sends request to real backend', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;

    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();

    await authedPage.getByLabel('Suchbegriff').fill('gui truth');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    await authedPage.waitForTimeout(5_000);

    await expect(authedPage.getByText('AUTH_REQUIRED')).not.toBeVisible();
    await expect(authedPage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
  });

  test('search API error is an error state, not an empty result', async ({ authedPage }) => {
    await authedPage.route('**/api/v1/search/chunks**', (route) => route.abort('failed'));

    await authedPage.getByLabel('Suchbegriff').fill('truthneedle');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    await expect(authedPage.getByText('Fehlercode: API_UNREACHABLE')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('Keine Treffer gefunden')).not.toBeVisible();
  });
});
