import { StatusBadge } from '../status/StatusBadge.jsx';

export function DocumentMetaCard({ document }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Dokumentdetail</p>
          <h2>{document.title}</h2>
        </div>
        <div className="badge-row" data-testid="lifecycle-status">
          <StatusBadge status={document.lifecycleStatus} testId="document-status-badge" />
          <StatusBadge status={document.importStatus} />
        </div>
      </div>
      <dl className="meta-grid">
        <div><dt>Status</dt><dd>{document.lifecycleStatus.label}</dd></div>
        <div><dt>Importquelle</dt><dd>{document.sourceType}</dd></div>
        <div><dt>Dateityp</dt><dd>{document.mimeType}</dd></div>
        <div><dt>Verarbeitungsversion</dt><dd>{document.parserVersion}</dd></div>
        {document.tags?.length > 0 && (
          <div><dt>Tags</dt><dd>{document.tags.map(t => t.name).join(', ')}</dd></div>
        )}
        <div><dt>OCR genutzt</dt><dd>{document.ocrUsed == null ? 'Unbekannt' : document.ocrUsed ? 'Ja' : 'Nein'}</dd></div>
        <div><dt>Versionen</dt><dd>{document.versions.length}</dd></div>
        <div><dt>Chunks</dt><dd>{document.chunkCount}</dd></div>
        <div><dt>Zeichen</dt><dd>{document.totalChars}</dd></div>
        <div><dt>Archiviert</dt><dd>{document.archivedAtLabel || 'Nein'}</dd></div>
        <div><dt>Erstellt</dt><dd>{document.createdAtLabel}</dd></div>
        <div><dt>Aktualisiert</dt><dd>{document.updatedAtLabel}</dd></div>
      </dl>
    </section>
  );
}