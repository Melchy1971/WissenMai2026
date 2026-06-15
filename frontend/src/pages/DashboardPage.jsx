import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { dashboardApi } from '../api/dashboard.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';

export function DashboardPage() {
  const { viewState, setLoading, setSuccess, setError } = useViewState('idle');
  const [summary, setSummary] = useState(null);
  const [activity, setActivity] = useState([]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    try {
      const [summaryData, activityData] = await Promise.all([
        dashboardApi.getSummary(),
        dashboardApi.getActivity(),
      ]);
      setSummary(summaryData);
      setActivity(activityData?.items ?? []);
    } catch (error) {
      setError(error);
      return;
    }
    setSuccess();
  }

  if (viewState.state === 'loading') return <LoadingState label="Dashboard wird geladen..." />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="dashboard-page">
      <h1 className="page__title">Dashboard</h1>

      <section className="page__section">
        <h2>Uebersicht</h2>
        <div className="card-grid" data-testid="dashboard-summary">
          <div className="stat-card">
            <span className="stat-card__label">Dokumente</span>
            <span className="stat-card__value">{summary?.document_count ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Aktiv</span>
            <span className="stat-card__value">{summary?.active_document_count ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Archiviert</span>
            <span className="stat-card__value">{summary?.archived_document_count ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Neue Imports</span>
            <span className="stat-card__value">{summary?.new_imports_count ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Offene Analysen</span>
            <span className="stat-card__value">{summary?.open_analysis_count ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Themen</span>
            <span className="stat-card__value">{summary?.topic_count ?? 0}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Quality Score</span>
            <span className="stat-card__value">{summary?.quality_score ?? '-'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Drift</span>
            <span className="stat-card__value">{summary?.drift_status ?? 'unknown'}</span>
          </div>
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
                  <td>{item.item_type ?? '-'}</td>
                  <td>{item.status ?? '-'}</td>
                  <td>{item.created_at ? new Date(item.created_at).toLocaleString('de-DE') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
