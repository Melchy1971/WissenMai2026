import { requestJson } from '../../api/client.js';

const BASE = '/api/v1/drift';

function withQuery(path, params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value != null && value !== '') {
      query.set(key, String(value));
    }
  });
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export function getDriftSummary(options = {}) {
  return requestJson(`${BASE}/summary`, options);
}

export function listDriftFindings(
  { severityFilter = null, typeFilter = null, limit = 50, offset = 0 } = {},
  options = {},
) {
  return requestJson(
    withQuery(`${BASE}/findings`, {
      severity: severityFilter,
      finding_type: typeFilter,
      limit,
      offset,
    }),
    options,
  );
}

export const driftApi = {
  getSummary: getDriftSummary,
  listFindings: listDriftFindings,
};
