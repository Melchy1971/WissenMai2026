import { expect, test } from '@playwright/test';

test.describe('01 Login flow', () => {
  test('renders login form with all required elements', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByTestId('login-page')).toBeVisible();
    await expect(page.getByTestId('login-email')).toBeVisible();
    await expect(page.getByTestId('login-password')).toBeVisible();
    await expect(page.getByTestId('login-submit')).toBeVisible();
  });

  test('redirects unauthenticated request to login page', async ({ page }) => {
    await page.goto('/documents');
    await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 10_000 });
  });

  test('shows error state on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.getByTestId('login-email').fill('nonexistent_user_xyz_000');
    await page.getByTestId('login-password').fill('wrong_password_xyz_000');
    await page.getByTestId('login-submit').click();
    await expect(page.getByTestId('auth-error')).toBeVisible({ timeout: 10_000 });
  });

  test('successful login with truth credentials redirects to documents page', async ({ page }) => {
    const login = process.env.TRUTH_LOGIN;
    const password = process.env.TRUTH_PASSWORD;

    await page.goto('/login');
    await page.getByTestId('login-email').fill(login);
    await page.getByTestId('login-password').fill(password);
    await page.getByTestId('login-submit').click();

    await expect(page.getByTestId('documents-page')).toBeVisible({ timeout: 15_000 });
  });
});
