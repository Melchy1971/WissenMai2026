import { useEffect, useRef, useState } from 'react';

import { useAuth } from '../auth/AuthContext.jsx';
import { getDocuments, importDocument } from '../api/documents.js';
import { getJob } from '../api/jobs.js';
import { createRequestCoordinator } from '../api/requestCoordinator.js';
import { searchChunks } from '../api/search.js';
import { DocumentTable } from '../components/documents/DocumentTable.jsx';
import { SearchResultList } from '../components/documents/SearchResultList.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { mapDocumentListItem, mapError, mapImportOutcome, mapJobStatus, mapSearchResult } from '../view-models/mappers.js';

const ALLOWED_LIFECYCLE_FILTERS = ['active', 'archived'];
const POLL_MAX_ATTEMPTS = 120; // 30s at 250ms intervals
const POLL_MAX_NETWORK_ERRORS = 3;

export function DocumentsPage() {
  const { token, active_workspace_id: workspaceId, isAuthReady } = useAuth();
  const [state, setState] = useState({ status: 'loading', items: [], error: null });
  const [searchState, setSearchState] = useState({ status: 'idle', items: [], error: null, query: '' });
  const [uploadState, setUploadState] = useState({ status: 'idle', fileName: '', job: null, result: null, error: null });
  const [queryInput, setQueryInput] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState('active');
  const pollTimeoutRef = useRef(null);
  const pollAttemptsRef = useRef(0);
  const pollNetworkErrorRef = useRef(0);
  const requestContextRef = useRef({ authToken: '', workspaceId: '' });
  const requestCoordinatorRef = useRef(null);
  const uploadInFlightRef = useRef(false);
  const prevWorkspaceIdRef = useRef(workspaceId);
  const uploadJobState = mapJobStatus(uploadState.job);
  const uploadOutcome =
    uploadState.status === 'success'
      ? mapImportOutcome(uploadState.result, { fileName: uploadState.fileName })
      : null;
  const uploadErrorTestId =
    uploadState.error?.code === 'OCR_REQUIRED'
      ? 'upload-ocr-required'
      : uploadState.error?.code === 'FILE_TOO_LARGE'
        ? 'upload-file-too-large'
        : 'upload-error';

  requestContextRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!requestCoordinatorRef.current) {
    requestCoordinatorRef.current = createRequestCoordinator({
      getContext: () => requestContextRef.current,
    });
  }

  async function loadDocuments() {
    const ticket = requestCoordinatorRef.current.begin('documents:list');
    setState({ status: 'loading', items: [], error: null });
    try {
      const response = await getDocuments(
        { limit: 20, offset: 0, lifecycleStatus: lifecycleFilter },
        { signal: ticket.signal, correlationId: ticket.correlationId },
      );
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      const items = response.map(mapDocumentListItem).filter((item) => item.lifecycleStatus.kind !== 'deleted');
      setState({ status: 'success', items, error: null });
    } catch (error) {
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      setState({ status: 'error', items: [], error: mapError(error) });
    } finally {
      requestCoordinatorRef.current.complete(ticket);
    }
  }

  useEffect(() => {
    if (!isAuthReady) {
      setState({ status: 'loading', items: [], error: null });
      return () => {
        requestCoordinatorRef.current.cancel('documents:list');
      };
    }

    void loadDocuments();
    return () => {
      requestCoordinatorRef.current.cancel('documents:list');
    };
  }, [isAuthReady, workspaceId, lifecycleFilter]);

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
      requestCoordinatorRef.current.cancelAll();
    };
  }, []);

  // Rule 6: reset transient upload/search state whenever the active workspace changes
  useEffect(() => {
    if (prevWorkspaceIdRef.current === workspaceId) return;
    prevWorkspaceIdRef.current = workspaceId;
    if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
    requestCoordinatorRef.current.cancel('documents:upload');
    requestCoordinatorRef.current.cancel('documents:search');
    uploadInFlightRef.current = false;
    setUploadState({ status: 'idle', fileName: '', job: null, result: null, error: null });
    setSearchState({ status: 'idle', items: [], error: null, query: '' });
    setQueryInput('');
  }, [workspaceId]);

  async function pollImportJob(jobId, fileName, ticket) {
    if (!requestCoordinatorRef.current.isCurrent(ticket)) {
      uploadInFlightRef.current = false;
      return;
    }
    if (pollAttemptsRef.current >= POLL_MAX_ATTEMPTS) {
      uploadInFlightRef.current = false;
      setUploadState({
        status: 'error',
        fileName,
        job: null,
        result: null,
        error: mapError({ code: 'JOB_TIMEOUT', message: 'Der Import-Job hat zu lange gedauert.', details: {} }),
      });
      return;
    }
    pollAttemptsRef.current += 1;

    try {
      const job = await getJob(jobId, { signal: ticket.signal, correlationId: ticket.correlationId });
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      pollNetworkErrorRef.current = 0;
      if (job.status === 'completed') {
        uploadInFlightRef.current = false;
        setUploadState({ status: 'success', fileName, job, result: job.result, error: null });
        await loadDocuments();
        requestCoordinatorRef.current.complete(ticket);
        return;
      }
      if (job.status === 'failed') {
        uploadInFlightRef.current = false;
        setUploadState({
          status: 'error',
          fileName,
          job,
          result: null,
          error: mapError({ code: job.error_code, message: job.error_message, details: {} }),
        });
        requestCoordinatorRef.current.complete(ticket);
        return;
      }

      setUploadState({ status: 'polling', fileName, job, result: null, error: null });
      pollTimeoutRef.current = setTimeout(() => {
        void pollImportJob(jobId, fileName, ticket);
      }, 250);
    } catch (error) {
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      pollNetworkErrorRef.current += 1;
      if (pollNetworkErrorRef.current <= POLL_MAX_NETWORK_ERRORS) {
        pollTimeoutRef.current = setTimeout(() => {
          void pollImportJob(jobId, fileName, ticket);
        }, 1000 * pollNetworkErrorRef.current);
      } else {
        uploadInFlightRef.current = false;
        setUploadState({ status: 'error', fileName, job: null, result: null, error: mapError(error) });
        requestCoordinatorRef.current.complete(ticket);
      }
    }
  }

  async function handleUploadSubmit(event) {
    event.preventDefault();
    if (uploadInFlightRef.current || uploadState.status === 'loading' || uploadState.status === 'polling') {
      return;
    }
    const form = event.currentTarget;
    const file = form.elements.file?.files?.[0];
    if (!file) {
      setUploadState({
        status: 'error',
        fileName: '',
        job: null,
        result: null,
        error: mapError({ code: 'FILE_REQUIRED', message: 'Bitte waehle eine Datei fuer den Import aus.', details: {} }),
      });
      return;
    }

    pollAttemptsRef.current = 0;
    pollNetworkErrorRef.current = 0;
    uploadInFlightRef.current = true;
    const ticket = requestCoordinatorRef.current.begin('documents:upload');
    setUploadState({ status: 'loading', fileName: file.name, job: null, result: null, error: null });
    try {
      const job = await importDocument(file, { signal: ticket.signal, correlationId: ticket.correlationId });
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      setUploadState({ status: 'polling', fileName: file.name, job, result: null, error: null });
      form.reset();
      void pollImportJob(job.id, file.name, ticket);
    } catch (error) {
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      uploadInFlightRef.current = false;
      setUploadState({ status: 'error', fileName: file.name, job: null, result: null, error: mapError(error) });
      requestCoordinatorRef.current.complete(ticket);
    }
  }

  async function handleSearchSubmit(event) {
    event.preventDefault();

    const query = queryInput.trim();
    if (!query) {
      setSearchState({ status: 'idle', items: [], error: null, query: '' });
      return;
    }

    const ticket = requestCoordinatorRef.current.begin('documents:search');

    setSearchState({ status: 'loading', items: [], error: null, query });
    try {
      const response = await searchChunks(
        { query, limit: 10, offset: 0 },
        { signal: ticket.signal, correlationId: ticket.correlationId },
      );
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      setSearchState({ status: 'success', items: response.map(mapSearchResult), error: null, query });
    } catch (error) {
      if (!requestCoordinatorRef.current.isCurrent(ticket)) return;
      setSearchState({ status: 'error', items: [], error: mapError(error), query });
    } finally {
      requestCoordinatorRef.current.complete(ticket);
    }
  }

  function handleSearchReset() {
    requestCoordinatorRef.current.cancel('documents:search');
    setQueryInput('');
    setSearchState({ status: 'idle', items: [], error: null, query: '' });
  }

  const canUseDocumentControls = state.status !== 'error';

  return (
    <section className="page-stack" data-testid="documents-page">
      <div className="page-header">
        <div>
          <p className="panel__eyebrow">Dokumentuebersicht</p>
          <h2>Dokumente</h2>
        </div>
        <p className="page-header__meta">Workspace: {workspaceId || 'nicht konfiguriert'}</p>
      </div>
      {canUseDocumentControls ? (
      <section className="panel" data-testid="lifecycle-panel">
        <div className="panel__header search-bar__header">
          <div>
            <p className="panel__eyebrow">Lifecycle</p>
            <h3>Sichtbarkeit</h3>
          </div>
        </div>
        <form className="search-bar" onSubmit={(event) => event.preventDefault()}>
          <label className="search-bar__field">
            <span className="search-bar__label">Statusfilter</span>
            <select data-testid="archived-filter" value={lifecycleFilter} onChange={(event) => { if (ALLOWED_LIFECYCLE_FILTERS.includes(event.target.value)) setLifecycleFilter(event.target.value); }}>
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
      ) : null}
      {canUseDocumentControls ? (
      <section className="panel" data-testid="upload-panel">
        <div className="panel__header search-bar__header">
          <div>
            <p className="panel__eyebrow">Import</p>
            <h3>Dokument hochladen</h3>
          </div>
        </div>
        <form className="search-bar" data-testid="upload-form" onSubmit={handleUploadSubmit}>
          <label className="search-bar__field">
            <span className="search-bar__label">Datei</span>
            <input data-testid="upload-file-input" type="file" name="file" accept=".txt,.md,.docx,.doc,.pdf" />
          </label>
          <div className="search-bar__actions">
            <button
              data-testid="upload-submit"
              type="submit"
              disabled={uploadState.status === 'loading' || uploadState.status === 'polling'}
            >
              {uploadState.status === 'loading' || uploadState.status === 'polling' ? 'Upload laeuft...' : 'Dokument importieren'}
            </button>
          </div>
        </form>

        {uploadState.status === 'polling' ? (
          <div className="meta-grid" data-testid="upload-job-status">
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
          <div className="meta-grid" data-testid="upload-success">
            <div>
              <dt>Import</dt>
              <dd>{uploadOutcome.title}</dd>
            </div>
            <div>
              <dt>Hinweis</dt>
              <dd>{uploadOutcome.message}</dd>
            </div>
            <div>
              <dt>Code</dt>
              <dd>{uploadOutcome.code}</dd>
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

        {uploadState.status === 'error' ? (
          uploadErrorTestId === 'upload-error' ? (
            <ErrorState error={uploadState.error} testId="upload-error" />
          ) : (
            <div data-testid={uploadErrorTestId}>
              <ErrorState error={uploadState.error} testId="upload-error" />
            </div>
          )
        ) : null}
      </section>
      ) : null}
      {canUseDocumentControls ? (
      <section className="panel" data-testid="search-page">
        <div className="panel__header search-bar__header">
          <div>
            <p className="panel__eyebrow">Einfache Suche</p>
            <h3>Chunk-Suche</h3>
          </div>
        </div>
        <form className="search-bar" data-testid="search-form" onSubmit={handleSearchSubmit}>
          <label className="search-bar__field">
            <span className="search-bar__label">Suchbegriff</span>
            <input
              data-testid="search-input"
              type="search"
              value={queryInput}
              onChange={(event) => setQueryInput(event.target.value)}
              placeholder="z. B. Vertragsentwurf oder Paragraph 5"
            />
          </label>
          <div className="search-bar__actions">
            <button data-testid="search-submit" type="submit">Suchen</button>
            <button type="button" className="button-secondary" onClick={handleSearchReset}>Zuruecksetzen</button>
          </div>
        </form>
      </section>
      ) : null}

      {canUseDocumentControls && searchState.status === 'loading' ? (
        <LoadingState label="Suchtreffer werden geladen..." testId="search-loading" />
      ) : null}
      {canUseDocumentControls && searchState.status === 'error' ? <ErrorState error={searchState.error} testId="search-error" /> : null}
      {canUseDocumentControls && searchState.status === 'success' && searchState.items.length === 0 ? (
        <EmptyState
          testId="search-empty"
          title="Keine Treffer gefunden"
          message={`Fuer \"${searchState.query}\" wurden im aktuellen Workspace keine Chunks gefunden.`}
        />
      ) : null}
      {canUseDocumentControls && searchState.status === 'success' && searchState.items.length > 0 ? (
        <SearchResultList items={searchState.items} query={searchState.query} />
      ) : null}
      {state.status === 'loading' ? (
        <LoadingState label="Dokumente werden geladen..." />
      ) : state.status === 'error' ? (
        <ErrorState error={state.error} testId="auth-error" />
      ) : state.items.length === 0 ? (
        <div data-testid="document-list">
          <EmptyState title="Keine Dokumente vorhanden" message="Fuer diesen Workspace liegen aktuell keine Dokumente vor." />
        </div>
      ) : (
        <div data-testid="document-list">
          <DocumentTable items={state.items} />
        </div>
      )}
    </section>
  );
}
