import { requestJson } from './client.js';

const BASE = '/api/v1/topics';

export function getTopics({ q = '', limit = 100, offset = 0 } = {}, { signal, correlationId } = {}) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (q) query.set('q', q);
  return requestJson(BASE + '?' + query.toString(), { signal, correlationId });
}

export function getTopicDetail(id, { signal, correlationId } = {}) {
  return requestJson(BASE + '/' + id, { signal, correlationId });
}

export function createTopic(payload, { signal, correlationId } = {}) {
  return requestJson(BASE, {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
    correlationId,
  });
}

export function updateTopic(id, payload, { signal, correlationId } = {}) {
  return requestJson(BASE + '/' + id, {
    method: 'PATCH',
    body: JSON.stringify(payload),
    signal,
    correlationId,
  });
}

export function deleteTopic(id, { signal, correlationId } = {}) {
  return requestJson(BASE + '/' + id, {
    method: 'DELETE',
    signal,
    correlationId,
  });
}
