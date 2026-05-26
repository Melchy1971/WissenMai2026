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

Locator: getByRole('heading', { name: 'Anmeldung' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('heading', { name: 'Anmeldung' })

```

# Test source

```ts
  1  | import { expect, test } from '@playwright/test';
  2  | 
  3  | test.describe('01 Login flow', () => {
  4  |   test('renders login form with all required elements', async ({ page }) => {
  5  |     await page.goto('/login');
  6  |     await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible();
  7  |     await expect(page.getByLabel('Login')).toBeVisible();
  8  |     await expect(page.getByLabel('Passwort')).toBeVisible();
  9  |     await expect(page.getByRole('button', { name: 'Anmelden' })).toBeVisible();
  10 |   });
  11 | 
  12 |   test('redirects unauthenticated request to login page', async ({ page }) => {
  13 |     await page.goto('/documents');
> 14 |     await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible();
     |                                                                    ^ Error: expect(locator).toBeVisible() failed
  15 |   });
  16 | 
  17 |   test('shows error state on invalid credentials', async ({ page }) => {
  18 |     await page.goto('/login');
  19 |     await page.getByLabel('Login').fill('nonexistent_user_xyz_000');
  20 |     await page.getByLabel('Passwort').fill('wrong_password_xyz_000');
  21 |     await page.getByRole('button', { name: 'Anmelden' }).click();
  22 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
  23 |   });
  24 | 
  25 |   test('successful login with truth credentials redirects to documents page', async ({ page }) => {
  26 |     const login = process.env.TRUTH_LOGIN;
  27 |     const password = process.env.TRUTH_PASSWORD;
  28 | 
  29 |     await page.goto('/login');
  30 |     await page.getByLabel('Login').fill(login);
  31 |     await page.getByLabel('Passwort').fill(password);
  32 |     await page.getByRole('button', { name: 'Anmelden' }).click();
  33 | 
  34 |     await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  35 |   });
  36 | });
  37 | 
```