import { expect, test } from '@playwright/test';

test.describe('01 Login flow', () => {
  test('renders login form with all required elements', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible();
    await expect(page.getByLabel('Login')).toBeVisible();
    await expect(page.getByLabel('Passwort')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Anmelden' })).toBeVisible();
  });

  test('redirects unauthenticated request to login page', async ({ page }) => {
    await page.goto('/documents');
    await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible();
  });

  test('shows error state on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel('Login').fill('nonexistent_user_xyz_000');
    await page.getByLabel('Passwort').fill('wrong_password_xyz_000');
    await page.getByRole('button', { name: 'Anmelden' }).click();
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
  });

  test('successful login with truth credentials redirects to documents page', async ({ page }) => {
    const login = process.env.TRUTH_LOGIN;
    const password = process.env.TRUTH_PASSWORD;

    await page.goto('/login');
    await page.getByLabel('Login').fill(login);
    await page.getByLabel('Passwort').fill(password);
    await page.getByRole('button', { name: 'Anmelden' }).click();

    await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  });
});
