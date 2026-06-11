import { callApi } from '../lib/apiClient.js';
export async function getTeams() {
  return callApi('/api/v1/collaboration/teams');
}
export async function getCollaborationRuns() {
  return callApi('/api/v1/collaboration/runs');
}
