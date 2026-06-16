import { requestJson } from './client.js';

export async function getSystemStatus(options = {}) {
  return requestJson('/api/v1/status', options);
}

export async function getHealth(options = {}) {
  return requestJson('/api/v1/health', options);
}
