import { useEffect, useRef, useState } from 'react';

import { useAuth } from '../auth/AuthContext.jsx';
import { getDocuments, importDocument } from '../api/documents.js';
import { getJob } from '../api/jobs.js';
import { searchChunks } from '../api/search.js';
import { DocumentTable } from '../components/documents/DocumentTable.jsx';
import { SearchResultList } from '../components/documents/SearchResultList.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { mapDocumentListItem, mapError, mapJobStatus, mapSearchResult } from '../view-models/mappers.js';

export function DocumentsPage() {
  const { active_workspace_id: workspaceId, isAuthReady } = useAuth();
  const [state, setState] = useState({ status: 'loading', items: [], error: null });
  const [searchState, setSearchState] = useState({ status: 'idle', items: [], error: null, query: '' });
  const [uploadState, setUploadState] = useState({ status: 'idle', fileName: '', job: null, result: null, error: null });
  const [queryInput, setQueryInput] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState('active');
  const pollTimeoutRef = useRef(null);
  const uploadJobState = mapJobStatus(uploadState.job);

  async function loadDocuments({ cancelled = false } = {}) {
    setState({ status: 'loading', items: [], error: null });
    try {
      const response = await getDocuments({ limit: 20, offset: 0, lifecycleStatus: lifecycleFilter });
      if (cancelled) return;
      const items = response.map(mapDocumentListItem).filter((item) => item.lifecycleStatus.kind !== 'deleted');
      setState({ status: 'success', items, error: null });
    } catch (error) {
      if (cancelled) return;
      setState({ status: 'error', items: [], error: mapError(error) });
    }
  }

  useEffect(() => {
    let cancelled = false;

    if (!isAuthReady) {
      setState({ status: 'loading', items: [], error: null });
      return () => {
        cancelled = true;
      };
    }

    void loadDocuments({ cancelled });
    return () => {
      cancelled = true;
    };
  }, [isAuthReady, workspaceId, lifecycleFilter]);

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, []);

  async function pollImportJob(jobId, fileName) {
    try {
      const job = await getJob(jobId);
      if (job.status === 'completed') {
        setUploadState({ status: 'success', fileName, job, result: job.result, error: null });
        await loadDocuments();
        return;
      }
      if (job.status === 'failed') {
        setUploadState({
          status: 'error',
          fileName,
          job,
          result: null,
          error: mapError({ code: job.error_code, message: job.error_message, details: {} }),
        });
        return;
      }

      setUploadState({ status: 'polling', fileName, job, result: null, error: null });
      pollTimeoutRef.current = setTimeout(() => {
        void pollImportJob(jobId, fileName);
      }, 250);
    } catch (error) {
      setUploadState({ status: 'error', fileName, job: null, result: null, error: mapError(error) });
    }
  }

  async function handleUploadSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = form.elements.file?.files?.[0];
    if (!file) {
      setUploadState({
        status: 'error',
        fileName: '',
        job: null,
        result: null,
        error: {
          code: 'FILE_REQUIRED',
          title: 'Datei fehlt',
          message: 'Bitte waehle eine Datei fuer den Import aus.',
        },
      });
      return;
    }

    setUploadState({ status: 'loading', fileName: file.name, job: null, result: null, error: null });
    try {
      const job = await importDocument(file);
      setUploadState({ status: 'polling', fileName: file.name, job, result: null, error: null });
      form.reset();
      void pollImportJob(job.id, file.name);
    } catch (error) {
      setUploadState({ status: 'error', fileName: file.name, job: null, result: null, error: mapError(error) });
    }
  }

  async function handleSearchSubmit(event) {
    event.preventDefault();

    const query = queryInput.trim();
    if (!query) {
      setSearchState({ status: 'idle', items: [], error: null, query: '' });
      return;
    }

    setSearchState({ status: 'loading', items: [], error: null, query });
    try {
      const response = await searchChunks({ query, limit: 10, offset: 0 });
      setSearchState({ status: 'success', items: response.map(mapSearchResult), error: null, query });
    } catch (error) {
      setSearchState({ status: 'error', items: [], error: mapError(error), query });
    }
  }

  function handleSearchReset() {
    setQueryInput('');
    setSearchState({ status: 'idle', items: [], error: null, query: '' });
  }

  return (
    <section className="page-stack">
      <div className="page-header">
        <div>
          <p className="panel__eyebrow">Dokumentuebersicht</p>
          <h2>Dokumente</h2>
        </div>
        <p className="page-header__meta">Workspace: {workspaceId || 'nicht konfiguriert'}</p>
      </div>
      <section className="panel">
        <div className="panel__header search-bar__header">
          <div>
            <p className="panel__eyebrow">Lifecycle</p>
            <h3>Sichtbarkeit</h3>
          </div>
        </div>
        <form className="search-bar" onSubmit={(event) => event.preventDefault()}>
          <label className="search-bar__field">
            <span className="search-bar__label">Statusfilter</span>
            <select value={lifecycleFilter} onChange={(event) => setLifecycleFilter(event.target.value)}>
              <option value="active">Nur aktive Dokumente</option>
              <option value="archived">Nur archivierte Dokumente</option>
            </select>
          </label>
        </form>
        <div className="chat-warning lifecycle-warning">
          <strong>Hinweis</strong>
          <p>Archivierte Dokumente erscheinen nicht in Suche oder Chat. Geloeschte Dokumente werden in der GUI nicht angezeigt.</p>
        </div>
      </section>
      <section className="panel">
        <div className="panel__header search-bar__header">
          <div>
            <p className="panel__eyebrow">Import</p>
            <h3>Dokument hochladen</h3>
          </div>
        </div>
        <form className="search-bar" onSubmit={handleUploadSubmit}>
          <label className="search-bar__field">
            <span className="search-bar__label">Datei</span>
            <input type="file" name="file" accept=".txt,.md,.docx,.doc,.pdf" />
          </label>
          <div className="search-bar__actions">
            <button type="submit" disabled={uploadState.status === 'loading' || uploadState.status === 'polling'}>
              {uploadState.status === 'loading' || uploadState.status === 'polling' ? 'Upload laeuft...' : 'Dokument importieren'}
            </button>
          </div>
        </form>

        {uploadState.status === 'polling' ? (
          <div className="meta-grid">
            <div>
              <dt>Job-ID</dt>
              <dd>{uploadState.job?.id}</dd>
            </div>
            <div>
              <dt>Datei</dt>
              <dd>{uploadState.fileName}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>{uploadJobState.label}</dd>
            </div>
            <div>
              <dt>Fortschritt</dt>
              <dd>{uploadJobState.message}</dd>
            </div>
          </div>
        ) : null}

        {uploadState.status === 'success' ? (
          <div className="meta-grid">
            <div>
              <dt>Import</dt>
              <dd>
                {uploadState.result?.import_status === 'duplicate'
                  ? `${uploadState.fileName} bereits vorhanden`
                  : `${uploadState.fileName} erfolgreich verarbeitet`}
              </dd>
            </div>
            <div>
              <dt>Dokument</dt>
              <dd>{uploadState.result?.document_id || 'unbekannt'}</dd>
            </div>
            <div>
              <dt>Import-Status</dt>
              <dd>{uploadState.result?.import_status || 'unbekannt'}</dd>
            </div>
            <div>
              <dt>Chunks</dt>
              <dd>{uploadState.result?.chunk_count ?? 0}</dd>
            </div>
            {uploadState.result?.duplicate_of_document_id ? (
              <div>
                <dt>Vorhandenes Dokument</dt>
                <dd>{uploadState.result.duplicate_of_document_id}</dd>
              </div>
            ) : null}
            {uploadState.result?.parser_type ? (
              <div>
                <dt>Parser</dt>
                <dd>{uploadState.result.parser_type}</dd>
              </div>
            ) : null}
          </div>
        ) : null}

        {uploadState.status === 'error' ? <ErrorState error={uploadState.error} /> : null}
      </section>
      <section className="panel">
        <div className="panel__header search-bar__header">
          <div>
            <p className="panel__eyebrow">Einfache Suche</p>
            <h3>Chunk-Suche</h3>
          </div>
        </div>
        <form className="search-bar" onSubmit={handleSearchSubmit}>
          <label className="search-bar__field">
            <span className="search-bar__label">Suchbegriff</span>
            <input
              type="search"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
              placeholder="z. B. Vertragsentwurf oder Paragraph 5"
            />
          </label>
          <div className="search-bar__actions">
            <button type="submit">Suchen</button>
            <button type="button" className="button-secondary" onClick={handleSearchReset}>Zuruecksetzen</button>
          </div>
        </form>
      </section>

      {searchState.status === 'loading' ? <LoadingState label="Suchtreffer werden geladen..." /> : null}
      {searchState.status === 'error' ? <ErrorState error={searchState.error} /> : null}
      {searchState.status === 'success' && searchState.items.length === 0 ? (
        <EmptyState
          title="Keine Treffer gefunden"
          message={`Fuer \"${searchState.query}\" wurden im aktuellen Workspace keine Chunks gefunden.`}
        />
      ) : null}
      {searchState.status === 'success' && searchState.items.length > 0 ? (
        <SearchResultList items={searchState.items} query={searchState.query} />
      ) : null}
      {state.status === 'loading' ? (
        <LoadingState label="Dokumente werden geladen..." />
      ) : state.status === 'error' ? (
        <ErrorState error={state.error} />
      ) : state.items.length === 0 ? (
        <EmptyState title="Keine Dokumente vorhanden" message="Fuer diesen Workspace liegen aktuell keine Dokumente vor." />
      ) : (
        <DocumentTable items={state.items} />
      )}
    </section>
  );
}