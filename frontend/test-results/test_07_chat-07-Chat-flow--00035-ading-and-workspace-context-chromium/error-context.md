# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_07_chat.spec.js >> 07 Chat flow >> shows chat page heading and workspace context
- Location: tests\gui_truth\test_07_chat.spec.js:4:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'Dokumentgestuetzter Chat' })
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for getByRole('heading', { name: 'Dokumentgestuetzter Chat' })

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
  3  | test.describe('07 Chat flow', () => {
  4  |   test('shows chat page heading and workspace context', async ({ authedPage }) => {
  5  |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  6  |     await authedPage.goto('/chat');
> 7  |     await expect(authedPage.getByRole('heading', { name: 'Dokumentgestuetzter Chat' })).toBeVisible({ timeout: 10_000 });
     |                                                                                         ^ Error: expect(locator).toBeVisible() failed
  8  |     await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  9  |   });
  10 | 
  11 |   test('shows empty chat state or session list', async ({ authedPage }) => {
  12 |     await authedPage.goto('/chat');
  13 | 
  14 |     // Either no sessions exist (empty state) or there are existing sessions
  15 |     await authedPage.waitForTimeout(3_000);
  16 |     const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
  17 |     expect(hasError).toBe(false);
  18 |   });
  19 | 
  20 |   test('shows chat composer form', async ({ authedPage }) => {
  21 |     await authedPage.goto('/chat');
  22 |     // Wait for loading to finish
  23 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible({ timeout: 10_000 });
  24 |     await expect(authedPage.getByLabel('Titel der Sitzung')).toBeVisible({ timeout: 5_000 });
  25 |     await expect(authedPage.locator('.chat-layout')).toBeVisible();
  26 |   });
  27 | 
  28 |   test('navigation from documents to chat preserves workspace context', async ({ authedPage }) => {
  29 |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  30 |     // Start on documents
  31 |     await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  32 |     // Navigate to chat
  33 |     await authedPage.getByRole('link', { name: 'Chat' }).click();
  34 |     await expect(authedPage.getByRole('heading', { name: 'Dokumentgestuetzter Chat' })).toBeVisible({ timeout: 10_000 });
  35 |     await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  36 |   });
  37 | });
  38 | 
```