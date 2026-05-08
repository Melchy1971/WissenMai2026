import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { archiveDocument, deleteDocument, getDocumentChunks, getDocumentDetail, getDocumentVersions, restoreDocument } from '../api/documents.js';
import { ChunkPreviewList } from '../components/documents/ChunkPreviewList.jsx';
import { DocumentMetaCard } from '../components/documents/DocumentMetaCard.jsx';
import { VersionList } from '../components/documents/VersionList.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { mapDocumentDetail, mapError } from '../view-models/mappers.js';
import { useAuth } from '../auth/AuthContext.jsx';

export function DocumentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { isAuthReady } = useAuth();
  const [state, setState] = useState({ status: 'loading', document: null, error: null });
  const [mutationState, setMutationState] = useState({ status: 'idle', error: null });

  async function loadDocument({ cancelled = false } = {}) {
    setState({ status: 'loading', document: null, error: null });
    try {
      const [detail, versions, chunks] = await Promise.all([
        getDocumentDetail(id),
        getDocumentVersions(id),
        getDocumentChunks(id, { limit: 5 }),
      ]);
      if (cancelled) return;
      setState({ status: 'success', document: mapDocumentDetail(detail, versions, chunks), error: null });
    } catch (error) {
      if (cancelled) return;
      setState({ status: 'error', document: null, error: mapError(error) });
    }
  }

  useEffect(() => {
    let cancelled = false;

    if (!isAuthReady) {
      setState({ status: 'loading', document: null, error: null });
      return () => {
        cancelled = true;
      };
    }

    void loadDocument({ cancelled });
    return () => {
      cancelled = true;
    };
  }, [id, isAuthReady]);

  async function handleArchive() {
    setMutationState({ status: 'loading', error: null });
    try {
      await archiveDocument(id);
      await loadDocument();
      setMutationState({ status: 'success', error: null });
    } catch (error) {
      setMutationState({ status: 'error', error: mapError(error) });
    }
  }

  async function handleRestore() {
    setMutationState({ status: 'loading', error: null });
    try {
      await restoreDocument(id);
      await loadDocument();
      setMutationState({ status: 'success', error: null });
    } catch (error) {
      setMutationState({ status: 'error', error: mapError(error) });
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm('Delete ist destruktiv. Das Dokument wird aus der GUI entfernt und bleibt nur als Soft-Delete erhalten. Fortfahren?');
    if (!confirmed) {
      return;
    }

    setMutationState({ status: 'loading', error: null });
    try {
      await deleteDocument(id);
      navigate('/documents');
    } catch (error) {
      setMutationState({ status: 'error', error: mapError(error) });
    }
  }

  if (state.status === 'loading') {
    return <LoadingState label="Dokumentdetail wird geladen..." />;
  }

  if (state.status === 'error') {
    return <ErrorState error={state.error} />;
  }

  if (!state.document) {
    return <EmptyState title="Kein Dokument geladen" message="Das angeforderte Dokument konnte nicht dargestellt werden." />;
  }

  return (
    <div className="page-stack">
      <div className="page-header">
        <div>
          <Link className="back-link" to="/documents">
            Zur Dokumentliste
          </Link>
          <h2>{state.document.title}</h2>
        </div>
        <div className="search-bar__actions">
          {state.document.lifecycleStatus.kind === 'active' ? (
            <button type="button" className="button-secondary" onClick={handleArchive} disabled={mutationState.status === 'loading'}>
              Dokument archivieren
            </button>
          ) : null}
          {state.document.lifecycleStatus.kind === 'archived' ? (
            <button type="button" className="button-secondary" onClick={handleRestore} disabled={mutationState.status === 'loading'}>
              Dokument wiederherstellen
            </button>
          ) : null}
          <button type="button" onClick={handleDelete} disabled={mutationState.status === 'loading'}>
            Dokument loeschen
          </button>
        </div>
      </div>
      <div className="chat-warning lifecycle-warning">
        <strong>Hinweis</strong>
        <p>
          {state.document.lifecycleStatus.kind === 'archived'
            ? 'Archivierte Dokumente erscheinen nicht in Suche oder Chat, koennen aber wiederhergestellt werden.'
            : 'Archivieren blendet das Dokument aus Suche und Chat aus.'}
        </p>
        <p>Delete ist destruktiv und fuehrt in der GUI nur einen Soft-Delete aus.</p>
      </div>
      {mutationState.status === 'error' ? <ErrorState error={mutationState.error} /> : null}
      <DocumentMetaCard document={state.document} />
      <div className="detail-grid">
        <VersionList items={state.document.versions} />
        <ChunkPreviewList items={state.document.chunks} />
      </div>
    </div>
  );
}