# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_02_auth_bootstrap.spec.js >> 02 Auth bootstrap — 05 backend unreachable >> retry button re-triggers bootstrap
- Location: tests\gui_truth\test_02_auth_bootstrap.spec.js:208:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.state-card--error')
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 15000ms
  - waiting for locator('.state-card--error')

```

# Test source

```ts
  134 | 
  135 |     expect(authMeCalls).toHaveLength(0);
  136 |   });
  137 | });
  138 | 
  139 | // ─── Scenario 04: Invalid token ──────────────────────────────────────────────
  140 | test.describe('02 Auth bootstrap — 04 invalid token', () => {
  141 |   test('shows session-expired error, does not redirect silently', async ({ page }) => {
  142 |     await page.goto('/');
  143 |     await page.evaluate(() => {
  144 |       window.localStorage.setItem('wissen.authState', JSON.stringify({
  145 |         token: 'this-token-is-definitely-invalid-xyz-000',
  146 |         user: null,
  147 |         memberships: [],
  148 |         active_workspace_id: '',
  149 |       }));
  150 |       window.localStorage.setItem('wissen.authToken', 'this-token-is-definitely-invalid-xyz-000');
  151 |     });
  152 |     await page.goto('/documents');
  153 | 
  154 |     // Should show auth error (session expired), NOT silently redirect or show blank page
  155 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  156 |     await expect(page).not.toHaveURL(/\/login/);
  157 |   });
  158 | 
  159 |   test('invalid token error contains session-expired messaging', async ({ page }) => {
  160 |     await page.goto('/');
  161 |     await page.evaluate(() => {
  162 |       window.localStorage.setItem('wissen.authState', JSON.stringify({
  163 |         token: 'invalid-bootstrap-token-xyz-001',
  164 |         user: null,
  165 |         memberships: [],
  166 |         active_workspace_id: '',
  167 |       }));
  168 |       window.localStorage.setItem('wissen.authToken', 'invalid-bootstrap-token-xyz-001');
  169 |     });
  170 |     await page.goto('/documents');
  171 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  172 | 
  173 |     const errorText = await page.locator('.state-card--error').textContent();
  174 |     expect(errorText).toBeTruthy();
  175 |     await expect(page.getByText('Fehlercode: AUTH_REQUIRED')).toBeVisible();
  176 |   });
  177 | });
  178 | 
  179 | // ─── Scenario 05: Backend unreachable ────────────────────────────────────────
  180 | test.describe('02 Auth bootstrap — 05 backend unreachable', () => {
  181 |   test('shows API_UNREACHABLE error with retry button', async ({ page }) => {
  182 |     const token = process.env.TRUTH_TOKEN;
  183 | 
  184 |     await page.goto('/');
  185 |     await page.evaluate(
  186 |       ({ t }) => {
  187 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  188 |           token: t, user: null, memberships: [], active_workspace_id: '',
  189 |         }));
  190 |         window.localStorage.setItem('wissen.authToken', t);
  191 |       },
  192 |       { t: token },
  193 |     );
  194 | 
  195 |     // Intercept GET /auth/me and abort to simulate network failure while keeping CORS preflight recoverable.
  196 |     await page.route('**/auth/me', (route) => {
  197 |       if (route.request().method() === 'GET') return route.abort('failed');
  198 |       return route.continue();
  199 |     });
  200 | 
  201 |     await page.goto('/documents');
  202 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  203 | 
  204 |     // Retry button must be visible for transient errors
  205 |     await expect(page.getByRole('button', { name: 'Erneut versuchen' })).toBeVisible();
  206 |   });
  207 | 
  208 |   test('retry button re-triggers bootstrap', async ({ page }) => {
  209 |     const token = process.env.TRUTH_TOKEN;
  210 |     const authMeCalls = [];
  211 | 
  212 |     await page.goto('/');
  213 |     await page.evaluate(
  214 |       ({ t }) => {
  215 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  216 |           token: t, user: null, memberships: [], active_workspace_id: '',
  217 |         }));
  218 |         window.localStorage.setItem('wissen.authToken', t);
  219 |       },
  220 |       { t: token },
  221 |     );
  222 | 
  223 |     page.on('request', (req) => {
  224 |       if (req.url().includes('/auth/me')) authMeCalls.push(req.url());
  225 |     });
  226 | 
  227 |     let blocked = true;
  228 |     await page.route('**/auth/me', (route) => {
  229 |       if (blocked && route.request().method() === 'GET') return route.abort('failed');
  230 |       return route.continue();
  231 |     });
  232 | 
  233 |     await page.goto('/documents');
> 234 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                                                      ^ Error: expect(locator).toBeVisible() failed
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
  334 |   await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
```