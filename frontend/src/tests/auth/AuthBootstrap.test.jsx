import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
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

function isDocumentListRequest(input) {
  return String(input).includes('/documents?limit=100&offset=0&lifecycle_status=');
}

function isStatusRequest(input) {
  return String(input).includes('/api/v1/status');
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
    expect(screen.getByRole('button', { name: 'Erneut versuchen' })).toBeInTheDocument();
    expect(screen.queryByText(/API is not reachable/i)).not.toBeInTheDocument();
  });

  it('retries bootstrap after transient backend-down state', async () => {
    storeTokenOnly();
    let authBootstrapAttempts = 0;
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);

      if (url.includes('/api/v1/auth/me')) {
        authBootstrapAttempts += 1;
        if (authBootstrapAttempts === 1) {
          throw new Error('connection refused');
        }

        return jsonResponse({
          user: { id: 'user-1', login: 'admin' },
          memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
          active_workspace_id: 'workspace-1',
        });
      }

      if (isDocumentListRequest(url) || isStatusRequest(url)) {
        return jsonResponse([]);
      }

      throw new Error(`unexpected fetch call: ${url}`);
    });

    renderApp('/documents');

    fireEvent.click(await screen.findByRole('button', { name: 'Erneut versuchen' }));

    expect(await screen.findByText(/Keine Dokumente vorhanden/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(authBootstrapAttempts).toBe(2);
      expect(fetchSpy).toHaveBeenCalledWith(
          expect.stringContaining('/documents?limit=100&offset=0&lifecycle_status=active'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
            'X-Workspace-Id': 'workspace-1',
          }),
        }),
      );
    });
  });

  it('shows expired-session state on 401', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized', details: {} },
    }, 401));

    renderApp('/documents');

    expect(await screen.findByText('Login erforderlich')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: AUTH_REQUIRED')).toBeInTheDocument();
  });

  it('rejects sessions without memberships', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      user: { id: 'user-1', login: 'admin' },
      memberships: [],
      active_workspace_id: null,
    }));

    renderApp('/documents');

    expect(await screen.findByText('Workspace fehlt')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: WORKSPACE_NOT_CONFIGURED')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: WORKSPACE_NOT_CONFIGURED')).toBeInTheDocument();
  });

  it('does not choose an implicit default workspace', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      user: { id: 'user-1', login: 'admin' },
      memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      active_workspace_id: null,
    }));

    renderApp('/documents');

    expect(await screen.findByText('Workspace fehlt')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: AUTH_WORKSPACE_MISSING')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: WORKSPACE_NOT_CONFIGURED')).toBeInTheDocument();
  });

  it('rejects active workspace outside memberships', async () => {
    storeTokenOnly();
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse({
      user: { id: 'user-1', login: 'admin' },
      memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      active_workspace_id: 'workspace-2',
    }));

    renderApp('/documents');

    expect(await screen.findByText('Workspace fehlt')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: AUTH_WORKSPACE_NOT_ALLOWED')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: WORKSPACE_NOT_CONFIGURED')).toBeInTheDocument();
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

    expect(await screen.findByText(/Keine Dokumente vorhanden/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/auth/me'),
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
        }),
      );
      expect(fetchSpy).toHaveBeenCalledWith(
          expect.stringContaining('/documents?limit=100&offset=0&lifecycle_status=active'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
            'X-Workspace-Id': 'workspace-1',
          }),
        }),
      );
    });
  });

  it('logs in, hydrates /auth/me, and loads documents with workspace context', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes('/api/v1/auth/login')) {
        return jsonResponse({
        token: 'real-api-token',
        expires_at: '2036-05-08T12:00:00Z',
        user: { id: 'login-user', login: 'mdickscheit', display_name: 'Login User' },
        memberships: [{ workspace_id: 'login-workspace', role: 'owner' }],
        active_workspace_id: 'login-workspace',
        });
      }
      if (url.includes('/api/v1/auth/me')) {
        return jsonResponse({
        user: { id: 'user-1', login: 'mdickscheit', display_name: 'Login User' },
        memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
        active_workspace_id: 'workspace-1',
        });
      }
      if (isStatusRequest(url) || isDocumentListRequest(url)) {
        return jsonResponse([]);
      }
      throw new Error(`unexpected fetch call: ${url}`);
    });

    renderApp('/login');

    fireEvent.change(screen.getByLabelText('Login'), { target: { value: 'mdickscheit' } });
    fireEvent.change(screen.getByLabelText('Passwort'), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: 'Anmelden' }));

    expect(await screen.findByText(/Keine Dokumente vorhanden/i)).toBeInTheDocument();
    expect(screen.getByTestId('status-bar').textContent).toContain('workspace-1');
    expect(screen.queryByText(/nicht konfiguriert/i)).not.toBeInTheDocument();

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenNthCalledWith(
        1,
        expect.stringContaining('/api/v1/auth/login'),
        expect.objectContaining({ method: 'POST' }),
      );
      expect(fetchSpy).toHaveBeenNthCalledWith(
        2,
        expect.stringContaining('/api/v1/auth/me'),
        expect.objectContaining({
          headers: expect.objectContaining({ Authorization: 'Bearer real-api-token' }),
        }),
      );
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/documents?limit=100&offset=0&lifecycle_status=active'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer real-api-token',
            'X-Workspace-Id': 'workspace-1',
          }),
        }),
      );
    });
  });

  it('revokes the session on logout and returns to login', async () => {
    window.localStorage.setItem(AUTH_STATE_STORAGE_KEY, JSON.stringify({
      token: 'real-api-token',
      user: { id: 'user-1', login: 'mdickscheit', display_name: 'Login User' },
      memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      active_workspace_id: 'workspace-1',
    }));

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (isDocumentListRequest(input) || isStatusRequest(input)) {
        return jsonResponse([]);
      }
      if (String(input).includes('/api/v1/auth/logout')) {
        return {
        ok: true,
        status: 204,
        statusText: 'No Content',
        headers: new Headers(),
        json: async () => null,
        };
      }
      throw new Error(`unexpected fetch call: ${String(input)}`);
    });

    renderApp('/documents');

    expect(await screen.findByText(/Keine Dokumente vorhanden/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Abmelden' }));

    expect(await screen.findByText('Anmeldung')).toBeInTheDocument();
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1/auth/logout'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({ Authorization: 'Bearer real-api-token' }),
        }),
      );
    });
  });
});
