import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { mapError } from '../view-models/mappers.js';

function isAdmin(auth) {
  return auth.memberships?.some((m) => m.workspace_id === auth.active_workspace_id && ['owner', 'admin'].includes(m.role));
}

function visibleMetrics(payload) {
  return [
    ...(payload?.operational_metrics || []),
    ...(payload?.drift_awareness?.indicators || []),
  ];
}

export function AdminDiagnosticsPage() {
  const auth = useAuth();
  const [state, setState] = useState({ status: 'idle', data: null, error: null });

  useEffect(() => {
    if (!isAdmin(auth)) return;
    async function load() {
      setState({ status: 'loading', data: null, error: null });
      const res = await callApi('/api/v1/admin/diagnostics');
      if (!res.ok) setState({ status: 'error', data: null, error: res.error });
      else setState({ status: 'success', data: res.data, error: null });
    }
    load();
  }, [auth]);

  if (!isAdmin(auth)) {
    return (
      <section className="page-stack" data-testid="admin-diagnostics-page">
        <h1>Systemdiagnose</h1>
        <div className="state-card"><h2>Kein Admin-Zugriff</h2></div>
      </section>
    );
  }
  if (state.status === 'loading') return <LoadingState label="Systemdiagnose wird geladen..." />;
  if (state.status === 'error') return <ErrorState error={mapError(state.error)} />;
  if (!state.data) return null;

  const data = state.data;
  const metrics = visibleMetrics(data);

  return (
    <section className="page-stack" data-testid="admin-diagnostics-page">
      <h1>Systemdiagnose</h1>
      <p className="state-card__meta">Correlation-ID: {data.correlation_id}</p>

      <section className="panel">
        <h2>Systemstatus</h2>
        <p>{data.system?.status}</p>
      </section>
      <section className="panel">
        <h2>DB Status</h2>
        <p>Migration Status</p>
        <p>{data.database?.is_current ? 'current' : 'degraded'}</p>
      </section>
      <section className="panel">
        <h2>Dokumente und Chunks</h2>
        <p>{data.counts?.documents ?? 0}</p>
      </section>
      <section className="panel">
        <h2>Import Job Status</h2>
        <p>{data.imports?.last_error_code || '-'}</p>
      </section>
      <section className="panel">
        <h2>Search Index Status</h2>
        <p>Stale Eintraege</p>
        <p>{data.search?.stale_index_entries ?? 0}</p>
      </section>
      <section className="panel">
        <h2>Auth/Workspace Status</h2>
        <p>{data.auth?.workspace_isolation_enabled ? 'aktiv' : 'inaktiv'}</p>
      </section>
      <section className="panel">
        <h2>Sichtbare Degradierung</h2>
        <p>Keine stille Degradation</p>
        {data.drift_awareness?.concept?.map((line) => <p key={line}>{line}</p>)}
      </section>
      <section className="panel">
        <h2>Operational Metrics</h2>
        {metrics.map((metric, index) => (
          <article key={`${metric.key}-${metric.label}-${index}`} className={`diagnostics-indicator diagnostics-indicator--${metric.severity}`}>
            <h3>{metric.label}</h3>
            <p>{metric.severity}</p>
            <p>Messwert:</p>
            <p>{metric.value ?? metric.state}</p>
            <p>{metric.summary}</p>
          </article>
        ))}
      </section>
    </section>
  );
}
