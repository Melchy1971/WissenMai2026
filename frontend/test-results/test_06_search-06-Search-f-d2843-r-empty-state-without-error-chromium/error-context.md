# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_06_search.spec.js >> 06 Search flow >> search returns results or empty state without error
- Location: tests\gui_truth\test_06_search.spec.js:14:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: 'Suchen' })
    - locator resolved to <button type="submit">Suchen</button>
  - attempting click action
    - waiting for element to be visible, enabled and stable
  - element was detached from the DOM, retrying

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
  3  | test.describe('06 Search flow', () => {
  4  |   test('shows search form elements', async ({ authedPage }) => {
  5  |     await expect(authedPage.getByLabel('Suchbegriff')).toBeVisible();
  6  |     await expect(authedPage.getByRole('button', { name: 'Suchen' })).toBeVisible();
  7  |   });
  8  | 
  9  |   test('submitting empty search term shows idle state without error', async ({ authedPage }) => {
  10 |     await authedPage.getByRole('button', { name: 'Suchen' }).click();
  11 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  12 |   });
  13 | 
  14 |   test('search returns results or empty state without error', async ({ authedPage }) => {
  15 |     await authedPage.getByLabel('Suchbegriff').fill('test');
> 16 |     await authedPage.getByRole('button', { name: 'Suchen' }).click();
     |                                                              ^ Error: locator.click: Test timeout of 30000ms exceeded.
  17 | 
  18 |     // Either results appear or empty search state — no error
  19 |     await authedPage.waitForTimeout(3_000);
  20 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  21 |   });
  22 | 
  23 |   test('search with workspace context sends request to real backend', async ({ authedPage }) => {
  24 |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  25 | 
  26 |     // Confirm workspace context is loaded before searching
  27 |     await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  28 | 
  29 |     await authedPage.getByLabel('Suchbegriff').fill('gui truth');
  30 |     await authedPage.getByRole('button', { name: 'Suchen' }).click();
  31 | 
  32 |     // Wait for the backend to respond
  33 |     await authedPage.waitForTimeout(5_000);
  34 | 
  35 |     // Page should not show an authentication error
  36 |     await expect(authedPage.getByText('AUTH_REQUIRED')).not.toBeVisible();
  37 |     await expect(authedPage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
  38 |   });
  39 | });
  40 | 
```