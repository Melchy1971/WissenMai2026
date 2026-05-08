import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiClientError, requestJson, setApiRequestContext } from '../../api/client.js';

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 403 ? 'Forbidden' : 'Unauthorized',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => payload,
  };
}

describe('api client error classification', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    setApiRequestContext({ authToken: '', workspaceId: '' });
  });

  it('maps unreachable backend to API_UNREACHABLE', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('Failed to fetch'));

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      name: 'ApiClientError',
      code: 'API_UNREACHABLE',
      status: null,
    });
  });

  it('maps CORS-like fetch failures to CORS_ERROR', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new TypeError('CORS access-control blocked'));

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'CORS_ERROR',
      status: null,
    });
  });

  it('maps timeout aborts to TIMEOUT', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new DOMException('The operation was aborted', 'AbortError'));

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'TIMEOUT',
      status: null,
    });
  });

  it('maps 401 to AUTH_REQUIRED', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      error: { code: 'UNAUTHORIZED', message: 'Token fehlt', details: {} },
    }, 401));

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'AUTH_REQUIRED',
      message: 'Token fehlt',
      status: 401,
    });
  });

  it('maps workspace-required payloads to WORKSPACE_NOT_CONFIGURED', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      error: { code: 'WORKSPACE_REQUIRED', message: 'Workspace fehlt', details: {} },
    }, 400));

    await expect(requestJson('/api/v1/documents')).rejects.toMatchObject({
      code: 'WORKSPACE_NOT_CONFIGURED',
      message: 'Workspace fehlt',
      status: 400,
    });
  });

  it('maps 403 to FORBIDDEN', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      error: { code: 'WORKSPACE_ACCESS_FORBIDDEN', message: 'Workspace verboten', details: {} },
    }, 403));

    let error;
    try {
      await requestJson('/api/v1/documents');
    } catch (caught) {
      error = caught;
    }

    expect(error).toBeInstanceOf(ApiClientError);
    expect(error).toMatchObject({
      code: 'FORBIDDEN',
      status: 403,
    });
  });
});
