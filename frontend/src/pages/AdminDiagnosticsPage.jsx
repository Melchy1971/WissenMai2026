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

function severityTone(severity) {
  const lookup = {
    info: 'info',
    warning: 'warning',
    critical: 'danger',
  };
  return lookup[severity] || 'neutral';
}

function indicatorStateLabel(state) {
  const lookup = {
    active: 'aktiv',
    inactive: 'inaktiv',
    unknown: 'unbekannt',
  };
  return lookup[state] || state;
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

function awarenessBanner(indicators) {
  if (!Array.isArray(indicators)) {
    return null;
  }

  return (
    indicators.find((indicator) => indicator.severity === 'critical' && indicator.state === 'active')
    || indicators.find((indicator) => indicator.severity === 'warning' && indicator.state !== 'inactive')
    || indicators.find((indicator) => indicator.severity === 'info' && indicator.state === 'active')
    || null
  );
}

function OperationalMetricCard({ metric }) {
  return (
    <article className={`diagnostics-card diagnostics-indicator diagnostics-indicator--${metric.severity}`}>
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Operative Metrik</p>
          <h3>{metric.label}</h3>
        </div>
        <span className={`status-badge status-badge--${severityTone(metric.severity)}`}>{metric.severity}</span>
      </div>
      <p className="diagnostics-indicator__state">
        Zustand: <strong>{indicatorStateLabel(metric.state)}</strong>
      </p>
      <p className="diagnostics-metric__value">
        Messwert: <strong>{metric.value}</strong>
      </p>
      <p className="diagnostics-card__text">{metric.summary}</p>
      <p className="diagnostics-indicator__source">Quelle: {metric.source}</p>
    </article>
  );
}

function DriftIndicatorCard({ indicator }) {
  return (
    <article className={`diagnostics-card diagnostics-indicator diagnostics-indicator--${indicator.severity}`}>
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Statusindikator</p>
          <h3>{indicator.label}</h3>
        </div>
        <span className={`status-badge status-badge--${severityTone(indicator.severity)}`}>{indicator.severity}</span>
      </div>
      <p className="diagnostics-indicator__state">
        Zustand: <strong>{indicatorStateLabel(indicator.state)}</strong>
      </p>
      <p className="diagnostics-card__text">{indicator.summary}</p>
      <p className="diagnostics-indicator__source">Quelle: {indicator.source}</p>
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
  const { active_workspace_id: workspaceId, memberships, isAuthReady } = useAuth();
  const [state, setState] = useState({ status: 'loading', diagnostics: null, error: null });

  const activeMembership = useMemo(() => membershipForWorkspace(memberships, workspaceId), [memberships, workspaceId]);
  const isWorkspaceAdmin = activeMembership?.role === 'owner' || activeMembership?.role === 'admin';
  const cards = state.diagnostics ? diagnosticsCards(state.diagnostics) : [];
  const driftAwareness = state.diagnostics?.drift_awareness || null;
  const operationalMetrics = state.diagnostics?.operational_metrics || [];
  const topWarning = awarenessBanner(operationalMetrics);

  useEffect(() => {
    let cancelled = false;

    if (!isAuthReady) {
      setState({ status: 'loading', diagnostics: null, error: null });
      return () => {
        cancelled = true;
      };
    }

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
  }, [isWorkspaceAdmin, isAuthReady]);

  return (
    <section className="page-stack" data-testid="diagnostics-page">
      <div className="page-header">
        <div>
          <p className="panel__eyebrow">M4d Diagnostics</p>
          <h2>Systemdiagnose</h2>
        </div>
        <div>
          <p className="page-header__meta">Read-only · Workspace: {workspaceId || 'nicht konfiguriert'}</p>
          {state.diagnostics?.correlation_id ? (
            <p className="page-header__meta">Correlation-ID: {state.diagnostics.correlation_id}</p>
          ) : null}
        </div>
      </div>

      {state.status === 'loading' ? (
        <EmptyState title="Diagnose wird geladen" message="Die read-only Systemdaten werden abgefragt." />
      ) : null}

      {state.status === 'error' || state.status === 'blocked' ? <ErrorState error={state.error} /> : null}

      {state.status === 'success' ? (
        <>
          {topWarning ? (
            <section className={`panel diagnostics-alert-banner diagnostics-alert-banner--${topWarning.severity}`} aria-label="Operative Warnung">
              <div className="panel__header">
                <div>
                  <p className="panel__eyebrow">Operational Metrics</p>
                  <h3>{topWarning.label}</h3>
                </div>
                <span className={`status-badge status-badge--${severityTone(topWarning.severity)}`}>{topWarning.severity}</span>
              </div>
              <p className="diagnostics-metric__value">
                Messwert: <strong>{topWarning.value}</strong>
              </p>
              <p className="diagnostics-card__text">{topWarning.summary}</p>
            </section>
          ) : null}

          {operationalMetrics.length ? (
            <section className="diagnostics-indicator-grid" aria-label="Operational metrics">
              {operationalMetrics.map((metric) => (
                <OperationalMetricCard key={metric.key} metric={metric} />
              ))}
            </section>
          ) : null}

          {driftAwareness ? (
            <section className="diagnostics-card-grid" aria-label="Drift awareness model">
              <article className="diagnostics-card diagnostics-card--accent">
                <div className="panel__header">
                  <div>
                    <p className="panel__eyebrow">Drift-Awareness-Konzept</p>
                    <h3>Sichtbare Degradierung</h3>
                  </div>
                </div>
                <ul className="diagnostics-rule-list">
                  {driftAwareness.concept.map((rule) => (
                    <li key={rule}>{rule}</li>
                  ))}
                </ul>
              </article>

              <article className="diagnostics-card">
                <div className="panel__header">
                  <div>
                    <p className="panel__eyebrow">UI-Warnmodell</p>
                    <h3>Keine stille Degradation</h3>
                  </div>
                </div>
                <dl className="meta-grid">
                  {Object.entries(driftAwareness.warning_model).map(([key, value]) => (
                    <div key={key}>
                      <dt>{key}</dt>
                      <dd>{value ? 'ja' : 'nein'}</dd>
                    </div>
                  ))}
                </dl>
              </article>
            </section>
          ) : null}

          {driftAwareness ? (
            <section className="diagnostics-indicator-grid" aria-label="Status indicators">
              {driftAwareness.indicators.map((indicator) => (
                <DriftIndicatorCard key={indicator.key} indicator={indicator} />
              ))}
            </section>
          ) : null}

          <section className="panel diagnostics-card-grid" aria-label="Diagnostics summary">
            {cards.map((card) => (
              <DiagnosticsCard key={card.title} {...card} />
            ))}
          </section>
        </>
      ) : null}
    </section>
  );
}
