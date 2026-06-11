import { callApi } from '../lib/apiClient.js';

export async function getSystemStatus() {
  return callApi('/api/v1/status');
}

export async function getHealth() {
  return callApi('/api/v1/health');
}
