import { expect, test } from './fixtures.js';

test.describe('07 Chat flow', () => {
  test('shows chat page heading and workspace context', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await authedPage.goto('/chat');
    await expect(authedPage.getByRole('heading', { name: 'Dokumentgestuetzter Chat' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  });

  test('shows empty chat state or session list', async ({ authedPage }) => {
    await authedPage.goto('/chat');

    // Either no sessions exist (empty state) or there are existing sessions
    await authedPage.waitForTimeout(3_000);
    const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  test('shows chat composer form', async ({ authedPage }) => {
    await authedPage.goto('/chat');
    // Wait for loading to finish
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByLabel('Titel der Sitzung')).toBeVisible({ timeout: 5_000 });
    await expect(authedPage.locator('.chat-layout')).toBeVisible();
  });

  test('navigation from documents to chat preserves workspace context', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    // Start on documents
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
    // Navigate to chat
    await authedPage.getByRole('link', { name: 'Chat' }).click();
    await expect(authedPage.getByRole('heading', { name: 'Dokumentgestuetzter Chat' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  });
});
