import React from 'react';

const SORT_FIELDS = [
  { field: 'title', label: 'Titel' },
  { field: 'mimeType', label: 'Typ' },
  { field: 'lifecycleStatus', label: 'Status' },
  { field: 'updatedAtLabel', label: 'Aktualisiert' },
  { field: 'chunkCount', label: 'Chunks' },
];

function SortButton({ field, current, onSort }) {
  const active = current.field === field;
  return (
    <button
      className={`sort-btn ${active ? 'sort-btn--active' : ''}`}
      onClick={() => {
        if (active) {
          onSort({ field, dir: current.dir === 'asc' ? 'desc' : 'asc' });
        } else {
          onSort({ field, dir: 'asc' });
        }
      }}
      aria-pressed={active}
    >
      {SORT_FIELDS.find((f) => f.field === field)?.label}
      {active && <span className="sort-indicator">{current.dir === 'asc' ? ' ↑' : ' ↓'}</span>}
    </button>
  );
}

function LifecycleBadge({ status }) {
  const toneClass =
    status.tone === 'success'
      ? 'badge--success'
      : status.tone === 'warning'
        ? 'badge--warning'
        : status.tone === 'danger'
          ? 'badge--danger'
          : 'badge--neutral';
  return <span className={`badge ${toneClass}`}>{status.label}</span>;
}

function EmptyState({ hasFilter }) {
  return (
    <div className="doc-list__empty">
      {hasFilter ? (
        <>
          <span>Keine Dokumente gefunden.</span>
          <span className="doc-list__empty-hint">Filter anpassen oder zurücksetzen.</span>
        </>
      ) : (
        <>
          <span>Keine Dokumente vorhanden.</span>
          <span className="doc-list__empty-hint">Importiere dein erstes Dokument über den Import-Bereich.</span>
        </>
      )}
    </div>
  );
}

export function DocumentListPanel({ items, selectedId, onSelect, sort, onSort, listState, hasFilter = false }) {

  if (listState.status === 'loading') {
    return (
      <div className="doc-list-panel panel doc-list-panel--loading">
        <div className="doc-list__loading">Dokumente werden geladen …</div>
      </div>
    );
  }

  if (listState.status === 'error') {
    return (
      <div className="doc-list-panel panel doc-list-panel--error">
        <div className="doc-list__error">
          <strong>Fehler beim Laden</strong>
          <span>{listState.error?.userMessage || 'Dokumente konnten nicht geladen werden.'}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="doc-list-panel panel" data-testid="document-list">
      <div className="panel__header doc-list-panel__header">
        <span className="panel__eyebrow">{items.length} Dokument{items.length !== 1 ? 'e' : ''}</span>
        <div className="doc-list-sort-bar">
          <span className="doc-list-sort-label">Sortierung:</span>
          {SORT_FIELDS.map(({ field }) => (
            <SortButton key={field} field={field} current={sort} onSort={onSort} />
          ))}
        </div>
      </div>

      {items.length === 0 ? (
        <EmptyState hasFilter={hasFilter} />
      ) : (
        <div className="doc-list-panel__scroll">
          <table className="data-table doc-list-table" role="grid">
            <colgroup>
              <col style={{ width: '40%' }} />
              <col style={{ width: '12%' }} />
              <col style={{ width: '14%' }} />
              <col style={{ width: '18%' }} />
              <col style={{ width: '8%' }} />
              <col style={{ width: '8%' }} />
            </colgroup>
            <thead>
              <tr>
                <th>Titel</th>
                <th>Typ</th>
                <th>Status</th>
                <th>Aktualisiert</th>
                <th>Vers.</th>
                <th>Chunks</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.id}
                  className={`doc-list-row ${selectedId === item.id ? 'doc-list-row--selected' : ''}`}
                  onClick={() => onSelect(item.id === selectedId ? null : item.id)}
                  tabIndex={0}
                  role="row"
                  aria-selected={selectedId === item.id}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') onSelect(item.id === selectedId ? null : item.id);
                  }}
                >
                  <td className="doc-list-cell--title">
                    <span className="doc-list-title" title={item.title}>
                      {item.title}
                    </span>
                  </td>
                  <td>
                    <span className="doc-mime" title={item.mimeType}>
                      {item.mimeTypeShort || item.mimeType}
                    </span>
                  </td>
                  <td>
                    <LifecycleBadge status={item.lifecycleStatus} />
                  </td>
                  <td className="doc-list-cell--date">{item.updatedAtLabel}</td>
                  <td className="doc-list-cell--num">{item.versionCount ?? '—'}</td>
                  <td className="doc-list-cell--num">{item.chunkCount ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`
        .doc-list-panel {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 0;
          overflow: hidden;
        }
        .doc-list-panel--loading,
        .doc-list-panel--error {
          justify-content: center;
          align-items: center;
        }
        .doc-list-panel__header {
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
        }
        .doc-list-sort-bar {
          display: flex;
          align-items: center;
          gap: 4px;
          flex-wrap: wrap;
        }
        .doc-list-sort-label {
          font-size: 11px;
          color: var(--color-text-secondary, #666);
          margin-right: 4px;
        }
        .sort-btn {
          font-size: 11px;
          padding: 2px 8px;
          border: 1px solid var(--color-border, #ddd);
          border-radius: 4px;
          background: transparent;
          cursor: pointer;
          color: var(--color-text, #1c1c1c);
        }
        .sort-btn--active {
          background: var(--color-accent-light, #fce4ec);
          border-color: var(--t-magenta, #E20074);
          color: var(--t-magenta, #E20074);
          font-weight: 600;
        }
        .sort-indicator { display: inline; }
        .doc-list-panel__scroll {
          overflow-y: auto;
          flex: 1;
        }
        .doc-list-table {
          width: 100%;
          border-collapse: collapse;
        }
        .doc-list-row {
          cursor: pointer;
          transition: background 0.1s;
        }
        .doc-list-row:hover {
          background: var(--color-hover, #f5f5f5);
        }
        .doc-list-row--selected {
          background: var(--color-accent-light, #fce4ec) !important;
        }
        .doc-list-cell--title { max-width: 0; }
        .doc-list-title {
          display: block;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          font-weight: 500;
        }
        .doc-list-cell--date { font-size: 12px; color: var(--color-text-secondary, #666); }
        .doc-list-cell--num { text-align: right; font-variant-numeric: tabular-nums; }
        .doc-mime { font-size: 11px; text-transform: uppercase; color: var(--color-text-secondary, #666); }
        .doc-list__empty,
        .doc-list__loading,
        .doc-list__error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 8px;
          padding: 48px 24px;
          color: var(--color-text-secondary, #666);
          font-size: 14px;
          text-align: center;
        }
        .doc-list__empty-hint { font-size: 12px; }
        .doc-list__error { color: var(--color-danger, #880e4f); }
        .badge--success { background: #e8f5e9; color: #1b5e20; border-color: #a5d6a7; }
        .badge--warning { background: #fff8e1; color: #bf360c; border-color: #ffe082; }
        .badge--danger { background: #fce4ec; color: #880e4f; border-color: #f48fb1; }
        .badge--neutral { background: #f5f5f5; color: #555; border-color: #ddd; }
      `}</style>
    </div>
  );
}
