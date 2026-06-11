export function DataClassificationBadge({ classification }) {
  const map = {
    PUBLIC:             { label: 'PUBLIC',            bg: 'var(--color-info-bg)',    fg: 'var(--color-info-fg)' },
    INTERNAL:           { label: 'INTERN',            bg: 'var(--color-neutral-bg)', fg: 'var(--color-neutral-fg)' },
    CONFIDENTIAL:       { label: 'VERTRAULICH',       bg: 'var(--color-warning-bg)', fg: 'var(--color-warning-fg)' },
    SENSITIVE_PERSONAL: { label: '⚠ PERS. DATEN',    bg: 'var(--color-warning-bg)', fg: 'var(--color-warning-fg)' },
    SECRET:             { label: '🔒 GESPERRT',       bg: 'var(--color-danger-bg)',  fg: 'var(--color-danger-fg)', fontWeight: '700' },
  };
  const cfg = map[classification] || map.INTERNAL;
  return (
    <span style={{ background: cfg.bg, color: cfg.fg, fontWeight: cfg.fontWeight || '500',
                   padding: '2px 8px', borderRadius: 'var(--radius-pill)', fontSize: '0.75rem' }}>
      {cfg.label}
    </span>
  );
}
