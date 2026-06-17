import { requestJson } from './client.js';

const BASE = '/api/v1/drift';

export function getDriftOverview(options = {}) {
  return requestJson(`${BASE}/overview`, options);
}

export function getDriftSnapshots(
  { type, status, page = 1, pageSize = 20 } = {},
  options = {},
) {
  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (status) params.set('status', status);
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return requestJson(`${BASE}/snapshots?${params}`, options);
}

export function getDriftSnapshot(id, options = {}) {
  return requestJson(`${BASE}/snapshots/${encodeURIComponent(id)}`, options);
}

export function getDriftSnapshotMetrics(id, options = {}) {
  return requestJson(
    `${BASE}/snapshots/${encodeURIComponent(id)}/metrics`,
    options,
  );
}

export function postDriftRecalculate(options = {}) {
  return requestJson(`${BASE}/snapshots/recalculate`, {
    ...options,
    method: 'POST',
  });
}

export const driftAnalyticsApi = {
  getOverview: getDriftOverview,
  getSnapshots: getDriftSnapshots,
  getSnapshot: getDriftSnapshot,
  getSnapshotMetrics: getDriftSnapshotMetrics,
  recalculate: postDriftRecalculate,
};
