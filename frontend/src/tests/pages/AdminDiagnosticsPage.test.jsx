import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../auth/AuthContext.jsx';
import { AdminDiagnosticsPage } from '../../pages/AdminDiagnosticsPage.jsx';

const adminAuthState = {
  token: 'test-token',
  user: null,
  active_workspace_id: 'workspace-1',
  memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
};

function diagnosticsPayload(overrides = {}) {
  return {
    system: {
      status: 'ok',
      version: '0.1.0',
      environment: 'test',
      secret: 'must-not-render',
      ...overrides.system,
    },
    database: {
      reachable: true,
      migration_head: '20260505_0016',
      current_revision: '20260505_0016',
      is_current: true,
      ...overrides.database,
    },
    counts: {
      documents: 2,
      versions: 2,
      chunks: 7,
      chat_sessions: 1,
      chat_messages: 3,
      ...overrides.counts,
    },
    imports: {
      running_jobs: 0,
      failed_jobs_last_24h: 0,
      last_error_code: null,
      error_message: 'Sensitive filename.pdf',
      ...overrides.imports,
    },
    search: {
      index_available: true,
      indexed_chunks: 7,
      stale_index_entries: 0,
      ...overrides.search,
    },
    auth: {
      auth_enabled: true,
      workspace_isolation_enabled: true,
      token: 'secret-token',
      ...overrides.auth,
    },
  };
}

function renderPage(initialAuthState = adminAuthState) {
  return render(
    <AuthProvider initialAuthState={initialAuthState}>
      <MemoryRouter initialEntries={['/admin/diagnostics']}>
        <Routes>
          <Route path="/admin/diagnostics" element={<AdminDiagnosticsPage />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe('AdminDiagnosticsPage', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it('blocks access without admin role', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    renderPage({
      token: 'test-token',
      user: null,
      active_workspace_id: 'workspace-1',
      memberships: [{ workspace_id: 'workspace-1', role: 'member' }],
    });

    expect(screen.getByText('Systemdiagnose')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Kein Admin-Zugriff')).toBeInTheDocument();
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('shows API down state', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('connection refused'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('API nicht erreichbar')).toBeInTheDocument();
    });
    expect(screen.getByText('Fehlercode: NETWORK_ERROR')).toBeInTheDocument();
  });

  it('renders degraded status visibly', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () =>
        diagnosticsPayload({
          system: { status: 'degraded' },
          database: { current_revision: '20260505_0015', is_current: false },
          imports: { failed_jobs_last_24h: 2, last_error_code: 'PARSER_FAILED' },
          search: { stale_index_entries: 4 },
        }),
    });

    renderPage();

    expect(await screen.findByText('Systemstatus')).toBeInTheDocument();
    expect(screen.getAllByText('degraded').length).toBeGreaterThan(0);
    expect(screen.getByText('Migration Status')).toBeInTheDocument();
    expect(screen.getByText('PARSER_FAILED')).toBeInTheDocument();
    expect(screen.getByText('Stale Eintraege')).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders diagnostics without sensitive content or admin actions', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => diagnosticsPayload(),
    });

    renderPage();

    expect(await screen.findByText('DB Status')).toBeInTheDocument();
    expect(screen.getByText('Dokumente und Chunks')).toBeInTheDocument();
    expect(screen.getByText('Import Job Status')).toBeInTheDocument();
    expect(screen.getByText('Search Index Status')).toBeInTheDocument();
    expect(screen.getByText('Auth/Workspace Status')).toBeInTheDocument();
    expect(globalThis.fetch.mock.calls[0][0]).toContain('/api/v1/admin/diagnostics');

    expect(screen.queryByText(/Search Index neu aufbauen/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Reindex/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Cleanup/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Backup/i)).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/admin-token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/must-not-render/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Sensitive filename/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/secret-token/i)).not.toBeInTheDocument();
  });
});
