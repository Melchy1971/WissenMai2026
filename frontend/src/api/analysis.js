import { requestJson } from './client.js';

var BASE = '/api/v1/analysis';

function withQuery(path, params) {
  var query = new URLSearchParams();
  for (var key of Object.keys(params)) {
    var value = params[key];
    if (value !== undefined && value !== null && value !== '') {
      query.set(key, String(value));
    }
  }
  var suffix = query.size > 0 ? ('?' + query.toString()) : '';
  return path + suffix;
}

// ── Jobs ──────────────────────────────────────────────────────────────────────

export function listAnalysisJobs(params, options) {
  var p = params || {};
  var limit = p.limit != null ? p.limit : 20;
  var offset = p.offset != null ? p.offset : 0;
  var status = p.status != null ? p.status : null;
  var source_type = p.sourceType != null ? p.sourceType : null;
  return requestJson(
    withQuery(BASE + '/jobs', { limit: limit, offset: offset, status: status, source_type: source_type }),
    options || {},
  );
}

export function createAnalysisJob(fields, options) {
  var f = fields || {};
  return requestJson(BASE + '/jobs', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({
      source_document_ids: f.sourceDocumentIds || [],
      analysis_type: f.analysisType,
      prompt: f.prompt,
      source_type: f.sourceType || null,
      source_ids: f.sourceIds || null,
      provider: f.provider || null,
      model: f.model || null,
    }),
  }));
}

export function getAnalysisJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId), options || {});
}

export function cancelAnalysisJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/cancel', Object.assign({}, options || {}, {
    method: 'POST',
  }));
}

export function retryAnalysisJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/retry', Object.assign({}, options || {}, {
    method: 'POST',
  }));
}

// ── Results ───────────────────────────────────────────────────────────────────

export function getAnalysisResult(resultId, options) {
  return requestJson(BASE + '/results/' + encodeURIComponent(resultId), options || {});
}

export function updateAnalysisResult(resultId, fields, options) {
  return requestJson(BASE + '/results/' + encodeURIComponent(resultId), Object.assign({}, options || {}, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  }));
}

export function markResultForReview(resultId, note, options) {
  return requestJson(BASE + '/results/' + encodeURIComponent(resultId) + '/review', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({ note: note || null }),
  }));
}

export function approveAnalysisResult(resultId, reviewerNote, options) {
  return requestJson(BASE + '/results/' + encodeURIComponent(resultId) + '/approve', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({ confirm: true, reviewer_note: reviewerNote || null }),
  }));
}

export function rejectAnalysisResult(resultId, reason, options) {
  return requestJson(BASE + '/results/' + encodeURIComponent(resultId) + '/reject', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({ reason: reason }),
  }));
}

// ── Legacy (backward compat) ──────────────────────────────────────────────────

export function compareAnalysisJob(jobId, params, options) {
  var p = params || {};
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/compare', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({
      compared_document_ids: p.comparedDocumentIds || [],
      max_differences: p.maxDifferences != null ? p.maxDifferences : 50,
    }),
  }));
}

export function summarizeAnalysisJob(jobId, params, options) {
  var p = params || {};
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/summarize', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({ prompt: p.prompt || null, max_suggestions: p.maxSuggestions != null ? p.maxSuggestions : 10 }),
  }));
}

export function approveAnalysisJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/approve', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({ decision: 'approved' }),
  }));
}

export function getAnalysisResultByJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/result', options || {});
}

// IMPORT GUARD CONTRACT: only callable after result.status === 'approved'.
// The UI enforces this in AnalysisResultPanel — the button is not rendered otherwise.
export function importAnalysisResult(resultId, options) {
  return requestJson(BASE + '/results/' + encodeURIComponent(resultId) + '/import', Object.assign({}, options || {}, {
    method: 'POST',
  }));
}

export var analysisApi = {
  listJobs: listAnalysisJobs,
  createJob: createAnalysisJob,
  getJob: getAnalysisJob,
  cancelJob: cancelAnalysisJob,
  retryJob: retryAnalysisJob,
  getResult: getAnalysisResult,
  updateResult: updateAnalysisResult,
  markForReview: markResultForReview,
  approveResult: approveAnalysisResult,
  rejectResult: rejectAnalysisResult,
  importResult: importAnalysisResult,
  // legacy
  compareJob: compareAnalysisJob,
  summarizeJob: summarizeAnalysisJob,
  approveJob: approveAnalysisJob,
  getResultByJob: getAnalysisResultByJob,
};
