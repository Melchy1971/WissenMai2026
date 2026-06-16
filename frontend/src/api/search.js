import { requestJson } from './client.js';

export function searchChunks({ query, limit = 20, offset = 0 }, { signal, correlationId } = {}) {
  const search = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  });

  return requestJson(`/api/v1/search/chunks?${search.toString()}`, { signal, correlationId });
}

export function searchUnified(
  { query, limit = 20, cursor, sort = 'score_desc', kind, status },
  { signal, correlationId } = {}
) {
  var params = new URLSearchParams({ q: query, limit: String(limit), sort });
  if (cursor) params.set('cursor', cursor);
  if (Array.isArray(kind) && kind.length) kind.forEach(function(k) { params.append('kind', k); });
  if (Array.isArray(status) && status.length) status.forEach(function(s) { params.append('status', s); });
  return requestJson('/api/v1/search/unified?' + params.toString(), { signal, correlationId });
}
