export function ChangeSetDiff({ changeset, onApply, requiresAdmin }) {
  if (!changeset) return null;
  return (
    <div data-testid="changeset-diff" style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: 16, fontSize: '0.875rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{changeset.id}</span>
        <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{changeset.created_at ? new Date(changeset.created_at).toLocaleString('de-DE') : ''}</span>
      </div>
      {(changeset.changes || []).map((c, i) => (
        <div key={i} style={{ marginBottom: 8, padding: '8px', background: 'var(--t-gray-05)', borderRadius: 'var(--radius-sm)' }}>
          <strong style={{ fontSize: '0.8rem' }}>{c.field}</strong>
          <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
            <span style={{ color: 'var(--color-danger-fg)', textDecoration: 'line-through', flex: 1 }}>{JSON.stringify(c.before)}</span>
            <span style={{ color: 'var(--color-success-fg)', flex: 1 }}>{JSON.stringify(c.after)}</span>
          </div>
        </div>
      ))}
      {onApply && (
        <div style={{ marginTop: 12 }}>
          {requiresAdmin
            ? <p style={{ color: 'var(--color-warning-fg)', fontSize: '0.8rem' }}>⚠ Anwenden erfordert Admin-Berechtigung und erzeugt einen Approval.</p>
            : <button type="button" onClick={() => onApply(changeset.id)} style={{ background: 'var(--t-magenta)', color: '#fff', border: 'none', borderRadius: 4, padding: '6px 16px', cursor: 'pointer' }}>Anwenden</button>
          }
        </div>
      )}
    </div>
  );
}
