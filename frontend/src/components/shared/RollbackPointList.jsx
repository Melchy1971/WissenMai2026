import { useState } from 'react';

export function RollbackPointList({ points = [], onRollback, hasAdminPermission }) {
  const [confirming, setConfirming] = useState(null);
  return (
    <div>
      {points.length === 0 && <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>Keine Rollback-Punkte verfügbar.</p>}
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
            {['ID','Beschreibung','Erstellt','Status','Aktion'].map(h => <th key={h} style={{ textAlign: 'left', padding: '8px', fontWeight: '600' }}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {points.map(p => (
            <tr key={p.id} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '0.75rem' }}>{p.id}</td>
              <td style={{ padding: '8px' }}>{p.description || '—'}</td>
              <td style={{ padding: '8px', color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>{p.created_at ? new Date(p.created_at).toLocaleString('de-DE') : '—'}</td>
              <td style={{ padding: '8px' }}>{p.status || '—'}</td>
              <td style={{ padding: '8px' }}>
                {hasAdminPermission ? (
                  confirming === p.id ? (
                    <span style={{ display: 'flex', gap: 8 }}>
                      <span style={{ color: 'var(--color-danger-fg)', fontSize: '0.8rem' }}>Wirklich zurückrollen?</span>
                      <button type="button" onClick={() => { onRollback?.(p.id); setConfirming(null); }} style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger-fg)', border: 'none', borderRadius: 4, padding: '2px 8px', cursor: 'pointer' }}>Ja</button>
                      <button type="button" onClick={() => setConfirming(null)} style={{ border: '1px solid var(--color-border)', background: 'none', borderRadius: 4, padding: '2px 8px', cursor: 'pointer' }}>Nein</button>
                    </span>
                  ) : (
                    <button type="button" onClick={() => setConfirming(p.id)} style={{ background: 'var(--color-warning-bg)', color: 'var(--color-warning-fg)', border: 'none', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}>Rollback</button>
                  )
                ) : <span style={{ color: 'var(--color-text-tertiary)', fontSize: '0.8rem' }}>Admin erforderlich</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
