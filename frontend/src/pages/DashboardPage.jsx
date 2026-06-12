import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';

export function DashboardPage() {
  const { viewState, setLoading, setSuccess, setError } = useViewState('idle');
  const [status, setStatus] = useState(null);
  const [docSummary, setDocSummary] = useState(null);
  const [importStatus, setImportStatus] = useState(null);
  const [dqSummary, setDqSummary] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [sysRes, docRes, importRes, dqRes, runsRes] = await Promise.all([
      callApi('/api/v1/status'),
      callApi('/api/v1/documents?summary=true'),
      callApi('/api/v1/jobs?type=import&limit=1'),
      callApi('/api/v1/data-quality/summary'),
      callApi('/api/v1/data-quality/runs?limit=5'),
    ]);
    if (!sysRes.ok) { setError(sysRes.error); return; }
    setStatus(sysRes.data);
    setDocSummary(docRes.ok ? docRes.data : null);
    setImportStatus(importRes.ok ? (importRes.data?.items?.[0] ?? null) : null);
    setDqSummary(dqRes.ok ? dqRes.data : null);
    setRecentRuns(runsRes.ok ? (runsRes.data?.items ?? []) : []);
    setSuccess();
  }

  if (viewState.state === 'loading') return <LoadingState label="Dashboard wird geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;

  const warnings = status?.warnings ?? [];

  return (
    <div className="page" data-testid="dashboard-page">
      <h1 className="page__title">Dashboard</h1>

      {warnings.length > 0 && (
        <div className="alert alert--warning" role="alert" data-testid="dashboard-warnings">
          <strong>Warnungen:</strong>
          <ul>
            {warnings.map((w, i) => <li key={i}>{w.message ?? w}</li>)}
          </ul>
        </div>
      )}

      <section className="page__section">
        <h2>Systemstatus</h2>
        <div className="card-grid" data-testid="system-status">
          <div className="stat-card">
            <span className="stat-card__label">Provider</span>
            <span className="stat-card__value">{status?.provider_name ?? '—'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Autonomie</span>
            <span className="stat-card__value">{status?.autonomy_level ?? '—'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Release</span>
            <span className="stat-card__value">{status?.release_status ?? '—'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Privacy Mode</span>
            <span className="stat-card__value">{status?.privacy_mode ? 'Aktiv' : 'Inaktiv'}</span>
          </div>
        </div>
      </section>

      <section className="page__section">
        <h2>Dokumente</h2>
        <div className="card-grid" data-testid="document-summary">
          <div className="stat-card">
            <span className="stat-card__label">Gesamt</span>
            <span className="stat-card__value">{docSummary?.total ?? '—'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Aktiv</span>
            <span className="stat-card__value">{docSummary?.active ?? '—'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Archiviert</span>
            <span className="stat-card__value">{docSummary?.archived ?? '—'}</span>
          </div>
        </div>
      </section>

      <section className="page__section">
        <h2>Importstatus</h2>
        <div data-testid="import-status">
          {importStatus ? (
            <div className="card-grid">
              <div className="stat-card">
                <span className="stat-card__label">Letzter Import</span>
                <span className="stat-card__value">{importStatus.status ?? '—'}</span>
              </div>
              <div className="stat-card">
                <span className="stat-card__label">Verarbeitet</span>
                <span className="stat-card__value">{importStatus.processed ?? '—'}</span>
              </div>
            </div>
          ) : (
            <p className="text-muted">Kein Import-Job vorhanden.</p>
          )}
        </div>
      </section>

      <section className="page__section">
        <h2>Data Quality Score</h2>
        <div className="card-grid" data-testid="data-quality-summary">
          <div className="stat-card">
            <span className="stat-card__label">Score</span>
            <span className="stat-card__value">{dqSummary?.score != null ? `${dqSummary.score}%` : '—'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-card__label">Status</span>
            <span className="stat-card__value">{dqSummary?.status ?? '—'}</span>
          </div>
        </div>
      </section>

      <section className="page__section">
        <h2>Letzte Analysen</h2>
        <div data-testid="recent-analyses">
          {recentRuns.length === 0 ? (
            <p className="text-muted">Keine Analysen vorhanden.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Run ID</th>
                  <th>Status</th>
                  <th>Score</th>
                  <th>Zeitpunkt</th>
                </tr>
              </thead>
              <tbody>
                {recentRuns.map(r => (
                  <tr key={r.id}>
                    <td className="mono">{r.id?.slice(0, 8) ?? '—'}</td>
                    <td>{r.status ?? '—'}</td>
                    <td>{r.score != null ? `${r.score}%` : '—'}</td>
                    <td>{r.created_at ? new Date(r.created_at).toLocaleString('de-DE') : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}
