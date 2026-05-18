import { describe, expect, it } from 'vitest';

import { createRequestCoordinator } from '../../api/requestCoordinator.js';

function contextRef(initial = {}) {
  const current = {
    authToken: initial.authToken || 'token-1',
    workspaceId: initial.workspaceId || 'workspace-1',
  };
  return {
    current,
    getContext: () => ({ ...current }),
  };
}

describe('RequestCoordinator', () => {
  it('aborts older parallel requests for the same key', () => {
    const ctx = contextRef();
    const coordinator = createRequestCoordinator({ getContext: ctx.getContext });

    const first = coordinator.begin('search');
    const second = coordinator.begin('search');

    expect(first.signal.aborted).toBe(true);
    expect(coordinator.isCurrent(first)).toBe(false);
    expect(coordinator.isCurrent(second)).toBe(true);
  });

  it('rejects stale responses after a workspace switch', () => {
    const ctx = contextRef();
    const coordinator = createRequestCoordinator({ getContext: ctx.getContext });

    const ticket = coordinator.begin('documents:list');
    ctx.current.workspaceId = 'workspace-2';

    expect(coordinator.isCurrent(ticket)).toBe(false);
  });

  it('rejects stale responses after logout changes auth context', () => {
    const ctx = contextRef();
    const coordinator = createRequestCoordinator({ getContext: ctx.getContext });

    const ticket = coordinator.begin('chat:message');
    ctx.current.authToken = '';
    ctx.current.workspaceId = '';

    expect(coordinator.isCurrent(ticket)).toBe(false);
  });

  it('cancels all active requests', () => {
    const ctx = contextRef();
    const coordinator = createRequestCoordinator({ getContext: ctx.getContext });

    const search = coordinator.begin('search');
    const upload = coordinator.begin('upload');

    coordinator.cancelAll();

    expect(search.signal.aborted).toBe(true);
    expect(upload.signal.aborted).toBe(true);
    expect(coordinator.isCurrent(search)).toBe(false);
    expect(coordinator.isCurrent(upload)).toBe(false);
  });

  it('creates optional correlation ids for propagation', () => {
    const ctx = contextRef();
    const coordinator = createRequestCoordinator({ getContext: ctx.getContext });

    const ticket = coordinator.begin('search');
    const custom = coordinator.begin('upload', { correlationId: 'manual-correlation-id' });

    expect(ticket.correlationId).toMatch(/^search-/);
    expect(custom.correlationId).toBe('manual-correlation-id');
  });
});
