import { callApi } from '../lib/apiClient.js';
export async function getSettings() {
  return callApi('/api/v1/settings');
}
export async function patchSettings(section, changes, dry_run = false) {
  // WICHTIG: Secrets werden NICHT geloggt
  return callApi('/api/v1/settings', {
    method: 'PATCH',
    body: JSON.stringify({ section, changes, dry_run }),
  });
}
