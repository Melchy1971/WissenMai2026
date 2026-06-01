import { requestJson } from './client.js';

const BASE = '/api/v1/data-quality';

export async function getDataQualitySummary() {
  return requestJson(`${BASE}/summary`);
}

export async function listDataQualityRuns({ limit = 20, offset = 0 } = {}) {
  return requestJson(`${BASE}/runs?limit=${limit}&offset=${offset}`);
}

export async function getDataQualityRun(runId) {
  return requestJson(`${BASE}/runs/${encodeURIComponent(runId)}`);
}

export async function listDataQualityFindings({
  runId = null,
  severity = null,
  findingType = null,
  documentId = null,
  limit = 50,
  offset = 0,
} = {}) {
  const params = new URLSearchParams();
  if (runId != null) params.set('run_id', runId);
  if (severity != null) params.set('severity', severity);
  if (findingType != null) params.set('finding_type', findingType);
  if (documentId != null) params.set('document_id', documentId);
  params.set('limit', String(limit));
  params.set('offset', String(offset));
  return requestJson(`${BASE}/findings?${params.toString()}`);
}
