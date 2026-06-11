import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { DataClassificationBadge } from '../components/shared/DataClassificationBadge.jsx';

export function RAGCenterPage() {
  const { viewState, setLoading, setSuccess, setError, setEmpty } = useViewState('idle');
  const [docs, setDocs] = useState([]);
  const [privacyMode, setPrivacyMode] = useState(false);
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState(null);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [docsRes, statusRes] = await Promise.all([
      callApi('/api/v1/rag/documents'),
      callApi('/api/v1/status'),
    ]);
    if (!docsRes.ok) { setError(docsRes.error); return; }
    const items = docsRes.data?.items ?? [];
    if (!items.length) { setEmpty(); return; }
    setDocs(items);
    setPrivacyMode(statusRes.ok ? (statusRes.data?.privacy_mode ?? false) : false);
    setSuccess();
  }

  async function reindex(docId) {
    const res = await callApi(`/api/v1/rag/documents/${docId}/reindex`, { method: 'POST' });
    if (!res.ok) { alert(res.error.message); return; }
    alert('Reindex gestartet.');
  }

  async function runRetrievalTest(e) {
    e.preventDefault();
    if (!testQuery.trim()) return;
    // SECRET-Dokumente werden nicht als Prompt-Kontext verwendet
    const res = await callApi('/api/v1/rag/retrieve', {
      method: 'POST',
      body: JSON.stringify({ query: testQuery, exclude_secret: true }),
    });
    if (!res.ok) { alert(res.error.message); return; }
    setTestResults(res.data?.results ?? []);
  }

  async function importDocument() {
    if (privacyMode) {
      alert('Privacy Mode aktiv: Import-Persistenz ist blockiert.');
      return;
    }
    // GUI greift nie direkt auf Dateien zu – Upload über API
    alert('Import-Dialog: wird über API-Endpunkt /api/v1/rag/import verarbeitet.');
  }

  if (viewState.state === 'loading') return <LoadingState label="RAG-Dokumente werden geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="rag-center-page">
      <div className="page__header-row">
        <h1 className="page__title">RAG Center</h1>
        <button type="button" className="button-primary" onClick={importDocument}
          disabled={privacyMode} title={privacyMode ? 'Privacy Mode aktiv' : ''}>
          Dokument importieren
        </button>
      </div>

      {privacyMode && (
        <div className="alert alert--info">Privacy Mode: Import-Persistenz deaktiviert.</div>
      )}

      <section className="page__section">
        <h2>Retrieval-Test</h2>
        <form className="search-bar" onSubmit={runRetrievalTest}>
          <input className="input" placeholder="Testanfrage eingeben…" value={testQuery}
            onChange={e => setTestQuery(e.target.value)} data-testid="rag-test-query" />
          <button type="submit" className="button-primary">Testen</button>
        </form>
        {testResults && (
          <ul data-testid="rag-test-results">
            {testResults.length === 0
              ? <li className="text-muted">Keine Treffer.</li>
              : testResults.map((r, i) => (
                <li key={i} className="list-item">
                  <strong>{r.title}</strong> — Score: {r.score?.toFixed(3)}
                  <DataClassificationBadge classification={r.classification} />
                </li>
              ))}
          </ul>
        )}
      </section>

      {viewState.state === 'empty' && docs.length === 0
        ? <EmptyState label="Keine RAG-Dokumente." />
        : (
          <section className="page__section">
            <h2>Dokumente ({docs.length})</h2>
            <table className="data-table" data-testid="rag-docs-table">
              <thead>
                <tr><th>Titel</th><th>Klassifikation</th><th>Chunks</th><th>Status</th><th>Aktion</th></tr>
              </thead>
              <tbody>
                {docs.map(d => (
                  <tr key={d.id}>
                    <td>{d.title}</td>
                    <td><DataClassificationBadge classification={d.classification} /></td>
                    <td>{d.chunk_count ?? '—'}</td>
                    <td>{d.index_status}</td>
                    <td>
                      {d.classification === 'SECRET'
                        ? <span className="text-muted text-sm">gesperrt</span>
                        : <button type="button" className="button-secondary button--sm"
                            onClick={() => reindex(d.id)}>Reindex</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
    </div>
  );
}
