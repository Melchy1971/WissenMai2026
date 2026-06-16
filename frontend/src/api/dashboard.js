import { requestJson } from './client.js';

const BASE = '/api/v1/dashboard';

function withLimit(path, limit) {
  if (limit == null) return path;
  const query = new URLSearchParams({ limit: String(limit) });
  return `${path}?${query.toString()}`;
}

export function getDashboardSummary(options = {}) {
  return requestJson(`${BASE}/summary`, options);
}

export function getDashboardActivity({ limit = 20 } = {}, options = {}) {
  return requestJson(withLimit(`${BASE}/activity`, limit), options);
}

export function getDashboardImports({ limit = 20 } = {}, options = {}) {
  return requestJson(withLimit(`${BASE}/imports`, limit), options);
}

export function getDashboardAnalysis({ limit = 20 } = {}, options = {}) {
  return requestJson(withLimit(`${BASE}/analysis`, limit), options);
}

export function getDashboardQuality({ limit = 20 } = {}, options = {}) {
  return requestJson(withLimit(`${BASE}/quality`, limit), options);
}

export function getDashboardTopics({ limit = 50 } = {}, options = {}) {
  return requestJson(withLimit(`${BASE}/topics`, limit), options);
}

export const dashboardApi = {
  getSummary: getDashboardSummary,
  getActivity: getDashboardActivity,
  getImports: getDashboardImports,
  getAnalysis: getDashboardAnalysis,
  getQuality: getDashboardQuality,
  getTopics: getDashboardTopics,
};

export function getDashboardTopicsWidgets(options = {}) {
  return requestJson(`${BASE}/topics-widgets`, options);
}
