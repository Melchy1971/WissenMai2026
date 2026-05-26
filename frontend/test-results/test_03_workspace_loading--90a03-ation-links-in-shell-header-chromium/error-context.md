# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: test_03_workspace_loading.spec.js >> 03 Workspace loading >> shows navigation links in shell header
- Location: tests\gui_truth\test_03_workspace_loading.spec.js:14:7

# Error details

```
TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
Call log:
  - waiting for locator('.shell') to be visible

```

# Test source

```ts
  1   | import { test as base } from '@playwright/test';
  2   | 
  3   | const KEYS = {
  4   |   authState: 'wissen.authState',
  5   |   authToken: 'wissen.authToken',
  6   |   workspaceId: 'wissen.workspaceId',
  7   | };
  8   | 
  9   | async function injectAuthState(page, state) {
  10  |   await page.evaluate(
  11  |     ({ keys, s }) => {
  12  |       window.localStorage.setItem(keys.authState, JSON.stringify(s));
  13  |       if (s.token) window.localStorage.setItem(keys.authToken, s.token);
  14  |       if (s.active_workspace_id) window.localStorage.setItem(keys.workspaceId, s.active_workspace_id);
  15  |     },
  16  |     { keys: KEYS, s: state },
  17  |   );
  18  | }
  19  | 
  20  | async function clearAuthState(page) {
  21  |   await page.evaluate((keys) => {
  22  |     window.localStorage.removeItem(keys.authState);
  23  |     window.localStorage.removeItem(keys.authToken);
  24  |     window.localStorage.removeItem(keys.workspaceId);
  25  |   }, KEYS);
  26  | }
  27  | 
  28  | async function waitForProtectedDocumentsReady(page) {
  29  |   await page.waitForLoadState('domcontentloaded');
  30  |   await page.waitForFunction(
  31  |     () => !document.body.textContent?.includes('Authentifizierung wird initialisiert...'),
  32  |     undefined,
  33  |     { timeout: 15_000 },
  34  |   );
> 35  |   await page.waitForSelector('.shell', { state: 'visible', timeout: 15_000 });
      |              ^ TimeoutError: page.waitForSelector: Timeout 15000ms exceeded.
  36  |   await page.waitForSelector('h2', { state: 'visible', timeout: 15_000 });
  37  | }
  38  | 
  39  | async function waitForProtectedErrorReady(page) {
  40  |   await page.waitForLoadState('domcontentloaded');
  41  |   await page.waitForFunction(
  42  |     () => !document.body.textContent?.includes('Authentifizierung wird initialisiert...'),
  43  |     undefined,
  44  |     { timeout: 15_000 },
  45  |   );
  46  |   await page.waitForSelector('.state-card--error', { state: 'visible', timeout: 15_000 });
  47  | }
  48  | 
  49  | export const test = base.extend({
  50  |   /**
  51  |    * Pre-authenticated page: complete auth state injected, bootstrap skipped.
  52  |    * Real API calls use TRUTH_TOKEN + TRUTH_WORKSPACE_ID.
  53  |    */
  54  |   authedPage: async ({ page }, use) => {
  55  |     const token = process.env.TRUTH_TOKEN;
  56  |     const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  57  |     const userId = process.env.TRUTH_USER_ID;
  58  |     const login = process.env.TRUTH_LOGIN || 'gui_truth_user';
  59  | 
  60  |     await page.goto('/');
  61  |     await injectAuthState(page, {
  62  |       token,
  63  |       user: { id: userId, login, display_name: 'GUI Truth User' },
  64  |       memberships: [{ workspace_id: workspaceId, role: 'owner' }],
  65  |       active_workspace_id: workspaceId,
  66  |     });
  67  |     await page.goto('/documents');
  68  |     await waitForProtectedDocumentsReady(page);
  69  |     await use(page);
  70  |   },
  71  | 
  72  |   /**
  73  |    * Partial-auth page: only TRUTH_TOKEN injected (no user/memberships).
  74  |    * AuthContext sees token-only state → triggers /auth/me bootstrap.
  75  |    */
  76  |   partialAuthPage: async ({ page }, use) => {
  77  |     const token = process.env.TRUTH_TOKEN;
  78  | 
  79  |     await page.goto('/');
  80  |     await injectAuthState(page, {
  81  |       token,
  82  |       user: null,
  83  |       memberships: [],
  84  |       active_workspace_id: '',
  85  |     });
  86  |     await page.goto('/documents');
  87  |     await waitForProtectedDocumentsReady(page);
  88  |     await use(page);
  89  |   },
  90  | 
  91  |   /**
  92  |    * Multi-workspace page: user has memberships to 2 workspaces.
  93  |    * Bootstrap triggers /auth/me → AppShell renders workspace switcher.
  94  |    */
  95  |   multiWorkspacePage: async ({ page }, use) => {
  96  |     const token = process.env.TRUTH_MULTI_WS_TOKEN;
  97  |     const workspaceId = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
  98  |     const workspace2Id = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
  99  | 
  100 |     await page.goto('/');
  101 |     await injectAuthState(page, {
  102 |       token,
  103 |       user: { id: 'multi-ws-user', login: 'gui-truth-multi-ws', display_name: 'GUI Truth Multi WS' },
  104 |       memberships: [
  105 |         { workspace_id: workspaceId, role: 'owner' },
  106 |         { workspace_id: workspace2Id, role: 'member' },
  107 |       ],
  108 |       active_workspace_id: workspaceId,
  109 |     });
  110 |     await page.goto('/documents');
  111 |     await waitForProtectedDocumentsReady(page);
  112 |     await use(page);
  113 |   },
  114 | 
  115 |   /**
  116 |    * No-membership page: valid token but user has zero workspace memberships.
  117 |    * Bootstrap completes → WORKSPACE_NOT_CONFIGURED error state.
  118 |    */
  119 |   noMembershipPage: async ({ page }, use) => {
  120 |     const token = process.env.TRUTH_NO_MEMBERSHIP_TOKEN;
  121 | 
  122 |     await page.goto('/');
  123 |     await injectAuthState(page, {
  124 |       token,
  125 |       user: null,
  126 |       memberships: [],
  127 |       active_workspace_id: '',
  128 |     });
  129 |     await page.goto('/documents');
  130 |     await waitForProtectedErrorReady(page);
  131 |     await use(page);
  132 |   },
  133 | 
  134 |   /**
  135 |    * Bare page: no auth state in localStorage at all.
```