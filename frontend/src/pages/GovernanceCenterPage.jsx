import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { ApprovalQueue } from '../components/shared/ApprovalQueue.jsx';
import { AuditLogTable } from '../components/shared/AuditLogTable.jsx';
import { ChangeSetDiff } from '../components/shared/ChangeSetDiff.jsx';
import { RollbackPointList } from '../components/shared/RollbackPointList.jsx';
import { PolicyDecisionView } from '../components/shared/PolicyDecisionView.jsx';

export function GovernanceCenterPage() {
  const { viewState, setLoading, setSuccess, setError } = useViewState('idle');
  const [approvals, setApprovals] = useState([]);
  const [changeSets, setChangeSets] = useState([]);
  const [rollbackPoints, setRollbackPoints] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [policyDecisions, setPolicyDecisions] = useState([]);
  const [privacyMode, setPrivacyMode] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [aprRes, csRes, rbRes, audRes, polRes, statusRes] = await Promise.all([
      callApi('/api/v1/approvals'),
      callApi('/api/v1/governance/changesets'),
      callApi('/api/v1/governance/rollback-points'),
      callApi('/api/v1/audit'),
      callApi('/api/v1/governance/policy-decisions'),
      callApi('/api/v1/governance/status'),
    ]);
    if (!aprRes.ok && !csRes.ok) { setError(aprRes.error || csRes.error); return; }
    setApprovals(aprRes.ok ? (aprRes.data?.items ?? []) : []);
    setChangeSets(csRes.ok ? (csRes.data?.items ?? []) : []);
    setRollbackPoints(rbRes.ok ? (rbRes.data?.items ?? []) : []);
    setAuditLog(audRes.ok ? (audRes.data?.items ?? []) : []);
    setPolicyDecisions(polRes.ok ? (polRes.data?.items ?? []) : []);
    if (statusRes.ok) {
      setPrivacyMode(statusRes.data?.privacy_mode ?? false);
      setIsAdmin(statusRes.data?.current_user_is_admin ?? false);
    }
    setSuccess();
  }

  async function togglePrivacyMode() {
    const res = await callApi('/api/v1/governance/privacy-mode', {
      method: 'PATCH',
      body: JSON.stringify({ enabled: !privacyMode }),
    });
    if (!res.ok) { alert(res.error.message); return; }
    setPrivacyMode(!privacyMode);
  }

  if (viewState.state === 'loading') return <LoadingState label="Governance wird geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="governance-center-page">
      <div className="page__header-row">
        <h1 className="page__title">Governance Center</h1>
        <label className="toggle-label">
          <input type="checkbox" checked={privacyMode} onChange={togglePrivacyMode}
            data-testid="privacy-mode-toggle" />
          Privacy Mode {privacyMode ? 'AN' : 'AUS'}
        </label>
      </div>

      <section className="page__section">
        <h2>Ausstehende Freigaben ({approvals.filter(a => a.status === 'pending').length})</h2>
        {approvals.length === 0
          ? <p className="text-muted">Keine offenen Freigaben.</p>
          : <ApprovalQueue items={approvals} onRefresh={load} />}
      </section>

      <section className="page__section">
        <h2>Change Sets</h2>
        {changeSets.length === 0
          ? <p className="text-muted">Keine Change Sets.</p>
          : changeSets.map(cs => <ChangeSetDiff key={cs.id} changeset={cs} />)}
      </section>

      {/* Rollback nur mit Admin Permission */}
      {isAdmin && (
        <section className="page__section">
          <h2>Rollback-Punkte</h2>
          <RollbackPointList items={rollbackPoints} onRefresh={load} />
        </section>
      )}

      <section className="page__section">
        <h2>Policy-Entscheidungen</h2>
        {policyDecisions.length === 0
          ? <p className="text-muted">Keine Policy-Entscheidungen.</p>
          : policyDecisions.map(p => <PolicyDecisionView key={p.id} decision={p} />)}
      </section>

      <section className="page__section">
        <h2>Audit-Log</h2>
        <AuditLogTable items={auditLog} />
      </section>
    </div>
  );
}
