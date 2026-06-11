import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { CollaborationRunView } from '../components/shared/CollaborationRunView.jsx';
import { ConflictReportView } from '../components/shared/ConflictReportView.jsx';

export function CollaborationCenterPage() {
  const { viewState, setLoading, setSuccess, setError, setEmpty } = useViewState('idle');
  const [teams, setTeams] = useState([]);
  const [runs, setRuns] = useState([]);
  const [conflicts, setConflicts] = useState([]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [teamsRes, runsRes, conflictsRes] = await Promise.all([
      callApi('/api/v1/collaboration/teams'),
      callApi('/api/v1/collaboration/runs'),
      callApi('/api/v1/collaboration/conflicts'),
    ]);
    if (!teamsRes.ok) { setError(teamsRes.error); return; }
    const items = teamsRes.data?.items ?? [];
    if (!items.length && !(runsRes.data?.items?.length)) { setEmpty(); return; }
    setTeams(items);
    setRuns(runsRes.ok ? (runsRes.data?.items ?? []) : []);
    setConflicts(conflictsRes.ok ? (conflictsRes.data?.items ?? []) : []);
    setSuccess();
  }

  if (viewState.state === 'loading') return <LoadingState label="Collaboration wird geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;
  if (viewState.state === 'empty') return <EmptyState label="Keine Teams oder Runs vorhanden." />;

  return (
    <div className="page" data-testid="collaboration-center-page">
      <h1 className="page__title">Collaboration Center</h1>

      {conflicts.length > 0 && (
        <section className="page__section">
          <h2>Eskalierte Konflikte</h2>
          <ConflictReportView conflicts={conflicts} />
        </section>
      )}

      <section className="page__section">
        <h2>Teams ({teams.length})</h2>
        <ul data-testid="teams-list">
          {teams.map(t => (
            <li key={t.id} className="list-item">
              <strong>{t.name}</strong> — Agents: {t.agent_ids?.join(', ') || '—'}
              <small>Max Agents: {t.max_agents} | Revision Cycles: {t.revision_cycles}</small>
            </li>
          ))}
        </ul>
      </section>

      <section className="page__section">
        <h2>Letzte Runs ({runs.length})</h2>
        {runs.length === 0
          ? <p className="text-muted">Keine Runs.</p>
          : runs.map(r => (
              <CollaborationRunView key={r.id} run={r} />
            ))}
      </section>
    </div>
  );
}
