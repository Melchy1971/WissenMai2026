import { expect, test } from './fixtures.js';

test.describe('03 Workspace loading', () => {
  test('shows active workspace id in documents page header', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible({ timeout: 10_000 });
  });

  test('shows active workspace id in app shell session area', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await expect(authedPage.locator('.shell__session').getByText(workspaceId)).toBeVisible();
  });

  test('shows navigation links in shell header', async ({ authedPage }) => {
    await expect(authedPage.getByRole('link', { name: 'Dokumente' })).toBeVisible();
    await expect(authedPage.getByRole('link', { name: 'Chat' })).toBeVisible();
    await expect(authedPage.getByRole('link', { name: 'Admin' })).toBeVisible();
  });

  test('shows logout button when authenticated', async ({ authedPage }) => {
    await expect(authedPage.getByRole('button', { name: 'Abmelden' })).toBeVisible();
  });

  test('does not show workspace missing warning when workspace is configured', async ({ authedPage }) => {
    await expect(authedPage.getByText('nicht konfiguriert')).not.toBeVisible();
    await expect(authedPage.getByText('Workspace fehlt')).not.toBeVisible();
  });
});
