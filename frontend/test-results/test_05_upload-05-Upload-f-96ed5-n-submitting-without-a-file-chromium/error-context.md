# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_05_upload.spec.js >> 05 Upload flow >> shows error when submitting without a file
- Location: tests\gui_truth\test_05_upload.spec.js:44:7

# Error details

```
Error: locator.click: Error: strict mode violation: locator('button[type="submit"]') resolved to 2 elements:
    1) <button type="submit">Dokument importieren</button> aka getByRole('button', { name: 'Dokument importieren' })
    2) <button type="submit">Suchen</button> aka getByRole('button', { name: 'Suchen' })

Call log:
  - waiting for locator('button[type="submit"]')

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - banner [ref=e4]:
    - generic [ref=e5]:
      - img "Deutsche Telekom" [ref=e6]
      - generic [ref=e9]:
        - paragraph [ref=e10]: Deutsche Telekom
        - generic [ref=e11]: Wissensbasis V1
    - navigation [ref=e12]:
      - generic [ref=e13]:
        - link "Dokumente" [ref=e14] [cursor=pointer]:
          - /url: /documents
        - link "Chat" [ref=e15] [cursor=pointer]:
          - /url: /chat
        - link "Admin" [ref=e16] [cursor=pointer]:
          - /url: /admin/diagnostics
    - generic [ref=e17]:
      - generic [ref=e18]:
        - strong [ref=e19]: GUI Truth User
        - generic [ref=e20]: f1000000-0056-03d1-6f10-58aaed725241
      - button "Abmelden" [ref=e21] [cursor=pointer]
  - main [ref=e22]:
    - generic [ref=e23]:
      - generic [ref=e24]:
        - generic [ref=e25]:
          - paragraph [ref=e26]: Dokumentuebersicht
          - heading "Dokumente" [level=2] [ref=e27]
        - paragraph [ref=e28]: "Workspace: f1000000-0056-03d1-6f10-58aaed725241"
      - generic [ref=e29]:
        - generic [ref=e31]:
          - paragraph [ref=e32]: Lifecycle
          - heading "Sichtbarkeit" [level=3] [ref=e33]
        - generic [ref=e35]:
          - generic [ref=e36]: Statusfilter
          - combobox "Statusfilter" [ref=e37]:
            - option "Nur aktive Dokumente" [selected]
            - option "Nur archivierte Dokumente"
        - generic [ref=e38]:
          - strong [ref=e39]: Hinweis
          - paragraph [ref=e40]: Archivierte Dokumente erscheinen nicht in Suche oder Chat. Geloeschte Dokumente werden in der GUI nicht angezeigt.
      - generic [ref=e41]:
        - generic [ref=e43]:
          - paragraph [ref=e44]: Import
          - heading "Dokument hochladen" [level=3] [ref=e45]
        - generic [ref=e46]:
          - generic [ref=e47]:
            - generic [ref=e48]: Datei
            - button "Datei" [ref=e49]
          - button "Dokument importieren" [ref=e51] [cursor=pointer]
      - generic [ref=e52]:
        - generic [ref=e54]:
          - paragraph [ref=e55]: Einfache Suche
          - heading "Chunk-Suche" [level=3] [ref=e56]
        - generic [ref=e57]:
          - generic [ref=e58]:
            - generic [ref=e59]: Suchbegriff
            - searchbox "Suchbegriff" [ref=e60]
          - generic [ref=e61]:
            - button "Suchen" [ref=e62] [cursor=pointer]
            - button "Zuruecksetzen" [ref=e63] [cursor=pointer]
      - table [ref=e65]:
        - rowgroup [ref=e66]:
          - row "Titel Typ Lifecycle Status Versionen Chunks Aktualisiert" [ref=e67]:
            - columnheader "Titel" [ref=e68]
            - columnheader "Typ" [ref=e69]
            - columnheader "Lifecycle" [ref=e70]
            - columnheader "Status" [ref=e71]
            - columnheader "Versionen" [ref=e72]
            - columnheader "Chunks" [ref=e73]
            - columnheader "Aktualisiert" [ref=e74]
        - rowgroup [ref=e75]:
          - row "GUI Truth Active Document text/plain active Lesbar 1 1 13.05.2026, 12:00" [ref=e76]:
            - cell "GUI Truth Active Document" [ref=e77]:
              - link "GUI Truth Active Document" [ref=e78] [cursor=pointer]:
                - /url: /documents/f3000000-84fd-a1c2-cdd1-14b13214a4cc
            - cell "text/plain" [ref=e79]
            - cell "active" [ref=e80]:
              - generic [ref=e81]: active
            - cell "Lesbar" [ref=e82]:
              - generic [ref=e83]: Lesbar
            - cell "1" [ref=e84]
            - cell "1" [ref=e85]
            - cell "13.05.2026, 12:00" [ref=e86]
```

# Test source

```ts
  1   | import { expect, test } from './fixtures.js';
  2   | import fs from 'node:fs';
  3   | import os from 'node:os';
  4   | import path from 'node:path';
  5   | 
  6   | const BLANK_PDF = `%PDF-1.4
  7   | 1 0 obj
  8   | << /Type /Catalog /Pages 2 0 R >>
  9   | endobj
  10  | 2 0 obj
  11  | << /Type /Pages /Kids [3 0 R] /Count 1 >>
  12  | endobj
  13  | 3 0 obj
  14  | << /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Contents 4 0 R /Resources << >> >>
  15  | endobj
  16  | 4 0 obj
  17  | << /Length 0 >>
  18  | stream
  19  | 
  20  | endstream
  21  | endobj
  22  | xref
  23  | 0 5
  24  | 0000000000 65535 f 
  25  | 0000000009 00000 n 
  26  | 0000000058 00000 n 
  27  | 0000000115 00000 n 
  28  | 0000000220 00000 n 
  29  | trailer
  30  | << /Size 5 /Root 1 0 R >>
  31  | startxref
  32  | 269
  33  | %%EOF`;
  34  | 
  35  | test.describe('05 Upload flow', () => {
  36  |   test.setTimeout(45_000);
  37  | 
  38  |   test('shows upload form elements', async ({ authedPage }) => {
  39  |     await expect(authedPage.getByTestId('upload-panel')).toBeVisible();
  40  |     await expect(authedPage.locator('input[type="file"]')).toBeVisible();
  41  |     await expect(authedPage.locator('button[type="submit"]')).toBeVisible();
  42  |   });
  43  | 
  44  |   test('shows error when submitting without a file', async ({ authedPage }) => {
> 45  |     await authedPage.locator('button[type="submit"]').click();
      |                                                       ^ Error: locator.click: Error: strict mode violation: locator('button[type="submit"]') resolved to 2 elements:
  46  |     await expect(authedPage.getByText('Fehlercode: FILE_REQUIRED')).toBeVisible({ timeout: 5_000 });
  47  |   });
  48  | 
  49  |   test('uploads a text file and completes the import job', async ({ authedPage }) => {
  50  |     const content = `# GUI Truth Import Test\n\nThis document was imported by gui_truth at ${new Date().toISOString()}.`;
  51  | 
  52  |     await authedPage.locator('input[type="file"]').setInputFiles({
  53  |       name: 'gui-truth-import.txt',
  54  |       mimeType: 'text/plain',
  55  |       buffer: Buffer.from(content),
  56  |     });
  57  | 
  58  |     await authedPage.locator('button[type="submit"]').click();
  59  | 
  60  |     // Wait for polling to start
  61  |     await expect(
  62  |       authedPage.getByRole('button', { name: 'Upload laeuft...' }),
  63  |     ).toBeVisible({ timeout: 5_000 });
  64  | 
  65  |     // Wait for completion (success or duplicate)
  66  |     const success = authedPage.getByText(/gui-truth-import\.txt (erfolgreich verarbeitet|bereits vorhanden)/);
  67  |     await expect(success).toBeVisible({ timeout: 30_000 });
  68  |   });
  69  | 
  70  |   test('polls job status and surfaces parser failure', async ({ authedPage }) => {
  71  |     await authedPage.getByLabel('Datei').setInputFiles({
  72  |       name: 'gui-truth-broken.pdf',
  73  |       mimeType: 'application/pdf',
  74  |       buffer: Buffer.from('%PDF-1.7 broken', 'utf-8'),
  75  |     });
  76  |     await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
  77  |     await expect(authedPage.getByRole('button', { name: 'Upload laeuft...' })).toBeVisible({ timeout: 5_000 });
  78  |     await expect(authedPage.getByText('Fehlercode: PARSER_FAILED')).toBeVisible({ timeout: 30_000 });
  79  |     await expect(authedPage.getByText('Technischer Code: IMPORT_FAILED')).toBeVisible();
  80  |   });
  81  | 
  82  |   test('polls job status and surfaces OCR_REQUIRED', async ({ authedPage }) => {
  83  |     await authedPage.getByLabel('Datei').setInputFiles({
  84  |       name: 'gui-truth-blank-scan.pdf',
  85  |       mimeType: 'application/pdf',
  86  |       buffer: Buffer.from(BLANK_PDF, 'utf-8'),
  87  |     });
  88  |     await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
  89  |     await expect(authedPage.getByRole('button', { name: 'Upload laeuft...' })).toBeVisible({ timeout: 5_000 });
  90  |     await expect(authedPage.getByText('Fehlercode: OCR_REQUIRED')).toBeVisible({ timeout: 30_000 });
  91  |   });
  92  | 
  93  |   test('surfaces FILE_TOO_LARGE without creating a successful import', async ({ authedPage }) => {
  94  |     test.setTimeout(90_000);
  95  |     const tooLargePath = path.join(os.tmpdir(), `gui-truth-too-large-${Date.now()}.txt`);
  96  |     fs.writeFileSync(tooLargePath, Buffer.alloc(51 * 1024 * 1024, 'x'));
  97  | 
  98  |     try {
  99  |       await authedPage.getByLabel('Datei').setInputFiles(tooLargePath);
  100 |       await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
  101 |       await expect(authedPage.getByText('Fehlercode: FILE_TOO_LARGE')).toBeVisible({ timeout: 30_000 });
  102 |       await expect(authedPage.getByText('Technischer Code: VALIDATION_ERROR')).toBeVisible();
  103 |     } finally {
  104 |       fs.rmSync(tooLargePath, { force: true });
  105 |     }
  106 |   });
  107 | });
  108 | 
```