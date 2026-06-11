import { useState } from 'react';
import { RiskBadge } from './RiskBadge.jsx';

export function ApprovalQueue({ approvals = [], onApprove, onReject, loading }) {
  const [rejectId, setRejectId] = useState(null);
  const [rejectReason, setRejectReason] = useState('');

  if (loading) return <p style={{ color: 'var(--color-text-secondary)' }}>Lädt...</p>;
  if (!approvals.length) return <p data-testid="approval-queue-empty" style={{ color: 'var(--color-text-secondary)' }}>Keine offenen Approvals.</p>;

  return (
    <div data-testid="approval-queue">
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
            {['ID','Typ','Beschreibung','Risiko','Erstellt','Aktionen'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px', fontWeight: '600' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {approvals.map(a => (
            <tr key={a.id} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <td style={{ padding: '8px', fontFamily: 'monospace', fontSize: '0.75rem' }}>{a.id}</td>
              <td style={{ padding: '8px' }}>{a.type || '—'}</td>
              <td style={{ padding: '8px' }}>{a.description || '—'}</td>
              <td style={{ padding: '8px' }}><RiskBadge level={a.risk_level || 'MEDIUM'} /></td>
              <td style={{ padding: '8px', color: 'var(--color-text-secondary)', fontSize: '0.75rem' }}>{a.created_at ? new Date(a.created_at).toLocaleString('de-DE') : '—'}</td>
              <td style={{ padding: '8px', display: 'flex', gap: 8, alignItems: 'center' }}>
                <button type="button" onClick={() => onApprove?.(a.id)}
                  style={{ background: 'var(--color-success-bg)', color: 'var(--color-success-fg)', border: 'none', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}>
                  Genehmigen
                </button>
                {rejectId === a.id ? (
                  <span style={{ display: 'flex', gap: 4 }}>
                    <input value={rejectReason} onChange={e => setRejectReason(e.target.value)}
                      placeholder="Grund..." style={{ border: '1px solid var(--color-border)', borderRadius: 4, padding: '2px 6px', fontSize: '0.875rem' }} />
                    <button type="button" onClick={() => { onReject?.(a.id, rejectReason); setRejectId(null); setRejectReason(''); }}
                      style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger-fg)', border: 'none', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}>
                      Senden
                    </button>
                    <button type="button" onClick={() => setRejectId(null)}
                      style={{ background: 'none', border: '1px solid var(--color-border)', borderRadius: 4, padding: '4px 8px', cursor: 'pointer' }}>✕</button>
                  </span>
                ) : (
                  <button type="button" onClick={() => setRejectId(a.id)}
                    style={{ background: 'var(--color-danger-bg)', color: 'var(--color-danger-fg)', border: 'none', borderRadius: 4, padding: '4px 10px', cursor: 'pointer' }}>
                    Ablehnen
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
