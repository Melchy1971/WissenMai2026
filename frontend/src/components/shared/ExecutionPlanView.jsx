const STATUS_ICON = { pending: '○', running: '⟳', done: '✓', failed: '✗' };
const STATUS_COLOR = { pending: 'var(--color-text-tertiary)', running: 'var(--color-info-fg)', done: 'var(--color-success-fg)', failed: 'var(--color-danger-fg)' };

export function ExecutionPlanView({ plan }) {
  if (!plan) return <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>Kein Execution Plan verfügbar.</p>;
  return (
    <div style={{ fontSize: '0.875rem' }}>
      <p style={{ marginBottom: 8, color: 'var(--color-text-secondary)', fontSize: '0.8rem' }}>
        Agent: {plan.agent_id || '—'} | Status: <strong>{plan.status}</strong>
      </p>
      <ol style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
        {(plan.steps || []).map((s, i) => (
          <li key={s.step_id || i}>
            <span style={{ color: STATUS_COLOR[s.status] || 'inherit', marginRight: 6 }}>{STATUS_ICON[s.status] || '?'}</span>
            <strong>{s.type}</strong>
            {s.tool && <span style={{ color: 'var(--color-info-fg)', marginLeft: 6 }}>[{s.tool}]</span>}
            {s.input_summary && <span style={{ color: 'var(--color-text-secondary)', marginLeft: 6 }}>{s.input_summary}</span>}
            {s.duration_ms != null && <span style={{ color: 'var(--color-text-tertiary)', marginLeft: 6, fontSize: '0.75rem' }}>{s.duration_ms}ms</span>}
          </li>
        ))}
      </ol>
    </div>
  );
}
