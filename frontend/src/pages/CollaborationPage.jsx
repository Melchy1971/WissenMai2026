import { useEffect, useState } from 'react';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';

export function CollaborationPage() {
  const [state, setState] = useState({ status: 'loading', runs: [], error: null });
  const [objective, setObjective] = useState('');

  async function load() {
    setState({ status: 'loading', runs: [], error: null });
    const res = await callApi('/api/v1/collaboration/runs');
    if (!res.ok) setState({ status: 'error', runs: [], error: res.error });
    else setState({ status: 'success', runs: res.data?.items ?? [], error: null });
  }

  useEffect(() => { load(); }, []);

  async function start(e) {
    e.preventDefault();
    if (!objective.trim()) return;
    const res = await callApi('/api/v1/collaboration/runs', {
      method: 'POST',
      body: JSON.stringify({
        objective,
        protocol: { name: 'default-review', roles: ['planner'], decision_policy: 'approval_required' },
      }),
    });
    if (!res.ok) setState({ status: 'error', runs: [], error: res.error });
    else {
      setObjective('');
      await load();
    }
  }

  if (state.status === 'loading') return <LoadingState label="Collaboration wird geladen..." />;
  if (state.status === 'error') return <ErrorState error={state.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="collaboration-page">
      <h1 className="page__title">Collaboration</h1>
      <form className="search-bar" onSubmit={start}>
        <input className="input" value={objective} onChange={(e) => setObjective(e.target.value)} placeholder="Team-Ziel formulieren" />
        <button type="submit">Mit Protocol starten</button>
      </form>
      {state.runs.length === 0 ? (
        <EmptyState title="Keine Collaboration Runs" message="Es wurden noch keine Team-Runs gestartet." />
      ) : (
        <table className="data-table"><tbody>{state.runs.map((r) => <tr key={r.id}><td>{r.objective}</td><td>{r.status}</td></tr>)}</tbody></table>
      )}
    </div>
  );
}
