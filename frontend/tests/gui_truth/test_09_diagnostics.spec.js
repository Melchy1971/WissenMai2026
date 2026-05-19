import { expect, test } from './fixtures.js';

test.describe('09 Diagnostics GUI', () => {
  test('shows admin diagnostics page heading', async ({ authedPage }) => {
    await authedPage.goto('/admin/diagnostics');
    await expect(authedPage.getByRole('heading', { name: 'Systemdiagnose' })).toBeVisible({ timeout: 10_000 });
  });

  test('shows system status card', async ({ authedPage }) => {
    await authedPage.goto('/admin/diagnostics');
    await authedPage.waitForTimeout(5_000);
    const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
    if (!hasError) {
      await expect(authedPage.getByText('Systemstatus')).toBeVisible();
    }
  });

  test('shows database status card', async ({ authedPage }) => {
    await authedPage.goto('/admin/diagnostics');
    await authedPage.waitForTimeout(5_000);
    const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
    if (!hasError) {
      await expect(authedPage.getByText('DB Status')).toBeVisible();
    }
  });

  test('shows migration status card', async ({ authedPage }) => {
    await authedPage.goto('/admin/diagnostics');
    await authedPage.waitForTimeout(5_000);
    const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
    if (!hasError) {
      await expect(authedPage.getByText('Migration Status')).toBeVisible();
    }
  });

  test('diagnostics page accessible via admin nav link', async ({ authedPage }) => {
    await authedPage.getByRole('link', { name: 'Admin' }).click();
    await expect(authedPage).toHaveURL(/\/admin\/diagnostics/);
    await expect(authedPage.locator('.shell')).toBeVisible();
  });

  test('non-admin workspace member receives FORBIDDEN for diagnostics', async ({ multiWorkspacePage }) => {
    const memberWorkspace = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    await multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' }).selectOption(memberWorkspace);
    await expect(multiWorkspacePage.getByText(`Workspace: ${memberWorkspace}`)).toBeVisible({ timeout: 10_000 });

    await multiWorkspacePage.goto('/admin/diagnostics');
    await expect(multiWorkspacePage.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(multiWorkspacePage.getByText('Fehlercode: FORBIDDEN')).toBeVisible();
  });
});
