import { callApi } from '../lib/apiClient.js';
export async function getProjects() {
  return callApi('/api/v1/projects');
}
export async function createProject(data) {
  return callApi('/api/v1/projects', { method: 'POST', body: JSON.stringify(data) });
}
export async function updateProject(id, changes) {
  return callApi(`/api/v1/projects/${id}`, { method: 'PATCH', body: JSON.stringify(changes) });
}
