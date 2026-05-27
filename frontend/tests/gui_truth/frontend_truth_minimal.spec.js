import { expect, test } from '@playwright/test';

const AUTH_KEYS = ['wissen.authState', 'wissen.authToken', 'wissen.workspaceId'];

async function clearSession(page) {
  await page.goto('/');
  await page.evaluate((keys) => {
    for (const key of keys) window.localStorage.removeItem(key);
  }, AUTH_KEYS);
}

async function login(page) {
  const username = process.env.TRUTH_LOGIN;
  const password = process.env.TRUTH_PASSWORD;

  await clearSession(page);
  await page.goto('/login');
  await page.getByTestId('login-email').fill(username);
  await page.getByTestId('login-password').fill(password);
  await page.getByTestId('login-submit').click();
  await expect(page.getByTestId('documents-page')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('app-shell')).toBeVisible({ timeout: 15_000 });
}

test.describe('Frontend Truth Minimal Vertical Slice', () => {
  test('01 app is reachable', async ({ page }) => {
    await clearSession(page);
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('02 login is visible', async ({ page }) => {
    await clearSession(page);
    await page.goto('/login');
    await expect(page.getByTestId('login-page')).toBeVisible();
    await expect(page.getByTestId('login-email')).toBeVisible();
    await expect(page.getByTestId('login-password')).toBeVisible();
    await expect(page.getByTestId('login-submit')).toBeVisible();
  });

  test('03 login succeeds', async ({ page }) => {
    await login(page);
  });

  test('04 workspace is ready', async ({ page }) => {
    await login(page);
    await expect(page.getByTestId('app-shell')).toContainText(process.env.TRUTH_WORKSPACE_ID);
  });

  test('05 document list is visible', async ({ page }) => {
    await login(page);
    await expect(page.getByTestId('document-list')).toBeVisible({ timeout: 15_000 });
  });

  test('06 logout works', async ({ page }) => {
    await login(page);
    await page.getByRole('button', { name: 'Abmelden' }).click();
    await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 15_000 });
    await expect(page.evaluate(() => window.localStorage.getItem('wissen.authToken'))).resolves.toBeNull();
  });
});
