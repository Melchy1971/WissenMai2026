import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppRoutes } from '../../app/routes.jsx';
import { AuthProvider } from '../../auth/AuthContext.jsx';
import { setApiRequestContext } from '../../api/client.js';

const validAuthState = {
  token: 'test-token',
  user: { id: 'user-1', login: 'user' },
  memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
  active_workspace_id: 'workspace-1',
};

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 403 ? 'Forbidden' : 'OK',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => payload,
  };
}

function renderApp(initialEntry, initialAuthState = validAuthState) {
  return render(
    <AuthProvider initialAuthState={initialAuthState}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AppRoutes />
      </MemoryRouter>
    </AuthProvider>,
  );
}

function isDocumentListRequest(input) {
  return String(input).includes('/documents?limit=200&offset=0&lifecycle_status=');
}

function isStatusRequest(input) {
  return String(input).includes('/api/v1/status');
}

function renderStoredApp(initialEntry) {
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

describe('GUI state invariant component guards', () => {
  beforeEach(() => {
    installMemoryStorage();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
    window.localStorage.clear();
    setApiRequestContext({ authToken: '', workspaceId: '' });
  });

  it.each([
    ['/documents', 'Dokumente'],
    ['/chat', 'Dokumentgestuetzter Chat'],
  ])('does not mount %s without a validated workspace', async (route, heading) => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    renderApp(route, {
      token: 'test-token',
      user: { id: 'user-1', login: 'user' },
      memberships: [],
      active_workspace_id: '',
    });

    expect(await screen.findByText('Workspace fehlt')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: WORKSPACE_NOT_CONFIGURED')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: heading })).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('blocks document, search, chat and upload controls without a validated workspace', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    renderApp('/documents', {
      token: 'test-token',
      user: { id: 'user-1', login: 'user' },
      memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      active_workspace_id: 'workspace-2',
    });

    expect(await screen.findByText('Workspace fehlt')).toBeInTheDocument();
    expect(screen.getByText('Fehlercode: AUTH_WORKSPACE_NOT_ALLOWED')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: WORKSPACE_NOT_CONFIGURED')).toBeInTheDocument();
    expect(screen.queryByText('Chunk-Suche')).not.toBeInTheDocument();
    expect(screen.queryByText('Dokument hochladen')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Dokument importieren' })).not.toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('clears sensitive document state after AUTH_REQUIRED', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (isStatusRequest(url)) {
        return jsonResponse({});
      }
      if (url.includes('/documents?limit=200&offset=0&lifecycle_status=active')) {
        return jsonResponse([
        {
          id: 'doc-1',
          title: 'Sensitive Document',
          mime_type: 'text/plain',
          created_at: '2026-05-01T10:00:00Z',
          updated_at: '2026-05-01T10:00:00Z',
          latest_version_id: 'version-1',
          import_status: 'chunked',
          lifecycle_status: 'active',
          version_count: 1,
          chunk_count: 1,
        },
        ]);
      }
      if (url.includes('/documents?limit=200&offset=0&lifecycle_status=archived')) {
        return jsonResponse([]);
      }
      if (url.includes('/documents/doc-1/archive')) {
        return jsonResponse(
        { error: { code: 'UNAUTHORIZED', message: 'Token expired', details: {} } },
        401,
        );
      }
      throw new Error(`unexpected fetch: ${url}`);
    });

    renderApp('/documents');

    expect(await screen.findByText('Sensitive Document')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Sensitive Document'));
    fireEvent.click(await screen.findByRole('button', { name: 'Archivieren' }));
    fireEvent.click(screen.getByRole('button', { name: /Best/i }));

    expect(await screen.findByText('Anmeldung')).toBeInTheDocument();
    expect(screen.queryByText('Sensitive Document')).not.toBeInTheDocument();
  });

  it('resets old workspace search and upload state on workspace switch', async () => {
    let activeListCalls = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, options = {}) => {
      const url = String(input);
      if (isStatusRequest(url)) {
        return jsonResponse({});
      }
      if (url.includes('/documents?limit=200&offset=0&lifecycle_status=active')) {
        activeListCalls += 1;
        if (activeListCalls > 1) {
          return jsonResponse([]);
        }
        return jsonResponse([
        {
          id: 'doc-1',
          title: 'Workspace One Document',
          mime_type: 'text/plain',
          created_at: '2026-05-01T10:00:00Z',
          updated_at: '2026-05-01T10:00:00Z',
          latest_version_id: 'version-1',
          import_status: 'chunked',
          lifecycle_status: 'active',
          version_count: 1,
          chunk_count: 1,
        },
        ]);
      }
      if (isDocumentListRequest(url)) {
        return jsonResponse([]);
      }
      throw new Error(`unexpected fetch: ${url}`);
    });

    renderApp('/documents', {
      ...validAuthState,
      memberships: [
        { workspace_id: 'workspace-1', role: 'owner' },
        { workspace_id: 'workspace-2', role: 'member' },
      ],
    });

    expect(await screen.findByText('Workspace One Document')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Workspace wechseln'), {
      target: { value: 'workspace-2' },
    });

    await waitFor(() => {
      expect(screen.getByTestId('status-bar').textContent).toContain('workspace-2');
    });
    expect(await screen.findByText(/Keine Dokumente vorhanden/i)).toBeInTheDocument();
    expect(screen.queryByText('Workspace One Document')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Dokumentsuche')).toHaveValue('');
  });

  it('renders API_UNREACHABLE as an error, not a fake empty state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (isStatusRequest(input)) {
        return jsonResponse({});
      }
      if (isDocumentListRequest(input)) {
        throw new TypeError('Failed to fetch');
      }
      throw new Error(`unexpected fetch: ${String(input)}`);
    });

    renderApp('/documents');

    expect(await screen.findByText('Fehler beim Laden')).toBeInTheDocument();
    expect(screen.getByText('Dokumente konnten nicht geladen werden.')).toBeInTheDocument();
    expect(screen.queryByText(/Keine Dokumente vorhanden/i)).not.toBeInTheDocument();
  });

  it('does not offer retry or loop on FORBIDDEN bootstrap errors', async () => {
    let authMeCalls = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (String(input).includes('/api/v1/auth/me')) {
        authMeCalls += 1;
        return jsonResponse({ error: { code: 'FORBIDDEN', message: 'Access denied', details: {} } }, 403);
      }
      throw new Error(`unexpected fetch: ${String(input)}`);
    });

    window.localStorage.setItem('wissen.authState', JSON.stringify({
      token: 'token-only',
      user: null,
      memberships: [],
      active_workspace_id: '',
    }));
    window.localStorage.setItem('wissen.authToken', 'token-only');

    renderStoredApp('/documents');

    expect(await screen.findByText('Zugriff verboten')).toBeInTheDocument();
    expect(screen.getByText('Technischer Code: FORBIDDEN')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Erneut versuchen' })).not.toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(authMeCalls).toBe(1);
  });
});
