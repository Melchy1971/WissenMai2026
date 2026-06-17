/**
 * 15 Export Flow — E2E Tests (GP-07)
 *
 * Ziel: Freigegebenes Ergebnis als PDF/Markdown/JSON exportieren.
 * Regeln:
 * - Draft-Status → kein ExportButton (Guard aktiv, Hinweis-Banner)
 * - Quellen immer eingeschlossen
 * - Keine UUIDs als Primärtext
 * - Nur APPROVED Results exportierbar
 * - Keine echten Secrets
 */
import { expect, test } from './fixtures.js';

const API = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

const MOCK_EXPORT_JOB = {
  id: 'export-job-001',
  status: 'pending',
  format: 'pdf',
  result_id: 'result-approved-001',
  created_at: '2026-06-17T10:05:00Z',
};
const MOCK_EXPORT_JOB_DONE = { ...MOCK_EXPORT_JOB, status: 'completed', download_url: '/api/v1/export/jobs/export-job-001/download' };

const MOCK_TEMPLATES = [
  { id: 'tpl-001', name: 'Standard', formats: ['pdf', 'markdown', 'json'] },
];

const MOCK_DRAFT_RESULT = {
  id: 'result-draft-001',
  status: 'draft',
  summary: 'Draft Analyse.',
  sources: [{ document_id: 'doc-001', title: 'Quelldokument' }],
};

const MOCK_APPROVED_RESULT = {
  id: 'result-approved-001',
  status: 'approved',
  summary: 'Genehmigte Analyse.',
  sources: [{ document_id: 'doc-001', title: 'Quelldokument' }],
};

test.describe('15 Export flow (GP-07)', () => {
  test.setTimeout(30_000);

  test('export center page visible with required controls', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/export/templates`, async (route) => {
      await route.fulfill({ json: MOCK_TEMPLATES });
    });
    await authedPage.goto('/export');
    await expect(authedPage.getByTestId('export-center-page')).toBeVisible();
    await expect(authedPage.getByTestId('export-job-list')).toBeVisible();
  });

  test('draft result shows notice banner, no export button (Guard aktiv)', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_DRAFT_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_DRAFT_RESULT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_DRAFT_RESULT.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    // DRAFT zeigt Hinweis-Banner
    await expect(authedPage.getByTestId('draft-notice')).toBeVisible();
    // Kein ExportButton
    await expect(authedPage.getByTestId('export-button')).not.toBeVisible();
  });

  test('approved result shows export button', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_APPROVED_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_APPROVED_RESULT });
    });
    await authedPage.route(`${API}/api/v1/export/templates`, async (route) => {
      await route.fulfill({ json: MOCK_TEMPLATES });
    });

    await authedPage.goto(`/analysis/results/${MOCK_APPROVED_RESULT.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('export-button')).toBeVisible();
  });

  test('export job transitions pending → completed, download link appears', async ({ authedPage }) => {
    let callCount = 0;
    await authedPage.route(`${API}/api/v1/export/jobs`, async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({ json: MOCK_EXPORT_JOB, status: 201 });
      } else {
        await route.continue();
      }
    });
    await authedPage.route(`${API}/api/v1/export/jobs/${MOCK_EXPORT_JOB.id}`, async (route) => {
      callCount++;
      await route.fulfill({ json: callCount >= 2 ? MOCK_EXPORT_JOB_DONE : MOCK_EXPORT_JOB });
    });
    await authedPage.route(`${API}/api/v1/export/templates`, async (route) => {
      await route.fulfill({ json: MOCK_TEMPLATES });
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_APPROVED_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_APPROVED_RESULT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_APPROVED_RESULT.id}`);
    await expect(authedPage.getByTestId('export-button')).toBeVisible({ timeout: 10_000 });
    await authedPage.getByTestId('export-button').click();

    // Format-Dialog
    await expect(authedPage.getByTestId('export-format-dialog')).toBeVisible({ timeout: 5_000 });
    await authedPage.getByTestId('export-format-pdf').click();
    await authedPage.getByTestId('export-start-button').click();

    await expect(authedPage.getByTestId('export-job-status')).toContainText('pending', { timeout: 5_000 });
    await expect(authedPage.getByTestId('export-download-link')).toBeVisible({ timeout: 20_000 });
  });

  test('export always includes sources in result', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_APPROVED_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_APPROVED_RESULT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_APPROVED_RESULT.id}`);
    await expect(authedPage.getByTestId('result-sources')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('result-sources')).toContainText('Quelldokument');
  });

  test('export API error shows explicit error code', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/export/jobs`, (route) => route.abort('failed'));
    await authedPage.route(`${API}/api/v1/export/templates`, async (route) => {
      await route.fulfill({ json: MOCK_TEMPLATES });
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_APPROVED_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_APPROVED_RESULT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_APPROVED_RESULT.id}`);
    await expect(authedPage.getByTestId('export-button')).toBeVisible({ timeout: 10_000 });
    await authedPage.getByTestId('export-button').click();
    await authedPage.getByTestId('export-start-button').click();
    await expect(authedPage.getByTestId('export-error')).toContainText('Fehlercode:', { timeout: 10_000 });
  });

  test('export center no UUID visible as primary text', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/export/templates`, async (route) => {
      await route.fulfill({ json: MOCK_TEMPLATES });
    });
    await authedPage.route(`${API}/api/v1/export/jobs`, async (route) => {
      await route.fulfill({ json: { items: [MOCK_EXPORT_JOB_DONE] } });
    });

    await authedPage.goto('/export');
    await expect(authedPage.getByTestId('export-center-page')).toBeVisible({ timeout: 10_000 });

    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const headings = await authedPage.locator('h1, h2, h3').allTextContents();
    for (const h of headings) {
      expect(uuidPattern.test(h)).toBe(false);
    }
  });
});
