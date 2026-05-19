/**
 * GUI State Invariants — Truth Flow E2E Tests
 *
 * These checks assert that invalid auth/workspace states never render protected
 * workspace data and controlled failures stay visible.
 */
import { expect, test } from './fixtures.js';

test.describe('11 GUI state invariants', () => {
  test('documents route does not render data controls without validated workspace', async ({ page }) => {
    const token = process.env.TRUTH_NO_MEMBERSHIP_TOKEN || 'truth-token';
    await page.goto('/');
    await page.evaluate((t) => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: t,
        user: { id: 'user-1', login: 'truth-user' },
        memberships: [],
        active_workspace_id: '',
      }));
      window.localStorage.setItem('wissen.authToken', t);
    }, token);

    const documentRequests = [];
    page.on('request', (req) => {
      if (req.url().includes('127.0.0.1:8000/documents') && req.method() === 'GET') {
        documentRequests.push(req.url());
      }
    });

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Dokument hochladen')).not.toBeVisible();
    await expect(page.getByText('Chunk-Suche')).not.toBeVisible();
    expect(documentRequests).toHaveLength(0);
  });

  test('API_UNREACHABLE on documents is not rendered as empty list', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: 'truth-token',
        user: { id: 'user-1', login: 'truth-user' },
        memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
        active_workspace_id: 'workspace-1',
      }));
      window.localStorage.setItem('wissen.authToken', 'truth-token');
      window.localStorage.setItem('wissen.workspaceId', 'workspace-1');
    });
    await page.route('**/documents?**', (route) => route.abort('failed'));

    await page.goto('/documents');

    await expect(page.getByRole('heading', { name: 'Backend nicht erreichbar' })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Fehlercode: API_UNREACHABLE')).toBeVisible();
    await expect(page.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  });

  test('FORBIDDEN bootstrap state has no retry action', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN || 'truth-token';
    let authMeCalls = 0;

    await page.goto('/');
    await page.evaluate((t) => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: t,
        user: null,
        memberships: [],
        active_workspace_id: '',
      }));
      window.localStorage.setItem('wissen.authToken', t);
    }, token);
    await page.route('**/auth/me', (route) => {
      authMeCalls += 1;
      return route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied', details: {} } }),
      });
    });

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole('button', { name: 'Erneut versuchen' })).not.toBeVisible();
    await page.waitForTimeout(500);
    expect(authMeCalls).toBe(1);
  });
});
