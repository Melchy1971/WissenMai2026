import { expect, test } from './fixtures.js';

test.describe('05 Upload flow', () => {
  test.setTimeout(45_000);

  test('shows upload form elements', async ({ authedPage }) => {
    await expect(authedPage.getByRole('heading', { name: 'Dokument hochladen' })).toBeVisible();
    await expect(authedPage.getByLabel('Datei')).toBeVisible();
    await expect(authedPage.getByRole('button', { name: 'Dokument importieren' })).toBeVisible();
  });

  test('shows error when submitting without a file', async ({ authedPage }) => {
    await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();
    await expect(authedPage.getByText('Fehlercode: FILE_REQUIRED')).toBeVisible({ timeout: 5_000 });
  });

  test('uploads a text file and completes the import job', async ({ authedPage }) => {
    const content = `# GUI Truth Import Test\n\nThis document was imported by gui_truth at ${new Date().toISOString()}.`;

    await authedPage.getByLabel('Datei').setInputFiles({
      name: 'gui-truth-import.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from(content),
    });

    await authedPage.getByRole('button', { name: 'Dokument importieren' }).click();

    // Wait for polling to start
    await expect(
      authedPage.getByRole('button', { name: 'Upload laeuft...' }),
    ).toBeVisible({ timeout: 5_000 });

    // Wait for completion (success or duplicate)
    const success = authedPage.getByText(/gui-truth-import\.txt (erfolgreich verarbeitet|bereits vorhanden)/);
    await expect(success).toBeVisible({ timeout: 30_000 });
  });
});
