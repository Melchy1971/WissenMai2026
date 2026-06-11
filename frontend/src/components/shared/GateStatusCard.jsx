import { StatusBadge } from '../status/StatusBadge.jsx';

const TONE_MAP = { PASS: 'success', FAIL: 'danger', BLOCKED: 'danger', NO_GO: 'warning', WARNING: 'warning', COMPLETE: 'success' };

export function GateStatusCard({ gate }) {
  if (!gate) return null;
  const tone = TONE_MAP[gate.status] || 'neutral';
  const pct = gate.criteria_total > 0 ? Math.round((gate.criteria_passed / gate.criteria_total) * 100) : null;
  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: 16, background: 'var(--color-surface)', boxShadow: 'var(--shadow-sm)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong style={{ fontSize: '0.875rem' }}>{gate.name}</strong>
        <StatusBadge status={{ tone, label: gate.status }} />
      </div>
      {pct != null && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: 4 }}>
            <span>Kriterien</span><span>{gate.criteria_passed}/{gate.criteria_total}</span>
          </div>
          <div style={{ height: 4, background: 'var(--t-gray-10)', borderRadius: 2 }}>
            <div style={{ width: `${pct}%`, height: '100%', background: tone === 'success' ? 'var(--color-success-fg)' : 'var(--color-warning-fg)', borderRadius: 2 }} />
          </div>
        </div>
      )}
      {gate.source && <p style={{ margin: '8px 0 0', fontSize: '0.7rem', color: 'var(--color-text-tertiary)', fontFamily: 'monospace' }}>{gate.source}</p>}
    </div>
  );
}
