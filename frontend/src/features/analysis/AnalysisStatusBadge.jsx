import React from 'react';

var STATUS_META = {
  queued:    { label: 'Warteschlange', bg: 'var(--color-neutral-bg)',  fg: 'var(--color-neutral-fg)' },
  pending:   { label: 'Ausstehend',   bg: 'var(--color-neutral-bg)',  fg: 'var(--color-neutral-fg)' },
  running:   { label: 'Läuft',        bg: 'var(--color-info-bg)',     fg: 'var(--color-info-fg)' },
  completed: { label: 'Abgeschlossen',bg: 'var(--color-success-bg)',  fg: 'var(--color-success-fg)' },
  failed:    { label: 'Fehlgeschlagen',bg:'var(--color-danger-bg)',   fg: 'var(--color-danger-fg)' },
  cancelled: { label: 'Abgebrochen',  bg: 'var(--color-neutral-bg)',  fg: 'var(--color-neutral-fg)' },
  approved:  { label: 'Genehmigt',    bg: 'var(--color-success-bg)',  fg: 'var(--color-success-fg)' },
};

var RESULT_STATUS_META = {
  draft:    { label: 'Entwurf',     bg: 'var(--color-neutral-bg)', fg: 'var(--color-neutral-fg)' },
  review:   { label: 'Prüfung',     bg: 'var(--color-warning-bg)', fg: 'var(--color-warning-fg)' },
  approved: { label: 'Genehmigt',   bg: 'var(--color-success-bg)', fg: 'var(--color-success-fg)' },
  rejected: { label: 'Abgelehnt',   bg: 'var(--color-danger-bg)',  fg: 'var(--color-danger-fg)' },
};

export function AnalysisStatusBadge({ status, variant }) {
  var meta = variant === 'result'
    ? (RESULT_STATUS_META[status] || { label: status, bg: 'var(--color-neutral-bg)', fg: 'var(--color-neutral-fg)' })
    : (STATUS_META[status] || { label: status, bg: 'var(--color-neutral-bg)', fg: 'var(--color-neutral-fg)' });

  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 'var(--radius-pill)',
      fontSize: '11px',
      fontWeight: 600,
      lineHeight: '18px',
      background: meta.bg,
      color: meta.fg,
      whiteSpace: 'nowrap',
    }}>
      {meta.label}
    </span>
  );
}
