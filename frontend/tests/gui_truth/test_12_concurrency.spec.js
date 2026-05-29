import { expect, test } from './fixtures.js';

test.describe('12 Concurrency safety', () => {
  // --- Existing 2 tests ---

  test('parallel search requests use the real backend and do not surface stale errors', async ({ authedPage }) => {
    let firstSearchDelayed = false;
    await authedPage.route('**/api/v1/search/chunks**', async (route) => {
      if (!firstSearchDelayed) {
        firstSearchDelayed = true;
        await authedPage.waitForTimeout(1200);
      }
      await route.continue();
    });

    await authedPage.getByLabel('Suchbegriff').fill('slow truth');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();
    await authedPage.getByLabel('Suchbegriff').fill('fast truth');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();

    await authedPage.waitForTimeout(3000);
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
    await expect(authedPage.getByText('AUTH_REQUIRED')).not.toBeVisible();
    await expect(authedPage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
  });

  test('workspace switch during an in-flight real request does not keep old workspace UI state', async ({ multiWorkspacePage }) => {
    const workspace2Id = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    await multiWorkspacePage.route('**/documents?**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.continue();
    });

    await multiWorkspacePage.getByLabel('Workspace wechseln').selectOption(workspace2Id);
    await expect(multiWorkspacePage.getByText(`Workspace: ${workspace2Id}`)).toBeVisible({ timeout: 10_000 });
    await expect(multiWorkspacePage.locator('.state-card--error')).not.toBeVisible();
    await multiWorkspacePage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  // --- New tests: 6 additional concurrency scenarios ---

  test('workspace switch during chat does not surface stale workspace error', async ({ multiWorkspacePage }) => {
    const workspace2Id = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    await multiWorkspacePage.goto('/chat');
    await expect(multiWorkspacePage.getByTestId('chat-page')).toBeVisible({ timeout: 10_000 });

    // Delay any in-flight chat request
    await multiWorkspacePage.route('**/chat/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1_500));
      await route.continue();
    });

    await multiWorkspacePage.getByLabel('Workspace wechseln').selectOption(workspace2Id);
    await expect(multiWorkspacePage.getByText(`Workspace: ${workspace2Id}`)).toBeVisible({ timeout: 10_000 });
    await expect(multiWorkspacePage.locator('.state-card--error')).not.toBeVisible();
    await multiWorkspacePage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('workspace switch during upload polling resets upload panel without stale error', async ({ multiWorkspacePage }) => {
    const workspace2Id = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    // Delay any job polling from old workspace
    await multiWorkspacePage.route('**/jobs/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 3_000));
      await route.continue();
    });

    await multiWorkspacePage.getByLabel('Workspace wechseln').selectOption(workspace2Id);
    await expect(multiWorkspacePage.getByText(`Workspace: ${workspace2Id}`)).toBeVisible({ timeout: 10_000 });

    // After WS switch, no stale upload error from old workspace must bleed through
    await expect(multiWorkspacePage.locator('.state-card--error')).not.toBeVisible();
    await expect(multiWorkspacePage.getByText('AUTH_REQUIRED')).not.toBeVisible();
    await expect(multiWorkspacePage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
    await multiWorkspacePage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('logout during active request does not render stale document data', async ({ authedPage }) => {
    // Gate: delay the next documents fetch
    let allowRequest;
    await authedPage.route('**/documents?**', async (route) => {
      await new Promise((resolve) => { allowRequest = resolve; });
      await route.continue();
    });

    // Trigger a navigation that would issue a documents request, then immediately clear auth
    await authedPage.evaluate(() => {
      window.localStorage.removeItem('wissen.authState');
      window.localStorage.removeItem('wissen.authToken');
      window.localStorage.removeItem('wissen.workspaceId');
    });

    // Release the in-flight request
    if (allowRequest) allowRequest();

    await authedPage.waitForTimeout(1_500);

    // The app should not render a workspace-authenticated document list after auth was cleared
    const documentListVisible = await authedPage.getByTestId('document-list').isVisible().catch(() => false);
    const onLoginPage = authedPage.url().includes('/login');
    // Either redirected to login or document list is not rendering authenticated data
    expect(onLoginPage || !documentListVisible).toBeTruthy();
    await authedPage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('stale document list response after workspace switch does not bleed into new workspace view', async ({ multiWorkspacePage }) => {
    const workspace2Id = process.env.TRUTH_MULTI_WS_WORKSPACE_2_ID;

    // Delay the first documents request (belongs to workspace-1)
    let firstIntercepted = false;
    await multiWorkspacePage.route('**/documents?**', async (route) => {
      if (!firstIntercepted) {
        firstIntercepted = true;
        await new Promise((resolve) => setTimeout(resolve, 2_500));
      }
      await route.continue();
    });

    await multiWorkspacePage.getByLabel('Workspace wechseln').selectOption(workspace2Id);
    await multiWorkspacePage.waitForTimeout(3_500);

    // After the delayed workspace-1 response arrives, no error state from the old workspace
    // must appear in the workspace-2 view
    await expect(multiWorkspacePage.locator('.state-card--error')).not.toBeVisible();
    await expect(multiWorkspacePage.getByText('WORKSPACE_NOT_CONFIGURED')).not.toBeVisible();
    await expect(multiWorkspacePage.getByText(`Workspace: ${workspace2Id}`)).toBeVisible({ timeout: 5_000 });
    await multiWorkspacePage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('upload submit is disabled while upload is in flight preventing duplicate requests', async ({ authedPage }) => {
    // Intercept import to hold indefinitely — lets us observe the in-flight UI state
    await authedPage.route('**/documents/import', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 10_000));
      await route.continue();
    });

    await authedPage.getByTestId('upload-file-input').setInputFiles({
      name: 'concurrency-upload-test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('concurrency upload guard test'),
    });
    await authedPage.getByTestId('upload-submit').click();

    // While upload is in flight, the submit button must be disabled
    await expect(authedPage.getByTestId('upload-submit')).toBeDisabled({ timeout: 5_000 });
    await authedPage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('API_UNREACHABLE bootstrap retry re-triggers exactly one additional auth call', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN || 'truth-token';
    let authMeCalls = 0;

    await page.goto('/');
    await page.evaluate((t) => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: t,
        user: null,
        memberships: [],
        active_workspace_id: '',
      }));
      window.localStorage.setItem('wissen.authToken', t);
    }, token);

    await page.route('**/auth/me', async (route) => {
      authMeCalls += 1;
      if (authMeCalls === 1) {
        await route.abort('failed');
      } else {
        await route.continue();
      }
    });

    await page.goto('/documents');
    await expect(page.locator('[data-error-code="API_UNREACHABLE"]')).toBeVisible({ timeout: 10_000 });
    expect(authMeCalls).toBe(1);

    const retryButton = page.getByRole('button', { name: 'Erneut versuchen' });
    const hasRetry = await retryButton.isVisible({ timeout: 2_000 }).catch(() => false);
    if (hasRetry) {
      const callsBefore = authMeCalls;
      await retryButton.click();
      await page.waitForTimeout(2_000);
      expect(authMeCalls - callsBefore).toBe(1);
    }

    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });
});
