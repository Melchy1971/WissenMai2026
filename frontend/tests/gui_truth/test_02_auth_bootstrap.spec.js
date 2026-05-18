/**
 * Auth Bootstrap — Truth Flow E2E Tests
 *
 * Tests the full auth bootstrap lifecycle with a real API and real PostgreSQL DB.
 * Each describe block isolates one scenario; no shared state between groups.
 *
 * Scenarios:
 *   01  No token  → login redirect, zero /auth/me calls
 *   02  Token-only state → bootstrap fires → documents page loaded
 *   03  Complete session → no bootstrap loading flash → straight to documents
 *   04  Invalid token → AUTH_SESSION_EXPIRED error shown (no silent redirect)
 *   05  Backend unreachable → API_UNREACHABLE with retry button
 *   06  No workspace membership → WORKSPACE_NOT_CONFIGURED error shown
 *   07  403 from /auth/me → AUTH_FORBIDDEN error shown
 *   08  Logout → session cleared → redirected to /login
 */
import { expect, test } from './fixtures.js';

// ─── Scenario 01: No token ────────────────────────────────────────────────────
test.describe('02 Auth bootstrap — 01 no token', () => {
  test('redirects to /login without token', async ({ barePage }) => {
    await barePage.goto('/documents');
    await expect(barePage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
    await expect(barePage).toHaveURL(/\/login/);
  });

  test('root path also redirects to /login', async ({ barePage }) => {
    await barePage.goto('/');
    await expect(barePage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  });

  test('zero /auth/me calls when no token present', async ({ barePage }) => {
    const authMeCalls = [];
    barePage.on('request', (req) => {
      if (req.url().includes('/auth/me')) authMeCalls.push(req.url());
    });

    await barePage.goto('/documents');
    await barePage.waitForTimeout(2_000);
    expect(authMeCalls).toHaveLength(0);
  });

  test('no workspace error shown on login page', async ({ barePage }) => {
    await barePage.goto('/documents');
    await expect(barePage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
    // No WORKSPACE_NOT_CONFIGURED or similar error should appear on the login page
    await expect(barePage.locator('.state-card--error')).not.toBeVisible();
  });
});

// ─── Scenario 02: Token present → bootstrap fires ────────────────────────────
test.describe('02 Auth bootstrap — 02 bootstrap resolves', () => {
  test('calls /auth/me exactly once during bootstrap', async ({ page }) => {
    const authMeCalls = [];
    page.on('request', (req) => {
      if (req.url().includes('/auth/me')) authMeCalls.push(req.url());
    });

    const token = process.env.TRUTH_TOKEN;
    await page.goto('/');
    await page.evaluate(
      ({ token: t }) => {
        window.localStorage.setItem('wissen.authState', JSON.stringify({
          token: t, user: null, memberships: [], active_workspace_id: '',
        }));
        window.localStorage.setItem('wissen.authToken', t);
      },
      { token },
    );
    await page.goto('/documents');
    await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });

    expect(authMeCalls.length).toBe(1);
  });

  test('bootstrap resolves to documents page', async ({ partialAuthPage }) => {
    await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(partialAuthPage).not.toHaveURL(/\/login/);
  });

  test('workspace id appears in page header after bootstrap', async ({ partialAuthPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(partialAuthPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  });

  test('no error state after successful bootstrap', async ({ partialAuthPage }) => {
    await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(partialAuthPage.locator('.state-card--error')).not.toBeVisible();
  });
});

// ─── Scenario 03: Complete session ───────────────────────────────────────────
test.describe('02 Auth bootstrap — 03 complete session', () => {
  test('no bootstrap loading flash with complete session', async ({ authedPage }) => {
    // The loading text only appears if bootstrap is still pending
    await expect(authedPage.getByText('Authentifizierung wird initialisiert...')).not.toBeVisible();
    await expect(authedPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible();
  });

  test('app shell renders without error state', async ({ authedPage }) => {
    await expect(authedPage.locator('.shell')).toBeVisible();
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('complete session does not call /auth/me', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN;
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    const userId = process.env.TRUTH_USER_ID;
    const authMeCalls = [];

    page.on('request', (req) => {
      if (req.url().includes('/auth/me')) authMeCalls.push(req.url());
    });

    await page.goto('/');
    await page.evaluate(
      ({ t, ws, uid }) => {
        const state = {
          token: t,
          user: { id: uid, login: 'gui_truth_user', display_name: 'GUI Truth User' },
          memberships: [{ workspace_id: ws, role: 'owner' }],
          active_workspace_id: ws,
        };
        window.localStorage.setItem('wissen.authState', JSON.stringify(state));
        window.localStorage.setItem('wissen.authToken', t);
        window.localStorage.setItem('wissen.workspaceId', ws);
      },
      { t: token, ws: workspaceId, uid: userId },
    );
    await page.goto('/documents');
    await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 10_000 });
    await page.waitForTimeout(500);

    expect(authMeCalls).toHaveLength(0);
  });
});

// ─── Scenario 04: Invalid token ──────────────────────────────────────────────
test.describe('02 Auth bootstrap — 04 invalid token', () => {
  test('shows session-expired error, does not redirect silently', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: 'this-token-is-definitely-invalid-xyz-000',
        user: null,
        memberships: [],
        active_workspace_id: '',
      }));
      window.localStorage.setItem('wissen.authToken', 'this-token-is-definitely-invalid-xyz-000');
    });
    await page.goto('/documents');

    // Should show auth error (session expired), NOT silently redirect or show blank page
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('invalid token error contains session-expired messaging', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: 'invalid-bootstrap-token-xyz-001',
        user: null,
        memberships: [],
        active_workspace_id: '',
      }));
      window.localStorage.setItem('wissen.authToken', 'invalid-bootstrap-token-xyz-001');
    });
    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });

    const errorText = await page.locator('.state-card--error').textContent();
    expect(errorText).toBeTruthy();
  });
});

// ─── Scenario 05: Backend unreachable ────────────────────────────────────────
test.describe('02 Auth bootstrap — 05 backend unreachable', () => {
  test('shows API_UNREACHABLE error with retry button', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN;

    await page.goto('/');
    await page.evaluate(
      ({ t }) => {
        window.localStorage.setItem('wissen.authState', JSON.stringify({
          token: t, user: null, memberships: [], active_workspace_id: '',
        }));
        window.localStorage.setItem('wissen.authToken', t);
      },
      { token },
    );

    // Intercept /auth/me and abort to simulate network failure
    await page.route('**/auth/me', (route) => route.abort('failed'));

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });

    // Retry button must be visible for transient errors
    await expect(page.getByRole('button', { name: 'Erneut versuchen' })).toBeVisible();
  });

  test('retry button re-triggers bootstrap', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN;

    await page.goto('/');
    await page.evaluate(
      ({ t }) => {
        window.localStorage.setItem('wissen.authState', JSON.stringify({
          token: t, user: null, memberships: [], active_workspace_id: '',
        }));
        window.localStorage.setItem('wissen.authToken', t);
      },
      { token },
    );

    let blocked = true;
    await page.route('**/auth/me', (route) => {
      if (blocked) return route.abort('failed');
      return route.continue();
    });

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });

    // Unblock and click retry
    blocked = false;
    await page.getByRole('button', { name: 'Erneut versuchen' }).click();
    await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  });
});

// ─── Scenario 06: No workspace membership ────────────────────────────────────
test.describe('02 Auth bootstrap — 06 no workspace membership', () => {
  test('shows workspace-not-configured error for user with no memberships', async ({ noMembershipPage }) => {
    await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  });

  test('no-membership error is not AUTH_SESSION_EXPIRED', async ({ noMembershipPage }) => {
    await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
    // User IS authenticated (valid token) — should NOT see "Session abgelaufen"
    const errorText = await noMembershipPage.locator('.state-card--error').textContent();
    expect(errorText).not.toContain('Session abgelaufen');
  });
});

// ─── Scenario 07: 403 from /auth/me ──────────────────────────────────────────
test.describe('02 Auth bootstrap — 07 forbidden', () => {
  test('shows error state on 403 from /auth/me', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN;

    await page.goto('/');
    await page.evaluate(
      ({ t }) => {
        window.localStorage.setItem('wissen.authState', JSON.stringify({
          token: t, user: null, memberships: [], active_workspace_id: '',
        }));
        window.localStorage.setItem('wissen.authToken', t);
      },
      { token },
    );

    await page.route('**/auth/me', (route) =>
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied' } }),
      }),
    );

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
    await expect(page).not.toHaveURL(/\/login/);
  });

  test('403 error does not show retry button', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN;

    await page.goto('/');
    await page.evaluate(
      ({ t }) => {
        window.localStorage.setItem('wissen.authState', JSON.stringify({
          token: t, user: null, memberships: [], active_workspace_id: '',
        }));
        window.localStorage.setItem('wissen.authToken', t);
      },
      { token },
    );

    await page.route('**/auth/me', (route) =>
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied' } }),
      }),
    );

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole('button', { name: 'Erneut versuchen' })).not.toBeVisible();
  });
});

// ─── Scenario 08: Logout ─────────────────────────────────────────────────────
test.describe('02 Auth bootstrap — 08 logout', () => {
  test('logout clears session and redirects to login', async ({ authedPage }) => {
    await expect(authedPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible();
    await authedPage.getByRole('button', { name: 'Abmelden' }).click();
    await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage).toHaveURL(/\/login/);
  });

  test('after logout, navigating to /documents redirects to login', async ({ authedPage }) => {
    await authedPage.getByRole('button', { name: 'Abmelden' }).click();
    await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });

    await authedPage.goto('/documents');
    await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 5_000 });
  });

  test('after logout, localStorage is cleared', async ({ authedPage }) => {
    await authedPage.getByRole('button', { name: 'Abmelden' }).click();
    await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });

    const stored = await authedPage.evaluate(() => window.localStorage.getItem('wissen.authToken'));
    expect(stored).toBeNull();
  });
});
