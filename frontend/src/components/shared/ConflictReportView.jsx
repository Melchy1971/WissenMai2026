import { RiskBadge } from './RiskBadge.jsx';

export function ConflictReportView({ conflict }) {
  if (!conflict) return null;
  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: 16, fontSize: '0.875rem' }}>
      <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{conflict.id}</span>
        <RiskBadge level={conflict.severity || 'MEDIUM'} />
      </div>
      <p style={{ margin: '0 0 12px' }}>{conflict.summary}</p>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {[['Memory A', conflict.memory_a_id], ['Memory B', conflict.memory_b_id]].map(([label, id]) => (
          <div key={label} style={{ padding: 10, background: 'var(--t-gray-05)', borderRadius: 'var(--radius-sm)' }}>
            <p style={{ fontWeight: '600', margin: '0 0 4px', fontSize: '0.8rem' }}>{label}</p>
            <p style={{ margin: 0, color: 'var(--color-text-secondary)', fontFamily: 'monospace', fontSize: '0.75rem' }}>{id}</p>
          </div>
        ))}
      </div>
      {conflict.resolution_suggestion && (
        <div style={{ marginTop: 12, padding: 10, background: 'var(--color-info-bg)', borderRadius: 'var(--radius-sm)' }}>
          <p style={{ fontWeight: '600', margin: '0 0 4px', fontSize: '0.8rem' }}>Lösungsvorschlag</p>
          <p style={{ margin: 0, color: 'var(--color-info-fg)' }}>{conflict.resolution_suggestion}</p>
        </div>
      )}
    </div>
  );
}
