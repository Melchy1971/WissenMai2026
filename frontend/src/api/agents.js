import { callApi } from '../lib/apiClient.js';
export async function getAgents() {
  return callApi('/api/v1/agents');
}
export async function getAgentExecutions() {
  return callApi('/api/v1/agents/executions');
}
export async function updateAgent(id, changes) {
  return callApi(`/api/v1/agents/${id}`, { method: 'PATCH', body: JSON.stringify(changes) });
}
