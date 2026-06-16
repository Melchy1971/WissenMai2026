import React from 'react';
import { AnalysisStatusBadge } from './AnalysisStatusBadge.jsx';
import { AnalysisResultPanel } from './AnalysisResultPanel.jsx';

var PANEL_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0',
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  overflow: 'hidden',
  flex: 2,
  minWidth: 0,
};

var HEADER_STYLE = {
  padding: '14px 18px',
  borderBottom: '1px solid var(--color-border-subtle)',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  flexShrink: 0,
};

var BODY_STYLE = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  gap: '0',
  overflowY: 'auto',
  padding: '16px',
  minHeight: 0,
};

var META_ROW_STYLE = {
  display: 'flex',
  gap: '24px',
  flexWrap: 'wrap',
  padding: '0 0 14px',
  borderBottom: '1px solid var(--color-border-subtle)',
  marginBottom: '14px',
};

var META_ITEM_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: '2px',
};

var META_LABEL_STYLE = {
  fontSize: '10px',
  fontWeight: 600,
  color: 'var(--color-text-tertiary)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
};

var META_VALUE_STYLE = {
  fontSize: '12px',
  color: 'var(--color-text)',
};

var BTN_BASE = {
  border: 'none',
  borderRadius: 'var(--radius-md)',
  padding: '6px 12px',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer',
};

var SKELETON_STYLE = {
  background: 'var(--t-gray-10)',
  borderRadius: 'var(--radius-sm)',
  margin: '4px 0',
};

function MetaItem({ label, value }) {
  return (
    <div style={META_ITEM_STYLE}>
      <span style={META_LABEL_STYLE}>{label}</span>
      <span style={META_VALUE_STYLE}>{value || '—'}</span>
    </div>
  );
}

function formatDate(isoStr) {
  if (!isoStr) return null;
  try { return new Intl.DateTimeFormat('de-DE', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(isoStr)); }
  catch (_) { return isoStr; }
}

function SkeletonBlock({ width, height }) {
  return <div style={Object.assign({}, SKELETON_STYLE, { width: width || '60%', height: height || '14px' })} />;
}

export function AnalysisJobDetail({ detailState, actionState, onCancel, onRetry, onMarkForReview, onApprove, onReject, onImport }) {
  if (detailState.status === 'idle') {
    return (
      <div style={Object.assign({}, PANEL_STYLE, { alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)', fontSize: '13px' })}
        data-testid="detail-idle">
        <div style={{ fontSize: '32px', marginBottom: '8px' }}>🔍</div>
        <div>Job aus der Liste wählen</div>
      </div>
    );
  }

  if (detailState.status === 'loading') {
    return (
      <div style={PANEL_STYLE} data-testid="detail-loading">
        <div style={HEADER_STYLE}>
          <SkeletonBlock width="40%" height="18px" />
          <SkeletonBlock width="60px" height="18px" />
        </div>
        <div style={BODY_STYLE}>
          <div style={META_ROW_STYLE}>
            {[0,1,2,3].map(function(i) {
              return (
                <div key={i} style={META_ITEM_STYLE}>
                  <SkeletonBlock width="60px" height="10px" />
                  <SkeletonBlock width="80px" height="14px" />
                </div>
              );
            })}
          </div>
          <SkeletonBlock width="100%" height="80px" />
        </div>
      </div>
    );
  }

  if (detailState.status === 'error') {
    return (
      <div style={Object.assign({}, PANEL_STYLE, { alignItems: 'center', justifyContent: 'center', color: 'var(--color-danger-fg)', fontSize: '13px', padding: '32px' })}
        data-testid="detail-error">
        {(detailState.error && detailState.error.userMessage) || 'Fehler beim Laden.'}
      </div>
    );
  }

  var job = detailState.data;
  if (!job) return null;

  var isBusy = actionState && actionState.status === 'loading';
  var canCancel = ['queued', 'pending', 'running'].includes(job.status);
  var canRetry  = ['failed', 'cancelled'].includes(job.status);

  return (
    <div style={PANEL_STYLE} data-testid="analysis-job-detail">
      <div style={HEADER_STYLE}>
        <span style={{ fontWeight: 700, fontSize: '14px', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {job.analysisType || 'Analyse'}
        </span>
        <AnalysisStatusBadge status={job.status} />
        <div style={{ display: 'flex', gap: '6px' }}>
          {canCancel && (
            <button
              onClick={function() { onCancel(job.id); }}
              disabled={isBusy}
              data-testid="btn-cancel-job"
              style={Object.assign({}, BTN_BASE, { background: 'var(--color-neutral-bg)', color: 'var(--color-neutral-fg)', opacity: isBusy ? 0.5 : 1 })}
            >
              Abbrechen
            </button>
          )}
          {canRetry && (
            <button
              onClick={function() { onRetry(job.id); }}
              disabled={isBusy}
              data-testid="btn-retry-job"
              style={Object.assign({}, BTN_BASE, { background: 'var(--t-magenta-10)', color: 'var(--t-magenta)', opacity: isBusy ? 0.5 : 1 })}
            >
              Erneut versuchen
            </button>
          )}
        </div>
      </div>

      <div style={BODY_STYLE}>
        {/* Metadata */}
        <div style={META_ROW_STYLE}>
          <MetaItem label="Typ" value={job.analysisType} />
          <MetaItem label="Provider" value={job.provider ? (job.provider + (job.model ? ' / ' + job.model : '')) : null} />
          <MetaItem label="Quelle" value={job.sourceType} />
          <MetaItem label="Gestartet" value={formatDate(job.startedAt)} />
          <MetaItem label="Abgeschlossen" value={formatDate(job.finishedAt)} />
          <MetaItem label="Dokumente" value={job.sourceDocumentIds.length > 0 ? job.sourceDocumentIds.length + ' Dok.' : null} />
        </div>

        {/* Prompt */}
        <div style={{ marginBottom: '16px' }}>
          <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--color-text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
            Prompt
          </div>
          <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: '1.5', background: 'var(--color-bg)', padding: '8px 10px', borderRadius: 'var(--radius-md)' }}>
            {job.prompt}
          </div>
        </div>

        {/* Error block */}
        {job.status === 'failed' && job.errorMessage && (
          <div style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger-fg)', padding: '10px 12px', borderRadius: 'var(--radius-md)', fontSize: '12px', marginBottom: '16px' }}
            data-testid="job-error-block">
            <strong>{job.errorCode || 'Fehler'}:</strong> {job.errorMessage}
          </div>
        )}

        {/* Action error */}
        {actionState && actionState.status === 'error' && (
          <div style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger-fg)', padding: '8px 12px', borderRadius: 'var(--radius-md)', fontSize: '12px', marginBottom: '12px' }}>
            {(actionState.error && actionState.error.userMessage) || 'Aktion fehlgeschlagen.'}
          </div>
        )}

        {/* Result panel */}
        {job.status === 'completed' && (
          <AnalysisResultPanel
            result={job.result}
            actionState={actionState}
            onMarkForReview={onMarkForReview}
            onApprove={onApprove}
            onReject={onReject}
            onImport={onImport}
          />
        )}
      </div>
    </div>
  );
}
