# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_02_auth_bootstrap.spec.js >> 02 Auth bootstrap — 08 logout >> after logout, navigating to /documents redirects to login
- Location: tests\gui_truth\test_02_auth_bootstrap.spec.js:314:7

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: 'Abmelden' })
    - locator resolved to <button type="button" class="button-secondary">Abmelden</button>
  - attempting click action
    - waiting for element to be visible, enabled and stable
    - element is not stable
  - retrying click action
    - waiting for element to be visible, enabled and stable
  - element was detached from the DOM, retrying

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - generic [ref=e4]:
    - generic [ref=e5]:
      - paragraph [ref=e6]: M4a Auth
      - heading "Anmeldung" [level=2] [ref=e7]
    - paragraph [ref=e8]: Lokale Session fuer geschuetzte API-Pfade
  - generic [ref=e9]:
    - generic [ref=e11]:
      - paragraph [ref=e12]: Session
      - heading "Mit Workspace-Kontext anmelden" [level=3] [ref=e13]
    - generic [ref=e14]:
      - generic [ref=e15]:
        - generic [ref=e16]: Login
        - textbox "Login" [ref=e17]
      - generic [ref=e18]:
        - generic [ref=e19]: Passwort
        - textbox "Passwort" [ref=e20]
      - button "Anmelden" [ref=e22] [cursor=pointer]
```

# Test source

```ts
  215 |       { token },
  216 |     );
  217 | 
  218 |     let blocked = true;
  219 |     await page.route('**/auth/me', (route) => {
  220 |       if (blocked) return route.abort('failed');
  221 |       return route.continue();
  222 |     });
  223 | 
  224 |     await page.goto('/documents');
  225 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  226 | 
  227 |     // Unblock and click retry
  228 |     blocked = false;
  229 |     await page.getByRole('button', { name: 'Erneut versuchen' }).click();
  230 |     await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  231 |   });
  232 | });
  233 | 
  234 | // ─── Scenario 06: No workspace membership ────────────────────────────────────
  235 | test.describe('02 Auth bootstrap — 06 no workspace membership', () => {
  236 |   test('shows workspace-not-configured error for user with no memberships', async ({ noMembershipPage }) => {
  237 |     await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  238 |   });
  239 | 
  240 |   test('no-membership error is not AUTH_SESSION_EXPIRED', async ({ noMembershipPage }) => {
  241 |     await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  242 |     // User IS authenticated (valid token) — should NOT see "Session abgelaufen"
  243 |     const errorText = await noMembershipPage.locator('.state-card--error').textContent();
  244 |     expect(errorText).not.toContain('Session abgelaufen');
  245 |   });
  246 | });
  247 | 
  248 | // ─── Scenario 07: 403 from /auth/me ──────────────────────────────────────────
  249 | test.describe('02 Auth bootstrap — 07 forbidden', () => {
  250 |   test('shows error state on 403 from /auth/me', async ({ page }) => {
  251 |     const token = process.env.TRUTH_TOKEN;
  252 | 
  253 |     await page.goto('/');
  254 |     await page.evaluate(
  255 |       ({ t }) => {
  256 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  257 |           token: t, user: null, memberships: [], active_workspace_id: '',
  258 |         }));
  259 |         window.localStorage.setItem('wissen.authToken', t);
  260 |       },
  261 |       { token },
  262 |     );
  263 | 
  264 |     await page.route('**/auth/me', (route) =>
  265 |       route.fulfill({
  266 |         status: 403,
  267 |         contentType: 'application/json',
  268 |         body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied' } }),
  269 |       }),
  270 |     );
  271 | 
  272 |     await page.goto('/documents');
  273 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  274 |     await expect(page).not.toHaveURL(/\/login/);
  275 |   });
  276 | 
  277 |   test('403 error does not show retry button', async ({ page }) => {
  278 |     const token = process.env.TRUTH_TOKEN;
  279 | 
  280 |     await page.goto('/');
  281 |     await page.evaluate(
  282 |       ({ t }) => {
  283 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  284 |           token: t, user: null, memberships: [], active_workspace_id: '',
  285 |         }));
  286 |         window.localStorage.setItem('wissen.authToken', t);
  287 |       },
  288 |       { token },
  289 |     );
  290 | 
  291 |     await page.route('**/auth/me', (route) =>
  292 |       route.fulfill({
  293 |         status: 403,
  294 |         contentType: 'application/json',
  295 |         body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied' } }),
  296 |       }),
  297 |     );
  298 | 
  299 |     await page.goto('/documents');
  300 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  301 |     await expect(page.getByRole('button', { name: 'Erneut versuchen' })).not.toBeVisible();
  302 |   });
  303 | });
  304 | 
  305 | // ─── Scenario 08: Logout ─────────────────────────────────────────────────────
  306 | test.describe('02 Auth bootstrap — 08 logout', () => {
  307 |   test('logout clears session and redirects to login', async ({ authedPage }) => {
  308 |     await expect(authedPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible();
  309 |     await authedPage.getByRole('button', { name: 'Abmelden' }).click();
  310 |     await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  311 |     await expect(authedPage).toHaveURL(/\/login/);
  312 |   });
  313 | 
  314 |   test('after logout, navigating to /documents redirects to login', async ({ authedPage }) => {
> 315 |     await authedPage.getByRole('button', { name: 'Abmelden' }).click();
      |                                                                ^ Error: locator.click: Test timeout of 30000ms exceeded.
  316 |     await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  317 | 
  318 |     await authedPage.goto('/documents');
  319 |     await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 5_000 });
  320 |   });
  321 | 
  322 |   test('after logout, localStorage is cleared', async ({ authedPage }) => {
  323 |     await authedPage.getByRole('button', { name: 'Abmelden' }).click();
  324 |     await expect(authedPage.getByRole('heading', { name: 'Anmeldung' })).toBeVisible({ timeout: 10_000 });
  325 | 
  326 |     const stored = await authedPage.evaluate(() => window.localStorage.getItem('wissen.authToken'));
  327 |     expect(stored).toBeNull();
  328 |   });
  329 | });
  330 | 
```