import { expect, test as base } from '@playwright/test';

const KEYS = {
  authState: 'wissen.authState',
  authToken: 'wissen.authToken',
  workspaceId: 'wissen.workspaceId',
};

const SELECTORS = {
  authError: '[data-testid="auth-error"]',
  appShell: '[data-testid="app-shell"]',
  documentList: '[data-testid="document-list"]',
  loginPage: '[data-testid="login-page"]',
  workspaceReady: '[data-testid="workspace-ready"]',
};

export async function injectAuthState(page, state) {
  if (page.url() === 'about:blank') {
    await page.goto('/login');
  }
  await page.evaluate(
    ({ keys, s }) => {
      window.localStorage.clear();
      window.localStorage.setItem(keys.authState, JSON.stringify(s));
      if (s.token) window.localStorage.setItem(keys.authToken, s.token);
      if (s.active_workspace_id) window.localStorage.setItem(keys.workspaceId, s.active_workspace_id);
    },
    { keys: KEYS, s: state },
  ).catch(() => {});
}

export async function clearAuthState(page) {
  if (page.url() === 'about:blank') {
    await page.goto('/login');
  }
  await page.evaluate((keys) => {
    window.localStorage.removeItem(keys.authState);
    window.localStorage.removeItem(keys.authToken);
    window.localStorage.removeItem(keys.workspaceId);
  }, KEYS);
}

async function failFastIfTerminal(page, phase) {
  const state = await page.evaluate((selectors) => {
    const authError = document.querySelector(selectors.authError);
    const bodyText = document.body?.innerText || document.body?.textContent || '';
    return {
      authErrorText: authError?.textContent || '',
      bodyText,
      hasAppShell: Boolean(document.querySelector(selectors.appShell)),
      hasLoginPage: Boolean(document.querySelector(selectors.loginPage)),
      hasWorkspaceReady: Boolean(document.querySelector(selectors.workspaceReady)),
    };
  }, SELECTORS).catch(() => null);

  if (!state) return;
  const text = `${state.authErrorText}\n${state.bodyText}`;
  if (/API_UNREACHABLE|Backend nicht erreichbar|Failed to fetch|NetworkError/i.test(text)) {
    throw new Error(`${phase}: API unreachable`);
  }
  if (/AUTH_INVALID_CREDENTIALS|Login fehlgeschlagen|Ungueltige|Ungültige/i.test(text)) {
    throw new Error(`${phase}: Login fehlgeschlagen`);
  }
  if (/WORKSPACE_NOT_CONFIGURED|WORKSPACE_REQUIRED|Kein aktiver Workspace|Workspace fehlt/i.test(text)) {
    throw new Error(`${phase}: Workspace fehlt`);
  }
  if (state.authErrorText) {
    throw new Error(`${phase}: ${state.authErrorText.trim()}`);
  }
}

export async function waitForLoginReady(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForSelector(`${SELECTORS.loginPage}, ${SELECTORS.authError}, ${SELECTORS.appShell}`, {
    state: 'attached',
    timeout: 15_000,
  });
  await failFastIfTerminal(page, 'login-page');
  await expect(page.getByTestId('login-page')).toBeVisible({ timeout: 10_000 });
}

export async function waitForWorkspaceReady(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForFunction(
    () => !document.body.textContent?.includes('Authentifizierung wird initialisiert...'),
    undefined,
    { timeout: 15_000 },
  );
  await page.waitForSelector(`${SELECTORS.appShell}, ${SELECTORS.authError}, ${SELECTORS.loginPage}`, {
    state: 'attached',
    timeout: 15_000,
  });
  await failFastIfTerminal(page, 'workspace-ready');
  await expect(page.getByTestId('app-shell')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('workspace-ready')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('document-list')).toBeVisible({ timeout: 15_000 });
}

export async function waitForProtectedErrorReady(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForFunction(
    () => !document.body.textContent?.includes('Authentifizierung wird initialisiert...'),
    undefined,
    { timeout: 15_000 },
  );
  await expect(page.getByTestId('auth-error')).toBeVisible({ timeout: 15_000 });
}

export const test = base.extend({
  /**
   * Pre-authenticated page: complete auth state injected, bootstrap skipped.
   * Real API calls use TRUTH_TOKEN + TRUTH_WORKSPACE_ID.
   */
  authedPage: async ({ page }, use) => {
    const token = process.env.TRUTH_TOKEN;
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    const userId = process.env.TRUTH_USER_ID;
    const login = process.env.TRUTH_LOGIN || 'gui_truth_user';

    await injectAuthState(page, {
      token,
      user: { id: userId, login, display_name: 'GUI Truth User' },
      memberships: [{ workspace_id: workspaceId, role: 'owner' }],
      active_workspace_id: workspaceId,
    });
    await page.goto('/documents');
    await waitForWorkspaceReady(page);
    await use(page);
  },

  /**
   * Partial-auth page: only TRUTH_TOKEN injected (no user/memberships).
   * AuthContext sees token-only state → triggers /auth/me bootstrap.
   */
  partialAuthPage: async ({ page }, use) => {
    const token = process.env.TRUTH_TOKEN;

    await injectAuthState(page, {
      token,
      user: null,
      memberships: [],
      active_workspace_id: '',
    });
    await page.goto('/documents');
    await waitForWorkspaceReady(page);
    await use(page);
  },

  /**
   * Multi-workspace page: user has memberships to 2 workspaces.
   * Bootstrap triggers /auth/me → AppShell renders workspace switcher.
   */
  multiWorkspacePage: async ({ page }, use) => {
    const token = process.env.TRUTH_MULTI_WS_TOKEN;
    const workspaceId = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
    const workspace2Id = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    await injectAuthState(page, {
      token,
      user: { id: 'multi-ws-user', login: 'gui-truth-multi-ws', display_name: 'GUI Truth Multi WS' },
      memberships: [
        { workspace_id: workspaceId, role: 'owner' },
        { workspace_id: workspace2Id, role: 'member' },
      ],
      active_workspace_id: workspaceId,
    });
    await page.goto('/documents');
    await waitForWorkspaceReady(page);
    await use(page);
  },

  /**
   * No-membership page: valid token but user has zero workspace memberships.
   * Bootstrap completes → WORKSPACE_NOT_CONFIGURED error state.
   */
  noMembershipPage: async ({ page }, use) => {
    const token = process.env.TRUTH_NO_MEMBERSHIP_TOKEN;

    await injectAuthState(page, {
      token,
      user: null,
      memberships: [],
      active_workspace_id: '',
    });
    await page.goto('/documents');
    await waitForProtectedErrorReady(page);
    await use(page);
  },

  /**
   * Bare page: no auth state in localStorage at all.
   * AuthContext sees no token → no bootstrap, straight to /login.
   */
  barePage: async ({ page }, use) => {
    await clearAuthState(page);
    await use(page);
  },

  credentials: async ({}, use) => {
    await use({
      login: process.env.TRUTH_LOGIN || 'gui_truth_user',
      password: process.env.TRUTH_PASSWORD || 'gui_truth_pw_42',
    });
  },
});

export { expect } from '@playwright/test';
