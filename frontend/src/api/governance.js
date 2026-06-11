import { callApi } from '../lib/apiClient.js';

export async function getGovernanceStatus() {
  return callApi('/api/v1/governance/status');
}
export async function getApprovals() {
  return callApi('/api/v1/approvals');
}
export async function approveAction(id) {
  return callApi(`/api/v1/approvals/${id}/approve`, { method: 'POST', body: JSON.stringify({}) });
}
export async function rejectAction(id, reason) {
  return callApi(`/api/v1/approvals/${id}/reject`, { method: 'POST', body: JSON.stringify({ reason }) });
}
export async function getAuditLog(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return callApi(`/api/v1/audit${qs ? '?' + qs : ''}`);
}
export async function getChangeSets() {
  return callApi('/api/v1/changesets');
}
export async function applyChangeSet(id) {
  return callApi(`/api/v1/changesets/${id}/apply`, { method: 'POST', body: JSON.stringify({}) });
}
export async function getRollbackPoints() {
  return callApi('/api/v1/rollback');
}
export async function triggerRollback(id) {
  return callApi(`/api/v1/rollback/${id}`, { method: 'POST', body: JSON.stringify({}) });
}
export async function getPolicyDecisions() {
  return callApi('/api/v1/policies/decisions');
}
export async function togglePrivacyMode(enabled) {
  return callApi('/api/v1/settings', {
    method: 'PATCH',
    body: JSON.stringify({ section: 'governance', changes: { privacy_mode_enabled: enabled }, dry_run: false }),
  });
}
