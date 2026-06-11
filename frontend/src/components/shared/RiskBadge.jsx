export function RiskBadge({ level, testId }) {
  const map = {
    LOW: { bg: 'var(--color-success-bg)', fg: 'var(--color-success-fg)' },
    MEDIUM: { bg: 'var(--color-warning-bg)', fg: 'var(--color-warning-fg)' },
    HIGH: { bg: 'var(--color-danger-bg)', fg: 'var(--color-danger-fg)' },
    CRITICAL: { bg: 'var(--color-danger-bg)', fg: 'var(--color-danger-fg)', fontWeight: '700' },
  };
  const style = map[level] || map.MEDIUM;
  return (
    <span
      style={{ background: style.bg, color: style.fg, fontWeight: style.fontWeight || '500',
               padding: '2px 8px', borderRadius: 'var(--radius-pill)', fontSize: '0.75rem' }}
      data-testid={testId}
    >
      {level}
    </span>
  );
}
