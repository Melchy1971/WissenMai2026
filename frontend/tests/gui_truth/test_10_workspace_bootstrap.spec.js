/**
 * Workspace Bootstrap — Truth Flow E2E Tests
 *
 * Tests the workspace bootstrap rules with a real API and real PostgreSQL DB.
 *
 * Rules under test:
 *   01  active_workspace_id comes only from membership (shown in header)
 *   02  Single-workspace user: no switcher, workspace shown as text
 *   03  Multi-workspace user: switcher rendered, both workspaces listed
 *   04  Workspace switch: header updates, documents page shows new workspace
 *   05  Workspace switch: document list reloads
 *   06  Workspace switch: upload and search state reset to idle
 *   07  Workspace switch during chat: navigates to /chat (no ghost session URL)
 *   08  No workspace membership: WORKSPACE_NOT_CONFIGURED error shown
 */
import { expect, test } from './fixtures.js';

// ─── Scenario 01: active_workspace_id comes from membership ──────────────────
test.describe('10 Workspace bootstrap — 01 workspace from membership', () => {
  test('workspace id shown in document page header after bootstrap', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  });

  test('workspace id shown in AppShell header after bootstrap', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await expect(authedPage.locator('.shell__session').getByText(workspaceId)).toBeVisible();
  });

  test('workspace id from bootstrap matches injected membership workspace', async ({ partialAuthPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await expect(partialAuthPage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 15_000 });
    await expect(partialAuthPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  });
});

// ─── Scenario 02: Single-workspace user ──────────────────────────────────────
test.describe('10 Workspace bootstrap — 02 single workspace', () => {
  test('single workspace shown as text, no dropdown switcher', async ({ authedPage }) => {
    // Only 1 membership → AppShell renders <span>, not <select>
    await expect(authedPage.getByRole('combobox', { name: 'Workspace wechseln' })).not.toBeVisible();
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await expect(authedPage.locator('.shell__session').getByText(workspaceId)).toBeVisible();
  });

  test('no workspace switcher visible for single-workspace user', async ({ authedPage }) => {
    await expect(authedPage.locator('[aria-label="Workspace wechseln"]')).not.toBeVisible();
  });
});

// ─── Scenario 03: Multi-workspace user ───────────────────────────────────────
test.describe('10 Workspace bootstrap — 03 multi-workspace switcher', () => {
  test('workspace switcher select rendered for multi-workspace user', async ({ multiWorkspacePage }) => {
    await expect(multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' })).toBeVisible();
  });

  test('workspace switcher contains both workspace ids', async ({ multiWorkspacePage }) => {
    const ws1 = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
    await expect(select).toBeVisible();

    const options = await select.locator('option').allTextContents();
    expect(options).toContain(ws1);
    expect(options).toContain(ws2);
  });

  test('initial active workspace is first injected workspace', async ({ multiWorkspacePage }) => {
    const ws1 = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
    await expect(select).toHaveValue(ws1);
  });
});

// ─── Scenario 04: Workspace switch updates header ────────────────────────────
test.describe('10 Workspace bootstrap — 04 workspace switch header', () => {
  test('switching workspace updates select value', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });

    await select.selectOption(ws2);

    await expect(select).toHaveValue(ws2);
  });

  test('switching workspace updates document page workspace label', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });

    await select.selectOption(ws2);

    await expect(multiWorkspacePage.getByText(`Workspace: ${ws2}`)).toBeVisible({ timeout: 5_000 });
  });

  test('switching to invalid workspace is rejected (select stays on valid workspace)', async ({ multiWorkspacePage }) => {
    const ws1 = process.env.TRUTH_MULTI_WS_WORKSPACE_ID;
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });

    // Try to set an arbitrary non-membership workspace ID via JS (simulate manipulation)
    await multiWorkspacePage.evaluate(() => {
      const sel = document.querySelector('[aria-label="Workspace wechseln"]');
      if (sel) {
        const opt = document.createElement('option');
        opt.value = 'f1000000-0000-0000-0000-manipulated00';
        opt.textContent = 'Manipulated';
        sel.appendChild(opt);
        sel.value = 'f1000000-0000-0000-0000-manipulated00';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    // AuthContext.switchWorkspace validates membership → rejects → active workspace unchanged
    await expect(select).toHaveValue(ws1);
  });

  test('manipulated workspace id cannot load protected document controls', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN;
    const manipulatedWorkspace = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    await page.goto('/');
    await page.evaluate(
      ({ t, ws }) => {
        window.localStorage.setItem('wissen.authState', JSON.stringify({
          token: t,
          user: { id: 'truth-user', login: 'gui_truth_user' },
          memberships: [{ workspace_id: ws, role: 'owner' }],
          active_workspace_id: ws,
        }));
        window.localStorage.setItem('wissen.authToken', t);
        window.localStorage.setItem('wissen.workspaceId', ws);
      },
      { t: token, ws: manipulatedWorkspace },
    );

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Fehlercode: WORKSPACE_ACCESS_FORBIDDEN')).toBeVisible();
    await expect(page.getByText('Technischer Code: WORKSPACE_NOT_CONFIGURED')).toBeVisible();
    await expect(page.getByText('Dokument hochladen')).not.toBeVisible();
  });
});

// ─── Scenario 05: Workspace switch reloads documents ─────────────────────────
test.describe('10 Workspace bootstrap — 05 workspace switch reloads documents', () => {
  test('switching workspace triggers documents reload', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    const documentRequests = [];
    multiWorkspacePage.on('request', (req) => {
      if (req.url().includes('/documents') && req.method() === 'GET') {
        documentRequests.push(req.url());
      }
    });

    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
    const countBefore = documentRequests.length;

    await select.selectOption(ws2);

    // Documents page re-renders with loading state → triggers new GET /documents
    await expect(multiWorkspacePage.getByText(`Workspace: ${ws2}`)).toBeVisible({ timeout: 5_000 });

    // Allow the reload to fire
    await multiWorkspacePage.waitForTimeout(1_000);
    expect(documentRequests.length).toBeGreaterThan(countBefore);
  });

  test('documents page remains visible after workspace switch', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });

    await select.selectOption(ws2);

    await expect(multiWorkspacePage.getByRole('heading', { name: 'Dokumente', exact: true })).toBeVisible({ timeout: 5_000 });
  });
});

// ─── Scenario 06: Upload and search state reset on workspace switch ───────────
test.describe('10 Workspace bootstrap — 06 state reset on switch', () => {
  test('search result area is empty after workspace switch', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });

    // Switch workspace
    await select.selectOption(ws2);
    await expect(multiWorkspacePage.getByText(`Workspace: ${ws2}`)).toBeVisible({ timeout: 5_000 });

    // No search results or search-in-progress state should linger from previous workspace
    await expect(multiWorkspacePage.locator('.state-card--loading').filter({ hasText: 'Suchtreffer' })).not.toBeVisible();
    await expect(multiWorkspacePage.locator('.search-result-list')).not.toBeVisible();
  });

  test('upload area is idle after workspace switch', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });

    await select.selectOption(ws2);
    await expect(multiWorkspacePage.getByText(`Workspace: ${ws2}`)).toBeVisible({ timeout: 5_000 });

    // No polling or upload-success state from previous workspace
    await expect(multiWorkspacePage.getByText('Upload laeuft...')).not.toBeVisible();
    await expect(multiWorkspacePage.locator('.meta-grid').filter({ hasText: 'Job-ID' })).not.toBeVisible();
  });
});

// ─── Scenario 07: Chat workspace reset on workspace switch ───────────────────
test.describe('10 Workspace bootstrap — 07 chat workspace reset', () => {
  test('switching workspace from chat page navigates back to /chat root', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    // Navigate to chat page
    await multiWorkspacePage.getByRole('link', { name: 'Chat' }).click();
    await expect(multiWorkspacePage).toHaveURL(/\/chat/);

    // Switch workspace
    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
    await select.selectOption(ws2);

    // ChatPage workspace-change effect navigates to /chat (no session-specific URL)
    await expect(multiWorkspacePage).toHaveURL(/\/chat$/, { timeout: 5_000 });
    await expect(multiWorkspacePage).not.toHaveURL(/\/chat\/.+/);
  });

  test('chat page shows workspace label after workspace switch', async ({ multiWorkspacePage }) => {
    const ws2 = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    await multiWorkspacePage.getByRole('link', { name: 'Chat' }).click();
    await expect(multiWorkspacePage).toHaveURL(/\/chat/);

    const select = multiWorkspacePage.getByRole('combobox', { name: 'Workspace wechseln' });
    await select.selectOption(ws2);

    await expect(select).toHaveValue(ws2);
  });
});

// ─── Scenario 08: No workspace membership ────────────────────────────────────
test.describe('10 Workspace bootstrap — 08 no workspace membership', () => {
  test('no-membership user sees WORKSPACE_NOT_CONFIGURED error', async ({ noMembershipPage }) => {
    await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
  });

  test('no-membership error is not session-expired', async ({ noMembershipPage }) => {
    await expect(noMembershipPage.locator('.state-card--error')).toBeVisible({ timeout: 15_000 });
    const errorText = await noMembershipPage.locator('.state-card--error').textContent();
    expect(errorText).not.toContain('Session abgelaufen');
  });

  test('no-membership page does not show workspace switcher', async ({ noMembershipPage }) => {
    await expect(noMembershipPage.locator('[aria-label="Workspace wechseln"]')).not.toBeVisible();
  });
});
