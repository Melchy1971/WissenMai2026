import { expect, test } from './fixtures.js';

test.describe('08 Lifecycle GUI', () => {
  // --- Part A: filter UI ---

  test('shows lifecycle filter with correct default option', async ({ authedPage }) => {
    const select = authedPage.getByLabel('Statusfilter');
    await expect(select).toBeVisible();
    await expect(select).toHaveValue('active');
  });

  test('lifecycle filter shows correct option labels', async ({ authedPage }) => {
    await expect(authedPage.getByRole('option', { name: 'Nur aktive Dokumente' })).toBeAttached();
    await expect(authedPage.getByRole('option', { name: 'Nur archivierte Dokumente' })).toBeAttached();
  });

  test('switching to archived filter triggers API call without error', async ({ authedPage }) => {
    await authedPage.getByLabel('Statusfilter').selectOption('archived');
    await authedPage.waitForTimeout(3_000);
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('switching back to active filter restores document list', async ({ authedPage }) => {
    const select = authedPage.getByLabel('Statusfilter');
    await select.selectOption('archived');
    await authedPage.waitForTimeout(1_000);
    await select.selectOption('active');
    await authedPage.waitForTimeout(3_000);
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible();
  });

  test('shows lifecycle warning hint text', async ({ authedPage }) => {
    await expect(
      authedPage.getByText('Archivierte Dokumente erscheinen nicht in Suche oder Chat.'),
    ).toBeVisible();
  });

  test('active document is visible while deleted document is hidden', async ({ authedPage }) => {
    await authedPage.getByLabel('Statusfilter').selectOption('active');
    await expect(authedPage.getByRole('link', { name: 'GUI Truth Active Document' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Deleted Document')).not.toBeVisible();
  });

  test('archived document is not returned by active search', async ({ authedPage }) => {
    await authedPage.getByLabel('Suchbegriff').fill('archivedneedle');
    await authedPage.getByRole('button', { name: 'Suchen' }).click();
    await expect(authedPage.getByText('Keine Treffer gefunden')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Archived Document')).not.toBeVisible();
  });

  test('archived document is visible only in archived filter', async ({ authedPage }) => {
    await authedPage.getByLabel('Statusfilter').selectOption('archived');
    await expect(authedPage.getByRole('link', { name: 'GUI Truth Archived Document' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText('GUI Truth Deleted Document')).not.toBeVisible();
  });

  // --- Part B: seeded document structural assertions ---

  test('S1: active document detail has lifecycle-status and action controls', async ({ authedPage }) => {
    await authedPage.getByRole('link', { name: 'GUI Truth Active Document' }).click();
    await expect(authedPage.getByTestId('lifecycle-status')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('document-archive')).toBeVisible();
    await expect(authedPage.getByTestId('document-delete')).toBeVisible();
    await expect(authedPage.getByTestId('document-restore')).not.toBeVisible();
  });

  test('S3: archived document shows document-status-badge in table', async ({ authedPage }) => {
    await authedPage.getByTestId('archived-filter').selectOption('archived');
    await expect(authedPage.getByRole('link', { name: 'GUI Truth Archived Document' })).toBeVisible({ timeout: 10_000 });
    const row = authedPage.locator('tr', {
      has: authedPage.getByRole('link', { name: 'GUI Truth Archived Document' }),
    });
    await expect(row.getByTestId('document-status-badge')).toContainText('archived', { timeout: 5_000 });
  });

  // --- Part C: full lifecycle action flow (fresh document, serial) ---

  test.describe.serial('lifecycle action flows', () => {
    const ctx = {};

    test.beforeAll(async ({ browser }) => {
      const apiBase = process.env.TRUTH_API_BASE_URL || 'http://127.0.0.1:8013';
      const token = process.env.TRUTH_TOKEN;
      const workspaceId = process.env.TRUTH_WORKSPACE_ID;

      const context = await browser.newContext();
      const page = await context.newPage();

      const uploadResp = await page.request.post(`${apiBase}/api/v1/documents/import`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'X-Workspace-Id': workspaceId,
        },
        multipart: {
          file: {
            name: 'lifecycle-e2e-test.txt',
            mimeType: 'text/plain',
            buffer: Buffer.from('lifecycle e2e test document content for automated testing'),
          },
        },
      });

      expect(uploadResp.ok()).toBeTruthy();
      const job = await uploadResp.json();

      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 500));
        const jobResp = await page.request.get(`${apiBase}/api/v1/jobs/${job.id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'X-Workspace-Id': workspaceId,
          },
        });
        const jobData = await jobResp.json();
        if (jobData.status === 'completed') {
          ctx.docId = jobData.result?.document_id;
          break;
        }
        if (jobData.status === 'failed') {
          throw new Error(`Upload job failed: ${jobData.error_message || 'unknown'}`);
        }
        attempts++;
      }

      if (!ctx.docId) throw new Error('document_id not available after upload job completed');
      await context.close();
    });

    test('S2: archive action updates document-status-badge to archived', async ({ authedPage }) => {
      await authedPage.goto(`/documents/${ctx.docId}`);
      await expect(authedPage.getByTestId('lifecycle-status')).toBeVisible({ timeout: 10_000 });
      await expect(authedPage.getByTestId('document-archive')).toBeVisible();

      await authedPage.getByTestId('document-archive').click();

      await expect(authedPage.getByTestId('document-status-badge')).toContainText('archived', { timeout: 10_000 });
      await expect(authedPage.getByTestId('document-restore')).toBeVisible({ timeout: 5_000 });
      await expect(authedPage.getByTestId('document-archive')).not.toBeVisible();
    });

    test('S4: archived document absent from active list and present in archived filter', async ({ authedPage }) => {
      // active filter should not show the archived document
      await authedPage.getByLabel('Statusfilter').selectOption('active');
      await authedPage.waitForTimeout(2_000);
      await expect(authedPage.locator(`a[href="/documents/${ctx.docId}"]`)).not.toBeVisible();

      // archived filter must show it
      await authedPage.getByTestId('archived-filter').selectOption('archived');
      await expect(authedPage.locator(`a[href="/documents/${ctx.docId}"]`)).toBeVisible({ timeout: 10_000 });
    });

    test('S5: restore action updates document-status-badge to active', async ({ authedPage }) => {
      await authedPage.goto(`/documents/${ctx.docId}`);
      await expect(authedPage.getByTestId('document-restore')).toBeVisible({ timeout: 10_000 });

      await authedPage.getByTestId('document-restore').click();

      await expect(authedPage.getByTestId('document-status-badge')).toContainText('active', { timeout: 10_000 });
      await expect(authedPage.getByTestId('document-archive')).toBeVisible({ timeout: 5_000 });
      await expect(authedPage.getByTestId('document-restore')).not.toBeVisible();
    });

    test('S6: restored document visible in active document list', async ({ authedPage }) => {
      await authedPage.getByLabel('Statusfilter').selectOption('active');
      await expect(authedPage.locator(`a[href="/documents/${ctx.docId}"]`)).toBeVisible({ timeout: 10_000 });
    });

    test('S7: delete action navigates to document list after dialog confirm', async ({ authedPage }) => {
      await authedPage.goto(`/documents/${ctx.docId}`);
      await expect(authedPage.getByTestId('document-delete')).toBeVisible({ timeout: 10_000 });

      authedPage.once('dialog', (dialog) => dialog.accept());
      await authedPage.getByTestId('document-delete').click();

      await expect(authedPage).toHaveURL(/\/documents$/, { timeout: 10_000 });
    });

    test('S8: deleted document absent from active document list', async ({ authedPage }) => {
      await authedPage.getByLabel('Statusfilter').selectOption('active');
      await authedPage.waitForTimeout(2_000);
      await expect(authedPage.locator(`a[href="/documents/${ctx.docId}"]`)).not.toBeVisible();
    });

    test('S9: deleted document absent from search results', async ({ authedPage }) => {
      await authedPage.getByTestId('search-input').fill('lifecycle e2e test document');
      await authedPage.getByTestId('search-submit').click();
      await authedPage.waitForTimeout(3_000);
      await expect(authedPage.locator(`a[href="/documents/${ctx.docId}"]`)).not.toBeVisible();
    });

    test('S10: lifecycle mutation error renders lifecycle-error testid', async ({ authedPage }) => {
      await authedPage.getByLabel('Statusfilter').selectOption('active');
      await expect(authedPage.getByRole('link', { name: 'GUI Truth Active Document' })).toBeVisible({ timeout: 10_000 });
      await authedPage.getByRole('link', { name: 'GUI Truth Active Document' }).click();
      await expect(authedPage.getByTestId('document-archive')).toBeVisible({ timeout: 10_000 });

      await authedPage.route('**/documents/**', async (route) => {
        if (route.request().method() === 'POST' || route.request().method() === 'PATCH') {
          return route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({
              error: { code: 'SERVER_ERROR', message: 'Forced error for lifecycle test', details: {} },
            }),
          });
        }
        return route.continue();
      });

      await authedPage.getByTestId('document-archive').click();
      await expect(authedPage.getByTestId('lifecycle-error')).toBeVisible({ timeout: 10_000 });
      await authedPage.unrouteAll({ behavior: 'ignoreErrors' });
    });
  });
});
