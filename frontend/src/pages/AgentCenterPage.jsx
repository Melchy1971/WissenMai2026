import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { ExecutionPlanView } from '../components/shared/ExecutionPlanView.jsx';
import { AgentLimitView } from '../components/shared/AgentLimitView.jsx';

export function AgentCenterPage() {
  const { viewState, setLoading, setSuccess, setError, setEmpty } = useViewState('idle');
  const [agents, setAgents] = useState([]);
  const [selected, setSelected] = useState(null);
  const [executions, setExecutions] = useState([]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [agentsRes, execRes] = await Promise.all([
      callApi('/api/v1/agents'),
      callApi('/api/v1/agents/executions'),
    ]);
    if (!agentsRes.ok) { setError(agentsRes.error); return; }
    const items = agentsRes.data?.items ?? [];
    if (!items.length) { setEmpty(); return; }
    setAgents(items);
    setExecutions(execRes.ok ? (execRes.data?.items ?? []) : []);
    setSuccess();
  }

  async function loadAgent(id) {
    const res = await callApi(`/api/v1/agents/${id}`);
    if (!res.ok) { alert(res.error.message); return; }
    setSelected(res.data);
  }

  // Kein direkter Toolstart aus Agent-UI – nur über Orchestrator
  // Agent-Aktionen nur über Orchestrator
  function startAgentAction(agentId, action) {
    alert(`Aktion "${action}" für Agent ${agentId} wird über Orchestrator weitergeleitet. Kein direkter Start.`);
  }

  if (viewState.state === 'loading') return <LoadingState label="Agents werden geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;
  if (viewState.state === 'empty') return <EmptyState label="Keine Agents registriert." />;

  return (
    <div className="page" data-testid="agent-center-page">
      <h1 className="page__title">Agent Center</h1>

      <div className="split-layout">
        <aside className="split-layout__list">
          <ul data-testid="agents-list">
            {agents.map(a => (
              <li key={a.id}
                className={`list-item list-item--clickable ${selected?.id === a.id ? 'list-item--active' : ''}`}
                onClick={() => loadAgent(a.id)}
              >
                <strong>{a.name}</strong>
                <small>{a.type} — {a.status}</small>
              </li>
            ))}
          </ul>
        </aside>

        <main className="split-layout__detail">
          {selected ? (
            <div data-testid="agent-detail">
              <h2>{selected.name}</h2>
              <AgentLimitView limits={selected.limits} />
              {selected.execution_plan && (
                <>
                  <h3>Execution Plan (read-only)</h3>
                  <ExecutionPlanView plan={selected.execution_plan} />
                </>
              )}
              {selected.validation_report && (
                <details>
                  <summary>Validierungsbericht</summary>
                  <pre className="code-block">{JSON.stringify(selected.validation_report, null, 2)}</pre>
                </details>
              )}
              <div className="action-row">
                <button type="button" className="button-secondary"
                  onClick={() => startAgentAction(selected.id, 'run')}>
                  Ausführen (via Orchestrator)
                </button>
              </div>
            </div>
          ) : (
            <p className="text-muted">Agent auswählen.</p>
          )}
        </main>
      </div>

      {executions.length > 0 && (
        <section className="page__section">
          <h2>Letzte Ausführungen</h2>
          <table className="data-table" data-testid="executions-table">
            <thead><tr><th>Agent</th><th>Status</th><th>Start</th><th>Ende</th></tr></thead>
            <tbody>
              {executions.map(e => (
                <tr key={e.id}>
                  <td>{e.agent_name}</td>
                  <td>{e.status}</td>
                  <td>{e.started_at}</td>
                  <td>{e.ended_at ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
