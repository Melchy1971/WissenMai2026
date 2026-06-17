/**
 * 19 ID Leak Gate — E2E Tests
 *
 * Regel: Keine technischen IDs (UUIDs, interne Schluessel, Dateipfade)
 * duerfen als sichtbarer Primaertext in der Endanwender-UI erscheinen.
 *
 * Geprueft: document.id, workspaceId, ownerUserId, userId, jobId,
 * analysisId, exportId, topicId, UUID-Muster, interne Dateipfade.
 *
 * Bereiche: Dashboard, Topics-Liste, Analysis-Job, Export-Center,
 * Drift-Analytics, Error-States.
 */
import { expect, test } from './fixtures.js';

const API = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

// UUID-Regex: blockiert echte UUIDs als sichtbarer Text
const UUID_PATTERN = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

// Interne Dateipfad-Muster
const INTERNAL_PATH_PATTERN = /\/(home|usr|var|tmp|opt|sessions|app|backend|frontend)\/\S+/;

// Mock-Daten mit echten UUID-artigen IDs, um sicherzustellen dass sie NICHT angezeigt werden
const MOCK_SUMMARY = {
  documents_count: 42,
  open_analyses: 3,
  topics_count: 15,
  workspace_name: 'Testzentrale',
  // Interne IDs die NICHT im DOM landen duerfen
  workspace_id: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  owner_user_id: 'f0e1d2c3-b4a5-6789-0123-456789abcdef',
};

const MOCK_DRIFT_OVERVIEW = {
  global_status: 'PASS',
  snapshots: [
    { snapshot_type: 'ID_LEAK_AUDIT', status: 'PASS', score: 100, drift_score: 0.0 },
  ],
};

const MOCK_TOPICS = {
  items: [
    { id: 'c0ffee01-dead-beef-cafe-123456789abc', name: 'Wissensmanagement', status: 'approved', tags: ['KM'] },
    { id: 'deadbeef-cafe-babe-0000-111111111111', name: 'Prozessdesign', status: 'approved', tags: ['PD'] },
  ],
  total: 2,
};

const MOCK_JOB = {
  id: '99999999-8888-7777-6666-555555555555',
  status: 'completed',
  result_id: 'aaaabbbb-cccc-dddd-eeee-ffffffffffff',
  topic_name: 'Wissensmanagement',
  started_at: '2026-06-17T10:00:00Z',
  completed_at: '2026-06-17T10:05:00Z',
};

const MOCK_RESULT = {
  id: 'aaaabbbb-cccc-dddd-eeee-ffffffffffff',
  status: 'approved',
  summary: 'Analyse abgeschlossen.',
  sources: [{ document_id: '11112222-3333-4444-5555-666677778888', title: 'Quelldokument A' }],
  topics: [{ id: 'c0ffee01-dead-beef-cafe-123456789abc', name: 'Wissensmanagement' }],
};

const MOCK_EXPORT_JOBS = {
  items: [
    {
      id: '77778888-9999-aaaa-bbbb-ccccddddeeee',
      status: 'completed',
      format: 'pdf',
      result_id: 'aaaabbbb-cccc-dddd-eeee-ffffffffffff',
      created_at: '2026-06-17T10:06:00Z',
    },
  ],
  total: 1,
};

/**
 * Hilfsfunktion: prueft alle sichtbaren Textknoten im DOM auf UUID-Leak.
 * Gibt Array der gefundenen Leaks zurueck.
 */
async function collectUuidLeaks(page) {
  return page.evaluate((uuidRe) => {
    const re = new RegExp(uuidRe, 'i');
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null,
    );
    const leaks = [];
    let node;
    while ((node = walker.nextNode())) {
      const text = node.textContent.trim();
      if (!text) continue;
      // Attribute ausschliessen (data-testid, href, value) — nur Textknoten
      const parent = node.parentElement;
      if (!parent) continue;
      const tag = parent.tagName.toLowerCase();
      // Script- und Style-Knoten ignorieren
      if (tag === 'script' || tag === 'style' || tag === 'meta') continue;
      if (re.test(text)) {
        leaks.push({ text: text.slice(0, 80), tag });
      }
    }
    return leaks;
  }, UUID_PATTERN.source);
}

async function collectPathLeaks(page) {
  return page.evaluate((pathRe) => {
    const re = new RegExp(pathRe);
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null,
    );
    const leaks = [];
    let node;
    while ((node = walker.nextNode())) {
      const text = node.textContent.trim();
      if (!text) continue;
      const parent = node.parentElement;
      if (!parent) continue;
      const tag = parent.tagName.toLowerCase();
      if (tag === 'script' || tag === 'style' || tag === 'meta') continue;
      if (re.test(text)) {
        leaks.push({ text: text.slice(0, 80), tag });
      }
    }
    return leaks;
  }, INTERNAL_PATH_PATTERN.source);
}

test.describe('19 ID Leak Gate', () => {
  test.setTimeout(30_000);

  test('dashboard: no UUID visible in DOM text nodes', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('dashboard-page')).toBeVisible({ timeout: 10_000 });

    const leaks = await collectUuidLeaks(authedPage);
    expect(leaks, 'UUID-Leak im Dashboard DOM: ' + JSON.stringify(leaks)).toHaveLength(0);
  });

  test('topics list: no UUID visible in DOM text nodes', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics`, async (route) => {
      await route.fulfill({ json: MOCK_TOPICS });
    });

    await authedPage.goto('/topics');
    await expect(authedPage.getByTestId('topic-list')).toBeVisible({ timeout: 10_000 });

    const leaks = await collectUuidLeaks(authedPage);
    expect(leaks, 'UUID-Leak in Topics-Liste DOM: ' + JSON.stringify(leaks)).toHaveLength(0);
  });

  test('analysis job detail: no UUID visible in DOM text nodes', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/jobs/${MOCK_JOB.id}`, async (route) => {
      await route.fulfill({ json: MOCK_JOB });
    });
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT });
    });

    await authedPage.goto('/analysis/jobs/' + MOCK_JOB.id);
    await expect(authedPage.getByTestId('analysis-job-detail')).toBeVisible({ timeout: 10_000 });

    const leaks = await collectUuidLeaks(authedPage);
    expect(leaks, 'UUID-Leak im Analysis-Job-Detail DOM: ' + JSON.stringify(leaks)).toHaveLength(0);
  });

  test('analysis result: no UUID visible in DOM text nodes', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/analysis/results/${MOCK_RESULT.id}`, async (route) => {
      await route.fulfill({ json: MOCK_RESULT });
    });

    await authedPage.goto('/analysis/results/' + MOCK_RESULT.id);
    await expect(authedPage.getByTestId('analysis-result-panel')).toBeVisible({ timeout: 10_000 });

    const leaks = await collectUuidLeaks(authedPage);
    expect(leaks, 'UUID-Leak im Analysis-Result DOM: ' + JSON.stringify(leaks)).toHaveLength(0);
  });

  test('export center: no UUID visible in DOM text nodes', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/export/jobs`, async (route) => {
      await route.fulfill({ json: MOCK_EXPORT_JOBS });
    });
    await authedPage.route(`${API}/api/v1/export/templates`, async (route) => {
      await route.fulfill({ json: [] });
    });

    await authedPage.goto('/export');
    await expect(authedPage.getByTestId('export-center-page')).toBeVisible({ timeout: 10_000 });

    const leaks = await collectUuidLeaks(authedPage);
    expect(leaks, 'UUID-Leak im Export-Center DOM: ' + JSON.stringify(leaks)).toHaveLength(0);
  });

  test('drift analytics: no UUID visible in DOM text nodes', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/drift/ID_LEAK_AUDIT`, async (route) => {
      await route.fulfill({
        json: {
          snapshot_type: 'ID_LEAK_AUDIT',
          status: 'PASS',
          history: [{ date: '2026-06-17', score: 100 }],
          current: { score: 100, drift_score: 0.0 },
        },
      });
    });
    await authedPage.route(`${API}/api/v1/drift/overview`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/drift-analytics/ID_LEAK_AUDIT');
    await expect(authedPage.getByTestId('drift-analytics-page')).toBeVisible({ timeout: 10_000 });

    const leaks = await collectUuidLeaks(authedPage);
    expect(leaks, 'UUID-Leak in Drift-Analytics DOM: ' + JSON.stringify(leaks)).toHaveLength(0);
  });

  test('error state: no UUID or internal path visible in error messages', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/documents/not-found-id`, async (route) => {
      await route.fulfill({
        json: { code: 'NOT_FOUND', message: 'Dokument nicht gefunden.' },
        status: 404,
      });
    });

    await authedPage.goto('/documents/not-found-id');
    await expect(authedPage.getByTestId('error-state')).toBeVisible({ timeout: 10_000 });

    const uuidLeaks = await collectUuidLeaks(authedPage);
    expect(uuidLeaks, 'UUID-Leak in Error-State DOM: ' + JSON.stringify(uuidLeaks)).toHaveLength(0);

    const pathLeaks = await collectPathLeaks(authedPage);
    expect(pathLeaks, 'Dateipfad-Leak in Error-State DOM: ' + JSON.stringify(pathLeaks)).toHaveLength(0);
  });

  test('no internal file paths visible anywhere on dashboard', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('dashboard-page')).toBeVisible({ timeout: 10_000 });

    const pathLeaks = await collectPathLeaks(authedPage);
    expect(pathLeaks, 'Dateipfad-Leak im Dashboard DOM: ' + JSON.stringify(pathLeaks)).toHaveLength(0);
  });
});
