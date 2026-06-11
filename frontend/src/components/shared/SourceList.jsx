import { DataClassificationBadge } from './DataClassificationBadge.jsx';

export function SourceList({ sources = [], required = false }) {
  const visible = sources.filter(s => s.classification !== 'SECRET');
  if (required && visible.length === 0) {
    return (
      <div data-testid="source-list" style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger-fg)', padding: 12, borderRadius: 'var(--radius-md)', fontSize: '0.875rem' }}>
        ⚠ Antwort ohne Quellen nicht zulässig (source_required=true).
      </div>
    );
  }
  if (!visible.length) return null;
  return (
    <div data-testid="source-list" style={{ marginTop: 12 }}>
      <p style={{ fontWeight: '600', fontSize: '0.8rem', marginBottom: 6, color: 'var(--color-text-secondary)' }}>Quellen ({visible.length})</p>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {visible.map((s, i) => (
          <li key={s.doc_id || i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.875rem', padding: '4px 0' }}>
            <span style={{ flex: 1 }}>{s.title || s.doc_id}</span>
            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>{s.score != null ? `${(s.score * 100).toFixed(0)}%` : ''}</span>
            <DataClassificationBadge classification={s.classification || 'INTERNAL'} />
          </li>
        ))}
      </ul>
    </div>
  );
}
