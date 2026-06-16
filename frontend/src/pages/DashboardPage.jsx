import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { dashboardApi } from '../api/dashboard.js';
import { getSystemStatus } from '../api/status.js';
import { requestJson } from '../api/client.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { StatusBadge } from '../components/status/StatusBadge.jsx';

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
        requestJson('/api/v1/approvals?status=pending&limit=25', { signal }),
        requestJson('/api/v1/audit?limit=50', { signal }),
        requestJson('/api/v1/governance/status', { signal }),
        requestJson('/api/v1/security/status', { signal }),
        requestJson('/api/v1/rag/documents', { signal }),
        requestJson('/api/v1/agents/executions?limit=25', { signal }),
        requestJson('/api/v1/collaboration/runs?limit=25', { signal }),
      ]);
      const [summaryResult, activityResult, approvalsResult, auditResult] = supplementalResults;
      const auditItems = listFromSettled(auditResult);
      setStatusData({
        ...currentStatus,
        open_approvals_count:
          approvalsResult.status === 'fulfilled'
            ? countValue(approvalsResult.value, 'total')
            : countValue(currentStatus, 'open_approvals_count'),
        critical_audit_events_count:
          auditResult.status === 'fulfilled'
            ? auditItems.filter(isCriticalAuditEvent).length
            : countValue(currentStatus, 'critical_audit_events_count'),
      });
      setSummary(summaryResult.status === 'fulfilled' ? summaryResult.value : null);
      setActivity(activityResult.status === 'fulfilled' ? activityResult.value?.items ?? [] : []);
      setBlockers(buildSupplementalBlockers(currentStatus, auditItems));
    } catch (error) {
      setError(error);
      return;
    }
    setSuccess();
  }

  if (viewState.state === 'loading') return <LoadingState label="Dashboard wird geladen..." />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={() => load()} actionLabel="Erneut laden" />;

  const privacyStatus = statusData?.privacy_mode == null
    ? normalizeStatus(null)
    : statusData.privacy_mode
      ? { label: 'ENABLED', tone: 'warning' }
      : { label: 'DISABLED', tone: 'neutral' };
  const blockerList = blockers;

  return (
    <div className="page" data-testid="dashboard-page">
      <h1 className="page__title">Dashboard</h1>

      <section className="page__section" data-testid="dashboard-critical-blockers">
        <h2>Kritische Blocker</h2>
        {blockerList == null ? (
          <p className="text-muted">Blocker-Status UNKNOWN.</p>
        ) : blockerList.length === 0 ? (
          <p className="text-muted">Keine kritischen Blocker gemeldet.</p>
        ) : (
          <ul>
            {blockerList.map((blocker) => (
              <li key={`${blocker.source}-${blocker.id}`}>
                <strong>{blocker.severity ?? 'CRITICAL'}</strong>: {blocker.title ?? 'Unbekannter Blocker'}
                <span className="text-muted"> ({blocker.source ?? 'unknown'})</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="page__section" data-testid="dashboard-privacy-mode">
        <h2>Privacy Mode</h2>
        <StatusBadge status={privacyStatus} testId="dashboard-status-privacy_mode" />
      </section>

      <section className="page__section">
        <h2>Status</h2>
        <div className="card-grid" data-testid="dashboard-status-grid">
          {STATUS_FIELDS.map(([field, label]) => (
            <StatusCard key={field} field={field} label={label} value={statusData?.[field]} />
          ))}
          <CountCard
            testId="dashboard-open-approvals"
            label="Offene Approvals"
            value={countValue(statusData, 'open_approvals_count')}
          />
          <CountCard
            testId="dashboard-critical-audit-events"
            label="Kritische Audit Events"
            value={countValue(statusData, 'critical_audit_events_count')}
          />
          <CountCard
            testId="dashboard-open-blockers"
            label="Offene Blocker"
            value={Array.isArray(blockerList) ? blockerList.length : UNKNOWN}
          />
        </div>
      </section>

      <section className="page__section">
        <h2>Uebersicht</h2>
        <div className="card-grid" data-testid="dashboard-summary">
          <CountCard testId="dashboard-document-count" label="Dokumente" value={countValue(summary, 'document_count')} />
          <CountCard testId="dashboard-active-documents" label="Aktiv" value={countValue(summary, 'active_document_count')} />
          <CountCard testId="dashboard-archived-documents" label="Archiviert" value={countValue(summary, 'archived_document_count')} />
          <CountCard testId="dashboard-new-imports" label="Neue Imports" value={countValue(summary, 'new_imports_count')} />
          <CountCard testId="dashboard-open-analysis" label="Offene Analysen" value={countValue(summary, 'open_analysis_count')} />
          <CountCard testId="dashboard-topic-count" label="Themen" value={countValue(summary, 'topic_count')} />
          <CountCard testId="dashboard-quality-score" label="Quality Score" value={summary?.quality_score ?? UNKNOWN} />
          <StatusCard field="drift_status" label="Drift" value={summary?.drift_status} />
        </div>
      </section>

      <section className="page__section">
        <h2>Letzte Aktivitaet</h2>
        {activity.length === 0 ? (
          <p className="text-muted">Keine Dashboard-Aktivitaet vorhanden.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Typ</th>
                <th>Status</th>
                <th>Zeitpunkt</th>
              </tr>
            </thead>
            <tbody>
              {activity.map((item) => (
                <tr key={item.id}>
                  <td>{item.item_type ?? UNKNOWN}</td>
                  <td>{normalizeStatus(item.status).label}</td>
                  <td>{item.created_at ? new Date(item.created_at).toLocaleString('de-DE') : UNKNOWN}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
