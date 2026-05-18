# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_09_diagnostics.spec.js >> 09 Diagnostics GUI >> shows migration status card
- Location: tests\gui_truth\test_09_diagnostics.spec.js:27:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('Migration Status')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByText('Migration Status')

```

```yaml
- paragraph: M4a Auth
- heading "Anmeldung" [level=2]
- paragraph: Lokale Session fuer geschuetzte API-Pfade
- paragraph: Session
- heading "Mit Workspace-Kontext anmelden" [level=3]
- text: Login
- textbox "Login"
- text: Passwort
- textbox "Passwort"
- button "Anmelden"
```

# Test source

```ts
  1  | import { expect, test } from './fixtures.js';
  2  | 
  3  | test.describe('09 Diagnostics GUI', () => {
  4  |   test('shows admin diagnostics page heading', async ({ authedPage }) => {
  5  |     await authedPage.goto('/admin/diagnostics');
  6  |     await expect(authedPage.getByRole('heading', { name: 'Systemdiagnose' })).toBeVisible({ timeout: 10_000 });
  7  |   });
  8  | 
  9  |   test('shows system status card', async ({ authedPage }) => {
  10 |     await authedPage.goto('/admin/diagnostics');
  11 |     await authedPage.waitForTimeout(5_000);
  12 |     const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
  13 |     if (!hasError) {
  14 |       await expect(authedPage.getByText('Systemstatus')).toBeVisible();
  15 |     }
  16 |   });
  17 | 
  18 |   test('shows database status card', async ({ authedPage }) => {
  19 |     await authedPage.goto('/admin/diagnostics');
  20 |     await authedPage.waitForTimeout(5_000);
  21 |     const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
  22 |     if (!hasError) {
  23 |       await expect(authedPage.getByText('DB Status')).toBeVisible();
  24 |     }
  25 |   });
  26 | 
  27 |   test('shows migration status card', async ({ authedPage }) => {
  28 |     await authedPage.goto('/admin/diagnostics');
  29 |     await authedPage.waitForTimeout(5_000);
  30 |     const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
  31 |     if (!hasError) {
> 32 |       await expect(authedPage.getByText('Migration Status')).toBeVisible();
     |                                                              ^ Error: expect(locator).toBeVisible() failed
  33 |     }
  34 |   });
  35 | 
  36 |   test('diagnostics page accessible via admin nav link', async ({ authedPage }) => {
  37 |     await authedPage.getByRole('link', { name: 'Admin' }).click();
  38 |     await expect(authedPage).toHaveURL(/\/admin\/diagnostics/);
  39 |     await expect(authedPage.locator('.shell')).toBeVisible();
  40 |   });
  41 | });
  42 | 
```