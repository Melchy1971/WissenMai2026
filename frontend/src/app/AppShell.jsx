import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { callApi } from '../lib/apiClient.js';
import { PrivacyModeBanner } from '../components/shared/PrivacyModeBanner.jsx';

function TelekomLogo() {
  return (
    <svg className="shell__logo" viewBox="0 0 34 34" fill="none"
      xmlns="http://www.w3.org/2000/svg" aria-label="Deutsche Telekom">
      <rect width="34" height="34" rx="6" fill="#E20074" />
      <path d="M7 10h20v4h-8v10h-4V14H7v-4z" fill="#FFFFFF" />
    </svg>
  );
}

const NAV_ITEMS = [
  { to: '/dashboard',      label: 'Dashboard' },
  { to: '/chat',           label: 'Chat' },
  { to: '/documents',      label: 'Dokumente' },
  { to: '/tools',          label: 'Tool Center' },
  { to: '/memory',         label: 'Memory' },
  { to: '/tasks',          label: 'Tasks' },
  { to: '/projects',       label: 'Projekte' },
  { to: '/rag',            label: 'RAG' },
  { to: '/agents',         label: 'Agents' },
  { to: '/collaboration',  label: 'Collaboration' },
  { to: '/governance',     label: 'Governance' },
  { to: '/settings',       label: 'Einstellungen' },
  { to: '/admin/diagnostics', label: 'Admin' },
];

export function AppShell() {
  const navigate = useNavigate();
  const { token, user, active_workspace_id: workspaceId, memberships, signOut, switchWorkspace } = useAuth();
  const [status, setStatus] = useState(null);

  useEffect(() => {
    callApi('/api/v1/status').then(r => { if (r.ok) setStatus(r.data); });
  }, []);

  async function handleLogout() {
    await signOut();
    navigate('/login', { replace: true });
  }

  const privacyMode = status?.privacy_mode ?? false;
  const provider    = status?.provider_name ?? '—';
  const autonomy    = status?.autonomy_level ?? '—';
  const release     = status?.release_status ?? '—';

  return (
    <div className="shell" data-testid="app-shell">
      <PrivacyModeBanner enabled={privacyMode} />

      {/* Status-Header */}
      <div className="shell__status-bar" data-testid="status-bar">
        <span>Workspace: <strong>{workspaceId || '—'}</strong></span>
        <span>Provider: <strong>{provider}</strong></span>
        <span>Autonomie: <strong>{autonomy}</strong></span>
        <span>Release: <strong>{release}</strong></span>
        {privacyMode && <span className="badge badge--warning">PRIVACY MODE</span>}
      </div>

      <header className="shell__header">
        <div className="shell__brand">
          <TelekomLogo />
          <div className="shell__title-group">
            <p className="shell__eyebrow">Deutsche Telekom</p>
            <span className="shell__app-name">Jarvis</span>
          </div>
        </div>

        <nav aria-label="Hauptnavigation">
          <div className="shell__nav">
            {NAV_ITEMS.map(item => (
              <NavLink key={item.to} to={item.to}
                className={({ isActive }) => isActive ? 'nav-link nav-link--active' : 'nav-link'}>
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>

        <div className="shell__session">
          <div className="shell__session-meta">
            <strong>{token ? (user?.display_name || user?.login || 'Angemeldet') : 'Gast'}</strong>
            {memberships.length > 1 ? (
              <select aria-label="Workspace wechseln" value={workspaceId || ''}
                onChange={e => switchWorkspace(e.target.value)}>
                {memberships.map(m => (
                  <option key={m.workspace_id} value={m.workspace_id}>{m.workspace_id}</option>
                ))}
              </select>
            ) : (
              <span>{workspaceId || 'Workspace fehlt'}</span>
            )}
          </div>
          {token && (
            <button type="button" className="button-secondary" onClick={handleLogout}>
              Abmelden
            </button>
          )}
        </div>
      </header>

      <main className="shell__content" data-testid="workspace-ready">
        <Outlet />
      </main>
    </div>
  );
}
