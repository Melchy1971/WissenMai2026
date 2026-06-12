import React, { useState } from 'react';
import { Link } from 'react-router-dom';

function ActionError({ error }) {
  if (!error) return null;
  return (
    <div className="doc-preview__action-error" role="alert">
      {error.userMessage || 'Aktion fehlgeschlagen.'}
    </div>
  );
}

function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="doc-preview__confirm" role="alertdialog" aria-modal="true">
      <p>{message}</p>
      <div className="doc-preview__confirm-actions">
        <button className="button-primary button-primary--danger" onClick={onConfirm}>
          Bestätigen
        </button>
        <button className="button-secondary" onClick={onCancel}>
          Abbrechen
        </button>
      </div>
    </div>
  );
}

export function DocumentPreviewPanel({ item, actionState, onArchive, onDelete }) {
  const [confirm, setConfirm] = useState(null); // 'archive' | 'delete' | null

  if (!item) {
    return (
      <aside className="doc-preview-panel panel doc-preview-panel--empty">
        <div className="doc-preview__placeholder">
          <span>Dokument auswählen</span>
          <span className="doc-preview__placeholder-hint">
            Klicke auf ein Dokument in der Liste, um Details zu sehen.
          </span>
        </div>
        <style>{panelStyles}</style>
      </aside>
    );
  }

  const canArchive = item.lifecycleStatus.kind === 'active';
  const canDelete = item.lifecycleStatus.kind === 'archived';
  const canRestore = item.lifecycleStatus.kind === 'archived';
  const isBusy = actionState.status === 'loading';

  function requestArchive() { setConfirm('archive'); }
  function requestDelete() { setConfirm('delete'); }
  function handleConfirm() {
    if (confirm === 'archive') onArchive(item.id);
    if (confirm === 'delete') onDelete(item.id);
    setConfirm(null);
  }

  return (
    <aside className="doc-preview-panel panel">
      <div className="panel__header">
        <span className="panel__eyebrow">Dokumentdetail</span>
      </div>

      <div className="doc-preview__body">
        {/* Titel + Typ */}
        <section className="doc-preview-section">
          <h2 className="doc-preview__title">{item.title}</h2>
          <span className="doc-preview__type">{item.mimeType}</span>
        </section>

        {/* Lifecycle */}
        <section className="doc-preview-section">
          <span className="doc-preview-label">Status</span>
          <span
            className={`badge badge--${item.lifecycleStatus.tone || 'neutral'}`}
          >
            {item.lifecycleStatus.label}
          </span>
        </section>

        {/* Metadaten */}
        <section className="doc-preview-section">
          <span className="doc-preview-label">Metadaten</span>
          <dl className="meta-grid">
            {item.createdAtLabel && (
              <>
                <dt>Erstellt</dt>
                <dd>{item.createdAtLabel}</dd>
              </>
            )}
            {item.updatedAtLabel && (
              <>
                <dt>Aktualisiert</dt>
                <dd>{item.updatedAtLabel}</dd>
              </>
            )}
            {item.versionCount != null && (
              <>
                <dt>Versionen</dt>
                <dd>{item.versionCount}</dd>
              </>
            )}
            {item.chunkCount != null && (
              <>
                <dt>Chunks</dt>
                <dd>{item.chunkCount}</dd>
              </>
            )}
          </dl>
        </section>

        {/* Tags */}
        {item.tags?.length > 0 && (
          <section className="doc-preview-section">
            <span className="doc-preview-label">Tags</span>
            <div className="doc-preview__tags">
              {item.tags.map((tag) => (
                <span key={tag} className="badge">
                  {tag}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Zugeordnete Themen (Future Phase — Platzhalter) */}
        <section className="doc-preview-section">
          <span className="doc-preview-label">Themen</span>
          <span className="doc-preview__future-note">Themen — folgt in nächster Phase</span>
        </section>

        {/* Aktionen */}
        <section className="doc-preview-section doc-preview-section--actions">
          <span className="doc-preview-label">Aktionen</span>

          {confirm && (
            <ConfirmDialog
              message={
                confirm === 'archive'
                  ? 'Dieses Dokument archivieren? Es bleibt erhalten und kann wiederhergestellt werden.'
                  : 'Dieses Dokument dauerhaft löschen? Diese Aktion kann nicht rückgängig gemacht werden.'
              }
              onConfirm={handleConfirm}
              onCancel={() => setConfirm(null)}
            />
          )}

          <div className="doc-preview__actions">
            <Link
              to={`/documents/${item.id}`}
              className="button-secondary doc-preview__action-btn"
            >
              Öffnen →
            </Link>

            {canArchive && !confirm && (
              <button
                className="button-secondary doc-preview__action-btn"
                onClick={requestArchive}
                disabled={isBusy}
              >
                Archivieren
              </button>
            )}

            {canRestore && !confirm && (
              <span className="doc-preview__action-note">
                Wiederherstellen über Dokumentdetail
              </span>
            )}

            {canDelete && !confirm && (
              <button
                className="button-secondary button-secondary--danger doc-preview__action-btn"
                onClick={requestDelete}
                disabled={isBusy}
              >
                Löschen
              </button>
            )}
          </div>

          <ActionError error={actionState.error} />
        </section>
      </div>

      <style>{panelStyles}</style>
    </aside>
  );
}

const panelStyles = `
  .doc-preview-panel {
    width: 280px;
    min-width: 220px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
  }
  .doc-preview-panel--empty {
    justify-content: center;
    align-items: center;
  }
  .doc-preview__placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 32px 16px;
    color: var(--color-text-secondary, #666);
    font-size: 14px;
    text-align: center;
  }
  .doc-preview__placeholder-hint { font-size: 12px; }
  .doc-preview__body {
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 16px;
    overflow-y: auto;
    flex: 1;
  }
  .doc-preview-section {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .doc-preview-section--actions { gap: 10px; }
  .doc-preview-label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--color-text-secondary, #666);
  }
  .doc-preview__title {
    font-size: 15px;
    font-weight: 600;
    margin: 0;
    word-break: break-word;
  }
  .doc-preview__type {
    font-size: 11px;
    color: var(--color-text-secondary, #666);
    text-transform: uppercase;
  }
  .doc-preview__tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .doc-preview__future-note {
    font-size: 12px;
    color: var(--color-text-secondary, #999);
    font-style: italic;
  }
  .doc-preview__actions {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .doc-preview__action-btn {
    width: 100%;
    text-align: center;
  }
  .doc-preview__action-note {
    font-size: 12px;
    color: var(--color-text-secondary, #666);
  }
  .doc-preview__action-error {
    background: #fce4ec;
    color: #880e4f;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
  }
  .doc-preview__confirm {
    background: var(--color-surface, #fff);
    border: 1px solid var(--color-border, #ddd);
    border-radius: 6px;
    padding: 12px;
  }
  .doc-preview__confirm p { margin: 0 0 10px; font-size: 13px; }
  .doc-preview__confirm-actions {
    display: flex;
    gap: 8px;
  }
  .button-secondary--danger {
    color: #880e4f;
    border-color: #f48fb1;
  }
  .button-primary--danger {
    background: #880e4f;
    color: #fff;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
  }
`;
