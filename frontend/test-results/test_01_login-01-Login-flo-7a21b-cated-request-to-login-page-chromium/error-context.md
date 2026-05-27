# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_01_login.spec.js >> 01 Login flow >> redirects unauthenticated request to login page
- Location: tests\gui_truth\test_01_login.spec.js:12:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByTestId('login-page')
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for getByTestId('login-page')

```

```yaml
- text: "{\"error\":{\"code\":\"AUTH_REQUIRED\",\"message\":\"Authentication required\",\"details\":{}}}"
```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test';
  2  | 
  3  | test.describe('01 Login flow', () => {
  4  |   test('renders login form with all required elements', async ({ page }) => {
  5  |     await page.goto('/login');
  6  |     await expect(page.getByTestId('login-page')).toBeVisible();
  7  |     await expect(page.getByTestId('login-email')).toBeVisible();
  8  |     await expect(page.getByTestId('login-password')).toBeVisible();
  9  |     await expect(page.getByTestId('login-submit')).toBeVisible();
  10 |   });
  11 | 
  12 |   test('redirects unauthenticated request to login page', async ({ page }) => {
  13 |     await page.goto('/documents');
> 14 |     await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 10_000 });
     |                                                  ^ Error: expect(locator).toBeVisible() failed
  15 |   });
  16 | 
  17 |   test('shows error state on invalid credentials', async ({ page }) => {
  18 |     await page.goto('/login');
  19 |     await page.getByTestId('login-email').fill('nonexistent_user_xyz_000');
  20 |     await page.getByTestId('login-password').fill('wrong_password_xyz_000');
  21 |     await page.getByTestId('login-submit').click();
  22 |     await expect(page.getByTestId('auth-error')).toBeVisible({ timeout: 10_000 });
  23 |   });
  24 | 
  25 |   test('successful login with truth credentials redirects to documents page', async ({ page }) => {
  26 |     const login = process.env.TRUTH_LOGIN;
  27 |     const password = process.env.TRUTH_PASSWORD;
  28 | 
  29 |     await page.goto('/login');
  30 |     await page.getByTestId('login-email').fill(login);
  31 |     await page.getByTestId('login-password').fill(password);
  32 |     await page.getByTestId('login-submit').click();
  33 | 
  34 |     await expect(page.getByTestId('documents-page')).toBeVisible({ timeout: 15_000 });
  35 |   });
  36 | });
  37 | 
```