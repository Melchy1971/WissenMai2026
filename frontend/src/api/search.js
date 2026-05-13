import { requestJson } from './client.js';

export function searchChunks({ query, limit = 20, offset = 0 }, { signal } = {}) {
  const search = new URLSearchParams({
    q: query,
    limit: String(limit),
    offset: String(offset),
  });

  return requestJson(`/api/v1/search/chunks?${search.toString()}`, { signal });
}