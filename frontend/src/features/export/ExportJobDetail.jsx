import React from 'react';

var PANEL_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  flex: 1,
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  overflow: 'hidden',
  minWidth: 0,
};

var HEADER_STYLE = {
  padding: '14px 20px',
  borderBottom: '1px solid var(--color-border-subtle)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  flexShrink: 0,
};

var BODY_STYLE = {
  flex: 1,
  overflowY: 'auto',
  padding: '20px',
};

var SECTION_STYLE = {
  marginBottom: '20px',
};

var LABEL_STYLE = {
  fontSize: '11px',
  fontWeight: 600,
  color: 'var(--color-text-tertiary)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  marginBottom: '4px',
};

var VALUE_STYLE = {
  fontSize: '13px',
  color: 'var(--color-text)',
};

var ACTIONS_STYLE = {
  display: 'flex',
  gap: '8px',
  flexWrap: 'wrap',
  padding: '14px 20px',
  borderTop: '1px solid var(--color-border-subtle)',
  flexShrink: 0,
};

var BTN_PRIMARY_STYLE = {
  border: 'none',
  borderRadius: 'var(--radius-sm)',
  padding: '7px 14px',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer',
  background: 'var(--t-magenta)',
  color: '#fff',
};

var BTN_SECONDARY_STYLE = {
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-sm)',
  padding: '7px 14px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer',
  background: 'transparent',
  color: 'var(--color-text)',
};

var BTN_DANGER_STYLE = {
  border: '1px solid #fca5a5',
  borderRadius: 'var(--radius-sm)',
  padding: '7px 14px',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer',
  background: 'transparent',
  color: '#b91c1c',
};

var STATUS_COLORS = {
  QUEUED:    { bg: 'var(--t-gray-5)',  text: 'var(--color-text-secondary)' },
  RUNNING:   { bg: '#dbeafe',          text: '#1d4ed8' },
  COMPLETED: { bg: '#dcfce7',          text: '#15803d' },
  FAILED:    { bg: '#fee2e2',          text: '#b91c1c' },
  CANCELLED: { bg: 'var(--t-gray-5)', text: 'var(--color-text-tertiary)' },
};

var FORMAT_LABELS   = { MARKDOWN: 'Markdown', JSON: 'JSON', PDF: 'PDF' };
var SOURCE_LABELS   = {
  SEARCH_RESULT: 'Suchergebnis',
  ANALYSIS_RESULT: 'Analyseergebnis',
  TOPIC: 'Thema',
  DOCUMENT_COLLECTION: 'Dokumentensammlung',
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
      fontSize: '11px',
      fontWeight: 700,
      padding: '2px 10px',
      borderRadius: '9999px',
      background: colors.bg,
      color: colors.text,
    }}>
      {status}
    </span>
  );
}

function Field({ label, children }) {
  return (
    <div style={SECTION_STYLE}>
      <div style={LABEL_STYLE}>{label}</div>
      <div style={VALUE_STYLE}>{children}</div>
    </div>
  );
}

function IdleState() {
  return (
    <div style={{ padding: '48px 24px', textAlign: 'center', color: 'var(--color-text-tertiary)', fontSize: '13px' }}>
      Export auswählen, um Details anzuzeigen.
    </div>
  );
}

function LoadingState() {
  var skel = {
    height: '14px',
    borderRadius: 'var(--radius-sm)',
    background: 'var(--t-gray-10)',
    marginBottom: '10px',
  };
  return (
    <div style={{ padding: '20px' }}>
      <div style={Object.assign({}, skel, { width: '50%', marginBottom: '20px' })} />
      <div style={Object.assign({}, skel, { width: '80%' })} />
      <div style={Object.assign({}, skel, { width: '60%' })} />
      <div style={Object.assign({}, skel, { width: '70%' })} />
    </div>
  );
}

export function ExportJobDetail({
  detailState,
  actionState,
  onStart,
  onCancel,
  onRetry,
  onDownload,
  onDeleteFile,
}) {
  var isActionLoading = actionState && actionState.status === 'loading';

  if (detailState.status === 'idle') {
    return (
      <div style={PANEL_STYLE} data-testid="export-job-detail">
        <IdleState />
      </div>
    );
  }

  if (detailState.status === 'loading') {
    return (
      <div style={PANEL_STYLE} data-testid="export-job-detail">
        <LoadingState />
      </div>
    );
  }

  if (detailState.status === 'error') {
    return (
      <div style={PANEL_STYLE} data-testid="export-job-detail">
        <div style={{ padding: '32px', textAlign: 'center', color: '#b91c1c', fontSize: '13px' }}>
          {detailState.error && detailState.error.userMessage
            ? detailState.error.userMessage
            : 'Fehler beim Laden des Export-Jobs.'}
        </div>
      </div>
    );
  }

  var job = detailState.data;
  if (!job) return null;

  var canStart    = job.status === 'QUEUED';
  var canCancel   = job.status === 'QUEUED' || job.status === 'RUNNING';
  var canRetry    = job.status === 'FAILED' || job.status === 'CANCELLED';
  var canDownload = job.status === 'COMPLETED' && !!job.filePath;
  var canDeleteFile = true;

  return (
    <div style={PANEL_STYLE} data-testid="export-job-detail">
      <div style={HEADER_STYLE}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
          <span style={{
            fontSize: '14px',
            fontWeight: 700,
            color: 'var(--color-text)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {job.fileName}
          </span>
        </div>
        <StatusBadge status={job.status} />
      </div>

      <div style={BODY_STYLE}>
        {actionState && actionState.status === 'error' && actionState.error && (
          <div style={{
            marginBottom: '16px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-sm)',
            background: '#fee2e2',
            color: '#b91c1c',
            fontSize: '13px',
          }}>
            {actionState.error.userMessage || 'Aktion fehlgeschlagen.'}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px' }}>
          <Field label="Format">{FORMAT_LABELS[job.exportFormat] || job.exportFormat || '—'}</Field>
          <Field label="Quelle">{SOURCE_LABELS[job.sourceType] || job.sourceType || '—'}</Field>
          <Field label="Erstellt am">{formatDate(job.createdAt)}</Field>
          <Field label="Gestartet">{formatDate(job.startedAt)}</Field>
          <Field label="Abgeschlossen">{formatDate(job.finishedAt)}</Field>
          <Field label="Erstellt von">{job.createdBy ? '••••' : '—'}</Field>
        </div>

        {job.filePath && (
          <Field label="Datei">
            <span style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--color-text-secondary)' }}>
              {job.fileName}
            </span>
          </Field>
        )}

        {job.errorMessage && (
          <div style={{
            marginTop: '8px',
            padding: '12px 14px',
            borderRadius: 'var(--radius-sm)',
            background: '#fee2e2',
            border: '1px solid #fca5a5',
          }}>
            <div style={LABEL_STYLE}>Fehlermeldung</div>
            <div style={{ fontSize: '12px', color: '#b91c1c', fontFamily: 'monospace', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {job.errorMessage}
            </div>
          </div>
        )}
      </div>

      <div style={ACTIONS_STYLE}>
        {canDownload && (
          <button
            style={BTN_PRIMARY_STYLE}
            disabled={isActionLoading}
            onClick={function() { onDownload && onDownload(job.id); }}
            data-testid="btn-download"
          >
            ↓ Herunterladen
          </button>
        )}
        {canStart && (
          <button
            style={BTN_SECONDARY_STYLE}
            disabled={isActionLoading}
            onClick={function() { onStart && onStart(job.id); }}
            data-testid="btn-start"
          >
            ▶ Starten
          </button>
        )}
        {canRetry && (
          <button
            style={BTN_SECONDARY_STYLE}
            disabled={isActionLoading}
            onClick={function() { onRetry && onRetry(job.id); }}
            data-testid="btn-retry"
          >
            ↺ Erneut versuchen
          </button>
        )}
        {canCancel && (
          <button
            style={BTN_DANGER_STYLE}
            disabled={isActionLoading}
            onClick={function() { onCancel && onCancel(job.id); }}
            data-testid="btn-cancel"
          >
            ✕ Abbrechen
          </button>
        )}
        {canDeleteFile && job.filePath && (
          <button
            style={BTN_DANGER_STYLE}
            disabled={isActionLoading}
            onClick={function() { onDeleteFile && onDeleteFile(job.id); }}
            data-testid="btn-delete-file"
          >
            🗑 Datei löschen
          </button>
        )}
        {isActionLoading && (
          <span style={{ fontSize: '12px', color: 'var(--color-text-tertiary)', alignSelf: 'center' }}>
            Wird verarbeitet…
          </span>
        )}
      </div>
    </div>
  );
}
