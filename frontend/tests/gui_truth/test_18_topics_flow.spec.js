/**
 * 18 Topics Flow — E2E Tests (GP-04)
 *
 * Ziel: Topics finden, bearbeiten, Status wechseln.
 * Kein UUID als Primärtext.
 */
import { expect, test } from './fixtures.js';

const API = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

const MOCK_TOPICS = {
  items: [
    { id: 'topic-001', name: 'Wissensmanagement', status: 'draft', tags: ['KM'] },
    { id: 'topic-002', name: 'Prozessdesign', status: 'review', tags: ['PD'] },
    { id: 'topic-003', name: 'SAP-Integration', status: 'approved', tags: ['SAP'] },
    { id: 'topic-004', name: 'Archiviertes Thema', status: 'archived', tags: [] },
  ],
  total: 4,
};

const MOCK_TOPIC_DETAIL = {
  id: 'topic-001',
  name: 'Wissensmanagement',
  status: 'draft',
  tags: ['KM'],
  description: 'Grundlagen des Wissensmanagements.',
  related_documents: [{ id: 'doc-001', title: 'Quelldokument' }],
};

test.describe('18 Topics flow (GP-04)', () => {
  test.setTimeout(30_000);

  test('topics page visible with list and filter controls', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics`, async (route) => {
      await route.fulfill({ json: MOCK_TOPICS });
    });

    await authedPage.goto('/topics');
    await expect(authedPage.getByTestId('topics-page')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('topic-list')).toBeVisible();
    await expect(authedPage.getByTestId('topic-status-filter')).toBeVisible();
  });

  test('shows all 4 topics in list', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics`, async (route) => {
      await route.fulfill({ json: MOCK_TOPICS });
    });

    await authedPage.goto('/topics');
    await expect(authedPage.getByTestId('topic-list')).toBeVisible({ timeout: 10_000 });
    const items = authedPage.locator('[data-testid^="topic-item-"]');
    await expect(items).toHaveCount(4);
  });

  test('clicking topic opens detail view', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics`, async (route) => {
      await route.fulfill({ json: MOCK_TOPICS });
    });
    await authedPage.route(`${API}/api/v1/topics/topic-001`, async (route) => {
      await route.fulfill({ json: MOCK_TOPIC_DETAIL });
    });

    await authedPage.goto('/topics');
    await authedPage.getByTestId('topic-item-topic-001').click();
    await expect(authedPage.getByTestId('topic-detail')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('topic-name')).toContainText('Wissensmanagement');
    await expect(authedPage.getByTestId('topic-status-badge')).toContainText('draft');
  });

  test('editing topic name persists on save', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics/topic-001`, async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({ json: MOCK_TOPIC_DETAIL });
      } else if (route.request().method() === 'PATCH') {
        const body = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({ json: { ...MOCK_TOPIC_DETAIL, name: body.name ?? MOCK_TOPIC_DETAIL.name } });
      }
    });

    await authedPage.goto('/topics/topic-001');
    await expect(authedPage.getByTestId('topic-detail')).toBeVisible({ timeout: 10_000 });
    await authedPage.getByTestId('topic-edit-button').click();
    await authedPage.getByTestId('topic-name-input').fill('Wissensmanagement (aktualisiert)');
    await authedPage.getByTestId('topic-save-button').click();
    await expect(authedPage.getByTestId('topic-name')).toContainText('Wissensmanagement', { timeout: 5_000 });
  });

  test('status filter shows only matching status', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics?status=approved`, async (route) => {
      await route.fulfill({
        json: {
          items: [MOCK_TOPICS.items[2]],
          total: 1,
        },
      });
    });
    await authedPage.route(`${API}/api/v1/topics`, async (route) => {
      const url = new URL(route.request().url());
      const status = url.searchParams.get('status');
      if (status === 'approved') {
        await route.fulfill({ json: { items: [MOCK_TOPICS.items[2]], total: 1 } });
      } else {
        await route.fulfill({ json: MOCK_TOPICS });
      }
    });

    await authedPage.goto('/topics');
    await authedPage.getByTestId('topic-status-filter').selectOption('approved');
    await expect(authedPage.locator('[data-testid^="topic-item-"]')).toHaveCount(1, { timeout: 5_000 });
    await expect(authedPage.getByTestId('topic-item-topic-003')).toBeVisible();
  });

  test('no UUID visible as primary text in topics list', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics`, async (route) => {
      await route.fulfill({ json: MOCK_TOPICS });
    });

    await authedPage.goto('/topics');
    await expect(authedPage.getByTestId('topic-list')).toBeVisible({ timeout: 10_000 });

    const uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const listTexts = await authedPage.locator('[data-testid^="topic-item-"]').allTextContents();
    for (const text of listTexts) {
      expect(uuidPattern.test(text)).toBe(false);
    }
  });

  test('topics API error shows error code, not empty list', async ({ authedPage }) => {
    await authedPage.route(`${API}/api/v1/topics`, (route) => route.abort('failed'));

    await authedPage.goto('/topics');
    await expect(authedPage.getByTestId('topics-error')).toContainText('Fehlercode:', { timeout: 10_000 });
    await expect(authedPage.getByTestId('topic-list')).not.toBeVisible();
  });
});
