import React from 'react';

var PANEL_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  overflow: 'hidden',
  minWidth: 0,
  flex: '0 0 340px',
};

var TOOLBAR_STYLE = {
  padding: '10px 14px',
  borderBottom: '1px solid var(--color-border-subtle)',
  display: 'flex',
  gap: '6px',
  alignItems: 'center',
  flexShrink: 0,
  flexWrap: 'wrap',
};

var SELECT_STYLE = {
  fontSize: '12px',
  padding: '4px 8px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--color-border)',
  background: 'var(--color-bg)',
  color: 'var(--color-text)',
  flex: 1,
  minWidth: '90px',
};

var LIST_STYLE = {
  flex: 1,
  overflowY: 'auto',
  padding: '6px 0',
};

var ITEM_BASE = {
  padding: '10px 14px',
  cursor: 'pointer',
  borderLeft: '3px solid transparent',
  borderBottom: '1px solid var(--color-border-subtle)',
  display: 'flex',
  flexDirection: 'column',
  gap: '3px',
};

var EMPTY_STYLE = {
  padding: '32px 16px',
  textAlign: 'center',
  color: 'var(--color-text-tertiary)',
  fontSize: '13px',
};

var SKELETON_STYLE = {
  height: '12px',
  borderRadius: 'var(--radius-sm)',
  background: 'var(--t-gray-10)',
  margin: '3px 0',
};

var FOOTER_STYLE = {
  padding: '8px 14px',
  borderTop: '1px solid var(--color-border-subtle)',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  fontSize: '12px',
  color: 'var(--color-text-tertiary)',
  flexShrink: 0,
};

var BTN_GHOST_STYLE = {
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: '3px 8px',
  fontSize: '12px',
  cursor: 'pointer',
  background: 'transparent',
  color: 'var(--color-text-secondary)',
};

var STATUS_COLORS = {
  QUEUED:    { bg: 'var(--t-gray-5)',      text: 'var(--color-text-secondary)' },
  RUNNING:   { bg: '#dbeafe',              text: '#1d4ed8' },
  COMPLETED: { bg: '#dcfce7',              text: '#15803d' },
  FAILED:    { bg: '#fee2e2',              text: '#b91c1c' },
  CANCELLED: { bg: 'var(--t-gray-5)',      text: 'var(--color-text-tertiary)' },
};

var FORMAT_LABELS = { MARKDOWN: 'MD', JSON: 'JSON', PDF: 'PDF' };
var SOURCE_LABELS = {
  SEARCH_RESULT: 'Suche',
  ANALYSIS_RESULT: 'Analyse',
  TOPIC: 'Thema',
  DOCUMENT_COLLECTION: 'Dokumente',
};

function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Intl.DateTimeFormat('de-DE', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(isoStr));
  } catch (_) {
    return isoStr;
  }
}

function StatusBadge({ status }) {
  var colors = STATUS_COLORS[status] || STATUS_COLORS.QUEUED;
  return (
    <span style={{
      display: 'inline-block',
      fontSize: '10px',
      fontWeight: 600,
      padding: '1px 6px',
      borderRadius: '9999px',
      background: colors.bg,
      color: colors.text,
    }}>
      {status}
    </span>
  );
}

function Skeleton() {
  return (
    <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div style={Object.assign({}, SKELETON_STYLE, { width: '70%' })} />
      <div style={Object.assign({}, SKELETON_STYLE, { width: '45%' })} />
    </div>
  );
}

export function ExportJobList({
  listState,
  selectedId,
  statusFilter,
  formatFilter,
  page,
  limit,
  onSelect,
  onRefresh,
  onStatusFilterChange,
  onFormatFilterChange,
  onPageChange,
}) {
  var items  = listState.items || [];
  var total  = listState.total || 0;
  var totalPages = Math.max(1, Math.ceil(total / (limit || 20)));

  return (
    <div style={PANEL_STYLE} data-testid="export-job-list">
      <div style={TOOLBAR_STYLE}>
        <select
          style={SELECT_STYLE}
          value={statusFilter || ''}
          onChange={function(e) { onStatusFilterChange && onStatusFilterChange(e.target.value || null); }}
          aria-label="Status-Filter"
        >
          <option value="">Alle Status</option>
          <option value="QUEUED">Warteschlange</option>
          <option value="RUNNING">Läuft</option>
          <option value="COMPLETED">Abgeschlossen</option>
          <option value="FAILED">Fehlgeschlagen</option>
          <option value="CANCELLED">Abgebrochen</option>
        </select>
        <select
          style={SELECT_STYLE}
          value={formatFilter || ''}
          onChange={function(e) { onFormatFilterChange && onFormatFilterChange(e.target.value || null); }}
          aria-label="Format-Filter"
        >
          <option value="">Alle Formate</option>
          <option value="MARKDOWN">Markdown</option>
          <option value="JSON">JSON</option>
          <option value="PDF">PDF</option>
        </select>
        <button
          style={BTN_GHOST_STYLE}
          onClick={onRefresh}
          title="Aktualisieren"
          data-testid="btn-refresh-jobs"
        >
          ↺
        </button>
      </div>

      <div style={LIST_STYLE}>
        {listState.status === 'loading' && (
          <>{[0,1,2,3].map(function(i) { return <Skeleton key={i} />; })}</>
        )}

        {listState.status === 'error' && (
          <div style={Object.assign({}, EMPTY_STYLE, { color: '#b91c1c' })}>
            {listState.error && listState.error.userMessage
              ? listState.error.userMessage
              : 'Fehler beim Laden der Exporte.'}
          </div>
        )}

        {listState.status === 'success' && items.length === 0 && (
          <div style={EMPTY_STYLE}>
            Keine Exporte gefunden.
          </div>
        )}

        {listState.status === 'success' && items.map(function(job) {
          var isSelected = job.id === selectedId;
          return (
            <div
              key={job.id}
              style={Object.assign({}, ITEM_BASE, {
                borderLeft: isSelected ? '3px solid var(--t-magenta)' : '3px solid transparent',
                background: isSelected ? 'var(--color-surface-hover)' : 'transparent',
              })}
              onClick={function() { onSelect && onSelect(job.id); }}
              data-testid={'job-item-' + job.id}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {job.fileName || '—'}
                </span>
                <span style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: '3px',
                  background: 'var(--t-gray-5)',
                  color: 'var(--color-text-secondary)',
                  flexShrink: 0,
                }}>
                  {FORMAT_LABELS[job.exportFormat] || job.exportFormat}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <StatusBadge status={job.status} />
                <span style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                  {SOURCE_LABELS[job.sourceType] || job.sourceType}
                </span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                {formatDate(job.createdAt)}
              </div>
            </div>
          );
        })}
      </div>

      <div style={FOOTER_STYLE}>
        <span>{total} Export{total !== 1 ? 'e' : ''}</span>
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          <button
            style={BTN_GHOST_STYLE}
            disabled={page <= 0}
            onClick={function() { onPageChange && onPageChange(page - 1); }}
            aria-label="Vorherige Seite"
          >
            ‹
          </button>
          <span>{page + 1} / {totalPages}</span>
          <button
            style={BTN_GHOST_STYLE}
            disabled={page >= totalPages - 1}
            onClick={function() { onPageChange && onPageChange(page + 1); }}
            aria-label="Nächste Seite"
          >
            ›
          </button>
        </div>
      </div>
    </div>
  );
}
