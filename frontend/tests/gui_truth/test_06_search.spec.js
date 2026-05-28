import { expect, test } from './fixtures.js';

test.describe('06 Search flow', () => {
  test('shows search form elements', async ({ authedPage }) => {
    await expect(authedPage.getByTestId('search-page')).toBeVisible();
    await expect(authedPage.getByTestId('search-form')).toBeVisible();
    await expect(authedPage.getByTestId('search-input')).toBeVisible();
    await expect(authedPage.getByTestId('search-submit')).toBeVisible();
  });

  test('submitting empty search term shows idle state without error', async ({ authedPage }) => {
    await authedPage.getByTestId('search-submit').click();
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('query with hits returns the seeded truth document', async ({ authedPage }) => {
    await authedPage.getByTestId('search-input').fill('truthneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
    await expect(authedPage.getByTestId('search-result-list')).toBeVisible({ timeout: 10_000 });
    await expect(
      authedPage.locator('.search-result-card a').first(),
    ).toBeVisible();
  });

  test('query with no hits renders empty search state', async ({ authedPage }) => {
    await authedPage.getByTestId('search-input').fill('nohitneedle-frontend-truth');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByText('Keine Treffer gefunden')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('search with workspace context sends request to real backend', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;

    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();

    await authedPage.getByTestId('search-input').fill('gui truth');
    await authedPage.getByTestId('search-submit').click();

    await authedPage.waitForTimeout(5_000);

    await expect(authedPage.getByText('AUTH_REQUIRED')).not.toBeVisible();
    await expect(authedPage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
  });

  test('search API error is an error state, not an empty result', async ({ authedPage }) => {
    await authedPage.route('**/api/v1/search/chunks**', (route) => route.abort('failed'));

    await authedPage.getByTestId('search-input').fill('truthneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByTestId('search-error')).toContainText('Fehlercode: API_UNREACHABLE', { timeout: 10_000 });
    await expect(authedPage.getByText('Keine Treffer gefunden')).not.toBeVisible();
  });
});
