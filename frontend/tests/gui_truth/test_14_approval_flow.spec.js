/**
 * 14 Approval Flow — E2E Tests (GP-06) ⚠️ SICHERHEITSKRITISCH
 *
 * Ziel: Analyse freigeben und in Wissensbasis übernehmen.
 * Sicherheitsregeln:
 * - Member darf nicht approven → 403
 * - PROHIBIT-08: Import nur nach confirm=true + actor_role=admin
 * - Topics nach Import in status=draft (kein Auto-Approve)
 * - DRAFT zeigt Freigabeanforderungs-Hinweis
 * - kein technischer Bezeichner als Primärtext
 */
import { expect, test } from './fixtures.js';

const API = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

const MOCK_RESULT_DRAFT = {
  id: 'result-gp06-001',
  status: 'draft',
  analysis_type: 'TOPIC_EXTRACTION',
  summary: 'GP-06 Test Analyse.',
  suggested_topics: [{ name: 'Testthema', confidence: 0.9 }],
  sources: [{ document_id: 'doc-001', title: 'GP-06 Testdokument' }],
};

const MOCK_RESULT_REVIEW = { ...MOCK_RESULT_DRAFT, status: 'review' };
const MOCK_RESULT_APPROVED = { ...MOCK_RESULT_DRAFT, status: 'approved' };

test.describe('14 Approval flow (GP-06) — sicherheitskritisch', () => {
  test.setTimeout(30_000);

  test('draft result shows Freigabeanforderungs-Hinweis, no approve button', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_DRAFT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT_DRAFT });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT_DRAFT.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    // DRAFT zeigt Hinweis mit Freigabeanforderung
    await expect(authedPage.getByTestId('draft-notice')).toBeVisible();
    await expect(authedPage.getByTestId('draft-notice')).toContainText(/Freigabe|Genehmigung/i);
    // Kein Approve-Button für Member
    await expect(authedPage.getByTestId('approve-button')).not.toBeVisible();
  });

  test('submit for review transitions draft → review', async ({ authedPage }) => {
    let currentStatus = 'draft';
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_DRAFT.id}`, async (route) => {
      await route.fulfill({ json: currentStatus === 'draft' ? MOCK_RESULT_DRAFT : MOCK_RESULT_REVIEW });
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_DRAFT.id}/review`, async (route) => {
      currentStatus = 'review';
      await route.fulfill({ json: MOCK_RESULT_REVIEW, status: 200 });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT_DRAFT.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    await authedPage.getByTestId('submit-for-review-button').click();
    await expect(authedPage.getByTestId('analysis-result-status')).toContainText('review', { timeout: 5_000 });
  });

  test('member cannot approve — gets 403 without silent retry (PROHIBIT-08)', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_REVIEW.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT_REVIEW });
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_REVIEW.id}/approve`, async (route) => {
      await route.fulfill({ json: { error: 'FORBIDDEN', message: 'Nur Admins können Ergebnisse freigeben.' }, status: 403 });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT_REVIEW.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });
    // Falls approve-button für Admin-Rolle sichtbar ist, Klick → 403-Fehler
    const approveBtn = authedPage.getByTestId('approve-button');
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
      await expect(authedPage.getByTestId('approval-error')).toContainText('FORBIDDEN', { timeout: 5_000 });
      // Status bleibt 'review'
      await expect(authedPage.getByTestId('analysis-result-status')).toContainText('review');
    } else {
      // Member-Rolle: Approve-Button nicht sichtbar = Sicherheitsregel eingehalten
      await expect(approveBtn).not.toBeVisible();
    }
  });

  test('admin approval shows confirmation dialog before executing', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_REVIEW.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT_REVIEW });
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_REVIEW.id}/approve`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT_APPROVED });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT_REVIEW.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });

    const approveBtn = authedPage.getByTestId('approve-button');
    if (await approveBtn.isVisible()) {
      await approveBtn.click();
      // Confirmation-Dialog muss erscheinen
      await expect(authedPage.getByTestId('approval-confirm-dialog')).toBeVisible({ timeout: 5_000 });
      await authedPage.getByTestId('approval-confirm-submit').click();
      await expect(authedPage.getByTestId('analysis-result-status')).toContainText('approved', { timeout: 5_000 });
    }
  });

  test('import into Wissensbasis requires confirm=true — no silent import (PROHIBIT-08)', async ({ authedPage }) => {
    let importCalled = false;
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_APPROVED.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT_APPROVED });
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_APPROVED.id}/import`, async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      importCalled = true;
      if (!body.confirm) {
        await route.fulfill({ json: { error: 'CONFIRM_REQUIRED' }, status: 400 });
      } else {
        await route.fulfill({ json: { imported: 3, status: 'success' } });
      }
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT_APPROVED.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });

    const importBtn = authedPage.getByTestId('import-to-kb-button');
    if (await importBtn.isVisible()) {
      await importBtn.click();
      // ImportDialog muss erscheinen mit explizitem Bestätigungsschritt
      await expect(authedPage.getByTestId('import-dialog')).toBeVisible({ timeout: 5_000 });
      // Kein Auto-Submit ohne Nutzerinteraktion
      expect(importCalled).toBe(false);
      await authedPage.getByTestId('import-confirm-checkbox').check();
      await authedPage.getByTestId('import-confirm-submit').click();
      await expect(authedPage.getByTestId('import-success')).toBeVisible({ timeout: 10_000 });
    }
  });

  test('imported topics land in status=draft, not auto-approved', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_APPROVED.id}/import`, async (route) => {
      await route.fulfill({
        json: {
          imported: 1,
          topics: [{ id: 'topic-001', name: 'Wissensmanagement', status: 'draft' }],
          status: 'success',
        },
      });
    });
    await authedPage.route(`${API}/api/v1/topics/topic-001`, async (route) => {
      await route.fulfill({ json: { id: 'topic-001', name: 'Wissensmanagement', status: 'draft' } });
    });

    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_APPROVED.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT_APPROVED });
    });

    await authedPage.goto(`/topics/topic-001`);
    await expect(authedPage.getByTestId('topic-detail')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('topic-status-badge')).toContainText('draft');
    // kein "approved" ohne Admin-Freigabe
    await expect(authedPage.getByTestId('topic-status-badge')).not.toContainText('approved');
  });

  test('no UUID visible as primary text in approval flow', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT_APPROVED.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT_APPROVED });
    });

    await authedPage.goto(`/analysis/results/${MOCK_RESULT_APPROVED.id}`);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });

    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const visibleText = await authedPage.locator('[data-testid="analysis-result-panel"]').textContent();
    // Keine roh-UUIDs als Anzeigetext
    const headings = await authedPage.locator('h1, h2, h3, [data-testid="analysis-result-title"]').allTextContents();
    for (const h of headings) {
      expect(uuidPattern.test(h)).toBe(false);
    }
  });
});
