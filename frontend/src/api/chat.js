import { requestJson } from './client.js';

export function getChatSessions({ limit = 20, offset = 0 } = {}, { signal, correlationId } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return requestJson(`/api/v1/chat/sessions?${query.toString()}`, { signal, correlationId });
}

export function createChatSession({ title }, { signal, correlationId } = {}) {
  return requestJson('/api/v1/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
    signal,
    correlationId,
  });
}

export function getChatSession(id, { signal, correlationId } = {}) {
  return requestJson(`/api/v1/chat/sessions/${id}`, { signal, correlationId });
}

export function postChatMessage(id, { question, retrievalLimit = 8 }, { signal, correlationId } = {}) {
  return requestJson(`/api/v1/chat/sessions/${id}/messages`, {
    method: 'POST',
    body: JSON.stringify({ question, retrieval_limit: retrievalLimit }),
    signal,
    correlationId,
  });
}
