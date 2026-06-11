import { callApi } from '../lib/apiClient.js';
export async function getTasks(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return callApi(`/api/v1/tasks${qs ? '?' + qs : ''}`);
}
export async function createTask(data) {
  return callApi('/api/v1/tasks', { method: 'POST', body: JSON.stringify(data) });
}
export async function updateTask(id, changes) {
  return callApi(`/api/v1/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(changes) });
}
