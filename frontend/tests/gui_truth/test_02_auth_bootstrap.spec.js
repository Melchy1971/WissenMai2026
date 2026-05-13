import { expect, test } from './fixtures.js';

test.describe('02 Auth bootstrap', () => {
  test('boots directly to documents page from complete stored session', async ({ authedPage }) => {
    await expect(authedPage.getByRole('heading', { name: 'Dokumente' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage).not.toHaveURL(/login/);
  });

  test('does not show bootstrap loading state with complete session', async ({ authedPage }) => {
    // The loading state text indicates bootstrapping is still pending
    await expect(authedPage.getByText('Authentifizierung wird initialisiert...')).not.toBeVisible();
    await expect(authedPage.getByRole('heading', { name: 'Dokumente' })).toBeVisible();
  });

  test('app shell renders after bootstrap without error state', async ({ authedPage }) => {
    await expect(authedPage.locator('.shell')).toBeVisible();
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('logout clears session and returns to login', async ({ authedPage }) => {
    await expect(authedPage.getByRole('heading', { name: 'Dokumente' })).toBeVisible();
    await authedPage.getByRole('button', { name: 'Abmelden' }).click();
    await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  });
});
