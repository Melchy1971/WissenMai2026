function LimitBar({ label, used, max }) {
  const pct = max > 0 ? Math.min(100, Math.round((used / max) * 100)) : 0;
  const danger = pct > 80;
  return (
    <div style={{ marginBottom: 8, fontSize: '0.8rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
        <span>{label}</span>
        <span style={{ color: danger ? 'var(--color-danger-fg)' : 'var(--color-text-secondary)' }}>{used}/{max}</span>
      </div>
      <div style={{ height: 4, background: 'var(--t-gray-10)', borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: '100%', background: danger ? 'var(--color-danger-fg)' : 'var(--color-info-fg)', borderRadius: 2 }} />
      </div>
    </div>
  );
}
export function AgentLimitView({ agent }) {
  if (!agent) return null;
  const u = agent.current_usage || {};
  return (
    <div style={{ fontSize: '0.875rem' }}>
      <p style={{ fontWeight: '600', margin: '0 0 8px' }}>{agent.name || agent.id}</p>
      <LimitBar label="Steps" used={u.steps || 0} max={agent.max_steps || 100} />
      <LimitBar label="Tool Calls" used={u.tool_calls || 0} max={agent.max_tool_calls || 50} />
      <LimitBar label="Laufzeit (s)" used={u.runtime_seconds || 0} max={agent.max_runtime_seconds || 3600} />
    </div>
  );
}
