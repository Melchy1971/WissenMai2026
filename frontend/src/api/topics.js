import { requestJson } from './client.js';

// Expected backend API contract — endpoints return 404 until backend is implemented.
// When backend exists, this file is the only thing that changes.

export function getTopics({ q = '', limit = 100, offset = 0 } = {}, { signal, correlationId } = {}) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (q) query.set('q', q);
  return requestJson('/topics?' + query.toString(), { signal, correlationId });
}

export function getTopicDetail(id, { signal, correlationId } = {}) {
  return requestJson('/topics/' + id, { signal, correlationId });
}

export function createTopic(payload, { signal, correlationId } = {}) {
  return requestJson('/topics', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
    correlationId,
  });
}

export function updateTopic(id, payload, { signal, correlationId } = {}) {
  return requestJson('/topics/' + id, {
    method: 'PATCH',
    body: JSON.stringify(payload),
    signal,
    correlationId,
  });
}

export function deleteTopic(id, { signal, correlationId } = {}) {
  return requestJson('/topics/' + id, {
    method: 'DELETE',
    signal,
    correlationId,
  });
}
