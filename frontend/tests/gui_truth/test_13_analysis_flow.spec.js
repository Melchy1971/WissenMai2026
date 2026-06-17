/**
 * 13 Analysis Flow — E2E Tests (GP-05)
 *
 * Ziel: Analyse-Job starten, Status-Polling durchlaufen, Ergebnis in status=draft anzeigen.
 * Keine echten LLM-Provider — deterministischer Mock via route intercept.
 * Keine echten Secrets in Testdaten.
 * Kein Auto-Approve (PROHIBIT-08).
 */
import { expect, test } from './fixtures.js';

const API = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

// Mock-Responses
const MOCK_JOB = {
  id: 'test-job-analysis-001',
  status: 'pending',
  document_ids: ['doc-001'],
  analysis_type: 'TOPIC_EXTRACTION',
  created_at: '2026-06-17T10:00:00Z',
};
const MOCK_JOB_RUNNING = { ...MOCK_JOB, status: 'running' };
const MOCK_JOB_DONE = { ...MOCK_JOB, status: 'completed', result_id: 'result-001' };

const MOCK_RESULT = {
  id: 'result-001',
  status: 'draft',
  analysis_type: 'TOPIC_EXTRACTION',
  summary: 'Analyse-Zusammenfassung: 3 Topics identifiziert.',
  suggested_topics: [
    { name: 'Wissensmanagement', confidence: 0.92 },
    { name: 'Prozessdesign', confidence: 0.85 },
    { name: 'SAP-Integration', confidence: 0.78 },
  ],
  sources: [{ document_id: 'doc-001', title: 'Testdokument' }],
  created_at: '2026-06-17T10:01:00Z',
};

test.describe('13 Analysis flow (GP-05)', () => {
  test.setTimeout(30_000);

  test('analysis page visible with required controls', async ({ authedPage }) => {
    await authedPage.goto('/analysis');
    await expect(authedPage.getByTestId('analysis-page')).toBeVisible();
    await expect(authedPage.getByTestId('new-analysis-button')).toBeVisible();
    await expect(authedPage.getByTestId('analysis-job-list')).toBeVisible();
  });

  test('opens new analysis wizard on button click', async ({ authedPage }) => {
    await authedPage.goto('/analysis');
    await authedPage.getByTestId('new-analysis-button').click();
    await expect(authedPage.getByTestId('new-analysis-dialog')).toBeVisible({ timeout: 5_000 });
    await expect(authedPage.getByTestId('analysis-wizard-step-1')).toBeVisible();
  });

  test('job transitions pending → running → completed (mock)', async ({ authedPage }) => {
    let callCount = 0;
    await authedPage.route(`${API}/api/v1/analysis/jobs`, async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({ json: MOCK_JOB, status: 201 });
      } else {
        await route.continue();
      }
    });
    await authedPage.route(`${API}/api/v1/analysis/jobs/${MOCK_JOB.id}`, async (route) => {
      callCount++;
      if (callCount === 1) {
        await route.fulfill({ json: MOCK_JOB_RUNNING });
      } else {
        await route.fulfill({ json: MOCK_JOB_DONE });
      }
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT });
    });

    await authedPage.goto('/analysis');
    await authedPage.getByTestId('new-analysis-button').click();
    await authedPage.getByTestId('analysis-submit').click();

    await expect(authedPage.getByTestId('analysis-job-status')).toContainText(/pending|running/, { timeout: 5_000 });
    await expect(authedPage.getByTestId('analysis-job-status')).toContainText('completed', { timeout: 20_000 });
  });

  test('result opens in status=draft, no auto-approve (PROHIBIT-08)', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('analysis-result-status')).toContainText('draft');
    // Kein Auto-Approve-Button sichtbar
    await expect(authedPage.getByTestId('approve-button')).not.toBeVisible();
  });

  test('result shows topics and sources', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('suggested-topics')).toBeVisible();
    await expect(authedPage.getByTestId('result-sources')).toBeVisible();
    // Quellen immer eingeschlossen
    await expect(authedPage.getByTestId('result-sources')).toContainText('Testdokument');
  });

  test('no UUID visible as primary text in result view', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });

    const content = await authedPage.locator('[data-testid="analysis-result-panel"]').textContent();
    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    // UUIDs dürfen nicht in sichtbaren Textnodes erscheinen
    await expect(
      authedPage.locator('[data-testid="analysis-result-panel"] *:not([data-testid]):not([class])').filter({ hasText: uuidPattern }),
    ).toHaveCount(0);
  });

  test('analysis list API error surfaces explicit error code', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/jobs`, (route) => route.abort('failed'));

    await authedPage.goto('/analysis');
    await expect(authedPage.getByTestId('analysis-error')).toContainText('Fehlercode: API_UNREACHABLE', { timeout: 10_000 });
  });
});
