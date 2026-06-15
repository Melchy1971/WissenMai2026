import { afterEach, describe, expect, it, vi } from 'vitest';

import { analysisApi } from '../../api/analysis.js';
import { dashboardApi } from '../../api/dashboard.js';
import { ApiClientError, setApiRequestContext } from '../../api/client.js';

function jsonResponse(payload, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 422 ? 'Unprocessable Entity' : 'OK',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async () => payload,
  };
}

function captureFetch(payload = {}) {
  let captured = null;
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, opts) => {
    captured = { url: String(url), opts };
    return jsonResponse(payload);
  });
  return () => captured;
}

afterEach(() => {
  vi.restoreAllMocks();
  setApiRequestContext({ authToken: '', workspaceId: '' });
});

describe('analysisApi contract alignment', () => {
  it('lists jobs with backend query contract', async () => {
    const getCapture = captureFetch({ items: [], total: 0, limit: 10, offset: 5 });

    await analysisApi.listJobs({ limit: 10, offset: 5, status: 'pending' });

    expect(getCapture().url).toContain('/api/v1/analysis/jobs?limit=10&offset=5&status=pending');
    expect(getCapture().opts.method).toBeUndefined();
  });

  it('creates jobs with snake_case backend payload', async () => {
    const getCapture = captureFetch({ id: 'job-1' });

    await analysisApi.createJob({
      sourceDocumentIds: ['doc-1', 'doc-2'],
      analysisType: 'comparison',
      prompt: 'Compare',
    });

    expect(getCapture().url).toContain('/api/v1/analysis/jobs');
    expect(getCapture().opts.method).toBe('POST');
    expect(JSON.parse(getCapture().opts.body)).toEqual({
      source_document_ids: ['doc-1', 'doc-2'],
      analysis_type: 'comparison',
      prompt: 'Compare',
    });
  });

  it('maps compare, summarize, approve, get and result endpoints', async () => {
    const getCapture = captureFetch({ ok: true });

    await analysisApi.getJob('job/1');
    expect(getCapture().url).toContain('/api/v1/analysis/jobs/job%2F1');

    await analysisApi.compareJob('job-1', { comparedDocumentIds: ['doc-2'], maxDifferences: 7 });
    expect(getCapture().url).toContain('/api/v1/analysis/jobs/job-1/compare');
    expect(JSON.parse(getCapture().opts.body)).toEqual({
      compared_document_ids: ['doc-2'],
      max_differences: 7,
    });

    await analysisApi.summarizeJob('job-1', { prompt: 'Privacy', maxSuggestions: 3 });
    expect(getCapture().url).toContain('/api/v1/analysis/jobs/job-1/summarize');
    expect(JSON.parse(getCapture().opts.body)).toEqual({
      prompt: 'Privacy',
      max_suggestions: 3,
    });

    await analysisApi.approveJob('job-1');
    expect(getCapture().url).toContain('/api/v1/analysis/jobs/job-1/approve');
    expect(JSON.parse(getCapture().opts.body)).toEqual({ decision: 'approved' });

    await analysisApi.getResult('job-1');
    expect(getCapture().url).toContain('/api/v1/analysis/jobs/job-1/result');
  });
});

describe('dashboardApi contract alignment', () => {
  it('maps all dashboard backend endpoints', async () => {
    const getCapture = captureFetch({ items: [], total: 0 });

    await dashboardApi.getSummary();
    expect(getCapture().url).toContain('/api/v1/dashboard/summary');

    await dashboardApi.getActivity({ limit: 11 });
    expect(getCapture().url).toContain('/api/v1/dashboard/activity?limit=11');

    await dashboardApi.getImports({ limit: 12 });
    expect(getCapture().url).toContain('/api/v1/dashboard/imports?limit=12');

    await dashboardApi.getAnalysis({ limit: 13 });
    expect(getCapture().url).toContain('/api/v1/dashboard/analysis?limit=13');

    await dashboardApi.getQuality({ limit: 14 });
    expect(getCapture().url).toContain('/api/v1/dashboard/quality?limit=14');

    await dashboardApi.getTopics({ limit: 15 });
    expect(getCapture().url).toContain('/api/v1/dashboard/topics?limit=15');
  });

  it('preserves response fields from dashboard summary contract', async () => {
    captureFetch({
      document_count: 2,
      active_document_count: 1,
      archived_document_count: 1,
      new_imports_count: 0,
      open_analysis_count: 0,
      topic_count: 3,
      quality_score: null,
      drift_status: null,
    });

    const summary = await dashboardApi.getSummary();

    expect(summary).toEqual({
      document_count: 2,
      active_document_count: 1,
      archived_document_count: 1,
      new_imports_count: 0,
      open_analysis_count: 0,
      topic_count: 3,
      quality_score: null,
      drift_status: null,
    });
  });
});

describe('shared auth and error handling', () => {
  it('sends Authorization and X-Workspace-Id through the central client', async () => {
    setApiRequestContext({ authToken: 'token-1', workspaceId: 'workspace-1' });
    const getCapture = captureFetch({ items: [], total: 0 });

    await analysisApi.listJobs({}, {
      headers: {
        Authorization: 'Bearer injected',
        'X-Workspace-Id': 'injected',
      },
    });

    expect(getCapture().opts.headers.Authorization).toBe('Bearer token-1');
    expect(getCapture().opts.headers['X-Workspace-Id']).toBe('workspace-1');
  });

  it('uses ApiClientError for backend validation failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(
        { error: { code: 'REQUEST_VALIDATION_FAILED', message: 'Invalid request', details: {} } },
        422,
      ),
    );

    const error = await analysisApi.createJob({
      sourceDocumentIds: [],
      analysisType: '',
      prompt: '',
    }).catch((caught) => caught);

    expect(error).toBeInstanceOf(ApiClientError);
    expect(error).toMatchObject({ code: 'VALIDATION_ERROR', status: 422 });
  });
});
