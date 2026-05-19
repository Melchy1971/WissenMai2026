import { expect, test } from './fixtures.js';

async function createPreparedChatSession(page, title) {
  const apiBaseUrl = process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://127.0.0.1:8000';
  const workspaceId = process.env.TRUTH_WORKSPACE_ID;
  const token = process.env.TRUTH_TOKEN;
  const response = await page.request.post(`${apiBaseUrl}/api/v1/chat/sessions`, {
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      'X-Workspace-Id': workspaceId,
    },
    data: { title },
  });

  expect(response.ok()).toBeTruthy();
  return response.json();
}

test.describe('07 Chat flow', () => {
  test('shows chat page heading and workspace context', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await authedPage.goto('/chat');
    await expect(authedPage.getByRole('heading', { name: 'Dokumentgestuetzter Chat' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  });

  test('shows empty chat state or session list', async ({ authedPage }) => {
    await authedPage.goto('/chat');

    // Either no sessions exist (empty state) or there are existing sessions
    await authedPage.waitForTimeout(3_000);
    const hasError = await authedPage.locator('.state-card--error').isVisible().catch(() => false);
    expect(hasError).toBe(false);
  });

  test('shows chat composer form', async ({ authedPage }) => {
    await authedPage.goto('/chat');
    // Wait for loading to finish
    await expect(authedPage.locator('.state-card--error')).not.toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByLabel('Titel der Sitzung')).toBeVisible({ timeout: 5_000 });
    await expect(authedPage.locator('.chat-layout')).toBeVisible();
  });

  test('navigation from documents to chat preserves workspace context', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    // Start on documents
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
    // Navigate to chat
    await authedPage.getByRole('link', { name: 'Chat' }).click();
    await expect(authedPage.getByRole('heading', { name: 'Dokumentgestuetzter Chat' })).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
  });

  test('creates a chat session through the real API', async ({ authedPage }) => {
    const title = `GUI Truth Chat ${Date.now()}`;
    await authedPage.goto('/chat');
    await authedPage.getByLabel('Titel der Sitzung').fill(title);
    await authedPage.getByRole('button', { name: 'Neue Sitzung' }).click();

    await expect(authedPage.getByText(title)).toBeVisible({ timeout: 10_000 });
    await expect(authedPage).toHaveURL(/\/chat\/.+/);
  });

  test('posts a question and renders an answer with citations', async ({ authedPage }) => {
    const title = `GUI Truth Citation Chat ${Date.now()}`;
    const session = await createPreparedChatSession(authedPage, title);
    await authedPage.goto(`/chat/${session.id}`);
    await expect(authedPage).toHaveURL(new RegExp(`/chat/${session.id}$`), { timeout: 10_000 });

    await authedPage.getByLabel('Frage').fill(
      'GUI Truth Active Document truthneedle active knowledge base content deterministic citations supporting text',
    );
    const [response] = await Promise.all([
      authedPage.waitForResponse((candidate) => (
        candidate.request().method() === 'POST'
        && candidate.url().includes(`/api/v1/chat/sessions/${session.id}/messages`)
      )),
      authedPage.getByRole('button', { name: 'Frage senden' }).click(),
    ]);

    expect(response.status()).toBe(201);
    const payload = await response.json();
    expect(payload.role).toBe('assistant');
    expect(Array.isArray(payload.citations)).toBe(true);
    expect(payload.citations.length).toBeGreaterThan(0);
    expect(payload.citations[0]?.document_title).toBe('GUI Truth Active Document');
  });

  test('insufficient context is rendered as a controlled error state', async ({ authedPage }) => {
    const title = `GUI Truth No Context Chat ${Date.now()}`;
    const session = await createPreparedChatSession(authedPage, title);
    await authedPage.goto(`/chat/${session.id}`);
    await expect(authedPage).toHaveURL(new RegExp(`/chat/${session.id}$`), { timeout: 10_000 });

    await authedPage.getByLabel('Frage').fill('nohitneedle-frontend-truth-without-context');
    const [response] = await Promise.all([
      authedPage.waitForResponse((candidate) => (
        candidate.request().method() === 'POST'
        && candidate.url().includes(`/api/v1/chat/sessions/${session.id}/messages`)
      )),
      authedPage.getByRole('button', { name: 'Frage senden' }).click(),
    ]);

    expect(response.status()).toBe(422);
    const payload = await response.json();
    expect(payload.error?.code).toBe('INSUFFICIENT_CONTEXT');
  });
});
