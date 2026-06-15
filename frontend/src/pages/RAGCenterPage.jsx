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
    setDocs(items);
    setPrivacyMode(statusRes.ok ? (statusRes.data?.privacy_mode ?? false) : false);
    if (!items.length) setEmpty(); else setSuccess();
  }

  async function reindex(docId) {
    const res = await callApi(`/api/v1/rag/documents/${docId}/reindex`, { method: 'POST' });
    if (!res.ok) { alert(res.error.message); return; }
    alert('Approval fuer Reindex wurde erstellt.');
  }

  async function runRetrievalTest(e) {
    e.preventDefault();
    if (!testQuery.trim()) return;
    const res = await callApi('/api/v1/rag/retrieve', {
      method: 'POST',
      body: JSON.stringify({ query: testQuery, exclude_secret: true }),
    });
    if (!res.ok) { alert(res.error.message); return; }
    setTestResults(res.data);
  }

  async function importDocument() {
    if (privacyMode) {
      alert('Privacy Mode aktiv: Import-Persistenz ist blockiert.');
      return;
    }
    alert('Import erfolgt ueber den API-Endpunkt /api/v1/rag/import.');
  }

  const sources = testResults?.sources ?? [];
  const retrievalBlocked = testResults?.status === 'blocked' || (testResults?.used_rag_context && sources.length === 0);

  if (viewState.state === 'loading') return <LoadingState label="RAG-Dokumente werden geladen..." />;
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

      {privacyMode ? (
        <div className="alert alert--info">Privacy Mode: Import-Persistenz deaktiviert.</div>
      ) : null}

      <section className="page__section">
        <h2>Retrieval-Test</h2>
        <form className="search-bar" onSubmit={runRetrievalTest}>
          <input className="input" placeholder="Testanfrage eingeben..." value={testQuery}
            onChange={(e) => setTestQuery(e.target.value)} data-testid="rag-test-query" />
          <button type="submit" className="button-primary">Testen</button>
        </form>
        {testResults ? (
          retrievalBlocked ? (
            <div className="chat-warning" data-testid="rag-answer-blocked">
              <strong>Antwort blockiert</strong>
              <p>Fuer diese Anfrage sind keine sichtbaren Quellen verfuegbar.</p>
              {(testResults.blocked_source_count ?? 0) > 0 ? (
                <p className="state-card__meta">Gesperrte Quellen: {testResults.blocked_source_count}</p>
              ) : null}
            </div>
          ) : (
            <ul data-testid="source-list">
              {sources.map((source, i) => (
                <li key={`${source.chunk_id}-${i}`} className="list-item">
                  <strong>{source.document_name}</strong> - Chunk: {source.chunk_id}
                  {source.page != null ? ` - Seite ${source.page}` : ''}
                  {source.score != null ? ` - Score: ${source.score.toFixed(3)}` : ''}
                  <DataClassificationBadge classification={source.classification} />
                </li>
              ))}
            </ul>
          )
        ) : null}
      </section>

      {viewState.state === 'empty' && docs.length === 0
        ? <EmptyState title="Keine RAG-Dokumente" message="Es sind noch keine indexierbaren RAG-Dokumente im Workspace vorhanden." />
        : (
          <section className="page__section">
            <h2>Dokumente ({docs.length})</h2>
            <table className="data-table" data-testid="rag-docs-table">
              <thead>
                <tr><th>Titel</th><th>Klassifikation</th><th>Chunks</th><th>Status</th><th>Aktion</th></tr>
              </thead>
              <tbody>
                {docs.map((d) => (
                  <tr key={d.id}>
                    <td>{d.title}</td>
                    <td><DataClassificationBadge classification={d.classification} /></td>
                    <td>{d.chunk_count ?? '-'}</td>
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
