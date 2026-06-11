export function TokenBudgetView({ used = 0, limit = 1, breakdown = [] }) {
  const pct = Math.min(100, Math.round((used / limit) * 100));
  const color = pct < 50 ? 'var(--color-success-fg)' : pct < 80 ? 'var(--color-warning-fg)' : 'var(--color-danger-fg)';
  const bg = pct < 50 ? 'var(--color-success-bg)' : pct < 80 ? 'var(--color-warning-bg)' : 'var(--color-danger-bg)';
  return (
    <div style={{ fontSize: '0.8rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ color: 'var(--color-text-secondary)' }}>Token-Budget</span>
        <span style={{ fontWeight: '600', color }}>{used.toLocaleString()} / {limit.toLocaleString()} ({pct}%)</span>
      </div>
      <div style={{ height: 6, background: 'var(--t-gray-10)', borderRadius: 3 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: bg, borderRadius: 3, transition: 'width 0.3s' }} />
      </div>
      {breakdown.length > 0 && (
        <ul style={{ listStyle: 'none', margin: '6px 0 0', padding: 0 }}>
          {breakdown.map((b, i) => (
            <li key={i} style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-text-secondary)' }}>
              <span>{b.label}</span><span>{b.tokens.toLocaleString()}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
