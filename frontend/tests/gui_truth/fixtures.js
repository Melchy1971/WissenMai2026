import { test as base } from '@playwright/test';

const KEYS = {
  authState: 'wissen.authState',
  authToken: 'wissen.authToken',
  workspaceId: 'wissen.workspaceId',
};

async function injectAuthState(page, state) {
  await page.evaluate(
    ({ keys, s }) => {
      window.localStorage.setItem(keys.authState, JSON.stringify(s));
      if (s.token) window.localStorage.setItem(keys.authToken, s.token);
      if (s.active_workspace_id) window.localStorage.setItem(keys.workspaceId, s.active_workspace_id);
    },
    { keys: KEYS, s: state },
  );
}

async function clearAuthState(page) {
  await page.evaluate((keys) => {
    window.localStorage.removeItem(keys.authState);
    window.localStorage.removeItem(keys.authToken);
    window.localStorage.removeItem(keys.workspaceId);
  }, KEYS);
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

    await page.goto('/');
    await injectAuthState(page, {
      token,
      user: { id: userId, login, display_name: 'GUI Truth User' },
      memberships: [{ workspace_id: workspaceId, role: 'owner' }],
      active_workspace_id: workspaceId,
    });
    await page.goto('/documents');
    await use(page);
  },

  /**
   * Partial-auth page: only TRUTH_TOKEN injected (no user/memberships).
   * AuthContext sees token-only state → triggers /auth/me bootstrap.
   */
  partialAuthPage: async ({ page }, use) => {
    const token = process.env.TRUTH_TOKEN;

    await page.goto('/');
    await injectAuthState(page, {
      token,
      user: null,
      memberships: [],
      active_workspace_id: '',
    });
    await page.goto('/documents');
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

    await page.goto('/');
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
    await use(page);
  },

  /**
   * No-membership page: valid token but user has zero workspace memberships.
   * Bootstrap completes → WORKSPACE_NOT_CONFIGURED error state.
   */
  noMembershipPage: async ({ page }, use) => {
    const token = process.env.TRUTH_NO_MEMBERSHIP_TOKEN;

    await page.goto('/');
    await injectAuthState(page, {
      token,
      user: null,
      memberships: [],
      active_workspace_id: '',
    });
    await page.goto('/documents');
    await use(page);
  },

  /**
   * Bare page: no auth state in localStorage at all.
   * AuthContext sees no token → no bootstrap, straight to /login.
   */
  barePage: async ({ page }, use) => {
    await page.goto('/');
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
