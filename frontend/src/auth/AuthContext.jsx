import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { getAuthSession } from '../api/auth.js';
import { getApiRequestContext, setApiRequestContext } from '../api/client.js';

const AUTH_STATE_STORAGE_KEY = 'wissen.authState';

const AuthContext = createContext(null);

function getStorage() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null;
  }

  const storage = window.localStorage;
  if (typeof storage.getItem !== 'function' || typeof storage.setItem !== 'function' || typeof storage.removeItem !== 'function') {
    return null;
  }

  return storage;
}

function normalizeAuthState(value = {}) {
  return {
    token: typeof value.token === 'string' ? value.token.trim() : '',
    user: value.user && typeof value.user === 'object' ? value.user : null,
    active_workspace_id: typeof value.active_workspace_id === 'string' ? value.active_workspace_id.trim() : '',
    memberships: Array.isArray(value.memberships) ? value.memberships : [],
  };
}

function authBootstrapError({ code, title, message, details = {}, status = null }) {
  return { code, title, message, details, status };
}

function validateSessionState(sessionState) {
  const normalized = normalizeAuthState(sessionState);

  if (!normalized.token) {
    return { state: normalized, error: null };
  }

  if (!normalized.user) {
    return {
      state: normalized,
      error: authBootstrapError({
        code: 'AUTH_SESSION_INVALID',
        title: 'Auth-Session unvollstaendig',
        message: 'Die Session enthaelt keinen Benutzerkontext.',
      }),
    };
  }

  if (normalized.memberships.length === 0) {
    return {
      state: normalized,
      error: authBootstrapError({
        code: 'WORKSPACE_NOT_CONFIGURED',
        title: 'Keine Workspace-Mitgliedschaft',
        message: 'Der Benutzer ist keinem Workspace zugeordnet.',
      }),
    };
  }

  if (!normalized.active_workspace_id) {
    return {
      state: normalized,
      error: authBootstrapError({
        code: 'AUTH_WORKSPACE_MISSING',
        title: 'Aktiver Workspace fehlt',
        message: 'Die Session enthaelt keinen aktiven Workspace.',
      }),
    };
  }

  const hasActiveMembership = normalized.memberships.some(
    (membership) => membership?.workspace_id === normalized.active_workspace_id,
  );
  if (!hasActiveMembership) {
    return {
      state: normalized,
      error: authBootstrapError({
        code: 'AUTH_WORKSPACE_NOT_ALLOWED',
        title: 'Workspace nicht zulaessig',
        message: 'Der aktive Workspace ist nicht in den Memberships der Session enthalten.',
        details: { active_workspace_id: normalized.active_workspace_id },
        status: 403,
      }),
    };
  }

  return { state: normalized, error: null };
}

function mapBootstrapFailure(error) {
  if (error?.code === 'API_UNREACHABLE' || error?.code === 'CORS_ERROR' || error?.code === 'TIMEOUT') {
    return authBootstrapError({
      code: error.code,
      title: error.code === 'TIMEOUT' ? 'Auth-Anfrage abgelaufen' : error.code === 'CORS_ERROR' ? 'Auth-Anfrage blockiert' : 'Backend nicht erreichbar',
      message: error.message || 'Der Auth-Status konnte nicht geladen werden.',
      details: error.details,
      status: error.status,
    });
  }

  if (error?.status === 401 || error?.code === 'UNAUTHORIZED' || error?.code === 'AUTH_REQUIRED') {
    return authBootstrapError({
      code: 'AUTH_SESSION_EXPIRED',
      title: 'Session abgelaufen',
      message: 'Der gespeicherte Token ist ungueltig oder abgelaufen. Bitte erneut anmelden.',
      details: error?.details || {},
      status: 401,
    });
  }

  if (error?.status === 403 || error?.code === 'FORBIDDEN') {
    return authBootstrapError({
      code: 'AUTH_FORBIDDEN',
      title: 'Auth-Zugriff verweigert',
      message: 'Die Session darf den Auth-Kontext nicht lesen.',
      details: error?.details || {},
      status: 403,
    });
  }

  return authBootstrapError({
    code: 'AUTH_BOOTSTRAP_FAILED',
    title: 'Auth-Initialisierung fehlgeschlagen',
    message: error?.message || 'Der Auth-Status konnte nicht geladen werden.',
    details: error?.details || {},
    status: error?.status ?? null,
  });
}

function applyApiContext(authState) {
  const normalized = normalizeAuthState(authState);
  setApiRequestContext({
    authToken: normalized.token,
    workspaceId: normalized.active_workspace_id,
  });
}

function readStoredAuthState() {
  const storage = getStorage();
  const requestContext = getApiRequestContext();

  if (!storage) {
    return normalizeAuthState({
      token: requestContext.authToken,
      active_workspace_id: requestContext.workspaceId,
    });
  }

  const rawState = storage.getItem(AUTH_STATE_STORAGE_KEY);
  if (!rawState) {
    return normalizeAuthState({
      token: requestContext.authToken,
      active_workspace_id: requestContext.workspaceId,
    });
  }

  try {
    return normalizeAuthState(JSON.parse(rawState));
  } catch {
    return normalizeAuthState({
      token: requestContext.authToken,
      active_workspace_id: requestContext.workspaceId,
    });
  }
}

export function AuthProvider({ children, initialAuthState = null }) {
  const hasInjectedAuthState = initialAuthState !== null;
  const [authState, setAuthState] = useState(() => normalizeAuthState(initialAuthState || readStoredAuthState()));
  const [bootstrapError, setBootstrapError] = useState(null);
  const [isBootstrapping, setIsBootstrapping] = useState(() => {
    const initialState = normalizeAuthState(initialAuthState || readStoredAuthState());
    if (hasInjectedAuthState) {
      return false;
    }
    return Boolean(initialState.token) && (!initialState.user || !initialState.active_workspace_id || initialState.memberships.length === 0);
  });

  useEffect(() => {
    const normalizedState = normalizeAuthState(authState);
    setApiRequestContext({
      authToken: normalizedState.token,
      workspaceId: normalizedState.active_workspace_id,
    });

    const storage = getStorage();
    if (!storage) {
      return;
    }

    storage.setItem(AUTH_STATE_STORAGE_KEY, JSON.stringify(normalizedState));
  }, [authState]);

  useEffect(() => {
    let cancelled = false;
    const normalizedState = normalizeAuthState(authState);
    if (hasInjectedAuthState) {
      setIsBootstrapping(false);
      return () => {
        cancelled = true;
      };
    }

    const needsBootstrap = Boolean(normalizedState.token) && (
      !normalizedState.user ||
      !normalizedState.active_workspace_id ||
      normalizedState.memberships.length === 0
    );

    if (!needsBootstrap || bootstrapError) {
      setIsBootstrapping(false);
      return () => {
        cancelled = true;
      };
    }

    setIsBootstrapping(true);

    async function bootstrapAuthState() {
      try {
        const sessionState = await getAuthSession();
        if (cancelled) {
          return;
        }
        const validated = validateSessionState({
          token: normalizedState.token,
          user: sessionState.user,
          memberships: sessionState.memberships,
          active_workspace_id: sessionState.active_workspace_id,
        });
        applyApiContext(validated.state);
        setAuthState(validated.state);
        setBootstrapError(validated.error);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setBootstrapError(mapBootstrapFailure(error));
      } finally {
        if (!cancelled) {
          setIsBootstrapping(false);
        }
      }
    }

    void bootstrapAuthState();

    return () => {
      cancelled = true;
    };
  }, [authState, bootstrapError, hasInjectedAuthState]);

  const value = useMemo(() => ({
    ...authState,
    isAuthReady: !isBootstrapping,
    bootstrapError,
    setAuthState(nextState) {
      const validated = validateSessionState(nextState);
      applyApiContext(validated.state);
      setBootstrapError(validated.error);
      setAuthState(validated.state);
    },
    updateAuthState(partialState) {
      setAuthState((current) => {
        const validated = validateSessionState({ ...current, ...partialState });
        applyApiContext(validated.state);
        setBootstrapError(validated.error);
        return validated.state;
      });
    },
    clearAuthState() {
      setBootstrapError(null);
      applyApiContext({});
      setAuthState(normalizeAuthState());
    },
  }), [authState, bootstrapError, isBootstrapping]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
}
