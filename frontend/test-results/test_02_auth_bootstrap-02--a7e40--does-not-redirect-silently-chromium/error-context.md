# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_02_auth_bootstrap.spec.js >> 02 Auth bootstrap — 04 invalid token >> shows session-expired error, does not redirect silently
- Location: tests\gui_truth\test_02_auth_bootstrap.spec.js:141:7

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
- text: "{\"error\":{\"code\":\"AUTH_REQUIRED\",\"message\":\"Authentication required\",\"details\":{}}}"
```

# Test source

```ts
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
> 155 |     await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
      |                                                      ^ Error: expect(locator).toBeVisible() failed
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
```