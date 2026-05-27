import { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';

import { getAuthSession, login } from '../api/auth.js';
import { setApiRequestContext } from '../api/client.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { mapError } from '../view-models/mappers.js';

function validateLoginSession(response) {
  const memberships = Array.isArray(response?.memberships) ? response.memberships : [];
  const activeWorkspaceId = typeof response?.active_workspace_id === 'string' ? response.active_workspace_id.trim() : '';

  if (!memberships.length) {
    return {
      code: 'WORKSPACE_NOT_CONFIGURED',
      title: 'Keine Workspace-Mitgliedschaft',
      message: 'Der Benutzer ist keinem Workspace zugeordnet.',
      details: {},
      status: null,
    };
  }

  if (!activeWorkspaceId) {
    return {
      code: 'AUTH_WORKSPACE_MISSING',
      title: 'Aktiver Workspace fehlt',
      message: 'Die Anmeldung liefert keinen aktiven Workspace.',
      details: {},
      status: null,
    };
  }

  const isMember = memberships.some((membership) => membership?.workspace_id === activeWorkspaceId);
  if (!isMember) {
    return {
      code: 'AUTH_WORKSPACE_NOT_ALLOWED',
      title: 'Workspace nicht zulaessig',
      message: 'Der aktive Workspace ist nicht in den Memberships der Anmeldung enthalten.',
      details: { active_workspace_id: activeWorkspaceId },
      status: 403,
    };
  }

  return null;
}

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { token, isAuthReady, setAuthState } = useAuth();
  const [loginInput, setLoginInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [state, setState] = useState({ status: 'idle', error: null });

  if (isAuthReady && token) {
    return <Navigate replace to={location.state?.from?.pathname || '/documents'} />;
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const normalizedLogin = loginInput.trim();
    const normalizedPassword = passwordInput.trim();
    if (!normalizedLogin || !normalizedPassword) {
      setState({
        status: 'error',
        error: mapError({
          code: 'AUTH_INVALID',
          message: 'Bitte Login und Passwort eingeben.',
          details: {},
          status: null,
        }),
      });
      return;
    }

    setState({ status: 'loading', error: null });
    try {
      const response = await login({ login: normalizedLogin, password: normalizedPassword });
      setApiRequestContext({ authToken: response.token, workspaceId: '' });
      const sessionState = await getAuthSession();
      const hydratedSession = {
        token: response.token,
        user: sessionState.user,
        memberships: sessionState.memberships || [],
        active_workspace_id: sessionState.active_workspace_id,
      };
      const sessionError = validateLoginSession(hydratedSession);
      if (sessionError) {
        setState({ status: 'error', error: mapError(sessionError) });
        return;
      }
      setAuthState(hydratedSession);
      navigate(location.state?.from?.pathname || '/documents', { replace: true });
    } catch (error) {
      setState({ status: 'error', error: mapError(error) });
    }
  }

  return (
    <section className="page-stack auth-page" data-testid="login-page">
      <div className="page-header">
        <div>
          <p className="panel__eyebrow">M4a Auth</p>
          <h2>Anmeldung</h2>
        </div>
        <p className="page-header__meta">Lokale Session fuer geschuetzte API-Pfade</p>
      </div>

      <section className="panel auth-panel">
        <div className="panel__header search-bar__header">
          <div>
            <p className="panel__eyebrow">Session</p>
            <h3>Mit Workspace-Kontext anmelden</h3>
          </div>
        </div>
        <form className="search-bar auth-form" onSubmit={handleSubmit}>
          <label className="search-bar__field">
            <span className="search-bar__label">Login</span>
            <input
              type="text"
              value={loginInput}
              onChange={(event) => setLoginInput(event.target.value)}
              autoComplete="username"
              data-testid="login-email"
            />
          </label>
          <label className="search-bar__field">
            <span className="search-bar__label">Passwort</span>
            <input
              type="password"
              value={passwordInput}
              onChange={(event) => setPasswordInput(event.target.value)}
              autoComplete="current-password"
              data-testid="login-password"
            />
          </label>
          <div className="search-bar__actions">
            <button
              type="submit"
              disabled={state.status === 'loading'}
              data-testid="login-submit"
            >
              {state.status === 'loading' ? 'Anmeldung laeuft...' : 'Anmelden'}
            </button>
          </div>
        </form>
      </section>

      {state.status === 'error' ? <ErrorState error={state.error} /> : null}
    </section>
  );
}
