import { describe, expect, it } from 'vitest';

import {
  hasValidatedWorkspace,
  isRetryableBootstrapError,
  validateSessionState,
} from '../../auth/stateInvariants.js';

const validAuthState = {
  token: 'token-1',
  user: { id: 'user-1', login: 'user' },
  memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
  active_workspace_id: 'workspace-1',
};

describe('GUI state invariants', () => {
  it('validates only explicit workspace memberships', () => {
    expect(validateSessionState(validAuthState)).toMatchObject({ error: null });
    expect(hasValidatedWorkspace(validAuthState)).toBe(true);
  });

  it('rejects missing workspace membership', () => {
    const result = validateSessionState({
      ...validAuthState,
      memberships: [],
      active_workspace_id: '',
    });

    expect(result.error).toMatchObject({ code: 'WORKSPACE_NOT_CONFIGURED' });
    expect(hasValidatedWorkspace(result.state, result.error)).toBe(false);
  });

  it('rejects active workspace outside memberships', () => {
    const result = validateSessionState({
      ...validAuthState,
      active_workspace_id: 'workspace-2',
    });

    expect(result.error).toMatchObject({ code: 'AUTH_WORKSPACE_NOT_ALLOWED', status: 403 });
    expect(hasValidatedWorkspace(result.state, result.error)).toBe(false);
  });

  it('treats bootstrap errors as invalid workspace guards', () => {
    expect(
      hasValidatedWorkspace(validAuthState, {
        code: 'FORBIDDEN',
        title: 'Forbidden',
        message: 'Denied',
      }),
    ).toBe(false);
  });

  it('allows retry only for transient bootstrap errors', () => {
    expect(isRetryableBootstrapError({ code: 'API_UNREACHABLE' })).toBe(true);
    expect(isRetryableBootstrapError({ code: 'TIMEOUT' })).toBe(true);
    expect(isRetryableBootstrapError({ code: 'FORBIDDEN' })).toBe(false);
    expect(isRetryableBootstrapError({ code: 'AUTH_REQUIRED' })).toBe(false);
  });
});
