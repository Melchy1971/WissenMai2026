import React, { useState } from 'react';
import { AnalysisStatusBadge } from './AnalysisStatusBadge.jsx';

var PANEL_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
  padding: '16px',
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',
  overflow: 'hidden',
  minWidth: 0,
  flex: 1,
};

var SECTION_STYLE = {
  borderBottom: '1px solid var(--color-border-subtle)',
  paddingBottom: '12px',
};

var LABEL_STYLE = {
  fontSize: '11px',
  fontWeight: 600,
  color: 'var(--color-text-tertiary)',
  textTransform: 'uppercase',
  letterSpacing: '0.04em',
  marginBottom: '6px',
};

var TAG_STYLE = {
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: 'var(--radius-pill)',
  fontSize: '11px',
  background: 'var(--t-magenta-10)',
  color: 'var(--t-magenta)',
  margin: '2px',
  fontWeight: 500,
};

var BTN_BASE = {
  border: 'none',
  borderRadius: 'var(--radius-md)',
  padding: '7px 14px',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer',
};

function ConfirmDialog({ title, message, onConfirm, onCancel, children }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000,
    }}
      role="dialog" aria-modal="true" aria-label={title}
    >
      <div style={{
        background: 'var(--color-surface)',
        borderRadius: 'var(--radius-xl)',
        padding: '24px',
        width: '360px',
        boxShadow: 'var(--shadow-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}>
        <div style={{ fontWeight: 700, fontSize: '16px' }}>{title}</div>
        <div style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>{message}</div>
        {children}
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={Object.assign({}, BTN_BASE, { background: 'var(--t-gray-10)', color: 'var(--color-text)' })}>
            Abbrechen
          </button>
          <button onClick={onConfirm} data-testid="confirm-btn" style={Object.assign({}, BTN_BASE, { background: 'var(--color-accent)', color: '#fff' })}>
            Bestätigen
          </button>
        </div>
      </div>
    </div>
  );
}

// IMPORT GUARD CONTRACT (enforced here, wired in Task #81):
// onImport is only callable when result.status === 'approved'.
// The button is not rendered for any other status. No override possible.
export function AnalysisResultPanel({ result, actionState, onMarkForReview, onApprove, onReject, onImport }) {
  var [dialog, setDialog] = useState(null); // null | 'approve' | 'reject'
  var [rejectReason, setRejectReason] = useState('');
  var [approveNote, setApproveNote] = useState('');

  if (!result) {
    return (
      <div style={Object.assign({}, PANEL_STYLE, { alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-tertiary)', fontSize: '13px' })}
        data-testid="result-empty">
        Kein Ergebnis vorhanden.
      </div>
    );
  }

  var isBusy = actionState && actionState.status === 'loading';

  function openApprove() { setApproveNote(''); setDialog('approve'); }
  function openReject()  { setRejectReason(''); setDialog('reject'); }
  function closeDialog() { setDialog(null); }

  function submitApprove() {
    onApprove(result.id, approveNote);
    closeDialog();
  }
  function submitReject() {
    if (!rejectReason.trim()) return;
    onReject(result.id, rejectReason.trim());
    closeDialog();
  }

  return (
    <div style={PANEL_STYLE} data-testid="analysis-result-panel">
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: '15px', color: 'var(--color-text)' }}>
            {result.title || 'Analyseergebnis'}
          </div>
          {result.updatedAt && (
            <div style={{ fontSize: '11px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
              Aktualisiert: {new Date(result.updatedAt).toLocaleString('de-DE')}
            </div>
          )}
        </div>
        <AnalysisStatusBadge status={result.status} variant="result" />
        {result.confidence != null && (
          <span style={{ fontSize: '11px', color: 'var(--color-text-secondary)' }}>
            {Math.round(result.confidence * 100)} % Konfidenz
          </span>
        )}
      </div>

      {/* Action bar */}
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', flexShrink: 0 }}>
        {result.status === 'draft' && (
          <button
            onClick={function() { onMarkForReview(result.id); }}
            disabled={isBusy}
            data-testid="btn-review"
            style={Object.assign({}, BTN_BASE, {
              background: 'var(--color-info-bg)',
              color: 'var(--color-info-fg)',
              opacity: isBusy ? 0.5 : 1,
            })}
          >
            Zur Prüfung einreichen
          </button>
        )}
        {result.status === 'review' && (
          <>
            <button
              onClick={openApprove}
              disabled={isBusy}
              data-testid="btn-approve"
              style={Object.assign({}, BTN_BASE, {
                background: 'var(--color-success-bg)',
                color: 'var(--color-success-fg)',
                opacity: isBusy ? 0.5 : 1,
              })}
            >
              Genehmigen
            </button>
            <button
              onClick={openReject}
              disabled={isBusy}
              data-testid="btn-reject"
              style={Object.assign({}, BTN_BASE, {
                background: 'var(--color-danger-bg)',
                color: 'var(--color-danger-fg)',
                opacity: isBusy ? 0.5 : 1,
              })}
            >
              Ablehnen
            </button>
          </>
        )}
        {/* IMPORT GUARD: button only rendered when status === 'approved' */}
        {result.status === 'approved' && onImport && (
          <button
            onClick={function() { onImport(result.id); }}
            disabled={isBusy}
            data-testid="btn-import"
            style={Object.assign({}, BTN_BASE, {
              background: 'var(--t-magenta)',
              color: '#fff',
              opacity: isBusy ? 0.5 : 1,
            })}
          >
            In Wissensbasis importieren
          </button>
        )}
        {result.status !== 'approved' && result.status !== 'draft' && result.status !== 'review' && (
          <span style={{ fontSize: '12px', color: 'var(--color-text-tertiary)', alignSelf: 'center' }}
            data-testid="import-blocked-hint">
            Import nur nach Genehmigung möglich.
          </span>
        )}
        {actionState && actionState.status === 'error' && (
          <span style={{ fontSize: '12px', color: 'var(--color-danger-fg)', alignSelf: 'center' }}>
            {(actionState.error && actionState.error.userMessage) || 'Fehler beim Speichern.'}
          </span>
        )}
      </div>

      {/* Summary */}
      <div style={SECTION_STYLE}>
        <div style={LABEL_STYLE}>Zusammenfassung</div>
        <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-text)', lineHeight: '1.6' }}>
          {result.summary || '—'}
        </p>
      </div>

      {/* Key points */}
      {result.keyPoints && result.keyPoints.length > 0 && (
        <div style={SECTION_STYLE}>
          <div style={LABEL_STYLE}>Kernpunkte</div>
          <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '13px', color: 'var(--color-text)', lineHeight: '1.8' }}>
            {result.keyPoints.map(function(p, i) { return <li key={i}>{p}</li>; })}
          </ul>
        </div>
      )}

      {/* Content markdown */}
      {result.contentMarkdown && (
        <div style={SECTION_STYLE}>
          <div style={LABEL_STYLE}>Vollständige Analyse</div>
          <pre style={{
            margin: 0,
            fontSize: '12px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            color: 'var(--color-text-secondary)',
            background: 'var(--color-bg)',
            padding: '10px',
            borderRadius: 'var(--radius-md)',
            maxHeight: '240px',
            overflow: 'auto',
          }}>
            {result.contentMarkdown}
          </pre>
        </div>
      )}

      {/* Tags & Topics */}
      {(result.suggestedTags.length > 0 || result.suggestedTopics.length > 0) && (
        <div style={SECTION_STYLE}>
          {result.suggestedTags.length > 0 && (
            <>
              <div style={LABEL_STYLE}>Vorgeschlagene Tags</div>
              <div style={{ marginBottom: '8px' }}>
                {result.suggestedTags.map(function(t) { return <span key={t} style={TAG_STYLE}>{t}</span>; })}
              </div>
            </>
          )}
          {result.suggestedTopics.length > 0 && (
            <>
              <div style={LABEL_STYLE}>Vorgeschlagene Themen</div>
              <div>
                {result.suggestedTopics.map(function(t) {
                  return <span key={t} style={Object.assign({}, TAG_STYLE, { background: 'var(--color-info-bg)', color: 'var(--color-info-fg)' })}>{t}</span>;
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* Approval metadata */}
      {result.status === 'approved' && result.approvedAt && (
        <div style={{ fontSize: '12px', color: 'var(--color-success-fg)', background: 'var(--color-success-bg)', padding: '8px 12px', borderRadius: 'var(--radius-md)' }}>
          Genehmigt am {new Date(result.approvedAt).toLocaleString('de-DE')}
        </div>
      )}

      {/* Dialogs */}
      {dialog === 'approve' && (
        <ConfirmDialog
          title="Ergebnis genehmigen"
          message="Das Ergebnis wird als genehmigt markiert. Diese Aktion kann nicht rückgängig gemacht werden."
          onConfirm={submitApprove}
          onCancel={closeDialog}
        >
         
          <textarea
            placeholder="Anmerkung (optional)"
            value={approveNote}
            onChange={function(e) { setApproveNote(e.target.value); }}
            style={{ width: '100%', height: '64px', fontSize: '13px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', padding: '6px', resize: 'vertical' }}
          />
        </ConfirmDialog>
      )}

      {dialog === 'reject' && (
        <ConfirmDialog
          title="Ergebnis ablehnen"
          message="Bitte gib einen Ablehnungsgrund an."
          onConfirm={submitReject}
          onCancel={closeDialog}
        >
          <textarea
            placeholder="Ablehnungsgrund *"
            value={rejectReason}
            onChange={function(e) { setRejectReason(e.target.value); }}
            style={{ width: '100%', height: '64px', fontSize: '13px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', padding: '6px', resize: 'vertical' }}
            data-testid="reject-reason-input"
          />
        </ConfirmDialog>
      )}
    </div>
  );
}
