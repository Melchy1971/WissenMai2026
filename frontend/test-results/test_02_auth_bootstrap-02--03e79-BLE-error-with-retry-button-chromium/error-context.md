# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_02_auth_bootstrap.spec.js >> 02 Auth bootstrap — 05 backend unreachable >> shows API_UNREACHABLE error with retry button
- Location: tests\gui_truth\test_02_auth_bootstrap.spec.js:180:7

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

```yaml
- paragraph: M4a Auth
- heading "Anmeldung" [level=2]
- paragraph: Lokale Session fuer geschuetzte API-Pfade
- paragraph: Session
- heading "Mit Workspace-Kontext anmelden" [level=3]
- text: Login
- textbox "Login"
- text: Passwort
- textbox "Passwort"
- button "Anmelden"
```

# Test source

```ts
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
  124 |         };
  125 |         window.localStorage.setItem('wissen.authState', JSON.stringify(state));
  126 |         window.localStorage.setItem('wissen.authToken', t);
  127 |         window.localStorage.setItem('wissen.workspaceId', ws);
  128 |       },
  129 |       { t: token, ws: workspaceId, uid: userId },
  130 |     );
  131 |     await page.goto('/documents');
  132 |     await expect(page.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 10_000 });
  133 |     await page.waitForTimeout(500);
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
  175 |   });
  176 | });
  177 | 
  178 | // ─── Scenario 05: Backend unreachable ────────────────────────────────────────
  179 | test.describe('02 Auth bootstrap — 05 backend unreachable', () => {
  180 |   test('shows API_UNREACHABLE error with retry button', async ({ page }) => {
  181 |     const token = process.env.TRUTH_TOKEN;
  182 | 
  183 |     await page.goto('/');
  184 |     await page.evaluate(
  185 |       ({ t }) => {
  186 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  187 |           token: t, user: null, memberships: [], active_workspace_id: '',
  188 |         }));
  189 |         window.localStorage.setItem('wissen.authToken', t);
  190 |       },
  191 |       { token },
  192 |     );
  193 | 
  194 |     // Intercept /auth/me and abort to simulate network failure
  195 |     await page.route('**/auth/me', (route) => route.abort('failed'));
  196 | 
  197 |     await page.goto('/documents');
> 198 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                                                      ^ Error: expect(locator).toBeVisible() failed
  199 | 
  200 |     // Retry button must be visible for transient errors
  201 |     await expect(page.getByRole('button', { name: 'Erneut versuchen' })).toBeVisible();
  202 |   });
  203 | 
  204 |   test('retry button re-triggers bootstrap', async ({ page }) => {
  205 |     const token = process.env.TRUTH_TOKEN;
  206 | 
  207 |     await page.goto('/');
  208 |     await page.evaluate(
  209 |       ({ t }) => {
  210 |         window.localStorage.setItem('wissen.authState', JSON.stringify({
  211 |           token: t, user: null, memberships: [], active_workspace_id: '',
  212 |         }));
  213 |         window.localStorage.setItem('wissen.authToken', t);
  214 |       },
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
```