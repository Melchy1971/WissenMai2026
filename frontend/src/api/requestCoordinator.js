import { getApiRequestContext } from './client.js';

let correlationCounter = 0;

function sanitize(value) {
  return String(value || 'request').replace(/[^a-zA-Z0-9_.:-]+/g, '-').slice(0, 80);
}

export function createRequestCoordinator({ getContext = getApiRequestContext } = {}) {
  const active = new Map();

  function begin(key, { cancelPrevious = true, correlationId = null } = {}) {
    const requestKey = sanitize(key);
    const previous = active.get(requestKey);
    if (cancelPrevious && previous?.controller) {
      previous.controller.abort();
    }

    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    const context = getContext();
    const sequence = (previous?.sequence || 0) + 1;
    const ticket = {
      key: requestKey,
      sequence,
      authToken: context.authToken || '',
      workspaceId: context.workspaceId || '',
      signal: controller?.signal,
      correlationId: correlationId || `${requestKey}-${Date.now()}-${++correlationCounter}`,
    };

    active.set(requestKey, { sequence, controller, ticket });
    return ticket;
  }

  function isCurrent(ticket) {
    if (!ticket) return false;
    if (ticket.signal?.aborted) return false;
    const current = active.get(ticket.key);
    if (!current || current.sequence !== ticket.sequence) return false;
    const context = getContext();
    return (
      (context.authToken || '') === ticket.authToken &&
      (context.workspaceId || '') === ticket.workspaceId
    );
  }

  function complete(ticket) {
    if (!ticket) return;
    const current = active.get(ticket.key);
    if (current?.sequence === ticket.sequence) {
      active.delete(ticket.key);
    }
  }

  function cancel(key) {
    const current = active.get(sanitize(key));
    if (current?.controller) {
      current.controller.abort();
    }
    active.delete(sanitize(key));
  }

  function cancelAll() {
    for (const current of active.values()) {
      if (current?.controller) {
        current.controller.abort();
      }
    }
    active.clear();
  }

  return {
    begin,
    isCurrent,
    complete,
    cancel,
    cancelAll,
  };
}
