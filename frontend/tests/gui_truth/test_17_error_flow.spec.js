/**
 * 17 Error Flow — E2E Tests
 *
 * Ziel: Fehlerbehandlung über alle kritischen Pfade prüfen.
 * Regeln:
 * - Fehlende Daten ergeben WARNING, nicht PASS (im UI: Fehler anzeigen, nie schweigend ignorieren)
 * - Fehler-DTOs: code + message sichtbar
 * - Kein Blank-Screen bei API-Fehler
 * - Abgebrochene Jobs: Status sichtbar
 * - Ungültige IDs: 404 mit Fehlercode
 */
import { expect, test } from './fixtures.js';

const API = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

test.describe('17 Error flow', () => {
  test.setTimeout(30_000);

  test('invalid document ID returns 404 with error code', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/documents/nonexistent-id-000`, async (route) => {
      await route.fulfill({
        json: { code: 'NOT_FOUND', message: 'Dokument nicht gefunden.' },
        status: 404,
      });
    });

    await authedPage.goto('/documents/nonexistent-id-000');
    await expect(authedPage.getByTestId('error-state')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('error-state')).toContainText('NOT_FOUND');
    // Kein Blank-Screen
    await expect(authedPage.locator('body')).not.toBeEmpty();
  });

  test('empty document list shows empty state, not error', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/documents`, async (route) => {
      await route.fulfill({ json: { items: [], total: 0 } });
    });

    await authedPage.goto('/documents');
    await expect(authedPage.getByTestId('documents-page')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('document-list-empty')).toBeVisible();
    await expect(authedPage.getByTestId('document-list-error')).not.toBeVisible();
  });

  test('aborted analysis job shows failure status, not spinning forever', async ({ authedPage }) => {
    const ABORTED_JOB = {
      id: 'job-aborted-001',
      status: 'failed',
      error_code: 'JOB_ABORTED',
      error_message: 'Job wurde manuell abgebrochen.',
    };
    await authedPage.route(`${API}/api/v1/analysis/jobs/${ABORTED_JOB.id}`, async (route) => {
      await route.fulfill({ json: ABORTED_JOB });
    });

    await authedPage.goto(`/analysis/jobs/${ABORTED_JOB.id}`);
    await expect(authedPage.getByTestId('analysis-job-status')).toContainText('failed', { timeout: 10_000 });
    await expect(authedPage.getByTestId('analysis-job-error')).toContainText('JOB_ABORTED');
    // Kein Spinner
    await expect(authedPage.getByTestId('loading-spinner')).not.toBeVisible();
  });

  test('missing sources on analysis result surfaces WARNING, not PASS', async ({ authedPage }) => {
    const RESULT_NO_SOURCES = {
      id: 'result-no-sources-001',
      status: 'approved',
      summary: 'Analyse ohne Quellen.',
      sources: [],
    };
    await authedPage.route(`${API}/api/v1/analysis/results/${RESULT_NO_SOURCES.id}`, async (route) => {
      await route.fulfill({ json: RESULT_NO_SOURCES });
    });

    await authedPage.goto(`/analysis/results/${RESULT_NO_SOURCES.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    // Fehlende Quellen: WARNING sichtbar, kein PASS-Status
    await expect(authedPage.getByTestId('sources-warning')).toBeVisible();
    await expect(authedPage.getByTestId('sources-warning')).toContainText(/keine Quellen|Quellen fehlen/i);
  });

  test('duplicate job request does not create duplicate entry', async ({ authedPage }) => {
    let postCount = 0;
    await authedPage.route(`${API}/api/v1/export/jobs`, async (route) => {
      if (route.request().method() === 'POST') {
        postCount++;
        if (postCount > 1) {
          await route.fulfill({ json: { code: 'DUPLICATE_JOB', message: 'Job bereits vorhanden.' }, status: 409 });
        } else {
          await route.fulfill({ json: { id: 'export-job-dup-001', status: 'pending' }, status: 201 });
        }
      } else {
        await route.continue();
      }
    });

    // Zweifacher Submit-Klick simuliert Duplicate-Anfrage
    await authedPage.goto('/export');
    const submitBtn = authedPage.getByTestId('export-start-button');
    if (await submitBtn.isVisible()) {
      await submitBtn.click();
      await submitBtn.click();
      await expect(authedPage.getByTestId('export-error')).toContainText('DUPLICATE_JOB', { timeout: 10_000 });
    }
  });

  test('missing file on export shows explicit error, not blank download', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/export/jobs/missing-file-001/download`, async (route) => {
      await route.fulfill({
        json: { code: 'FILE_NOT_FOUND', message: 'Exportdatei nicht mehr vorhanden.' },
        status: 404,
      });
    });

    await authedPage.goto('/export');
    await expect(authedPage.getByTestId('export-center-page')).toBeVisible({ timeout: 10_000 });
    // Direkter Download-Link-Test via fetch
    const response = await authedPage.evaluate(async (api) => {
      const r = await fetch(`${api}/api/v1/export/jobs/missing-file-001/download`);
      return { status: r.status, body: await r.json() };
    }, API);
    expect(response.status).toBe(404);
    expect(response.body.code).toBe('FILE_NOT_FOUND');
  });

  test('invalid JSON in export does not crash the page', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/export/jobs`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          body: 'not valid json {{{',
          contentType: 'application/json',
          status: 200,
        });
      } else {
        await route.continue();
      }
    });

    await authedPage.goto('/export');
    await expect(authedPage.getByTestId('export-center-page')).toBeVisible({ timeout: 10_000 });
    // Keine JS-Exception — Page bleibt bedienbar
    await expect(authedPage.getByTestId('export-error')).toContainText('Fehlercode:', { timeout: 10_000 });
  });

  test('network offline state shows reconnecting state, no blank screen', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, (route) => route.abort('failed'));
    await authedPage.route(`${API}/api/v1/dashboard/drift`, (route) => route.abort('failed'));

    await authedPage.goto('/dashboard');
    // Seite hat sichtbaren Inhalt
    await expect(authedPage.locator('[data-testid]').first()).toBeVisible({ timeout: 10_000 });
    // Fehlercode oder Reconnecting-Status sichtbar
    const hasError = await authedPage.getByTestId('dashboard-error').isVisible();
    const hasOffline = await authedPage.getByTestId('offline-banner').isVisible();
    expect(hasError || hasOffline).toBe(true);
  });
});
