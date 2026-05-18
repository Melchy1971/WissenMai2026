import { requestJson } from './client.js';

export function getChatSessions({ limit = 20, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return requestJson(`/api/v1/chat/sessions?${query.toString()}`);
}

export function createChatSession({ title }) {
  return requestJson('/api/v1/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export function getChatSession(id) {
  return requestJson(`/api/v1/chat/sessions/${id}`);
}

export function postChatMessage(id, { question, retrievalLimit = 8 }) {
  return requestJson(`/api/v1/chat/sessions/${id}/messages`, {
    method: 'POST',
    body: JSON.stringify({ question, retrieval_limit: retrievalLimit }),
  });
}