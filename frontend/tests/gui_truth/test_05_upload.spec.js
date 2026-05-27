import { expect, test } from './fixtures.js';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const BLANK_PDF = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] /Contents 4 0 R /Resources << >> >>
endobj
4 0 obj
<< /Length 0 >>
stream

endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000220 00000 n 
trailer
<< /Size 5 /Root 1 0 R >>
startxref
269
%%EOF`;

test.describe('05 Upload flow', () => {
  test.setTimeout(45_000);

  test('shows upload form elements', async ({ authedPage }) => {
    await expect(authedPage.getByTestId('upload-panel')).toBeVisible();
    await expect(authedPage.locator('input[type="file"]')).toBeVisible();
    await expect(authedPage.locator('button[type="submit"]')).toBeVisible();
  });

  test('shows error when submitting without a file', async ({ authedPage }) => {
    await authedPage.locator('button[type="submit"]').click();
    await expect(authedPage.getByText('Fehlercode: FILE_REQUIRED')).toBeVisible({ timeout: 5_000 });
  });

  test('uploads a text file and completes the import job', async ({ authedPage }) => {
    const content = `# GUI Truth Import Test\n\nThis document was imported by gui_truth at ${new Date().toISOString()}.`;

    await authedPage.locator('input[type="file"]').setInputFiles({
      name: 'gui-truth-import.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(content),
    });

    await authedPage.locator('button[type="submit"]').click();

    // Wait for polling to start
    await expect(
      authedPage.getByRole('button', { name: 'Upload laeuft...' }),
    ).toBeVisible({ timeout: 5_000 });

    // Wait for completion (success or duplicate)
    const success = authedPage.getByText(/gui-truth-import\.txt (erfolgreich verarbeitet|bereits vorhanden)/);
    await expect(success).toBeVisible({ timeout: 30_000 });
  });

  test('polls job status and surfaces parser failure', async ({ authedPage }) => {
    await authedPage.getByLabel('Datei').setInputFiles({
      name: 'gui-truth-broken.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.7 broken', 'utf-8'),
    });
    await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
    await expect(authedPage.getByRole('button', { name: 'Upload laeuft...' })).toBeVisible({ timeout: 5_000 });
    await expect(authedPage.getByText('Fehlercode: PARSER_FAILED')).toBeVisible({ timeout: 30_000 });
    await expect(authedPage.getByText('Technischer Code: IMPORT_FAILED')).toBeVisible();
  });

  test('polls job status and surfaces OCR_REQUIRED', async ({ authedPage }) => {
    await authedPage.getByLabel('Datei').setInputFiles({
      name: 'gui-truth-blank-scan.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from(BLANK_PDF, 'utf-8'),
    });
    await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
    await expect(authedPage.getByRole('button', { name: 'Upload laeuft...' })).toBeVisible({ timeout: 5_000 });
    await expect(authedPage.getByText('Fehlercode: OCR_REQUIRED')).toBeVisible({ timeout: 30_000 });
  });

  test('surfaces FILE_TOO_LARGE without creating a successful import', async ({ authedPage }) => {
    test.setTimeout(90_000);
    const tooLargePath = path.join(os.tmpdir(), `gui-truth-too-large-${Date.now()}.txt`);
    fs.writeFileSync(tooLargePath, Buffer.alloc(51 * 1024 * 1024, 'x'));

    try {
      await authedPage.getByLabel('Datei').setInputFiles(tooLargePath);
      await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
      await expect(authedPage.getByText('Fehlercode: FILE_TOO_LARGE')).toBeVisible({ timeout: 30_000 });
      await expect(authedPage.getByText('Technischer Code: VALIDATION_ERROR')).toBeVisible();
    } finally {
      fs.rmSync(tooLargePath, { force: true });
    }
  });
});
