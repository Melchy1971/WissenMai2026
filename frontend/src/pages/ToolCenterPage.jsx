import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { RiskBadge } from '../components/shared/RiskBadge.jsx';
import { ApprovalQueue } from '../components/shared/ApprovalQueue.jsx';

export function ToolCenterPage() {
  const { viewState, setLoading, setSuccess, setError, setEmpty } = useViewState('idle');
  const [tools, setTools] = useState([]);
  const [pendingApprovals, setPendingApprovals] = useState([]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [toolsRes, aprRes] = await Promise.all([
      callApi('/api/v1/tools'),
      callApi('/api/v1/approvals?category=tool&status=pending'),
    ]);
    if (!toolsRes.ok) { setError(toolsRes.error); return; }
    const items = toolsRes.data?.items ?? [];
    if (!items.length) { setEmpty(); return; }
    setTools(items);
    setPendingApprovals(aprRes.ok ? (aprRes.data?.items ?? []) : []);
    setSuccess();
  }

  async function toggleTool(toolId, enabled) {
    // Riskante Aktion HIGH/CRITICAL → Approval-Workflow, kein direkter Start
    const result = await callApi(`/api/v1/tools/${toolId}/toggle`, {
      method: 'PATCH',
      body: JSON.stringify({ enabled }),
    });
    if (!result.ok) { alert(result.error.message); return; }
    load();
  }

  async function healthCheck(toolId) {
    const result = await callApi(`/api/v1/tools/${toolId}/health`);
    if (!result.ok) { alert(result.error.message); return; }
    alert(`Health: ${result.data?.status ?? 'unbekannt'}`);
  }

  if (viewState.state === 'loading') return <LoadingState label="Tools werden geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;
  if (viewState.state === 'empty') return <EmptyState label="Keine Tools registriert." />;

  return (
    <div className="page" data-testid="tool-center-page">
      <h1 className="page__title">Tool Center</h1>

      {pendingApprovals.length > 0 && (
        <section className="page__section">
          <h2>Ausstehende Tool-Freigaben</h2>
          <ApprovalQueue items={pendingApprovals} onRefresh={load} />
        </section>
      )}

      <section className="page__section">
        <h2>Registrierte Tools ({tools.length})</h2>
        <table className="data-table" data-testid="tools-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Kategorie</th>
              <th>Risiko</th>
              <th>Status</th>
              <th>Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {tools.map(tool => (
              <tr key={tool.id}>
                <td><strong>{tool.name}</strong><br /><small>{tool.description}</small></td>
                <td>{tool.category}</td>
                <td><RiskBadge level={tool.risk_level} /></td>
                <td>
                  <span className={tool.enabled ? 'badge badge--success' : 'badge badge--neutral'}>
                    {tool.enabled ? 'Aktiv' : 'Inaktiv'}
                  </span>
                </td>
                <td className="action-cell">
                  <button
                    type="button"
                    className="button-secondary button--sm"
                    onClick={() => healthCheck(tool.id)}
                  >
                    Health
                  </button>
                  {(tool.risk_level === 'HIGH' || tool.risk_level === 'CRITICAL')
                    ? <span className="text-muted text-sm">→ Approval erforderlich</span>
                    : (
                      <button
                        type="button"
                        className={tool.enabled ? 'button-secondary button--sm' : 'button-primary button--sm'}
                        onClick={() => toggleTool(tool.id, !tool.enabled)}
                      >
                        {tool.enabled ? 'Deaktivieren' : 'Aktivieren'}
                      </button>
                    )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
