import { callApi } from '../lib/apiClient.js';
export async function getMemory(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return callApi(`/api/v1/memory${qs ? '?' + qs : ''}`);
}
export async function getMemoryReviewQueue() {
  return callApi('/api/v1/memory/review');
}
export async function approveMemory(id) {
  return callApi(`/api/v1/memory/review/${id}/approve`, { method: 'POST', body: JSON.stringify({}) });
}
export async function rejectMemory(id, reason) {
  return callApi(`/api/v1/memory/review/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) });
}
export async function getMemoryConflicts() {
  return callApi('/api/v1/memory/conflicts');
}
export async function searchMemory(query) {
  return callApi(`/api/v1/memory?q=${encodeURIComponent(query)}`);
}
