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

  test('search returns results or empty state without error', async ({ authedPage }) => {
    await authedPage.getByLabel('Suchbegriff').fill('test');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    // Either results appear or empty search state — no error
    await authedPage.waitForTimeout(3_000);
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('search with workspace context sends request to real backend', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;

    // Confirm workspace context is loaded before searching
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();

    await authedPage.getByLabel('Suchbegriff').fill('gui truth');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    // Wait for the backend to respond
    await authedPage.waitForTimeout(5_000);

    // Page should not show an authentication error
    await expect(authedPage.getByText('AUTH_REQUIRED')).not.toBeVisible();
    await expect(authedPage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
  });
});
