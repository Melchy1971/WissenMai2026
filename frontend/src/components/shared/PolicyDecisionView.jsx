import { useState } from 'react';

export function PolicyDecisionView({ decision }) {
  const [expanded, setExpanded] = useState(false);
  if (!decision) return null;
  const decColor = decision.decision === 'allowed' ? 'var(--color-success-fg)' : decision.decision === 'blocked' ? 'var(--color-danger-fg)' : 'var(--color-warning-fg)';
  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: 16, fontSize: '0.875rem' }}>
      <div style={{ display: 'flex', gap: 12, marginBottom: 8 }}>
        <span style={{ fontWeight: '600' }}>{decision.category}</span>
        <span style={{ fontWeight: '700', color: decColor }}>{decision.decision?.toUpperCase()}</span>
        <span style={{ color: 'var(--color-text-secondary)', marginLeft: 'auto', fontSize: '0.75rem' }}>{decision.timestamp ? new Date(decision.timestamp).toLocaleString('de-DE') : ''}</span>
      </div>
      <p style={{ color: 'var(--color-text-secondary)', margin: '4px 0' }}>{decision.input_summary}</p>
      <button type="button" onClick={() => setExpanded(!expanded)} style={{ background: 'none', border: 'none', color: 'var(--t-magenta)', cursor: 'pointer', padding: 0, fontSize: '0.8rem' }}>
        {expanded ? '▲ Begründung ausblenden' : '▼ Begründung anzeigen'}
      </button>
      {expanded && (
        <div style={{ marginTop: 8, padding: 12, background: 'var(--t-gray-05)', borderRadius: 'var(--radius-sm)' }}>
          <p style={{ margin: '0 0 8px', fontWeight: '600' }}>Begründung</p>
          <p style={{ margin: 0 }}>{decision.reasoning || '—'}</p>
          {decision.constraints?.length > 0 && (
            <ul style={{ marginTop: 8, paddingLeft: 16 }}>
              {decision.constraints.map((c, i) => <li key={i}>{c}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
