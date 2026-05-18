import { requestJson } from './client.js';

export function getDocuments(
  { limit = 20, offset = 0, lifecycleStatus } = {},
  { signal, correlationId } = {},
) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  if (lifecycleStatus) {
    query.set('lifecycle_status', lifecycleStatus);
  }

  return requestJson(`/documents?${query.toString()}`, { signal, correlationId });
}

export function getDocumentDetail(id, { signal, correlationId } = {}) {
  return requestJson(`/documents/${id}`, { signal, correlationId });
}

export function getDocumentVersions(id, { signal, correlationId } = {}) {
  return requestJson(`/documents/${id}/versions`, { signal, correlationId });
}

export function getDocumentChunks(id, { limit } = {}, { signal, correlationId } = {}) {
  const query = new URLSearchParams();
  if (limit != null) {
    query.set('limit', String(limit));
  }

  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  return requestJson(`/documents/${id}/chunks${suffix}`, { signal, correlationId });
}

export function importDocument(file, { signal, correlationId } = {}) {
  const formData = new FormData();
  formData.append('file', file);

  return requestJson('/documents/import', {
    method: 'POST',
    body: formData,
    signal,
    correlationId,
  });
}

export function archiveDocument(id, { signal, correlationId } = {}) {
  return requestJson(`/documents/${id}/archive`, {
    method: 'PATCH',
    signal,
    correlationId,
  });
}

export function restoreDocument(id, { signal, correlationId } = {}) {
  return requestJson(`/documents/${id}/restore`, {
    method: 'PATCH',
    signal,
    correlationId,
  });
}

export function deleteDocument(id, { signal, correlationId } = {}) {
  return requestJson(`/documents/${id}`, {
    method: 'DELETE',
    signal,
    correlationId,
  });
}
