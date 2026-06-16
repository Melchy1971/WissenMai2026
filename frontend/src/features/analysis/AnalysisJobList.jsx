import React from 'react';
import { AnalysisStatusBadge } from './AnalysisStatusBadge.jsx';

var PANEL_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  overflow: 'hidden',
  minWidth: 0,
  flex: '0 0 320px',
};

var TOOLBAR_STYLE = {
  padding: '12px 16px',
  borderBottom: '1px solid var(--color-border-subtle)',
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
  flexShrink: 0,
};

var SELECT_STYLE = {
  fontSize: '12px',
  padding: '4px 8px',
  borderRadius: 'var(--radius-sm)',
  border: '1px solid var(--color-border)',
  background: 'var(--color-bg)',
  color: 'var(--color-text)',
  flex: 1,
};

var LIST_STYLE = {
  flex: 1,
  overflowY: 'auto',
  padding: '8px 0',
};

var ITEM_BASE = {
  padding: '10px 16px',
  cursor: 'pointer',
  borderLeft: '3px solid transparent',
  borderBottom: '1px solid var(--color-border-subtle)',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
};

var EMPTY_STYLE = {
  padding: '32px 16px',
  textAlign: 'center',
  color: 'var(--color-text-tertiary)',
  fontSize: '13px',
};

var SKELETON_STYLE = {
  height: '14px',
  borderRadius: 'var(--radius-sm)',
  background: 'var(--t-gray-10)',
  margin: '4px 0',
};

function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    return new Intl.DateTimeFormat('de-DE', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(isoStr));
  } catch (_) {
    return isoStr;
  }
}

function Skeleton() {
  return (
    <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div style={Object.assign({}, SKELETON_STYLE, { width: '60%' })} />
      <div style={Object.assign({}, SKELETON_STYLE, { width: '40%' })} />
    </div>
  );
}

var STATUS_OPTIONS = [
  { value: '', label: 'Alle Status' },
  { value: 'queued', label: 'Warteschlange' },
  { value: 'running', label: 'Läuft' },
  { value: 'completed', label: 'Abgeschlossen' },
  { value: 'failed', label: 'Fehlgeschlagen' },
  { value: 'cancelled', label: 'Abgebrochen' },
];

export function AnalysisJobList({ listState, selectedId, statusFilter, onSelect, onFilterChange, onRefresh, onNew }) {
  var isLoading = listState.status === 'loading';
  var isError = listState.status === 'error';
  var items = listState.items || [];

  function handleFilterChange(e) {
    onFilterChange(e.target.value || null);
  }

  return (
    <div style={PANEL_STYLE} data-testid="analysis-job-list">
      <div style={TOOLBAR_STYLE}>
        <select
          style={SELECT_STYLE}
          value={statusFilter || ''}
          onChange={handleFilterChange}
          aria-label="Status filtern"
        >
          {STATUS_OPTIONS.map(function(o) {
            return <option key={o.value} value={o.value}>{o.label}</option>;
          })}
        </select>
        <button
          onClick={onRefresh}
          style={{
            background: 'none',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-sm)',
            padding: '4px 8px',
            cursor: 'pointer',
            fontSize: '12px',
            color: 'var(--color-text-secondary)',
          }}
          aria-label="Aktualisieren"
          title="Aktualisieren"
        >
          ↻
        </button>
        {onNew && (
          <button
            onClick={onNew}
            style={{
              background: 'var(--color-accent)',
              color: '#fff',
              border: 'none',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 10px',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 600,
            }}
            data-testid="new-analysis-btn"
          >
            + Neu
          </button>
        )}
      </div>

      <div style={LIST_STYLE} role="list" aria-label="Analyse-Jobs">
        {isLoading && items.length === 0 && (
          [0,1,2,3].map(function(i) { return <Skeleton key={i} />; })
        )}

        {isError && (
          <div style={EMPTY_STYLE} data-testid="list-error">
            <div style={{ color: 'var(--color-danger-fg)', marginBottom: '4px' }}>Fehler beim Laden</div>
            <div>{(listState.error && listState.error.userMessage) || 'Unbekannter Fehler.'}</div>
          </div>
        )}

        {!isLoading && !isError && items.length === 0 && (
          <div style={EMPTY_STYLE} data-testid="list-empty">
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>🔬</div>
            <div>Keine Analyse-Jobs vorhanden.</div>
            {onNew && (
              <button
                onClick={onNew}
                style={{
                  marginTop: '12px',
                  background: 'var(--color-accent)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: 'var(--radius-md)',
                  padding: '8px 16px',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 600,
                }}
              >
                Erste Analyse starten
              </button>
            )}
          </div>
        )}

        {items.map(function(job) {
          var isSelected = job.id === selectedId;
          return (
            <div
              key={job.id}
              role="listitem"
              onClick={function() { onSelect(job.id); }}
              style={Object.assign({}, ITEM_BASE, {
                borderLeftColor: isSelected ? 'var(--color-accent)' : 'transparent',
                background: isSelected ? 'var(--t-magenta-10)' : 'transparent',
              })}
              data-testid={'job-item-' + job.id}
              aria-current={isSelected ? 'true' : undefined}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {job.analysisType || 'Analyse'}
                </span>
                <AnalysisStatusBadge status={job.status} />
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {job.prompt}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)' }}>
                {formatDate(job.createdAt)}
                {job.provider ? (' · ' + job.provider) : ''}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
