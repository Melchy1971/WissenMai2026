import { useEffect, useState } from 'react';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';

export function AgentsPage() {
  const [state, setState] = useState({ status: 'loading', executions: [], error: null });
  const [goal, setGoal] = useState('');

  async function load() {
    setState({ status: 'loading', executions: [], error: null });
    const res = await callApi('/api/v1/agents/executions');
    if (!res.ok) setState({ status: 'error', executions: [], error: res.error });
    else setState({ status: 'success', executions: res.data?.items ?? [], error: null });
  }

  useEffect(() => { load(); }, []);

  async function start(e) {
    e.preventDefault();
    if (!goal.trim()) return;
    const res = await callApi('/api/v1/orchestrator/goals', {
      method: 'POST',
      body: JSON.stringify({
        goal,
        execution_plan: { steps: [{ order: 1, action: 'orchestrate_goal' }] },
      }),
    });
    if (!res.ok) setState({ status: 'error', executions: [], error: res.error });
    else {
      setGoal('');
      await load();
    }
  }

  if (state.status === 'loading') return <LoadingState label="Agenten werden geladen..." />;
  if (state.status === 'error') return <ErrorState error={state.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="agents-page">
      <h1 className="page__title">Agents</h1>
      <form className="search-bar" onSubmit={start}>
        <input className="input" value={goal} onChange={(e) => setGoal(e.target.value)} placeholder="Ziel formulieren" />
        <button type="submit">Ueber Orchestrator starten</button>
      </form>
      {state.executions.length === 0 ? (
        <EmptyState title="Keine Agent-Ausfuehrungen" message="Es wurden noch keine Orchestrator-Ausfuehrungen gestartet." />
      ) : (
        <table className="data-table"><tbody>{state.executions.map((e) => <tr key={e.id}><td>{e.goal}</td><td>{e.status}</td></tr>)}</tbody></table>
      )}
    </div>
  );
}
