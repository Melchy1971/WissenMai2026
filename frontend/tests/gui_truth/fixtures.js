import { test as base } from '@playwright/test';

const KEYS = {
  authState: 'wissen.authState',
  authToken: 'wissen.authToken',
  workspaceId: 'wissen.workspaceId',
};

export const test = base.extend({
  /**
   * Pre-authenticated page fixture.
   * Injects complete auth state into localStorage before navigating to /documents,
   * bypassing the bootstrap /auth/me call. Real API calls use TRUTH_TOKEN.
   */
  authedPage: async ({ page }, use) => {
    const token = process.env.TRUTH_TOKEN;
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    const userId = process.env.TRUTH_USER_ID;
    const login = process.env.TRUTH_LOGIN || 'gui_truth_user';

    // Navigate once to establish origin context for localStorage
    await page.goto('/');

    const authState = {
      token,
      user: { id: userId, login, display_name: 'GUI Truth User' },
      memberships: [{ workspace_id: workspaceId, role: 'owner' }],
      active_workspace_id: workspaceId,
    };

    // Set all three storage keys so client.js has auth context before effects run
    await page.evaluate(
      ({ keys, state }) => {
        window.localStorage.setItem(keys.authState, JSON.stringify(state));
        window.localStorage.setItem(keys.authToken, state.token);
        window.localStorage.setItem(keys.workspaceId, state.active_workspace_id);
      },
      { keys: KEYS, state: authState },
    );

    await page.goto('/documents');
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
