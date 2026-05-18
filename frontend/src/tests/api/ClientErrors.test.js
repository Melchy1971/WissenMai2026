import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiClientError, requestJson, setApiRequestContext } from '../../api/client.js';

// ─── Helpers ─────────────────────────────────────────────────────────────────

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: HTTP_STATUS_TEXT[status] ?? 'Unknown',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => payload,
  };
}

const HTTP_STATUS_TEXT = { 200: 'OK', 400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 422: 'Unprocessable Entity', 500: 'Internal Server Error', 503: 'Service Unavailable' };

function captureFetch(returnValue) {
  let captured = null;
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, opts) => {
    captured = { url, opts };
    return typeof returnValue === 'function' ? returnValue(url, opts) : returnValue;
  });
  return () => captured;
}

function signalAwarePendingFetch() {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((_url, { signal } = {}) =>
    new Promise((_, reject) => {
      if (signal?.aborted) {
        reject(new DOMException('The operation was aborted.', 'AbortError'));
        return;
      }
      signal?.addEventListener('abort', () =>
        reject(new DOMException('The operation was aborted.', 'AbortError')),
      );
    }),
  );
}

// ─── Setup / teardown ────────────────────────────────────────────────────────

afterEach(() => {
  vi.restoreAllMocks();
  setApiRequestContext({ authToken: '', workspaceId: '' });
});

// ─── 1. Header enforcement ────────────────────────────────────────────────────
describe('header enforcement', () => {
  it('sets Authorization header from context', async () => {
    setApiRequestContext({ authToken: 'test-token-abc', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents');

    expect(getCapture().opts.headers.Authorization).toBe('Bearer test-token-abc');
  });

  it('sets X-Workspace-Id header from context', async () => {
    setApiRequestContext({ authToken: 'tok', workspaceId: 'ws-id-123' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents');

    expect(getCapture().opts.headers['X-Workspace-Id']).toBe('ws-id-123');
  });

  it('does not set Authorization when context has no token', async () => {
    setApiRequestContext({ authToken: '', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents');

    expect(getCapture().opts.headers.Authorization).toBeUndefined();
  });

  it('does not set X-Workspace-Id when context has no workspace', async () => {
    setApiRequestContext({ authToken: 'tok', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents');

    expect(getCapture().opts.headers['X-Workspace-Id']).toBeUndefined();
  });

  it('caller-provided Authorization header is silently discarded', async () => {
    setApiRequestContext({ authToken: 'real-token', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents', {
      headers: { Authorization: 'Bearer attacker-injected-token' },
    });

    expect(getCapture().opts.headers.Authorization).toBe('Bearer real-token');
  });

  it('caller-provided X-Workspace-Id header is silently discarded', async () => {
    setApiRequestContext({ authToken: 'tok', workspaceId: 'real-ws' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents', {
      headers: { 'X-Workspace-Id': 'manipulated-ws' },
    });

    expect(getCapture().opts.headers['X-Workspace-Id']).toBe('real-ws');
  });

  it('caller-provided central headers are discarded case-insensitively', async () => {
    setApiRequestContext({ authToken: 'real-token', workspaceId: 'real-ws' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents', {
      headers: {
        authorization: 'Bearer injected-token',
        'x-workspace-id': 'injected-ws',
      },
    });

    expect(getCapture().opts.headers.authorization).toBeUndefined();
    expect(getCapture().opts.headers['x-workspace-id']).toBeUndefined();
    expect(getCapture().opts.headers.Authorization).toBe('Bearer real-token');
    expect(getCapture().opts.headers['X-Workspace-Id']).toBe('real-ws');
  });

  it('normalizes Headers instances without allowing central header overrides', async () => {
    setApiRequestContext({ authToken: 'real-token', workspaceId: 'real-ws' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));
    const headers = new Headers({
      Authorization: 'Bearer injected-token',
      'X-Workspace-Id': 'injected-ws',
      'X-Client-Feature': 'diagnostics',
    });

    await requestJson('/api/v1/documents', { headers });

    expect(getCapture().opts.headers.Authorization).toBe('Bearer real-token');
    expect(getCapture().opts.headers['X-Workspace-Id']).toBe('real-ws');
    expect(getCapture().opts.headers['x-client-feature']).toBe('diagnostics');
  });

  it('auto-infers Content-Type application/json for string bodies', async () => {
    setApiRequestContext({ authToken: 'tok', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ ok: true }));

    await requestJson('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({ login: 'user', password: 'pw' }),
    });

    expect(getCapture().opts.headers['Content-Type']).toBe('application/json');
  });

  it('does not set Content-Type for FormData bodies', async () => {
    setApiRequestContext({ authToken: 'tok', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ ok: true }));
    const form = new FormData();
    form.append('file', new Blob(['test'], { type: 'text/plain' }), 'test.txt');

    await requestJson('/documents/import', { method: 'POST', body: form });

    // FormData is not a string → no Content-Type injection
    expect(getCapture().opts.headers['Content-Type']).toBeUndefined();
  });

  it('forwards correlationId as X-Correlation-Id', async () => {
    setApiRequestContext({ authToken: 'tok', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents', { correlationId: 'trace-xyz-001' });

    expect(getCapture().opts.headers['X-Correlation-Id']).toBe('trace-xyz-001');
  });

  it('omits X-Correlation-Id when correlationId is not provided', async () => {
    setApiRequestContext({ authToken: 'tok', workspaceId: '' });
    const getCapture = captureFetch(jsonResponse({ data: 'ok' }));

    await requestJson('/api/v1/documents');

    expect(getCapture().opts.headers['X-Correlation-Id']).toBeUndefined();
  });
});

// ─── 2. Network / fetch failure classification ───────────────────────────────
describe('network error classification', () => {
  it('maps unreachable backend to API_UNREACHABLE', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      name: 'ApiClientError',
      code: 'API_UNREACHABLE',
      status: null,
    });
  });

  it('maps CORS-like fetch failures to API_UNREACHABLE', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(
      new TypeError('CORS access-control blocked'),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'API_UNREACHABLE',
      status: null,
    });
  });

  it('maps AbortError to TIMEOUT', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(
      new DOMException('The operation was aborted', 'AbortError'),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'TIMEOUT',
      status: null,
    });
  });
});

// ─── 3. HTTP error classification ─────────────────────────────────────────────
describe('HTTP error classification', () => {
  it('maps 401 to AUTH_REQUIRED', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ error: { code: 'UNAUTHORIZED', message: 'Token fehlt', details: {} } }, 401),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'AUTH_REQUIRED',
      message: 'Token fehlt',
      status: 401,
    });
  });

  it('maps WORKSPACE_REQUIRED payload to WORKSPACE_NOT_CONFIGURED', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'WORKSPACE_REQUIRED', message: 'Workspace fehlt', details: {} } },
        400,
      ),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'WORKSPACE_NOT_CONFIGURED',
      message: 'Workspace fehlt',
      status: 400,
    });
  });

  it('maps WORKSPACE_NOT_CONFIGURED payload to WORKSPACE_NOT_CONFIGURED', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        {
          error: {
            code: 'WORKSPACE_NOT_CONFIGURED',
            message: 'Keine Workspace-Mitgliedschaft',
            details: {},
          },
        },
        403,
      ),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'WORKSPACE_NOT_CONFIGURED',
      message: 'Keine Workspace-Mitgliedschaft',
      status: 403,
    });
  });

  it('maps WORKSPACE_ACCESS_FORBIDDEN payload to FORBIDDEN', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'WORKSPACE_ACCESS_FORBIDDEN', message: 'Workspace verboten', details: {} } },
        403,
      ),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'FORBIDDEN',
      status: 403,
    });
  });

  it('maps bare 403 to FORBIDDEN', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ error: { code: 'FORBIDDEN', message: 'Zugriff verweigert', details: {} } }, 403),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'FORBIDDEN',
      status: 403,
    });
  });

  it('maps 422 to VALIDATION_ERROR', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'VALIDATION_ERROR', message: 'Feld fehlt', details: {} } },
        422,
      ),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      message: 'Feld fehlt',
      status: 422,
    });
  });

  it('keeps backend domain code in details while exposing stable classification', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'INVALID_QUERY', message: 'Ungueltige Suche', details: {} } },
        422,
      ),
    );

    await expect(requestJson('/api/v1/search/chunks?q=*')).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      details: {
        backendCode: 'INVALID_QUERY',
        classification: 'VALIDATION_ERROR',
      },
      status: 422,
    });
  });

  it('maps 400 with VALIDATION_ERROR code to VALIDATION_ERROR', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'VALIDATION_ERROR', message: 'Ungültige Eingabe', details: {} } },
        400,
      ),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      status: 400,
    });
  });

  it('maps 400 with INVALID_INPUT code to VALIDATION_ERROR', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'INVALID_INPUT', message: 'Schemaverstoß', details: {} } },
        400,
      ),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'VALIDATION_ERROR',
      status: 400,
    });
  });

  it('maps 500 to SERVER_ERROR', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ error: { code: 'INTERNAL_ERROR', message: 'Datenbankfehler', details: {} } }, 500),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'SERVER_ERROR',
      message: 'Datenbankfehler',
      status: 500,
    });
  });

  it('maps 503 to SERVER_ERROR', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ error: { code: 'SERVICE_DOWN', message: 'Dienst nicht verfügbar', details: {} } }, 503),
    );

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'SERVER_ERROR',
      status: 503,
    });
  });
});

// ─── 4. Timeout ───────────────────────────────────────────────────────────────
describe('timeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('aborts and throws TIMEOUT after configured timeoutMs', async () => {
    signalAwarePendingFetch();

    const promise = requestJson('/api/v1/documents', { timeoutMs: 200 });
    vi.advanceTimersByTime(200);

    await expect(promise).rejects.toMatchObject({ code: 'TIMEOUT', status: null });
  });

  it('does not abort before timeoutMs elapses', async () => {
    signalAwarePendingFetch();

    const promise = requestJson('/api/v1/documents', { timeoutMs: 500 });
    vi.advanceTimersByTime(499);

    // Promise should still be pending — we just verify it hasn't rejected yet.
    let settled = false;
    promise.then(() => { settled = true; }).catch(() => { settled = true; });
    await Promise.resolve(); // flush microtasks
    expect(settled).toBe(false);

    // Clean up: advance past timeout so the pending fetch is aborted
    vi.advanceTimersByTime(1);
    await expect(promise).rejects.toMatchObject({ code: 'TIMEOUT' });
  });

  it('respects custom shorter timeout vs default', async () => {
    signalAwarePendingFetch();

    const promise = requestJson('/api/v1/documents', { timeoutMs: 100 });
    vi.advanceTimersByTime(100);

    await expect(promise).rejects.toMatchObject({ code: 'TIMEOUT' });
  });

  it('applies timeout even when an external AbortSignal is provided', async () => {
    signalAwarePendingFetch();
    const controller = new AbortController();

    const promise = requestJson('/api/v1/documents', {
      signal: controller.signal,
      timeoutMs: 100,
    });
    vi.advanceTimersByTime(100);

    await expect(promise).rejects.toMatchObject({ code: 'TIMEOUT' });
  });
});

// ─── 5. ApiClientError shape ─────────────────────────────────────────────────
describe('ApiClientError shape', () => {
  it('is an instance of Error', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const error = await requestJson('/api/v1/documents').catch((e) => e);
    expect(error).toBeInstanceOf(Error);
    expect(error).toBeInstanceOf(ApiClientError);
  });

  it('carries status null for network errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const error = await requestJson('/api/v1/documents').catch((e) => e);
    expect(error.status).toBeNull();
  });

  it('carries HTTP status for server responses', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse({ error: { code: 'E', message: 'm', details: {} } }, 422),
    );
    const error = await requestJson('/api/v1/documents').catch((e) => e);
    expect(error.status).toBe(422);
  });

  it('has name ApiClientError', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const error = await requestJson('/api/v1/documents').catch((e) => e);
    expect(error.name).toBe('ApiClientError');
  });
});
