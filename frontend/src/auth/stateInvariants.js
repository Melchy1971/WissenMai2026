export function normalizeAuthState(value = {}) {
  return {
    token: typeof value.token === 'string' ? value.token.trim() : '',
    user: value.user && typeof value.user === 'object' ? value.user : null,
    active_workspace_id:
      typeof value.active_workspace_id === 'string' ? value.active_workspace_id.trim() : '',
    memberships: Array.isArray(value.memberships) ? value.memberships : [],
  };
}

export function authBootstrapError({ code, title, message, details = {}, status = null }) {
  return { code, title, message, details, status };
}

export function validateSessionState(sessionState) {
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

export function hasValidatedWorkspace(authState, bootstrapError = null) {
  if (bootstrapError) return false;
  return validateSessionState(authState).error === null && Boolean(normalizeAuthState(authState).token);
}

export function isRetryableBootstrapError(error) {
  return error?.code === 'API_UNREACHABLE' || error?.code === 'TIMEOUT';
}
