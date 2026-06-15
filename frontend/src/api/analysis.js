import { requestJson } from './client.js';

const BASE = '/api/v1/analysis';

function withQuery(path, params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  }
  const suffix = query.size > 0 ? `?${query.toString()}` : '';
  return `${path}${suffix}`;
}

export function listAnalysisJobs({ limit = 20, offset = 0, status = null } = {}, options = {}) {
  return requestJson(withQuery(`${BASE}/jobs`, { limit, offset, status }), options);
}

export function createAnalysisJob({ sourceDocumentIds, analysisType, prompt }, options = {}) {
  return requestJson(`${BASE}/jobs`, {
    ...options,
    method: 'POST',
    body: JSON.stringify({
      source_document_ids: sourceDocumentIds,
      analysis_type: analysisType,
      prompt,
    }),
  });
}

export function getAnalysisJob(jobId, options = {}) {
  return requestJson(`${BASE}/jobs/${encodeURIComponent(jobId)}`, options);
}

export function compareAnalysisJob(
  jobId,
  { comparedDocumentIds = [], maxDifferences = 50 } = {},
  options = {},
) {
  return requestJson(`${BASE}/jobs/${encodeURIComponent(jobId)}/compare`, {
    ...options,
    method: 'POST',
    body: JSON.stringify({
      compared_document_ids: comparedDocumentIds,
      max_differences: maxDifferences,
    }),
  });
}

export function summarizeAnalysisJob(
  jobId,
  { prompt = null, maxSuggestions = 10 } = {},
  options = {},
) {
  return requestJson(`${BASE}/jobs/${encodeURIComponent(jobId)}/summarize`, {
    ...options,
    method: 'POST',
    body: JSON.stringify({
      prompt,
      max_suggestions: maxSuggestions,
    }),
  });
}

export function approveAnalysisJob(jobId, options = {}) {
  return requestJson(`${BASE}/jobs/${encodeURIComponent(jobId)}/approve`, {
    ...options,
    method: 'POST',
    body: JSON.stringify({ decision: 'approved' }),
  });
}

export function getAnalysisResult(jobId, options = {}) {
  return requestJson(`${BASE}/jobs/${encodeURIComponent(jobId)}/result`, options);
}

export const analysisApi = {
  listJobs: listAnalysisJobs,
  createJob: createAnalysisJob,
  getJob: getAnalysisJob,
  compareJob: compareAnalysisJob,
  summarizeJob: summarizeAnalysisJob,
  approveJob: approveAnalysisJob,
  getResult: getAnalysisResult,
};
