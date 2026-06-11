import { callApi } from '../lib/apiClient.js';
export async function getTools() {
  return callApi('/api/v1/tools');
}
export async function checkToolHealth(id) {
  return callApi(`/api/v1/tools/${id}/health`, { method: 'POST', body: JSON.stringify({}) });
}
export async function updateTool(id, changes) {
  return callApi(`/api/v1/tools/${id}`, { method: 'PATCH', body: JSON.stringify(changes) });
}
