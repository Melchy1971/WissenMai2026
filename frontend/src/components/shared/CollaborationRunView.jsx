import { PolicyDecisionView } from './PolicyDecisionView.jsx';
import { RiskBadge } from './RiskBadge.jsx';

export function CollaborationRunView({ run }) {
  if (!run) return null;
  // Shared Workspace: keine SECRET-Daten
  const safeWorkspace = run.shared_workspace_snapshot
    ? Object.fromEntries(Object.entries(run.shared_workspace_snapshot).filter(([, v]) => v?.classification !== 'SECRET'))
    : null;
  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', padding: 16, fontSize: '0.875rem' }}>
      <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
        <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{run.id}</span>
        <strong>{run.team_id}</strong>
        <span style={{ marginLeft: 'auto' }}>{run.status}</span>
      </div>
      {run.agents?.length > 0 && <p style={{ color: 'var(--color-text-secondary)', margin: '0 0 8px', fontSize: '0.8rem' }}>Agenten: {run.agents.join(', ')}</p>}
      {run.conflicts?.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <p style={{ fontWeight: '600', margin: '0 0 4px' }}>Konflikte ({run.conflicts.length})</p>
          {run.conflicts.map((c, i) => <div key={i} style={{ display: 'flex', gap: 8, padding: '4px 0' }}><RiskBadge level={c.severity || 'MEDIUM'} /><span>{c.summary}</span></div>)}
        </div>
      )}
      {run.consensus_report && <PolicyDecisionView decision={run.consensus_report} />}
    </div>
  );
}
