# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_02_auth_bootstrap.spec.js >> 02 Auth bootstrap — 08 logout >> logout clears session and redirects to login
- Location: tests\gui_truth\test_02_auth_bootstrap.spec.js:338:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'Dokumente', exact: true })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 15000ms
  - waiting for getByRole('heading', { name: 'Dokumente', exact: true })

```

```yaml
- text: "{\"error\":{\"code\":\"AUTH_REQUIRED\",\"message\":\"Authentication required\",\"details\":{}}}"
```

# Test source

```ts
  234 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  235 | 
  236 |     // Unblock and click retry
  237 |     blocked = false;
  238 |     await page.getByRole('button', { name: 'Erneut versuchen' }).click();
  239 |     await expect.poll(() => authMeCalls.length, { timeout: 15_000 }).toBeGreaterThanOrEqual(2);
  240 |     await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  241 |   });
  242 | });
  243 | 
  244 | // ─── Scenario 06: No workspace membership ────────────────────────────────────
  245 | test.describe('02 Auth bootstrap — 06 no workspace membership', () => {
  246 |   test('shows workspace-not-configured error for user with no memberships', async ({ noMembershipPage }) => {
  247 |     await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  248 |   });
  249 | 
  250 |   test('no-membership error is not AUTH_SESSION_EXPIRED', async ({ noMembershipPage }) => {
  251 |     await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  252 |     // User IS authenticated (valid token) — should NOT see "Session abgelaufen"
  253 |     const errorText = await noMembershipPage.locator('.state-card--error').textContent();
  254 |     expect(errorText).not.toContain('Session abgelaufen');
  255 |   });
  256 | });
  257 | 
  258 | // ─── Scenario 07: 403 from /auth/me ──────────────────────────────────────────
  259 | test.describe('02 Auth bootstrap — 07 forbidden', () => {
  260 |   test('shows error state on 403 from /auth/me', async ({ page }) => {
  261 |     const token = process.env.TRUTH_TOKEN;
  262 | 
  263 |     await page.goto('/');
  264 |     await page.evaluate(
  265 |       ({ t }) => {
  266 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  267 |           token: t, user: null, memberships: [], active_workspace_id: '',
  268 |         }));
  269 |         window.localStorage.setItem('wissen.authToken', t);
  270 |       },
  271 |       { t: token },
  272 |     );
  273 | 
  274 |     await page.route('**/auth/me', (route) =>
  275 |       route.fulfill({
  276 |         status: 403,
  277 |         contentType: 'application/json',
  278 |         body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied' } }),
  279 |       }),
  280 |     );
  281 | 
  282 |     await page.goto('/documents');
  283 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  284 |     await expect(page).not.toHaveURL(/\/login/);
  285 |   });
  286 | 
  287 |   test('403 error does not show retry button', async ({ page }) => {
  288 |     const token = process.env.TRUTH_TOKEN;
  289 | 
  290 |     await page.goto('/');
  291 |     await page.evaluate(
  292 |       ({ t }) => {
  293 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  294 |           token: t, user: null, memberships: [], active_workspace_id: '',
  295 |         }));
  296 |         window.localStorage.setItem('wissen.authToken', t);
  297 |       },
  298 |       { t: token },
  299 |     );
  300 | 
  301 |     await page.route('**/auth/me', (route) =>
  302 |       route.fulfill({
  303 |         status: 403,
  304 |         contentType: 'application/json',
  305 |         body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied' } }),
  306 |       }),
  307 |     );
  308 | 
  309 |     await page.goto('/documents');
  310 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  311 |     await expect(page.getByRole('button', { name: 'Erneut versuchen' })).not.toBeVisible();
  312 |   });
  313 | });
  314 | 
  315 | // ─── Scenario 08: Logout ─────────────────────────────────────────────────────
  316 | async function loginForLogoutScenario(page) {
  317 |   const apiBaseUrl = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';
  318 |   const response = await page.request.post(`${apiBaseUrl}/api/v1/auth/login`, {
  319 |     data: {
  320 |       login: process.env.TRUTH_LOGIN,
  321 |       password: process.env.TRUTH_PASSWORD,
  322 |     },
  323 |   });
  324 |   expect(response.ok()).toBeTruthy();
  325 |   const authState = await response.json();
  326 | 
  327 |   await page.goto('/');
  328 |   await page.evaluate((state) => {
  329 |     window.localStorage.setItem('wissen.authState', JSON.stringify(state));
  330 |     window.localStorage.setItem('wissen.authToken', state.token);
  331 |     window.localStorage.setItem('wissen.workspaceId', state.active_workspace_id);
  332 |   }, authState);
  333 |   await page.goto('/documents');
> 334 |   await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
      |                                                                               ^ Error: expect(locator).toBeVisible() failed
  335 | }
  336 | 
  337 | test.describe('02 Auth bootstrap — 08 logout', () => {
  338 |   test('logout clears session and redirects to login', async ({ page }) => {
  339 |     await loginForLogoutScenario(page);
  340 |     await page.getByRole('button', { name: 'Abmelden' }).click({ force: true });
  341 |     await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  342 |     await expect(page).toHaveURL(/\/login/);
  343 |   });
  344 | 
  345 |   test('after logout, navigating to /documents redirects to login', async ({ page }) => {
  346 |     await loginForLogoutScenario(page);
  347 |     await page.getByRole('button', { name: 'Abmelden' }).click({ force: true });
  348 |     await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  349 | 
  350 |     await page.goto('/documents');
  351 |     await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 5_000 });
  352 |   });
  353 | 
  354 |   test('after logout, localStorage is cleared', async ({ page }) => {
  355 |     await loginForLogoutScenario(page);
  356 |     await page.getByRole('button', { name: 'Abmelden' }).click({ force: true });
  357 |     await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  358 | 
  359 |     const stored = await page.evaluate(() => window.localStorage.getItem('wissen.authToken'));
  360 |     expect(stored).toBeNull();
  361 |   });
  362 | 
  363 |   test('after logout, a fresh login restores workspace ready state', async ({ page }) => {
  364 |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  365 | 
  366 |     await loginForLogoutScenario(page);
  367 |     await page.getByRole('button', { name: 'Abmelden' }).click({ force: true });
  368 |     await expect(page.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  369 | 
  370 |     await page.getByLabel('Login').fill(process.env.TRUTH_LOGIN);
  371 |     await page.getByLabel('Passwort').fill(process.env.TRUTH_PASSWORD);
  372 |     await page.getByRole('button', { name: 'Anmelden' }).click();
  373 | 
  374 |     await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  375 |     await expect(page.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  376 |   });
  377 | });
  378 | 
```