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
    correlation_id: 'diag-correlation-123',
    operational_metrics: overrides.operational_metrics || [
      {
        key: 'queue_degraded',
        label: 'Queue degraded',
        state: 'inactive',
        severity: 'info',
        value: 'Backlog 0 · Dead-Letter 0 · Retry 0.0/h',
        summary: 'Queue-Aging-Report meldet keine Degradierung fuer den aktiven Workspace.',
        source: 'queue_aging_report',
      },
      {
        key: 'search_drift',
        label: 'Drift erkannt',
        state: 'inactive',
        severity: 'info',
        value: '0',
        summary: 'Kein Search-Drift im aktuellen Diagnostics-Snapshot erkannt.',
        source: 'diagnostics.search.stale_index_entries',
      },
      {
        key: 'backup_stale',
        label: 'Backup veraltet',
        state: 'inactive',
        severity: 'info',
        value: '1 Tage',
        summary: 'Restore-/Backup-Nachweis ist 1 Tag alt und damit noch innerhalb der Frische-Schwelle.',
        source: 'reports/restore_truth_report.md',
      },
      {
        key: 'reindex_running',
        label: 'Reindex aktiv',
        state: 'inactive',
        severity: 'info',
        value: '0',
        summary: 'Kein aktiver Reindex-Job im Backend gefunden.',
        source: 'background_jobs.search_index_rebuild',
      },
      {
        key: 'restore_mode',
        label: 'Restore aktiv',
        state: 'inactive',
        severity: 'info',
        value: '0',
        summary: 'Kein aktiver Restore-Lauf im Backend markiert.',
        source: 'reports/restore_runtime_status.json',
      },
      {
        key: 'retrieval_regression',
        label: 'Retrieval Regression erkannt',
        state: 'inactive',
        severity: 'info',
        value: 'pass',
        summary: 'Aktueller Retrieval-Benchmark liegt innerhalb der definierten Baseline.',
        source: 'reports/m5_retrieval/latest.json',
      },
    ],
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
      indicators: [
        {
          key: 'search_drift',
          label: 'Search Drift erkannt',
          state: 'inactive',
          severity: 'info',
          summary: 'Kein Search-Drift im aktuellen Diagnostics-Snapshot erkannt.',
          source: 'diagnostics.search.stale_index_entries',
        },
        {
          key: 'queue_degraded',
          label: 'Queue degraded',
          state: 'inactive',
          severity: 'info',
          summary: 'Queue-Aging-Report meldet keine Degradierung fuer den aktiven Workspace.',
          source: 'queue_aging_report',
        },
        {
          key: 'restore_mode',
          label: 'Restore aktiv',
          state: 'inactive',
          severity: 'info',
          summary: 'Kein aktiver Restore-Lauf im Backend markiert.',
          source: 'reports/restore_runtime_status.json',
        },
        {
          key: 'reindex_running',
          label: 'Reindex aktiv',
          state: 'inactive',
          severity: 'info',
          summary: 'Kein aktiver Reindex-Job im Backend gefunden.',
          source: 'background_jobs.search_index_rebuild',
        },
        {
          key: 'retrieval_regression',
          label: 'Retrieval Regression erkannt',
          state: 'inactive',
          severity: 'info',
          summary: 'Aktueller Retrieval-Benchmark liegt innerhalb der definierten Baseline.',
          source: 'reports/m5_retrieval/latest.json',
        },
        {
          key: 'backup_stale',
          label: 'Backup veraltet',
          state: 'inactive',
          severity: 'info',
          summary: 'Restore-/Backup-Nachweis ist 1 Tag alt und damit noch innerhalb der Frische-Schwelle.',
          source: 'reports/restore_truth_report.md',
        },
      ],
      ...overrides.drift_awareness,
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
      expect(screen.getByText('Backend nicht erreichbar')).toBeInTheDocument();
    });
    expect(screen.getByText('Fehlercode: API_UNREACHABLE')).toBeInTheDocument();
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
          drift_awareness: {
            indicators: [
              {
                key: 'search_drift',
                label: 'Search Drift erkannt',
                state: 'active',
                severity: 'critical',
                summary: '4 stale Index-Eintraege weichen vom Lifecycle-/Searchability-Zustand ab.',
                source: 'diagnostics.search.stale_index_entries',
              },
            ],
          },
          operational_metrics: [
            {
              key: 'search_drift',
              label: 'Drift erkannt',
              state: 'active',
              severity: 'critical',
              value: '4',
              summary: '4 stale Index-Eintraege weichen vom Lifecycle-/Searchability-Zustand ab.',
              source: 'diagnostics.search.stale_index_entries',
            },
          ],
        }),
    });

    renderPage();

    expect(await screen.findByText('Systemstatus')).toBeInTheDocument();
    expect(screen.getAllByText('degraded').length).toBeGreaterThan(0);
    expect(screen.getByText('Operational Metrics')).toBeInTheDocument();
    expect(screen.getAllByText('Messwert:').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Search Drift erkannt').length).toBeGreaterThan(0);
    expect(screen.getAllByText('critical').length).toBeGreaterThan(0);
    expect(screen.getByText('Migration Status')).toBeInTheDocument();
    expect(screen.getByText('PARSER_FAILED')).toBeInTheDocument();
    expect(screen.getByText('Stale Eintraege')).toBeInTheDocument();
    expect(screen.getAllByText('4').length).toBeGreaterThan(0);
  });

  it('renders drift awareness concept, warning model and status indicators', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => diagnosticsPayload(),
    });

    renderPage();

    expect(await screen.findByText('Sichtbare Degradierung')).toBeInTheDocument();
    expect(screen.getByText('Correlation-ID: diag-correlation-123')).toBeInTheDocument();
    expect(screen.getByText('Drift erkannt')).toBeInTheDocument();
    expect(screen.getByText('Keine stille Degradation')).toBeInTheDocument();
    expect(screen.getByText('Search Drift erkannt')).toBeInTheDocument();
    expect(screen.getAllByText('Queue degraded').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Restore aktiv').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Reindex aktiv').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Retrieval Regression erkannt').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Backup veraltet').length).toBeGreaterThan(0);
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
    expect(screen.queryByPlaceholderText(/admin-token/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/must-not-render/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Sensitive filename/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/secret-token/i)).not.toBeInTheDocument();
  });
});
