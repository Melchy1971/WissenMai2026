import { DataClassificationBadge } from './DataClassificationBadge.jsx';

export function MemoryScoreCard({ memory }) {
  if (!memory) return null;
  const isSecret = memory.classification === 'SECRET';
  const isSensitive = memory.classification === 'SENSITIVE_PERSONAL';
  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: 12, fontSize: '0.875rem' }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
        <span style={{ flex: 1, fontStyle: isSecret ? 'italic' : 'normal', color: isSecret ? 'var(--color-text-tertiary)' : 'inherit' }}>
          {isSecret ? '[GESPERRT]' : (memory.content_summary?.substring(0, 120) || '—')}
        </span>
        <DataClassificationBadge classification={memory.classification || 'INTERNAL'} />
      </div>
      {isSensitive && !isSecret && <p style={{ color: 'var(--color-warning-fg)', fontSize: '0.8rem', margin: '0 0 8px' }}>⚠ Enthält personenbezogene Daten.</p>}
      <div style={{ display: 'flex', gap: 16, fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>
        {memory.score != null && <span>Score: <strong>{(memory.score * 100).toFixed(0)}%</strong></span>}
        {memory.confidence != null && <span>Konfidenz: <strong>{(memory.confidence * 100).toFixed(0)}%</strong></span>}
        {memory.aging_factor != null && <span>Aging: <strong>{memory.aging_factor}</strong></span>}
        <span>Status: <strong>{memory.review_status || '—'}</strong></span>
      </div>
    </div>
  );
}
