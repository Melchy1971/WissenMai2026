import { expect, test } from './fixtures.js';

test.describe('06 Search flow', () => {
  test('search page is visible with stable controls', async ({ authedPage }) => {
    await expect(authedPage.getByTestId('search-page')).toBeVisible();
    await expect(authedPage.getByTestId('search-form')).toBeVisible();
    await expect(authedPage.getByTestId('search-input')).toBeVisible();
    await expect(authedPage.getByTestId('search-submit')).toBeVisible();
  });

  test('query with hits returns the seeded truth document', async ({ authedPage }) => {
    await authedPage.getByTestId('search-input').fill('truthneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
    await expect(authedPage.getByTestId('search-results')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('search-results')).toContainText('GUI Truth Active Document');
  });

  test('query with no hits renders empty search state', async ({ authedPage }) => {
    await authedPage.getByTestId('search-input').fill('nohitneedle-frontend-truth');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByTestId('search-empty')).toContainText('Keine Treffer gefunden', { timeout: 10_000 });
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('archived document does not appear in active search', async ({ authedPage }) => {
    await authedPage.getByTestId('search-input').fill('archivedneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByTestId('search-empty')).toContainText('Keine Treffer gefunden', { timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Archived Document')).not.toBeVisible();
    await expect(authedPage.getByTestId('search-error')).not.toBeVisible();
  });

  test('deleted document does not appear in active search', async ({ authedPage }) => {
    await authedPage.getByTestId('search-input').fill('deletedneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByTestId('search-empty')).toContainText('Keine Treffer gefunden', { timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Deleted Document')).not.toBeVisible();
    await expect(authedPage.getByTestId('search-error')).not.toBeVisible();
  });

  test('loading state is shown while search request is pending', async ({ authedPage }) => {
    await authedPage.route('**/api/v1/search/chunks**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 800));
      await route.continue();
    });

    await authedPage.getByTestId('search-input').fill('truthneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByTestId('search-loading')).toContainText('Suchtreffer werden geladen', { timeout: 5_000 });
    await expect(authedPage.getByTestId('search-results')).toBeVisible({ timeout: 10_000 });
  });

  test('search API error is rendered explicitly', async ({ authedPage }) => {
    await authedPage.route('**/api/v1/search/chunks**', (route) => route.abort('failed'));

    await authedPage.getByTestId('search-input').fill('truthneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByTestId('search-error')).toContainText('Fehlercode: API_UNREACHABLE', { timeout: 10_000 });
  });

  test('API error is not rendered as fake empty state', async ({ authedPage }) => {
    await authedPage.route('**/api/v1/search/chunks**', (route) => route.abort('failed'));

    await authedPage.getByTestId('search-input').fill('truthneedle');
    await authedPage.getByTestId('search-submit').click();

    await expect(authedPage.getByTestId('search-error')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('search-empty')).not.toBeVisible();
    await expect(authedPage.getByTestId('search-results')).not.toBeVisible();
  });
});
