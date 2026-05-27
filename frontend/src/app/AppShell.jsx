import { NavLink, Outlet, useNavigate } from 'react-router-dom';

import { useAuth } from '../auth/AuthContext.jsx';

function TelekomLogo() {
  return (
    <svg
      className="shell__logo"
      viewBox="0 0 34 34"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Deutsche Telekom"
    >
      <rect width="34" height="34" rx="6" fill="#E20074" />
      <path
        d="M7 10h20v4h-8v10h-4V14H7v-4z"
        fill="#FFFFFF"
      />
    </svg>
  );
}

export function AppShell() {
  const navigate = useNavigate();
  const { token, user, active_workspace_id: workspaceId, memberships, signOut, switchWorkspace } = useAuth();

  async function handleLogout() {
    await signOut();
    navigate('/login', { replace: true });
  }

  return (
    <div className="shell" data-testid="app-shell">
      <header className="shell__header">
        <div className="shell__brand">
          <TelekomLogo />
          <div className="shell__title-group">
            <p className="shell__eyebrow">Deutsche Telekom</p>
            <span className="shell__app-name">Wissensbasis V1</span>
          </div>
        </div>
        <nav>
          <div className="shell__nav">
            <NavLink to="/documents">Dokumente</NavLink>
            <NavLink to="/chat">Chat</NavLink>
            <NavLink to="/admin/diagnostics">Admin</NavLink>
          </div>
        </nav>
        <div className="shell__session">
          <div className="shell__session-meta">
            <strong>{token ? (user?.display_name || user?.login || 'Angemeldet') : 'Gast'}</strong>
            {memberships.length > 1 ? (
              <select
                aria-label="Workspace wechseln"
                value={workspaceId || ''}
                onChange={(e) => switchWorkspace(e.target.value)}
              >
                {memberships.map((m) => (
                  <option key={m.workspace_id} value={m.workspace_id}>
                    {m.workspace_id}
                  </option>
                ))}
              </select>
            ) : (
              <span>{workspaceId || 'Workspace fehlt'}</span>
            )}
          </div>
          {token ? (
            <button type="button" className="button-secondary" onClick={handleLogout}>
              Abmelden
            </button>
          ) : null}
        </div>
      </header>
      <main className="shell__content" data-testid="workspace-ready">
        <Outlet />
      </main>
    </div>
  );
}
