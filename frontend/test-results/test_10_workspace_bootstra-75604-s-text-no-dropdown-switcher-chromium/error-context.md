# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_10_workspace_bootstrap.spec.js >> 10 Workspace bootstrap — 02 single workspace >> single workspace shown as text, no dropdown switcher
- Location: tests\gui_truth\test_10_workspace_bootstrap.spec.js:39:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('.shell__session').getByText('f1000000-0056-03d1-6f10-58aaed725241')
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 5000ms
  - waiting for locator('.shell__session').getByText('f1000000-0056-03d1-6f10-58aaed725241')

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
  1   | /**
  2   |  * Workspace Bootstrap — Truth Flow E2E Tests
  3   |  *
  4   |  * Tests the workspace bootstrap rules with a real API and real PostgreSQL DB.
  5   |  *
  6   |  * Rules under test:
  7   |  *   01  active_workspace_id comes only from membership (shown in header)
  8   |  *   02  Single-workspace user: no switcher, workspace shown as text
  9   |  *   03  Multi-workspace user: switcher rendered, both workspaces listed
  10  |  *   04  Workspace switch: header updates, documents page shows new workspace
  11  |  *   05  Workspace switch: document list reloads
  12  |  *   06  Workspace switch: upload and search state reset to idle
  13  |  *   07  Workspace switch during chat: navigates to /chat (no ghost session URL)
  14  |  *   08  No workspace membership: WORKSPACE_NOT_CONFIGURED error shown
  15  |  */
  16  | import { expect, test } from './fixtures.js';
  17  | 
  18  | // ─── Scenario 01: active_workspace_id comes from membership ──────────────────
  19  | test.describe('10 Workspace bootstrap — 01 workspace from membership', () => {
  20  |   test('workspace id shown in document page header after bootstrap', async ({ authedPage }) => {
  21  |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  22  |     await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  23  |   });
  24  | 
  25  |   test('workspace id shown in AppShell header after bootstrap', async ({ authedPage }) => {
  26  |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  27  |     await expect(authedPage.locator('.shell__session').getByText(workspaceId)).toBeVisible();
  28  |   });
  29  | 
  30  |   test('workspace id from bootstrap matches injected membership workspace', async ({ partialAuthPage }) => {
  31  |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  32  |     await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
  33  |     await expect(partialAuthPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  34  |   });
  35  | });
  36  | 
  37  | // ─── Scenario 02: Single-workspace user ──────────────────────────────────────
  38  | test.describe('10 Workspace bootstrap — 02 single workspace', () => {
  39  |   test('single workspace shown as text, no dropdown switcher', async ({ authedPage }) => {
  40  |     // Only 1 membership → AppShell renders <span>, not <select>
  41  |     await expect(authedPage.getByRole('combobox', { name: 'Workspace wechseln' })).not.toBeVisible();
  42  |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
> 43  |     await expect(authedPage.locator('.shell__session').getByText(workspaceId)).toBeVisible();
      |                                                                                ^ Error: expect(locator).toBeVisible() failed
  44  |   });
  45  | 
  46  |   test('no workspace switcher visible for single-workspace user', async ({ authedPage }) => {
  47  |     await expect(authedPage.locator('[aria-label="Workspace wechseln"]')).not.toBeVisible();
  48  |   });
  49  | });
  50  | 
  51  | // ─── Scenario 03: Multi-workspace user ───────────────────────────────────────
  52  | test.describe('10 Workspace bootstrap — 03 multi-workspace switcher', () => {
  53  |   test('workspace switcher select rendered for multi-workspace user', async ({ multiWorkspacePage }) => {
  54  |     await expect(multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' })).toBeVisible();
  55  |   });
  56  | 
  57  |   test('workspace switcher contains both workspace ids', async ({ multiWorkspacePage }) => {
  58  |     const ws1 = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
  59  |     const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
  60  | 
  61  |     const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
  62  |     await expect(select).toBeVisible();
  63  | 
  64  |     const options = await select.locator('option').allTextContents();
  65  |     expect(options).toContain(ws1);
  66  |     expect(options).toContain(ws2);
  67  |   });
  68  | 
  69  |   test('initial active workspace is first injected workspace', async ({ multiWorkspacePage }) => {
  70  |     const ws1 = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
  71  |     const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
  72  |     await expect(select).toHaveValue(ws1);
  73  |   });
  74  | });
  75  | 
  76  | // ─── Scenario 04: Workspace switch updates header ────────────────────────────
  77  | test.describe('10 Workspace bootstrap — 04 workspace switch header', () => {
  78  |   test('switching workspace updates select value', async ({ multiWorkspacePage }) => {
  79  |     const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
  80  |     const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
  81  | 
  82  |     await select.selectOption(ws2);
  83  | 
  84  |     await expect(select).toHaveValue(ws2);
  85  |   });
  86  | 
  87  |   test('switching workspace updates document page workspace label', async ({ multiWorkspacePage }) => {
  88  |     const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
  89  |     const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
  90  | 
  91  |     await select.selectOption(ws2);
  92  | 
  93  |     await expect(multiWorkspacePage.getByText(`Workspace: ${ws2}`)).toBeVisible({ timeout: 5_000 });
  94  |   });
  95  | 
  96  |   test('switching to invalid workspace is rejected (select stays on valid workspace)', async ({ multiWorkspacePage }) => {
  97  |     const ws1 = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
  98  |     const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
  99  | 
  100 |     // Try to set an arbitrary non-membership workspace ID via JS (simulate manipulation)
  101 |     await multiWorkspacePage.evaluate(() => {
  102 |       const sel = document.querySelector('[aria-label="Workspace wechseln"]');
  103 |       if (sel) {
  104 |         const opt = document.createElement('option');
  105 |         opt.value = 'f1000000-0000-0000-0000-manipulated00';
  106 |         opt.textContent = 'Manipulated';
  107 |         sel.appendChild(opt);
  108 |         sel.value = 'f1000000-0000-0000-0000-manipulated00';
  109 |         sel.dispatchEvent(new Event('change', { bubbles: true }));
  110 |       }
  111 |     });
  112 | 
  113 |     // AuthContext.switchWorkspace validates membership → rejects → active workspace unchanged
  114 |     await expect(select).toHaveValue(ws1);
  115 |   });
  116 | });
  117 | 
  118 | // ─── Scenario 05: Workspace switch reloads documents ─────────────────────────
  119 | test.describe('10 Workspace bootstrap — 05 workspace switch reloads documents', () => {
  120 |   test('switching workspace triggers documents reload', async ({ multiWorkspacePage }) => {
  121 |     const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
  122 | 
  123 |     const documentRequests = [];
  124 |     multiWorkspacePage.on('request', (req) => {
  125 |       if (req.url().includes('/documents') && req.method() === 'GET') {
  126 |         documentRequests.push(req.url());
  127 |       }
  128 |     });
  129 | 
  130 |     const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
  131 |     const countBefore = documentRequests.length;
  132 | 
  133 |     await select.selectOption(ws2);
  134 | 
  135 |     // Documents page re-renders with loading state → triggers new GET /documents
  136 |     await expect(multiWorkspacePage.getByText(`Workspace: ${ws2}`)).toBeVisible({ timeout: 5_000 });
  137 | 
  138 |     // Allow the reload to fire
  139 |     await multiWorkspacePage.waitForTimeout(1_000);
  140 |     expect(documentRequests.length).toBeGreaterThan(countBefore);
  141 |   });
  142 | 
  143 |   test('documents page remains visible after workspace switch', async ({ multiWorkspacePage }) => {
```