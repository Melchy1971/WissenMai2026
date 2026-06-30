import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppRoutes } from '../../app/routes.jsx';
import { setApiRequestContext } from '../../api/client.js';
import { AuthProvider } from '../../auth/AuthContext.jsx';

const baseAuthState = {
  token: 'test-token',
  user: { id: 'user-1', login: 'user' },
  memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
  active_workspace_id: 'workspace-1',
};

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

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status >= 500 ? 'Server Error' : status === 401 ? 'Unauthorized' : 'OK',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => payload,
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function diagnosticsPayload({ operationalMetrics, indicators }) {
  return {
    system: { status: 'degraded', version: '0.1.0', environment: 'test' },
    database: { reachable: true, migration_head: '20260505_0016', current_revision: '20260505_0016', is_current: true },
    counts: { documents: 2, versions: 2, chunks: 7, chat_sessions: 1, chat_messages: 3 },
    imports: { running_jobs: 0, failed_jobs_last_24h: 0, last_error_code: null },
    search: { index_available: true, indexed_chunks: 7, stale_index_entries: 0 },
    auth: { auth_enabled: true, workspace_isolation_enabled: true },
    correlation_id: 'chaos-correlation-001',
    operational_metrics: operationalMetrics,
    drift_awareness: {
      concept: [
        'Degradierte Betriebszustaende muessen sichtbar bleiben, auch wenn Fachdaten noch lesbar sind.',
        'Fehlende oder veraltete Evidenz wird als Warnsignal gerendert und nie als gesund angenommen.',
        'Der hoechste aktive Schweregrad steuert die Wahrnehmung; Warnungen duerfen nicht im Kartenraster verschwinden.',
      ],
      warning_model: {
        no_silent_degradation: true,
        no_fake_green: true,
        no_hidden_warnings: true,
        unknown_is_not_ok: true,
        highest_severity_wins: true,
      },
      indicators,
    },
  };
}

function renderApp(initialEntry, initialAuthState = baseAuthState) {
  return render(
    <AuthProvider initialAuthState={initialAuthState}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <AppRoutes />
      </MemoryRouter>
    </AuthProvider>,
  );
}

function isDocumentListRequest(input) {
  return String(input).includes('/documents?limit=100&offset=0&lifecycle_status=');
}

function isStatusRequest(input) {
  return String(input).includes('/api/v1/status');
}

function isDiagnosticsRequest(input) {
  return String(input).includes('/api/v1/admin/diagnostics');
}

describe('GUI chaos suite', () => {
  beforeEach(() => {
    installMemoryStorage();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
    window.localStorage.clear();
    setApiRequestContext({ authToken: '', workspaceId: '' });
  });

  it('simulates slow api without showing a fake empty state', async () => {
    const docsRequest = deferred();
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (isStatusRequest(input)) {
        return jsonResponse({});
      }
      if (String(input).includes('/documents?limit=100&offset=0&lifecycle_status=active')) {
        return docsRequest.promise;
      }
      if (String(input).includes('/documents?limit=100&offset=0&lifecycle_status=archived')) {
        return jsonResponse([]);
      }
      throw new Error(`unexpected fetch: ${String(input)}`);
    });

    renderApp('/documents');

    expect(await screen.findByText(/Dokumente werden geladen/i)).toBeInTheDocument();
    expect(screen.queryByText(/Keine Dokumente vorhanden/i)).not.toBeInTheDocument();
    expect(screen.queryByText('Backend nicht erreichbar')).not.toBeInTheDocument();

    docsRequest.resolve(jsonResponse([]));

    expect(await screen.findByText(/Keine Dokumente vorhanden/i)).toBeInTheDocument();
  });

  it('simulates api outage and keeps recovery explicit', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (isStatusRequest(input)) {
        return jsonResponse({});
      }
      if (String(input).includes('/api/v1/search/chunks')) {
        throw new TypeError('Failed to fetch');
      }
      throw new Error(`unexpected fetch: ${String(input)}`);
    });

    renderApp('/search');

    fireEvent.change(screen.getByLabelText('Suchbegriff'), { target: { value: 'chaos' } });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));

    expect(await screen.findByText(/Backend nicht erreichbar/i)).toBeInTheDocument();
    expect(screen.queryByText('Keine Treffer gefunden')).not.toBeInTheDocument();
  });

  it('simulates a db restart without leaving stale success state behind', async () => {
    let activeListCalls = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, options = {}) => {
      const url = String(input);
      if (isStatusRequest(url)) {
        return jsonResponse({});
      }
      if (url.includes('/documents?limit=100&offset=0&lifecycle_status=active')) {
        activeListCalls += 1;
        if (activeListCalls > 1) {
          return jsonResponse({ error: { code: 'SERVER_ERROR', message: 'database restarting', details: {} } }, 503);
        }
        return jsonResponse([
        {
          id: 'doc-1',
          title: 'Vor Neustart',
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
      if (url.includes('/documents?limit=100&offset=0&lifecycle_status=archived')) {
        return jsonResponse([]);
      }
      throw new Error(`unexpected fetch: ${url}`);
    });

    renderApp('/documents', {
      ...baseAuthState,
      memberships: [
        { workspace_id: 'workspace-1', role: 'owner' },
        { workspace_id: 'workspace-2', role: 'member' },
      ],
    });

    expect(await screen.findByText('Vor Neustart')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Workspace wechseln'), { target: { value: 'workspace-2' } });

    expect(await screen.findByText('Fehler beim Laden')).toBeInTheDocument();
    expect(screen.queryByText('Vor Neustart')).not.toBeInTheDocument();
  });

  it('simulates workspace switching during requests without ghost data', async () => {
    const staleSearch = deferred();
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, options = {}) => {
      const url = String(input);
      const workspaceId = options.headers?.['X-Workspace-Id'];
      if (isStatusRequest(url)) {
        return jsonResponse({});
      }
      if (url.includes('/documents?limit=100&offset=0&lifecycle_status=active') && workspaceId === 'workspace-1') {
        return staleSearch.promise;
      }
      if (isDocumentListRequest(url)) {
        return jsonResponse([]);
      }
      throw new Error(`unexpected fetch: ${url}`);
    });

    renderApp('/documents', {
      ...baseAuthState,
      memberships: [
        { workspace_id: 'workspace-1', role: 'owner' },
        { workspace_id: 'workspace-2', role: 'member' },
      ],
    });

    expect(await screen.findByText(/Dokumente werden geladen/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Workspace wechseln'), { target: { value: 'workspace-2' } });
    await waitFor(() => {
      expect(screen.getByTestId('status-bar').textContent).toContain('workspace-2');
    });

    staleSearch.resolve(jsonResponse([
      {
        id: 'doc-1',
        title: 'Workspace One Result',
        mime_type: 'text/plain',
        created_at: '2026-05-01T10:00:00Z',
        updated_at: '2026-05-01T10:00:00Z',
        latest_version_id: 'version-1',
        import_status: 'chunked',
        lifecycle_status: 'active',
        version_count: 1,
        chunk_count: 1,
      },
    ]));

    await waitFor(() => {
      expect(screen.queryByText('Workspace One Result')).not.toBeInTheDocument();
      expect(screen.getByLabelText('Dokumentsuche')).toHaveValue('');
    });
    expect(fetchSpy).toHaveBeenCalled();
  });

  it('simulates token expiration without retaining sensitive state', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input);
      if (isStatusRequest(url)) {
        return jsonResponse({});
      }
      if (url.includes('/documents?limit=100&offset=0&lifecycle_status=active')) {
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
      if (url.includes('/documents?limit=100&offset=0&lifecycle_status=archived')) {
        return jsonResponse([]);
      }
      if (url.includes('/documents/doc-1/archive')) {
        return jsonResponse({ error: { code: 'UNAUTHORIZED', message: 'Token expired', details: {} } }, 401);
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

  it('simulates restore during usage with visible degraded state', async () => {
    const payload = diagnosticsPayload({
      operationalMetrics: [
        {
          key: 'restore_mode',
          label: 'Restore aktiv',
          state: 'active',
          severity: 'warning',
          value: '1',
          summary: 'Ein Restore-Lauf ist im Backend aktiv. Start: 2026-05-18T10:00:00Z.',
          source: 'reports/restore_runtime_status.json',
        },
      ],
      indicators: [
        {
          key: 'restore_mode',
          label: 'Restore aktiv',
          state: 'active',
          severity: 'warning',
          summary: 'Ein Restore-Lauf ist im Backend aktiv. Start: 2026-05-18T10:00:00Z.',
          source: 'reports/restore_runtime_status.json',
        },
      ],
    });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (isStatusRequest(input)) return jsonResponse({});
      if (isDiagnosticsRequest(input)) return jsonResponse(payload);
      throw new Error(`unexpected fetch: ${String(input)}`);
    });

    renderApp('/admin/diagnostics');

    expect((await screen.findAllByText('Restore aktiv')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('warning').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Ein Restore-Lauf ist im Backend aktiv/).length).toBeGreaterThan(0);
    expect(screen.queryByText('Kein aktiver Restore-Lauf im Backend markiert.')).not.toBeInTheDocument();
  });

  it('simulates reindex during search with visible degraded state', async () => {
    const payload = diagnosticsPayload({
      operationalMetrics: [
        {
          key: 'reindex_running',
          label: 'Reindex aktiv',
          state: 'active',
          severity: 'warning',
          value: '1',
          summary: 'Ein Reindex-Job ist im Backend aktiv oder pending.',
          source: 'background_jobs.search_index_rebuild',
        },
        {
          key: 'search_drift',
          label: 'Drift erkannt',
          state: 'active',
          severity: 'warning',
          value: '3',
          summary: '3 stale Index-Eintraege weichen vom Lifecycle-/Searchability-Zustand ab.',
          source: 'diagnostics.search.stale_index_entries',
        },
      ],
      indicators: [
        {
          key: 'reindex_running',
          label: 'Reindex aktiv',
          state: 'active',
          severity: 'warning',
          summary: 'Ein Reindex-Job ist im Backend aktiv oder pending.',
          source: 'background_jobs.search_index_rebuild',
        },
        {
          key: 'search_drift',
          label: 'Search Drift erkannt',
          state: 'active',
          severity: 'warning',
          summary: '3 stale Index-Eintraege weichen vom Lifecycle-/Searchability-Zustand ab.',
          source: 'diagnostics.search.stale_index_entries',
        },
      ],
    });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (isStatusRequest(input)) return jsonResponse({});
      if (isDiagnosticsRequest(input)) return jsonResponse(payload);
      throw new Error(`unexpected fetch: ${String(input)}`);
    });

    renderApp('/admin/diagnostics');

    expect((await screen.findAllByText('Reindex aktiv')).length).toBeGreaterThan(0);
    expect(screen.getByText('Drift erkannt')).toBeInTheDocument();
    expect(screen.getAllByText('warning').length).toBeGreaterThan(0);
    expect(screen.queryByText('Kein aktiver Reindex-Job im Backend gefunden.')).not.toBeInTheDocument();
  });

  it('simulates queue backlog as a critical degraded state', async () => {
    const payload = diagnosticsPayload({
      operationalMetrics: [
        {
          key: 'queue_degraded',
          label: 'Queue degraded',
          state: 'active',
          severity: 'critical',
          value: 'Backlog 42 · Dead-Letter 5 · Retry 8.5/h',
          summary: 'Queue kritisch: 42 aktive Jobs, 4 stuck running, 5 dead-letter.',
          source: 'queue_aging_report',
        },
      ],
      indicators: [
        {
          key: 'queue_degraded',
          label: 'Queue degraded',
          state: 'active',
          severity: 'critical',
          summary: 'Queue kritisch: 42 aktive Jobs, 4 stuck running, 5 dead-letter.',
          source: 'queue_aging_report',
        },
      ],
    });
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      if (isStatusRequest(input)) return jsonResponse({});
      if (isDiagnosticsRequest(input)) return jsonResponse(payload);
      throw new Error(`unexpected fetch: ${String(input)}`);
    });

    renderApp('/admin/diagnostics');

    expect((await screen.findAllByText('Queue degraded')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('critical').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Messwert:').length).toBeGreaterThan(0);
    expect(screen.queryByText('Queue-Aging-Report meldet keine Degradierung fuer den aktiven Workspace.')).not.toBeInTheDocument();
  });
});
