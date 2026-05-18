# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_08_lifecycle.spec.js >> 08 Lifecycle GUI >> switching back to active filter restores document list
- Location: tests\gui_truth\test_08_lifecycle.spec.js:22:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.selectOption: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByLabel('Statusfilter')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - paragraph [ref=e6]: M4a Auth
      - heading "Anmeldung" [level=2] [ref=e7]
    - paragraph [ref=e8]: Lokale Session fuer geschuetzte API-Pfade
  - generic [ref=e9]:
    - generic [ref=e11]:
      - paragraph [ref=e12]: Session
      - heading "Mit Workspace-Kontext anmelden" [level=3] [ref=e13]
    - generic [ref=e14]:
      - generic [ref=e15]:
        - generic [ref=e16]: Login
        - textbox "Login" [ref=e17]
      - generic [ref=e18]:
        - generic [ref=e19]: Passwort
        - textbox "Passwort" [ref=e20]
      - button "Anmelden" [ref=e22] [cursor=pointer]
```

# Test source

```ts
  1  | import { expect, test } from './fixtures.js';
  2  | 
  3  | test.describe('08 Lifecycle GUI', () => {
  4  |   test('shows lifecycle filter with correct default option', async ({ authedPage }) => {
  5  |     const select = authedPage.getByLabel('Statusfilter');
  6  |     await expect(select).toBeVisible();
  7  |     await expect(select).toHaveValue('active');
  8  |   });
  9  | 
  10 |   test('lifecycle filter shows correct option labels', async ({ authedPage }) => {
  11 |     await expect(authedPage.getByRole('option', { name: 'Nur aktive Dokumente' })).toBeAttached();
  12 |     await expect(authedPage.getByRole('option', { name: 'Nur archivierte Dokumente' })).toBeAttached();
  13 |   });
  14 | 
  15 |   test('switching to archived filter triggers API call without error', async ({ authedPage }) => {
  16 |     await authedPage.getByLabel('Statusfilter').selectOption('archived');
  17 |     await authedPage.waitForTimeout(3_000);
  18 |     // Should show empty state or archived documents — no error
  19 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  20 |   });
  21 | 
  22 |   test('switching back to active filter restores document list', async ({ authedPage }) => {
  23 |     const select = authedPage.getByLabel('Statusfilter');
  24 |     await select.selectOption('archived');
  25 |     await authedPage.waitForTimeout(1_000);
> 26 |     await select.selectOption('active');
     |                  ^ Error: locator.selectOption: Test timeout of 30000ms exceeded.
  27 |     await authedPage.waitForTimeout(3_000);
  28 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  29 |   });
  30 | 
  31 |   test('shows lifecycle warning hint text', async ({ authedPage }) => {
  32 |     await expect(
  33 |       authedPage.getByText('Archivierte Dokumente erscheinen nicht in Suche oder Chat.'),
  34 |     ).toBeVisible();
  35 |   });
  36 | });
  37 | 
```