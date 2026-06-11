import { callApi } from '../lib/apiClient.js';
export async function getSecurityStatus() {
  return callApi('/api/v1/security/status');
}
