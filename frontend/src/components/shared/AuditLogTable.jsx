import { useState } from 'react';
import { RiskBadge } from './RiskBadge.jsx';

export function AuditLogTable({ events = [], loading }) {
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 50;
  const filtered = events.filter(e => e.classification !== 'SECRET');
  const visible = filtered.slice(0, (page + 1) * PAGE_SIZE);
  const hasMore = visible.length < filtered.length;

  if (loading) return <p style={{ color: 'var(--color-text-secondary)' }}>Lädt...</p>;
  if (!filtered.length) return <p style={{ color: 'var(--color-text-secondary)' }}>Keine Audit-Einträge.</p>;

  return (
    <div data-testid="audit-log-table">
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid var(--color-border)' }}>
            {['Timestamp','User','Aktion','Kategorie','Risiko','Details'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '6px 8px', fontWeight: '600' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visible.map((e, i) => (
            <tr key={e.id || i} style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
              <td style={{ padding: '6px 8px', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{e.timestamp ? new Date(e.timestamp).toLocaleString('de-DE') : '—'}</td>
              <td style={{ padding: '6px 8px' }}>{e.user || '—'}</td>
              <td style={{ padding: '6px 8px' }}>{e.action || '—'}</td>
              <td style={{ padding: '6px 8px' }}>{e.category || '—'}</td>
              <td style={{ padding: '6px 8px' }}><RiskBadge level={e.risk_level || 'LOW'} /></td>
              <td style={{ padding: '6px 8px', color: 'var(--color-text-secondary)', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.details || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {hasMore && (
        <button type="button" onClick={() => setPage(p => p + 1)}
          style={{ marginTop: 8, background: 'none', border: '1px solid var(--color-border)', borderRadius: 4, padding: '4px 12px', cursor: 'pointer', fontSize: '0.875rem' }}>
          Mehr laden ({filtered.length - visible.length} weitere)
        </button>
      )}
    </div>
  );
}
