/**
 * GUI State Invariants — Truth Flow E2E Tests
 *
 * These checks assert that invalid auth/workspace states never render protected
 * workspace data and controlled failures stay visible with the correct error code.
 * No fake empty lists, no endless spinners, retry only where the catalog allows it.
 */
import { expect, test } from './fixtures.js';

const AUTH_STATE_FULL = {
  token: 'truth-token',
  user: { id: 'user-1', login: 'truth-user' },
  memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
  active_workspace_id: 'workspace-1',
};

const AUTH_STATE_PARTIAL = {
  token: 'truth-token',
  user: null,
  memberships: [],
  active_workspace_id: '',
};

test.describe('11 GUI state invariants', () => {
  // --- Existing 3 tests ---

  test('documents route does not render data controls without validated workspace', async ({ page }) => {
    const token = process.env.TRUTH_NO_MEMBERSHIP_TOKEN || 'truth-token';
    await page.goto('/');
    await page.evaluate((t) => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: t,
        user: { id: 'user-1', login: 'truth-user' },
        memberships: [],
        active_workspace_id: '',
      }));
      window.localStorage.setItem('wissen.authToken', t);
    }, token);

    const documentRequests = [];
    page.on('request', (req) => {
      if (req.url().includes('127.0.0.1:8000/documents') && req.method() === 'GET') {
        documentRequests.push(req.url());
      }
    });

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Dokument hochladen')).not.toBeVisible();
    await expect(page.getByText('Chunk-Suche')).not.toBeVisible();
    expect(documentRequests).toHaveLength(0);
  });

  test('API_UNREACHABLE on documents is not rendered as empty list', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify({
        token: 'truth-token',
        user: { id: 'user-1', login: 'truth-user' },
        memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
        active_workspace_id: 'workspace-1',
      }));
      window.localStorage.setItem('wissen.authToken', 'truth-token');
      window.localStorage.setItem('wissen.workspaceId', 'workspace-1');
    });
    await page.route('**/documents?**', (route) => route.abort('failed'));

    await page.goto('/documents');

    await expect(page.getByRole('heading', { name: 'Backend nicht erreichbar' })).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Fehlercode: API_UNREACHABLE')).toBeVisible();
    await expect(page.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  });

  test('FORBIDDEN bootstrap state has no retry action', async ({ page }) => {
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
    await page.route('**/auth/me', (route) => {
      authMeCalls += 1;
      return route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'FORBIDDEN', message: 'Access denied', details: {} } }),
      });
    });

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByRole('button', { name: 'Erneut versuchen' })).not.toBeVisible();
    await page.waitForTimeout(500);
    expect(authMeCalls).toBe(1);
  });

  // --- New tests: 10 additional error codes ---

  test('AUTH_REQUIRED bootstrap state has no retry action', async ({ page }) => {
    const token = process.env.TRUTH_TOKEN || 'truth-token';
    let authMeCalls = 0;

    await page.goto('/');
    await page.evaluate((t) => {
      window.localStorage.setItem('wissen.authState', JSON.stringify(
        { token: t, user: null, memberships: [], active_workspace_id: '' },
      ));
      window.localStorage.setItem('wissen.authToken', t);
    }, token);
    await page.route('**/auth/me', (route) => {
      authMeCalls += 1;
      return route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'AUTH_REQUIRED', message: 'Unauthorized', details: {} } }),
      });
    });

    await page.goto('/documents');
    await expect(page.locator('.state-card--error')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-error-code="AUTH_REQUIRED"]')).toBeVisible({ timeout: 5_000 });
    await expect(page.locator('[data-retry="true"]')).not.toBeVisible();
    await page.waitForTimeout(500);
    expect(authMeCalls).toBe(1);
  });

  test('TIMEOUT on documents shows error code with retry', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify(AUTH_STATE_FULL));
      window.localStorage.setItem('wissen.authToken', 'truth-token');
      window.localStorage.setItem('wissen.workspaceId', 'workspace-1');
    });
    await page.route('**/documents?**', (route) =>
      route.fulfill({
        status: 408,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'TIMEOUT', message: 'Request timeout', details: {} } }),
      }),
    );

    await page.goto('/documents');

    await expect(page.locator('[data-error-code="TIMEOUT"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-retry="true"]')).toBeVisible();
    await expect(page.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  }, { timeout: 30_000 });

  test('VALIDATION_ERROR on documents shows error code without retry', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify(AUTH_STATE_FULL));
      window.localStorage.setItem('wissen.authToken', 'truth-token');
      window.localStorage.setItem('wissen.workspaceId', 'workspace-1');
    });
    await page.route('**/documents?**', (route) =>
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'VALIDATION_ERROR', message: 'Invalid params', details: {} } }),
      }),
    );

    await page.goto('/documents');

    await expect(page.locator('[data-error-code="VALIDATION_ERROR"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-retry="true"]')).not.toBeVisible();
    await expect(page.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  });

  test('SERVER_ERROR on documents shows error code with retry', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify(AUTH_STATE_FULL));
      window.localStorage.setItem('wissen.authToken', 'truth-token');
      window.localStorage.setItem('wissen.workspaceId', 'workspace-1');
    });
    await page.route('**/documents?**', (route) =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'SERVER_ERROR', message: 'Internal error', details: {} } }),
      }),
    );

    await page.goto('/documents');

    await expect(page.locator('[data-error-code="SERVER_ERROR"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-retry="true"]')).toBeVisible();
    await expect(page.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  });

  test('OCR_REQUIRED on import renders upload-ocr-required testid', async ({ authedPage }) => {
    await authedPage.route('**/documents/import', (route) =>
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'OCR_REQUIRED', message: 'OCR not available', details: {} },
        }),
      }),
    );

    await authedPage.getByTestId('upload-file-input').setInputFiles({
      name: 'ocr-test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('ocr test content'),
    });
    await authedPage.getByTestId('upload-submit').click();

    await expect(authedPage.getByTestId('upload-ocr-required')).toBeVisible({ timeout: 10_000 });
    await authedPage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('FILE_TOO_LARGE on import renders upload-file-too-large testid', async ({ authedPage }) => {
    await authedPage.route('**/documents/import', (route) =>
      route.fulfill({
        status: 413,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'FILE_TOO_LARGE', message: 'File exceeds upload limit', details: {} },
        }),
      }),
    );

    await authedPage.getByTestId('upload-file-input').setInputFiles({
      name: 'large-test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('large file content'),
    });
    await authedPage.getByTestId('upload-submit').click();

    await expect(authedPage.getByTestId('upload-file-too-large')).toBeVisible({ timeout: 10_000 });
    await authedPage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('DUPLICATE_DOCUMENT on import renders upload-success with duplicate code', async ({ authedPage }) => {
    const fakeJobId = 'test-job-dup-001';

    await authedPage.route('**/documents/import', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: fakeJobId, job_type: 'import' }),
      }),
    );
    await authedPage.route('**/jobs/**', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: fakeJobId,
          status: 'completed',
          job_type: 'import',
          result: {
            import_status: 'duplicate',
            duplicate_of_document_id: 'existing-doc-42',
            document_id: 'existing-doc-42',
          },
        }),
      }),
    );

    await authedPage.getByTestId('upload-file-input').setInputFiles({
      name: 'duplicate-test.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('duplicate test document'),
    });
    await authedPage.getByTestId('upload-submit').click();

    await expect(authedPage.getByTestId('upload-success')).toBeVisible({ timeout: 15_000 });
    await expect(authedPage.getByTestId('upload-success')).toContainText('DUPLICATE_DOCUMENT');
    await authedPage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('INSUFFICIENT_CONTEXT on chat message renders chat-insufficient-context testid', async ({ authedPage }) => {
    await authedPage.goto('/chat');
    await expect(authedPage.getByTestId('chat-page')).toBeVisible({ timeout: 10_000 });

    // Create a session
    await authedPage.getByTestId('chat-session-title').fill('E2E Invariant Test Session');
    await authedPage.getByTestId('chat-new-session').click();
    await authedPage.waitForTimeout(2_000);

    // Intercept message send to return INSUFFICIENT_CONTEXT
    await authedPage.route('**/messages', (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 422,
          contentType: 'application/json',
          body: JSON.stringify({
            error: {
              code: 'INSUFFICIENT_CONTEXT',
              message: 'Not enough context',
              details: { backendCode: 'INSUFFICIENT_CONTEXT' },
            },
          }),
        });
      }
      return route.continue();
    });

    await authedPage.getByTestId('chat-input').fill('test question for context');
    await authedPage.getByTestId('chat-submit').click();

    await expect(authedPage.getByTestId('chat-insufficient-context')).toBeVisible({ timeout: 10_000 });
    await authedPage.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('REINDEX_RUNNING on documents shows error code with retry and is not empty list', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify(AUTH_STATE_FULL));
      window.localStorage.setItem('wissen.authToken', 'truth-token');
      window.localStorage.setItem('wissen.workspaceId', 'workspace-1');
    });
    await page.route('**/documents?**', (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'REINDEX_RUNNING', message: 'Reindex in progress', details: {} },
        }),
      }),
    );

    await page.goto('/documents');

    await expect(page.locator('[data-error-code="REINDEX_RUNNING"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-retry="true"]')).toBeVisible();
    await expect(page.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  });

  test('QUEUE_DEGRADED on documents shows error code with retry and is not empty list', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      window.localStorage.setItem('wissen.authState', JSON.stringify(AUTH_STATE_FULL));
      window.localStorage.setItem('wissen.authToken', 'truth-token');
      window.localStorage.setItem('wissen.workspaceId', 'workspace-1');
    });
    await page.route('**/documents?**', (route) =>
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'QUEUE_DEGRADED', message: 'Queue is degraded', details: {} },
        }),
      }),
    );

    await page.goto('/documents');

    await expect(page.locator('[data-error-code="QUEUE_DEGRADED"]')).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('[data-retry="true"]')).toBeVisible();
    await expect(page.getByText('Keine Dokumente vorhanden')).not.toBeVisible();
  });
});
