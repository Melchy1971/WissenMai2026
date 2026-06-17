/**
 * 16 Dashboard & Drift Flow — E2E Tests (GP-08)
 *
 * Ziel: Dashboard Status prüfen, Drift-Widgets sehen, zu Drift Analytics navigieren.
 * Deterministischer Mock, kein Live-Provider.
 */
import { expect, test } from './fixtures.js';

const API = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

const MOCK_SUMMARY = {
  documents_count: 42,
  open_analyses: 3,
  topics_count: 15,
  workspace_name: 'Testzentrale',
};

const MOCK_DRIFT_OVERVIEW = {
  global_status: 'WARNING',
  snapshots: [
    { snapshot_type: 'PRODUCT_MATURITY', status: 'PASS', score: 87, drift_score: 0.04, updated_at: '2026-06-17T09:00:00Z' },
    { snapshot_type: 'GOLD_PATH', status: 'PASS', score: 100, drift_score: 0.0, updated_at: '2026-06-17T09:00:00Z' },
    { snapshot_type: 'TEST_COVERAGE', status: 'WARNING', score: 88, drift_score: 0.12, updated_at: '2026-06-17T09:00:00Z' },
    { snapshot_type: 'RELEASE_GATE', status: 'PASS', score: 92, drift_score: 0.02, updated_at: '2026-06-17T09:00:00Z' },
    { snapshot_type: 'SECURITY_AUDIT', status: 'PASS', score: 95, drift_score: 0.0, updated_at: '2026-06-17T09:00:00Z' },
    { snapshot_type: 'ID_LEAK_AUDIT', status: 'PASS', score: 100, drift_score: 0.0, updated_at: '2026-06-17T09:00:00Z' },
  ],
};

const MOCK_DRIFT_DETAIL = {
  snapshot_type: 'TEST_COVERAGE',
  status: 'WARNING',
  history: [
    { date: '2026-06-15', score: 92 },
    { date: '2026-06-16', score: 90 },
    { date: '2026-06-17', score: 88 },
  ],
  current: { score: 88, drift_score: 0.12 },
};

test.describe('16 Dashboard & Drift flow (GP-08)', () => {
  test.setTimeout(30_000);

  test('dashboard page shows summary widgets', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('dashboard-page')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('summary-documents-count')).toContainText('42');
    await expect(authedPage.getByTestId('summary-open-analyses')).toContainText('3');
    await expect(authedPage.getByTestId('summary-topics-count')).toContainText('15');
  });

  test('drift widget panel shows 6 drift cards', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('drift-widget-panel')).toBeVisible({ timeout: 10_000 });
    const cards = authedPage.locator('[data-testid^="drift-card-"]');
    await expect(cards).toHaveCount(6);
  });

  test('global status bar reflects worst drift status (WARNING)', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('global-status-bar')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('global-status-bar')).toContainText('WARNING');
  });

  test('drift badge visible in AppShell navigation', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('app-shell')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('drift-status-badge')).toBeVisible();
  });

  test('clicking drift card navigates to drift detail page', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });
    await authedPage.route(`${API}/api/v1/drift/overview`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });
    await authedPage.route(`${API}/api/v1/drift/TEST_COVERAGE`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_DETAIL });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('drift-card-TEST_COVERAGE')).toBeVisible({ timeout: 10_000 });
    await authedPage.getByTestId('drift-card-TEST_COVERAGE').click();

    await expect(authedPage).toHaveURL(/drift-analytics\/TEST_COVERAGE|drift\/TEST_COVERAGE/, { timeout: 5_000 });
    await expect(authedPage.getByTestId('drift-analytics-page')).toBeVisible({ timeout: 10_000 });
  });

  test('drift analytics page shows history chart and current status', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/drift/TEST_COVERAGE`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_DETAIL });
    });
    await authedPage.route(`${API}/api/v1/drift/overview`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/drift-analytics/TEST_COVERAGE');
    await expect(authedPage.getByTestId('drift-analytics-page')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('drift-history-chart')).toBeVisible();
    await expect(authedPage.getByTestId('drift-current-score')).toContainText('88');
    await expect(authedPage.getByTestId('drift-status-label')).toContainText('WARNING');
  });

  test('no UUID visible as primary text on dashboard', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, async (route) => {
      await route.fulfill({ json: MOCK_SUMMARY });
    });
    await authedPage.route(`${API}/api/v1/dashboard/drift`, async (route) => {
      await route.fulfill({ json: MOCK_DRIFT_OVERVIEW });
    });

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('dashboard-page')).toBeVisible({ timeout: 10_000 });

    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const headings = await authedPage.locator('h1, h2, h3').allTextContents();
    for (const h of headings) {
      expect(uuidPattern.test(h)).toBe(false);
    }
  });

  test('dashboard API error shows explicit error code, not blank screen', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/dashboard/summary`, (route) => route.abort('failed'));
    await authedPage.route(`${API}/api/v1/dashboard/drift`, (route) => route.abort('failed'));

    await authedPage.goto('/dashboard');
    await expect(authedPage.getByTestId('dashboard-error')).toContainText('Fehlercode:', { timeout: 10_000 });
  });
});
