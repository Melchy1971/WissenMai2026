# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_05_upload.spec.js >> 05 Upload flow >> shows upload form elements
- Location: tests\gui_truth\test_05_upload.spec.js:6:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('button', { name: 'Dokument importieren' })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for getByRole('button', { name: 'Dokument importieren' })

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
  3  | test.describe('05 Upload flow', () => {
  4  |   test.setTimeout(45_000);
  5  | 
  6  |   test('shows upload form elements', async ({ authedPage }) => {
  7  |     await expect(authedPage.getByRole('heading', { name: 'Dokument hochladen' })).toBeVisible();
  8  |     await expect(authedPage.getByLabel('Datei')).toBeVisible();
> 9  |     await expect(authedPage.getByRole('button', { name: 'Dokument importieren' })).toBeVisible();
     |                                                                                    ^ Error: expect(locator).toBeVisible() failed
  10 |   });
  11 | 
  12 |   test('shows error when submitting without a file', async ({ authedPage }) => {
  13 |     await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
  14 |     await expect(authedPage.getByText('Datei fehlt')).toBeVisible({ timeout: 5_000 });
  15 |   });
  16 | 
  17 |   test('uploads a text file and completes the import job', async ({ authedPage }) => {
  18 |     const content = `# GUI Truth Import Test\n\nThis document was imported by gui_truth at ${new Date().toISOString()}.`;
  19 | 
  20 |     await authedPage.getByLabel('Datei').setInputFiles({
  21 |       name: 'gui-truth-import.txt',
  22 |       mimeType: 'text/plain',
  23 |       buffer: Buffer.from(content),
  24 |     });
  25 | 
  26 |     await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
  27 | 
  28 |     // Wait for polling to start
  29 |     await expect(
  30 |       authedPage.getByRole('button', { name: 'Upload laeuft...' }),
  31 |     ).toBeVisible({ timeout: 5_000 });
  32 | 
  33 |     // Wait for completion (success or duplicate)
  34 |     const success = authedPage.getByText(/gui-truth-import\.txt (erfolgreich verarbeitet|bereits vorhanden)/);
  35 |     await expect(success).toBeVisible({ timeout: 30_000 });
  36 |   });
  37 | });
  38 | 
```