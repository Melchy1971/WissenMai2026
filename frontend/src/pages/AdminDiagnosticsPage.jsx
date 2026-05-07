import { useEffect, useMemo, useState } from 'react';

import { getDiagnostics } from '../api/admin.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { mapError } from '../view-models/mappers.js';

function membershipForWorkspace(memberships, workspaceId) {
  if (!Array.isArray(memberships) || !workspaceId) {
    return null;
  }

  return memberships.find((membership) => membership?.workspace_id === workspaceId) || null;
}

function statusTone(status) {
  const lookup = {
    ok: 'success',
    degraded: 'warning',
    error: 'danger',
  };
  return lookup[status] || 'neutral';
}

function boolLabel(value) {
  return value ? 'aktiv' : 'inaktiv';
}

function numberLabel(value) {
  return Number.isFinite(value) ? value.toLocaleString('de-DE') : '0';
}

function DiagnosticsCard({ title, eyebrow, status = 'ok', metrics }) {
  return (
    <article className="diagnostics-card">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">{eyebrow}</p>
          <h3>{title}</h3>
        </div>
        <span className={`status-badge status-badge--${statusTone(status)}`}>{status}</span>
      </div>
      <dl className="meta-grid">
        {metrics.map((metric) => (
          <div key={metric.label}>
            <dt>{metric.label}</dt>
            <dd>{metric.value}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function diagnosticsCards(diagnostics) {
  return [
    {
      title: 'Systemstatus',
      eyebrow: 'System',
      status: diagnostics.system.status,
      metrics: [
        { label: 'Version', value: diagnostics.system.version },
        { label: 'Umgebung', value: diagnostics.system.environment },
      ],
    },
    {
      title: 'DB Status',
      eyebrow: 'Database',
      status: diagnostics.database.reachable ? 'ok' : 'error',
      metrics: [
        { label: 'Erreichbar', value: boolLabel(diagnostics.database.reachable) },
        { label: 'Aktuell', value: diagnostics.database.is_current ? 'ja' : 'nein' },
      ],
    },
    {
      title: 'Migration Status',
      eyebrow: 'Alembic',
      status: diagnostics.database.is_current ? 'ok' : 'degraded',
      metrics: [
        { label: 'Head', value: diagnostics.database.migration_head || 'unbekannt' },
        { label: 'Aktuell', value: diagnostics.database.current_revision || 'unbekannt' },
      ],
    },
    {
      title: 'Dokumente und Chunks',
      eyebrow: 'Counts',
      status: 'ok',
      metrics: [
        { label: 'Dokumente', value: numberLabel(diagnostics.counts.documents) },
        { label: 'Versionen', value: numberLabel(diagnostics.counts.versions) },
        { label: 'Chunks', value: numberLabel(diagnostics.counts.chunks) },
        { label: 'Chat-Sessions', value: numberLabel(diagnostics.counts.chat_sessions) },
        { label: 'Chat-Nachrichten', value: numberLabel(diagnostics.counts.chat_messages) },
      ],
    },
    {
      title: 'Import Job Status',
      eyebrow: 'Imports',
      status: diagnostics.imports.failed_jobs_last_24h > 0 ? 'degraded' : 'ok',
      metrics: [
        { label: 'Laufende Jobs', value: numberLabel(diagnostics.imports.running_jobs) },
        { label: 'Fehler 24h', value: numberLabel(diagnostics.imports.failed_jobs_last_24h) },
        { label: 'Letzter Fehlercode', value: diagnostics.imports.last_error_code || 'keiner' },
      ],
    },
    {
      title: 'Search Index Status',
      eyebrow: 'Search',
      status: diagnostics.search.index_available && diagnostics.search.stale_index_entries === 0 ? 'ok' : 'degraded',
      metrics: [
        { label: 'Index verfuegbar', value: boolLabel(diagnostics.search.index_available) },
        { label: 'Indexierte Chunks', value: numberLabel(diagnostics.search.indexed_chunks) },
        { label: 'Stale Eintraege', value: numberLabel(diagnostics.search.stale_index_entries) },
      ],
    },
    {
      title: 'Auth/Workspace Status',
      eyebrow: 'Security',
      status: diagnostics.auth.auth_enabled && diagnostics.auth.workspace_isolation_enabled ? 'ok' : 'error',
      metrics: [
        { label: 'Auth', value: boolLabel(diagnostics.auth.auth_enabled) },
        { label: 'Workspace-Isolation', value: boolLabel(diagnostics.auth.workspace_isolation_enabled) },
      ],
    },
  ];
}

export function AdminDiagnosticsPage() {
  const { active_workspace_id: workspaceId, memberships } = useAuth();
  const [state, setState] = useState({ status: 'loading', diagnostics: null, error: null });

  const activeMembership = useMemo(() => membershipForWorkspace(memberships, workspaceId), [memberships, workspaceId]);
  const isWorkspaceAdmin = activeMembership?.role === 'owner' || activeMembership?.role === 'admin';
  const cards = state.diagnostics ? diagnosticsCards(state.diagnostics) : [];

  useEffect(() => {
    let cancelled = false;

    async function loadDiagnostics() {
      if (!isWorkspaceAdmin) {
        setState({
          status: 'blocked',
          diagnostics: null,
          error: {
            code: 'FORBIDDEN',
            title: 'Kein Admin-Zugriff',
            message: 'Die Systemdiagnose steht nur Workspace-Ownern und Admins zur Verfuegung.',
          },
        });
        return;
      }

      setState({ status: 'loading', diagnostics: null, error: null });
      try {
        const diagnostics = await getDiagnostics();
        if (!cancelled) {
          setState({ status: 'success', diagnostics, error: null });
        }
      } catch (error) {
        if (!cancelled) {
          setState({ status: 'error', diagnostics: null, error: mapError(error) });
        }
      }
    }

    void loadDiagnostics();

    return () => {
      cancelled = true;
    };
  }, [isWorkspaceAdmin]);

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="panel__eyebrow">M4d Diagnostics</p>
          <h2>Systemdiagnose</h2>
        </div>
        <p className="page-header__meta">Read-only · Workspace: {workspaceId || 'nicht konfiguriert'}</p>
      </div>

      {state.status === 'loading' ? (
        <EmptyState title="Diagnose wird geladen" message="Die read-only Systemdaten werden abgefragt." />
      ) : null}

      {state.status === 'error' || state.status === 'blocked' ? <ErrorState error={state.error} /> : null}

      {state.status === 'success' ? (
        <section className="panel diagnostics-card-grid" aria-label="Diagnostics summary">
          {cards.map((card) => (
            <DiagnosticsCard key={card.title} {...card} />
          ))}
        </section>
      ) : null}
    </section>
  );
}
