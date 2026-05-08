import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppRoutes } from '../../app/routes.jsx';
import { AuthProvider } from '../../auth/AuthContext.jsx';
import { setApiRequestContext } from '../../api/client.js';

const AUTH_STATE_STORAGE_KEY = 'wissen.authState';

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 401 ? 'Unauthorized' : 'OK',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => payload,
  };
}

function renderApp(initialEntry = '/documents') {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AppRoutes />
      </MemoryRouter>
    </AuthProvider>,
  );
}

function installMemoryStorage() {
  const values = new Map();
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: (key) => values.get(key) || null,
      setItem: (key, value) => values.set(key, String(value)),
      removeItem: (key) => values.delete(key),
      clear: () => values.clear(),
    },
  });
}

function storeTokenOnly() {
  window.localStorage.setItem(AUTH_STATE_STORAGE_KEY, JSON.stringify({ token: 'test-token' }));
}

function clearStoredAuth() {
  window.localStorage.removeItem(AUTH_STATE_STORAGE_KEY);
  window.localStorage.removeItem('wissen.authToken');
  window.localStorage.removeItem('wissen.workspaceId');
}

describe('Auth bootstrap', () => {
  beforeEach(() => {
    installMemoryStorage();
    clearStoredAuth();
    setApiRequestContext({ authToken: '', workspaceId: '' });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
    clearStoredAuth();
    setApiRequestContext({ authToken: '', workspaceId: '' });
  });

  it('routes to login when no token exists', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    renderApp('/documents');

    expect(await screen.findByText('Anmeldung')).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('shows precise backend-down state during bootstrap', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('connection refused'));

    renderApp('/documents');

    expect(await screen.findByText('Backend nicht erreichbar')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: API_UNREACHABLE')).toBeInTheDocument();
    expect(screen.queryByText(/API is not reachable/i)).not.toBeInTheDocument();
  });

  it('shows expired-session state on 401', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized', details: {} },
    }, 401));

    renderApp('/documents');

    expect(await screen.findByText('Session abgelaufen')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: AUTH_SESSION_EXPIRED')).toBeInTheDocument();
  });

  it('rejects sessions without memberships', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      user: { id: 'user-1', login: 'admin' },
      memberships: [],
      active_workspace_id: null,
    }));

    renderApp('/documents');

    expect(await screen.findByText('Keine Workspace-Mitgliedschaft')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: AUTH_NO_MEMBERSHIP')).toBeInTheDocument();
  });

  it('does not choose an implicit default workspace', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      user: { id: 'user-1', login: 'admin' },
      memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      active_workspace_id: null,
    }));

    renderApp('/documents');

    expect(await screen.findByText('Aktiver Workspace fehlt')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: AUTH_WORKSPACE_MISSING')).toBeInTheDocument();
  });

  it('rejects active workspace outside memberships', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      user: { id: 'user-1', login: 'admin' },
      memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      active_workspace_id: 'workspace-2',
    }));

    renderApp('/documents');

    expect(await screen.findByText('Workspace nicht zulaessig')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: AUTH_WORKSPACE_NOT_ALLOWED')).toBeInTheDocument();
  });

  it('loads /auth/me before protected data and sets active workspace context', async () => {
    storeTokenOnly();
    const fetchSpy = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse({
        user: { id: 'user-1', login: 'admin' },
        memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
        active_workspace_id: 'workspace-1',
      }))
      .mockResolvedValue(jsonResponse([]));

    renderApp('/documents');

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/auth/me'),
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
        }),
      );
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/documents?limit=20&offset=0&lifecycle_status=active'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
            'X-Workspace-Id': 'workspace-1',
          }),
        }),
      );
    });
  });
});
