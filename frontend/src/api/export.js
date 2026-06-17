import { requestJson, getApiRequestContext } from './client.js';

var BASE = '/api/v1/export';
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL != null ? import.meta.env.VITE_API_BASE_URL : 'http://127.0.0.1:8000').replace(/\/$/, '');

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

export function listExportJobs(params, options) {
  var p = params || {};
  return requestJson(
    withQuery(BASE + '/jobs', {
      limit: p.limit != null ? p.limit : 20,
      offset: p.offset != null ? p.offset : 0,
      status: p.status || '',
      format: p.format || '',
    }),
    options || {},
  );
}

export function createExportJob(fields, options) {
  var f = fields || {};
  return requestJson(BASE + '/jobs', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({
      source_type: f.sourceType,
      source_ids: f.sourceIds,
      export_format: f.exportFormat,
      file_name: f.fileName,
    }),
  }));
}

export function getExportJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId), options || {});
}

export function startExportJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/start', Object.assign({}, options || {}, {
    method: 'POST',
  }));
}

export function cancelExportJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/cancel', Object.assign({}, options || {}, {
    method: 'POST',
  }));
}

export function retryExportJob(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/retry', Object.assign({}, options || {}, {
    method: 'POST',
  }));
}

/**
 * Download export file — returns { blob, fileName }.
 * Uses fetch directly (binary, not JSON).
 */
export async function downloadExportFile(jobId) {
  var ctx = getApiRequestContext();
  var headers = { Accept: '*/*' };
  if (ctx.authToken) headers['Authorization'] = 'Bearer ' + ctx.authToken;
  if (ctx.workspaceId) headers['X-Workspace-Id'] = ctx.workspaceId;

  var resp = await fetch(API_BASE_URL + BASE + '/jobs/' + encodeURIComponent(jobId) + '/download', {
    headers: headers,
  });

  if (!resp.ok) {
    var errorText = await resp.text().catch(function() { return ''; });
    throw new Error('Download fehlgeschlagen (' + resp.status + '): ' + errorText);
  }

  var blob = await resp.blob();
  var disposition = resp.headers.get('Content-Disposition') || '';
  var match = disposition.match(/filename="?([^";\n]+)"?/);
  var fileName = match ? match[1] : 'export';
  return { blob: blob, fileName: fileName };
}

export function deleteExportFile(jobId, options) {
  return requestJson(BASE + '/jobs/' + encodeURIComponent(jobId) + '/file', Object.assign({}, options || {}, {
    method: 'DELETE',
  }));
}

// ── Templates ─────────────────────────────────────────────────────────────────

export function listExportTemplates(params, options) {
  var p = params || {};
  return requestJson(
    withQuery(BASE + '/templates', { format: p.format || '' }),
    options || {},
  );
}

export function createExportTemplate(fields, options) {
  var f = fields || {};
  return requestJson(BASE + '/templates', Object.assign({}, options || {}, {
    method: 'POST',
    body: JSON.stringify({
      name: f.name,
      export_format: f.exportFormat,
      layout_config: f.layoutConfig || null,
      is_default: f.isDefault || false,
    }),
  }));
}

export function updateExportTemplate(templateId, fields, options) {
  var f = fields || {};
  var body = {};
  if (f.name !== undefined) body.name = f.name;
  if (f.exportFormat !== undefined) body.export_format = f.exportFormat;
  if (f.layoutConfig !== undefined) body.layout_config = f.layoutConfig;
  if (f.isDefault !== undefined) body.is_default = f.isDefault;
  return requestJson(BASE + '/templates/' + encodeURIComponent(templateId), Object.assign({}, options || {}, {
    method: 'PUT',
    body: JSON.stringify(body),
  }));
}

export function deleteExportTemplate(templateId, options) {
  return requestJson(BASE + '/templates/' + encodeURIComponent(templateId), Object.assign({}, options || {}, {
    method: 'DELETE',
  }));
}

export var exportApi = {
  listJobs: listExportJobs,
  createJob: createExportJob,
  getJob: getExportJob,
  startJob: startExportJob,
  cancelJob: cancelExportJob,
  retryJob: retryExportJob,
  downloadFile: downloadExportFile,
  deleteFile: deleteExportFile,
  listTemplates: listExportTemplates,
  createTemplate: createExportTemplate,
  updateTemplate: updateExportTemplate,
  deleteTemplate: deleteExportTemplate,
};
