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

async function openPreparedSession(page, title) {
  const session = await createPreparedChatSession(page, title);
  await page.goto(`/chat/${session.id}`);
  await expect(page).toHaveURL(new RegExp(`/chat/${session.id}$`), { timeout: 10_000 });
  await expect(page.getByTestId('chat-submit')).toBeEnabled({ timeout: 10_000 });
  return session;
}

async function askQuestion(page, question, sessionId) {
  await page.getByTestId('chat-input').fill(question);
  const [response] = await Promise.all([
    page.waitForResponse((candidate) => (
      candidate.request().method() === 'POST'
      && candidate.url().includes(`/api/v1/chat/sessions/${sessionId}/messages`)
    )),
    page.getByTestId('chat-submit').click(),
  ]);
  return response;
}

test.describe('07 Chat flow', () => {
  test('chat page is visible with stable controls', async ({ authedPage }) => {
    const workspaceId = process.env.TRUTH_WORKSPACE_ID;
    await authedPage.goto('/chat');
    await expect(authedPage.getByTestId('chat-page')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByText(`Workspace: ${workspaceId}`)).toBeVisible();
    await expect(authedPage.getByTestId('chat-new-session')).toBeVisible();
    await expect(authedPage.getByTestId('chat-input')).toBeVisible();
    await expect(authedPage.getByTestId('chat-submit')).toBeVisible();
  });

  test('creates a new chat session through the UI', async ({ authedPage }) => {
    const title = `GUI Truth Chat ${Date.now()}`;
    await authedPage.goto('/chat');
    await authedPage.getByTestId('chat-session-title').fill(title);
    await authedPage.getByTestId('chat-new-session').click();

    await expect(authedPage.getByText(title)).toBeVisible({ timeout: 10_000 });
    await expect(authedPage).toHaveURL(/\/chat\/.+/);
  });

  test('posts a question through the real API', async ({ authedPage }) => {
    const session = await openPreparedSession(authedPage, `GUI Truth Question Chat ${Date.now()}`);
    const response = await askQuestion(
      authedPage,
      'GUI Truth Active Document truthneedle active knowledge base content',
      session.id,
    );

    expect(response.status()).toBe(201);
    await expect(authedPage.getByTestId('chat-message-list')).toContainText('GUI Truth Active Document truthneedle');
  });

  test('renders an assistant answer', async ({ authedPage }) => {
    const session = await openPreparedSession(authedPage, `GUI Truth Answer Chat ${Date.now()}`);
    const response = await askQuestion(
      authedPage,
      'GUI Truth Active Document truthneedle active knowledge base content deterministic citations supporting text',
      session.id,
    );

    expect(response.status()).toBe(201);
    await expect(authedPage.getByTestId('chat-answer')).toBeVisible({ timeout: 10_000 });
    await expect(authedPage.getByTestId('chat-answer')).not.toHaveText('');
  });

  test('renders citations for grounded answers', async ({ authedPage }) => {
    const session = await openPreparedSession(authedPage, `GUI Truth Citation Chat ${Date.now()}`);
    const response = await askQuestion(
      authedPage,
      'GUI Truth Active Document truthneedle active knowledge base content deterministic citations supporting text',
      session.id,
    );
    const payload = await response.json();

    expect(response.status()).toBe(201);
    expect(payload.citations.length).toBeGreaterThan(0);
    await expect(authedPage.getByTestId('chat-citations')).toContainText('GUI Truth Active Document', { timeout: 10_000 });
  });

  test('renders citation source_status', async ({ authedPage }) => {
    const session = await openPreparedSession(authedPage, `GUI Truth Source Status Chat ${Date.now()}`);
    const response = await askQuestion(
      authedPage,
      'GUI Truth Active Document truthneedle active knowledge base content deterministic citations supporting text',
      session.id,
    );
    const payload = await response.json();

    expect(response.status()).toBe(201);
    expect(payload.citations[0]?.source_status).toBe('active');
    await expect(authedPage.getByTestId('chat-citations')).toContainText('Source Status: active', { timeout: 10_000 });
  });

  test('renders insufficient_context as controlled error state', async ({ authedPage }) => {
    const session = await openPreparedSession(authedPage, `GUI Truth No Context Chat ${Date.now()}`);
    const response = await askQuestion(authedPage, 'nohitneedle-frontend-truth-without-context', session.id);

    expect(response.status()).toBe(422);
    await expect(authedPage.getByTestId('chat-insufficient-context')).toContainText('Fehlercode: INSUFFICIENT_CONTEXT', {
      timeout: 10_000,
    });
  });

  test('archived and deleted sources are not used in new retrieval', async ({ authedPage }) => {
    const session = await openPreparedSession(authedPage, `GUI Truth Lifecycle Filter Chat ${Date.now()}`);
    const response = await askQuestion(
      authedPage,
      'GUI Truth Active Document truthneedle active knowledge base content deterministic citations supporting text',
      session.id,
    );
    const payload = await response.json();

    expect(response.status()).toBe(201);
    expect(payload.citations.length).toBeGreaterThan(0);
    expect(payload.citations.every((citation) => citation.source_status === 'active')).toBe(true);
    expect(payload.citations.some((citation) => citation.document_title === 'GUI Truth Archived Document')).toBe(false);
    expect(payload.citations.some((citation) => citation.document_title === 'GUI Truth Deleted Document')).toBe(false);
    await expect(authedPage.getByTestId('chat-citations')).not.toContainText('GUI Truth Archived Document');
    await expect(authedPage.getByTestId('chat-citations')).not.toContainText('GUI Truth Deleted Document');
  });

  test('chat API error is visible', async ({ authedPage }) => {
    const session = await openPreparedSession(authedPage, `GUI Truth API Error Chat ${Date.now()}`);
    await authedPage.route(`**/api/v1/chat/sessions/${session.id}/messages`, (route) => route.abort('failed'));

    await authedPage.getByTestId('chat-input').fill('truthneedle');
    await authedPage.getByTestId('chat-submit').click();

    await expect(authedPage.getByTestId('chat-error')).toContainText('Fehlercode: API_UNREACHABLE', { timeout: 10_000 });
  });
});
