import { callApi } from '../lib/apiClient.js';
export async function getDocuments(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return callApi(`/api/v1/rag/documents${qs ? '?' + qs : ''}`);
}
export async function importDocument(formData) {
  // FormData – kein JSON.stringify, kein Content-Type header
  return callApi('/api/v1/rag/import', { method: 'POST', body: formData });
}
export async function reindexDocument(id) {
  return callApi(`/api/v1/rag/documents/${id}/reindex`, { method: 'POST', body: JSON.stringify({}) });
}
export async function testRetrieval(query) {
  return callApi('/api/v1/rag/test-retrieval', { method: 'POST', body: JSON.stringify({ query }) });
}
