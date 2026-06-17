import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { dashboardApi } from '../api/dashboard.js';
import { getSystemStatus } from '../api/status.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { StatusBadge } from '../components/status/StatusBadge.jsx';
import { TopicsWidgetPanel } from '../features/dashboard/TopicsWidgetPanel.jsx';
import { DriftWidgetPanel } from '../features/dashboard/DriftWidgetPanel.jsx';

const UNKNOWN = 'UNKNOWN';

const STATUS_FIELDS = [
  ['release_status', 'Release Status'],
  ['system_health', 'System Health'],
  ['provider_status', 'Provider Status'],
  ['workspace_status', 'Workspace Status'],
  ['autonomy_level', 'Autonomy Level'],
  ['governance_gate', 'Governance Gate'],
  ['security_gate', 'Security Gate'],
  ['gui_gate', 'GUI Gate'],
  ['rag_status', 'RAG Status'],
  ['agent_status', 'Agent Status'],
  ['collaboration_status', 'Collaboration Status'],
];

function normalizeStatus(value) {
  const label = value == null || String(value).trim() === '' ? UNKNOWN : String(value).trim().toUpperCase();
  if (['OK', 'HEALTHY', 'PASS', 'ACTIVE', 'READY', 'COMPLETED', 'INDEXED'].includes(label)) {
    return { label, tone: 'success' };
  }
  if (['WARNING', 'WARN', 'DEGRADED', 'PENDING', 'RUNNING', 'QUEUED'].includes(label)) {
    return { label, tone: 'warning' };
  }
  if (['FAIL', 'FAILED', 'BLOCKED', 'CRITICAL', 'ERROR'].includes(label)) {
    return { label, tone: 'danger' };
  }
  return { label: label || UNKNOWN, tone: 'neutral' };
}

function countValue(source, field) {
  return typeof source?.[field] === 'number' ? source[field] : UNKNOWN;
}

function listFromSettled(result) {
  if (result?.status !== 'fulfilled') return [];
  return Array.isArray(result.value?.items) ? result.value.items : [];
}

function isCriticalAuditEvent(item) {
  const severity = String(item?.severity ?? item?.details?.severity ?? '').toUpperCase();
  const risk = String(item?.risk ?? item?.details?.risk ?? '').toUpperCase();
  const action = String(item?.action ?? '');
  return severity === 'CRITICAL' || risk === 'CRITICAL' || action.endsWith('_BLOCKED');
}

function buildSupplementalBlockers(statusData, auditItems) {
  const blockers = Array.isArray(statusData?.open_blockers) ? [...statusData.open_blockers] : null;
  if (blockers == null) return null;
  for (const event of auditItems.filter(isCriticalAuditEvent)) {
    blockers.push({
      id: event.id ?? `audit-${blockers.length}`,
      severity: 'CRITICAL',
      title: `Critical audit event: ${event.action ?? 'unknown action'}`,
      source: 'audit',
      status: 'OPEN',
    });
  }
  return blockers;
}

function StatusCard({ field, label, value }) {
  const status = normalizeStatus(value);
  return (
    <div className="stat-card" data-testid={`dashboard-status-${field}`}>
      <span className="stat-card__label">{label}</span>
      <StatusBadge status={status} />
    </div>
  );
}

function CountCard({ testId, label, value }) {
  return (
    <div className="stat-card" data-testid={testId}>
      <span className="stat-card__label">{label}</span>
      <span className="stat-card__value">{value}</span>
    </div>
  );
}

function BlockerList({ blockers }) {
  if (!blockers || blockers.length === 0) return null;
  return (
    <section className="dashboard-section" data-testid="dashboard-blockers">
      <h2 className="dashboard-section__title">Offene Blocker ({blockers.length})</h2>
      <ul className="blocker-list">
        {blockers.map((b) => (
          <li key={b.id} className={`blocker-list__item blocker-list__item--${(b.severity || 'unknown').toLowerCase()}`}>
            <span className="blocker-list__severity">{b.severity}</span>
            <span className="blocker-list__title">{b.title}</span>
            {b.source && <span className="blocker-list__source">{b.source}</span>}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ActivityList({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <section className="dashboard-section" data-testid="dashboard-activity">
      <h2 className="dashboard-section__title">Letzte Aktivitäten</h2>
      <ul className="activity-list">
        {items.slice(0, 10).map((item) => (
          <li key={item.id} className="activity-list__item">
            <span className="activity-list__type badge badge--neutral">{item.item_type}</span>
            <span className="activity-list__title">{item.title}</span>
            <span className="activity-list__status">{item.status}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function DashboardPage() {
  const { viewState, setLoading, setSuccess, setError } = useViewState('idle');
  const [statusData, setStatusData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [activity, setActivity] = useState([]);
  const [blockers, setBlockers] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, []);

  async function load(signal) {
    setLoading();
    try {
      const currentStatus = await getSystemStatus({ signal });
      const supplementalResults = await Promise.allSettled([
        dashboardApi.getSummary({ signal }),
        dashboardApi.getActivity({ limit: 20 }, { signal }),
        dashboardApi.getQuality({ limit: 5 }, { signal }),
      ]);

      const [summaryResult, activityResult] = supplementalResults;
      const summaryData = summaryResult?.status === 'fulfilled' ? summaryResult.value : null;
      const activityItems = listFromSettled(activityResult);

      const derivedBlockers = buildSupplementalBlockers(currentStatus, []);

      setStatusData(currentStatus);
      setSummary(summaryData);
      setActivity(activityItems);
      setBlockers(derivedBlockers);
      setSuccess();
    } catch (err) {
      if (err?.name !== 'AbortError') setError(err);
    }
  }

  if (viewState.status === 'loading' || viewState.status === 'idle') {
    return <LoadingState />;
  }
  if (viewState.status === 'error') {
    return <ErrorState error={viewState.error} onRetry={() => load(new AbortController().signal)} />;
  }

  return (
    <div className="page-stack dashboard-page" data-testid="dashboard-page">
      <header className="dashboard-page__header">
        <h1 className="page-title">Dashboard</h1>
      </header>

      {/* Status grid */}
      <section className="dashboard-section" data-testid="dashboard-status">
        <h2 className="dashboard-section__title">Systemstatus</h2>
        <div className="stat-grid">
          {STATUS_FIELDS.map(([field, label]) => (
            <StatusCard key={field} field={field} label={label} value={statusData?.[field]} />
          ))}
        </div>
      </section>

      {/* Document counts */}
      {summary && (
        <section className="dashboard-section" data-testid="dashboard-counts">
          <h2 className="dashboard-section__title">Kennzahlen</h2>
          <div className="stat-grid">
            <CountCard testId="count-docs" label="Dokumente gesamt" value={countValue(summary, 'document_count')} />
            <CountCard testId="count-active" label="Aktiv" value={countValue(summary, 'active_document_count')} />
            <CountCard testId="count-archived" label="Archiviert" value={countValue(summary, 'archived_document_count')} />
            <CountCard testId="count-imports" label="Neue Imports" value={countValue(summary, 'new_imports_count')} />
            <CountCard testId="count-analysis" label="Offene Analysen" value={countValue(summary, 'open_analysis_count')} />
            <CountCard testId="count-topics" label="Themen" value={countValue(summary, 'topic_count')} />
          </div>
        </section>
      )}

      {/* Blockers */}
      <BlockerList blockers={blockers} />

      {/* Topics widget panel */}
      <section className="dashboard-section">
        <TopicsWidgetPanel />
      </section>

      {/* Activity */}
      {/* Drift Analytics widget panel (PRI-4) */}
      <section className="dashboard-section" data-testid="drift-widget-section">
        <DriftWidgetPanel />
      </section>

      <ActivityList items={activity} />

      <style>{`
        .dashboard-page { display: flex; flex-direction: column; gap: 0; overflow-y: auto; }
        .dashboard-page__header { padding: 16px 24px 0; }
        .dashboard-section { padding: 16px 24px; border-bottom: 1px solid var(--color-border, #e0e0e0); }
        .dashboard-section:last-child { border-bottom: none; }
        .dashboard-section__title { margin: 0 0 12px; font-size: 14px; font-weight: 600; color: var(--color-text-secondary, #666); text-transform: uppercase; letter-spacing: 0.05em; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
        .stat-card { background: var(--color-surface, #fff); border: 1px solid var(--color-border, #e0e0e0); border-radius: 8px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; }
        .stat-card__label { font-size: 11px; color: var(--color-text-secondary, #888); text-transform: uppercase; letter-spacing: 0.04em; }
        .stat-card__value { font-size: 22px; font-weight: 700; color: var(--color-text, #1c1c1c); }
        .blocker-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
        .blocker-list__item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 6px; border: 1px solid var(--color-border, #e0e0e0); font-size: 13px; }
        .blocker-list__item--critical { border-color: #e53935; background: #fff5f5; }
        .blocker-list__severity { font-size: 10px; font-weight: 700; text-transform: uppercase; background: #e53935; color: #fff; padding: 2px 7px; border-radius: 10px; flex-shrink: 0; }
        .blocker-list__title { flex: 1; }
        .blocker-list__source { font-size: 11px; color: var(--color-text-secondary, #888); }
        .activity-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
        .activity-list__item { display: flex; align-items: center; gap: 10px; font-size: 13px; padding: 6px 0; border-bottom: 1px solid var(--color-border, #f0f0f0); }
        .activity-list__item:last-child { border-bottom: none; }
        .activity-list__type { flex-shrink: 0; }
        .activity-list__title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .activity-list__status { font-size: 11px; color: var(--color-text-secondary, #888); flex-shrink: 0; }
      `}</style>
    </div>
  );
}
