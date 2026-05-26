# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_02_auth_bootstrap.spec.js >> 02 Auth bootstrap — 01 no token >> redirects to /login without token
- Location: tests\gui_truth\test_02_auth_bootstrap.spec.js:21:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'Anmeldung' })
Expected: visible
Timeout: 10000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 10000ms
  - waiting for getByRole('heading', { name: 'Anmeldung' })

```

# Test source

```ts
  1   | /**
  2   |  * Auth Bootstrap — Truth Flow E2E Tests
  3   |  *
  4   |  * Tests the full auth bootstrap lifecycle with a real API and real PostgreSQL DB.
  5   |  * Each describe block isolates one scenario; no shared state between groups.
  6   |  *
  7   |  * Scenarios:
  8   |  *   01  No token  → login redirect, zero /auth/me calls
  9   |  *   02  Token-only state → bootstrap fires → documents page loaded
  10  |  *   03  Complete session → no bootstrap loading flash → straight to documents
  11  |  *   04  Invalid token → AUTH_SESSION_EXPIRED error shown (no silent redirect)
  12  |  *   05  Backend unreachable → API_UNREACHABLE with retry button
  13  |  *   06  No workspace membership → WORKSPACE_NOT_CONFIGURED error shown
  14  |  *   07  403 from /auth/me → AUTH_FORBIDDEN error shown
  15  |  *   08  Logout → session cleared → redirected to /login
  16  |  */
  17  | import { expect, test } from './fixtures.js';
  18  | 
  19  | // ─── Scenario 01: No token ────────────────────────────────────────────────────
  20  | test.describe('02 Auth bootstrap — 01 no token', () => {
  21  |   test('redirects to /login without token', async ({ barePage }) => {
  22  |     await barePage.goto('/documents');
> 23  |     await expect(barePage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
      |                                                                        ^ Error: expect(locator).toBeVisible() failed
  24  |     await expect(barePage).toHaveURL(/\/login/);
  25  |   });
  26  | 
  27  |   test('root path also redirects to /login', async ({ barePage }) => {
  28  |     await barePage.goto('/');
  29  |     await expect(barePage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  30  |   });
  31  | 
  32  |   test('zero /auth/me calls when no token present', async ({ barePage }) => {
  33  |     const authMeCalls = [];
  34  |     barePage.on('request', (req) => {
  35  |       if (req.url().includes('/auth/me')) authMeCalls.push(req.url());
  36  |     });
  37  | 
  38  |     await barePage.goto('/documents');
  39  |     await barePage.waitForTimeout(2_000);
  40  |     expect(authMeCalls).toHaveLength(0);
  41  |   });
  42  | 
  43  |   test('no workspace error shown on login page', async ({ barePage }) => {
  44  |     await barePage.goto('/documents');
  45  |     await expect(barePage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  46  |     // No WORKSPACE_NOT_CONFIGURED or similar error should appear on the login page
  47  |     await expect(barePage.locator('.state-card--error')).not.toBeVisible();
  48  |   });
  49  | });
  50  | 
  51  | // ─── Scenario 02: Token present → bootstrap fires ────────────────────────────
  52  | test.describe('02 Auth bootstrap — 02 bootstrap resolves', () => {
  53  |   test('calls /auth/me exactly once during bootstrap', async ({ page }) => {
  54  |     const authMeCalls = [];
  55  |     page.on('request', (req) => {
  56  |       if (req.url().includes('/auth/me')) authMeCalls.push(req.url());
  57  |     });
  58  | 
  59  |     const token = process.env.TRUTH_TOKEN;
  60  |     await page.goto('/');
  61  |     await page.evaluate(
  62  |       ({ token: t }) => {
  63  |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  64  |           token: t, user: null, memberships: [], active_workspace_id: '',
  65  |         }));
  66  |         window.localStorage.setItem('wissen.authToken', t);
  67  |       },
  68  |       { token },
  69  |     );
  70  |     await page.goto('/documents');
  71  |     await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  72  | 
  73  |     expect(authMeCalls.length).toBe(1);
  74  |   });
  75  | 
  76  |   test('bootstrap resolves to documents page', async ({ partialAuthPage }) => {
  77  |     await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  78  |     await expect(partialAuthPage).not.toHaveURL(/\/login/);
  79  |   });
  80  | 
  81  |   test('workspace id appears in page header after bootstrap', async ({ partialAuthPage }) => {
  82  |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  83  |     await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  84  |     await expect(partialAuthPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  85  |   });
  86  | 
  87  |   test('no error state after successful bootstrap', async ({ partialAuthPage }) => {
  88  |     await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  89  |     await expect(partialAuthPage.locator('.state-card--error')).not.toBeVisible();
  90  |   });
  91  | });
  92  | 
  93  | // ─── Scenario 03: Complete session ───────────────────────────────────────────
  94  | test.describe('02 Auth bootstrap — 03 complete session', () => {
  95  |   test('no bootstrap loading flash with complete session', async ({ authedPage }) => {
  96  |     // The loading text only appears if bootstrap is still pending
  97  |     await expect(authedPage.getByText('Authentifizierung wird initialisiert...')).not.toBeVisible();
  98  |     await expect(authedPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible();
  99  |   });
  100 | 
  101 |   test('app shell renders without error state', async ({ authedPage }) => {
  102 |     await expect(authedPage.locator('.shell')).toBeVisible();
  103 |     await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  104 |   });
  105 | 
  106 |   test('complete session does not call /auth/me', async ({ page }) => {
  107 |     const token = process.env.TRUTH_TOKEN;
  108 |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  109 |     const userId = process.env.TRUTH_USER_ID;
  110 |     const authMeCalls = [];
  111 | 
  112 |     page.on('request', (req) => {
  113 |       if (req.url().includes('/auth/me')) authMeCalls.push(req.url());
  114 |     });
  115 | 
  116 |     await page.goto('/');
  117 |     await page.evaluate(
  118 |       ({ t, ws, uid }) => {
  119 |         const state = {
  120 |           token: t,
  121 |           user: { id: uid, login: 'gui_truth_user', display_name: 'GUI Truth User' },
  122 |           memberships: [{ workspace_id: ws, role: 'owner' }],
  123 |           active_workspace_id: ws,
```