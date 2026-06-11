import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { GateStatusCard } from '../components/shared/GateStatusCard.jsx';
import { AuditLogTable } from '../components/shared/AuditLogTable.jsx';
import { ApprovalQueue } from '../components/shared/ApprovalQueue.jsx';

export function DashboardPage() {
  const { viewState, setLoading, setSuccess, setError } = useViewState('idle');
  const [status, setStatus] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [sysRes, aprRes, audRes] = await Promise.all([
      callApi('/api/v1/status'),
      callApi('/api/v1/approvals?limit=10'),
      callApi('/api/v1/audit?limit=20'),
    ]);
    if (!sysRes.ok) { setError(sysRes.error); return; }
    setStatus(sysRes.data);
    setApprovals(aprRes.ok ? (aprRes.data?.items ?? []) : []);
    setAuditEvents(audRes.ok ? (audRes.data?.items ?? []) : []);
    setSuccess();
  }

  if (viewState.state === 'loading') return <LoadingState label="Dashboard wird geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;

  const gates = status?.gates ?? [];
  const blockers = gates.filter(g => g.status === 'FAIL' || g.status === 'NO_GO');

  return (
    <div className="page" data-testid="dashboard-page">
      <h1 className="page__title">Dashboard</h1>

      {blockers.length > 0 && (
        <div className="alert alert--danger" role="alert" data-testid="dashboard-blockers">
          <strong>Blocker aktiv:</strong> {blockers.length} Gate(s) fehlgeschlagen
        </div>
      )}

      <section className="page__section">
        <h2>System-Gates</h2>
        <div className="card-grid" data-testid="gate-status-cards">
          {gates.length === 0
            ? <p className="text-muted">Keine Gate-Daten verfügbar.</p>
            : gates.map(g => <GateStatusCard key={g.id} gate={g} />)}
        </div>
      </section>

      <section className="page__section">
        <h2>Offene Freigaben</h2>
        {approvals.length === 0
          ? <p className="text-muted">Keine offenen Freigaben.</p>
          : <ApprovalQueue items={approvals} onRefresh={load} />}
      </section>

      <section className="page__section">
        <h2>Letzte Audit-Ereignisse</h2>
        <AuditLogTable items={auditEvents} />
      </section>
    </div>
  );
}
