import { expect, test } from './fixtures.js';

test.describe('12 Concurrency safety', () => {
  test('parallel search requests use the real backend and do not surface stale errors', async ({ authedPage }) => {
    let firstSearchDelayed = false;
    await authedPage.route('**/api/v1/search/chunks**', async (route) => {
      if (!firstSearchDelayed) {
        firstSearchDelayed = true;
        await authedPage.waitForTimeout(1200);
      }
      await route.continue();
    });

    await authedPage.getByLabel('Suchbegriff').fill('slow truth');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();
    await authedPage.getByLabel('Suchbegriff').fill('fast truth');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    await authedPage.waitForTimeout(3000);
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
    await expect(authedPage.getByText('AUTH_REQUIRED')).not.toBeVisible();
    await expect(authedPage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
  });

  test('workspace switch during an in-flight real request does not keep old workspace UI state', async ({ multiWorkspacePage }) => {
    const workspace2Id = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    await multiWorkspacePage.route('**/documents?**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.continue();
    });

    await multiWorkspacePage.getByLabel('Workspace wechseln').selectOption(workspace2Id);
    await expect(multiWorkspacePage.getByText(`Workspace: ${workspace2Id}`)).toBeVisible({ timeout: 10_000 });
    await expect(multiWorkspacePage.locator('.state-card--error')).not.toBeVisible();
    await multiWorkspacePage.unrouteAll({ behavior: 'ignoreErrors' });
  });
});
