import { requestJson } from './client.js';

export async function getSearchIndexInconsistencies() {
  return requestJson('/api/v1/admin/search-index/inconsistencies');
}

export async function getDiagnostics() {
  return requestJson('/api/v1/admin/diagnostics');
}
