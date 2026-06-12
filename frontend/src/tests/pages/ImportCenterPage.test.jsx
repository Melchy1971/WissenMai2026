import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup, act } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { AuthProvider } from '../../auth/AuthContext.jsx';
import { setApiRequestContext } from '../../api/client.js';
import { ImportCenterPage } from '../../pages/ImportCenterPage.jsx';

// ── fixtures ──────────────────────────────────────────────────────────────────

var INITIAL_AUTH = {
  token: 'test-token',
  user: { id: 'user-1', login: 'test-user' },
  active_workspace_id: 'workspace-1',
  memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
};

var MOCK_FILE = new File(['PDF content'], 'bericht.pdf', { type: 'application/pdf' });

var JOB_QUEUED = {
  id: 'job-1',
  status: 'queued',
  job_type: 'document_import',
  result: null,
  error_code: null,
  error_message: null,
};

var JOB_COMPLETED = {
  id: 'job-1',
  status: 'completed',
  job_type: 'document_import',
  result: {
    document_id: 'doc-1',
    import_status: 'chunked',
    chunk_count: 7,
    parser_type: 'text',
  },
  error_code: null,
  error_message: null,
};

var JOB_DUPLICATE = {
  id: 'job-2',
  status: 'completed',
  job_type: 'document_import',
  result: {
    document_id: 'doc-99',
    import_status: 'duplicate',
    duplicate_of_document_id: 'doc-existing',
    chunk_count: 0,
    parser_type: 'text',
  },
  error_code: null,
  error_message: null,
};

var JOB_FAILED_OCR = {
  id: 'job-3',
  status: 'failed',
  job_type: 'document_import',
  result: null,
  error_code: 'OCR_REQUIRED',
  error_message: 'Das PDF enthält keinen extrahierbaren Text.',
};

// ── helpers ──────────────────────────────────────────────────────────────────

function jsonHeaders() {
  return new Headers({ 'content-type': 'application/json' });
}

function renderPage() {
  return render(
    React.createElement(AuthProvider, { initialAuthState: INITIAL_AUTH },
      React.createElement(MemoryRouter, { initialEntries: ['/import'] },
        React.createElement(Routes, null,
          React.createElement(Route, { path: '/import', element: React.createElement(ImportCenterPage) }),
          React.createElement(Route, { path: '/documents/:id', element: React.createElement('div', { 'data-testid': 'doc-page' }, 'Dokument') })
        )
      )
    )
  );
}

function primeRequestContext() {
  setApiRequestContext({ authToken: 'test-token', workspaceId: 'workspace-1' });
}

// Mock: upload → job immediately completed
function mockSuccessFlow(jobData) {
  var job = jobData || JOB_COMPLETED;
  vi.spyOn(globalThis, 'fetch').mockImplementation(function(url) {
    if (String(url).includes('/documents/import')) {
      return Promise.resolve({
        ok: true,
        status: 202,
        headers: jsonHeaders(),
        json: async function() { return JOB_QUEUED; },
      });
    }
    if (String(url).includes('/jobs/')) {
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: jsonHeaders(),
        json: async function() { return job; },
      });
    }
    return Promise.reject(new Error('Unexpected fetch: ' + url));
  });
}

function mockUploadHttpError(code, status) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(function(url) {
    if (String(url).includes('/documents/import')) {
      return Promise.resolve({
        ok: false,
        status: status || 422,
        headers: jsonHeaders(),
        json: async function() { return { error: { code: code } }; },
      });
    }
    return Promise.reject(new Error('Unexpected fetch: ' + url));
  });
}

function setFile(file) {
  var input = screen.getByTestId('file-input');
  Object.defineProperty(input, 'files', { value: [file], configurable: true });
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('ImportCenterPage', function() {
  afterEach(function() {
    setApiRequestContext({ authToken: '', workspaceId: '' });
    vi.restoreAllMocks();
    cleanup();
  });

  it('renders upload form in idle state', function() {
    primeRequestContext();
    renderPage();
    expect(screen.getByTestId('import-center-page')).toBeTruthy();
    expect(screen.getByTestId('upload-form')).toBeTruthy();
    expect(screen.getByTestId('file-input')).toBeTruthy();
    expect(screen.getByTestId('upload-submit').textContent).toBe('Importieren');
    // Status and history not shown yet
    expect(screen.queryByTestId('import-phase')).toBeNull();
    expect(screen.queryByTestId('import-history')).toBeNull();
    expect(screen.queryByTestId('reset-button')).toBeNull();
  });

  it('shows error when submitting without a file', async function() {
    primeRequestContext();
    renderPage();
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-error')).toBeTruthy();
    });
  });

  it('shows uploading phase while POST /documents/import is in-flight', async function() {
    primeRequestContext();
    // Make fetch hang so we can observe the uploading state
    var resolveUpload;
    vi.spyOn(globalThis, 'fetch').mockImplementation(function() {
      return new Promise(function(resolve) { resolveUpload = resolve; });
    });
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-phase')).toBeTruthy();
      expect(screen.getByTestId('upload-submit').disabled).toBe(true);
    });
    // Cleanup: resolve the hanging fetch
    resolveUpload({
      ok: false,
      status: 503,
      headers: jsonHeaders(),
      json: async function() { return {}; },
    });
  });

  it('shows success panel after completed import', async function() {
    primeRequestContext();
    mockSuccessFlow();
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-success')).toBeTruthy();
    }, { timeout: 2000 });
  });

  it('shows document id link after successful import', async function() {
    primeRequestContext();
    mockSuccessFlow();
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-document-id').textContent).toBe('doc-1');
    }, { timeout: 2000 });
  });

  it('shows chunk count after successful import', async function() {
    primeRequestContext();
    mockSuccessFlow();
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-chunks').textContent).toContain('7');
    }, { timeout: 2000 });
  });

  it('shows duplicate message for duplicate import', async function() {
    primeRequestContext();
    mockSuccessFlow(JOB_DUPLICATE);
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      var success = screen.getByTestId('import-success');
      // mapImportOutcome maps duplicate → 'bereits vorhanden' or similar
      expect(success.textContent).toBeTruthy();
    }, { timeout: 2000 });
    // Outcome title for duplicate contains a differentiated message
    var success = screen.getByTestId('import-success');
    expect(success.textContent.toLowerCase()).toMatch(/duplikat|vorhanden|bereits|duplicate/i);
  });

  it('shows error panel when job fails with OCR_REQUIRED', async function() {
    primeRequestContext();
    mockSuccessFlow(JOB_FAILED_OCR);
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-error')).toBeTruthy();
    }, { timeout: 2000 });
  });

  it('shows error panel when upload endpoint returns HTTP error', async function() {
    primeRequestContext();
    mockUploadHttpError('FILE_TOO_LARGE', 413);
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-error')).toBeTruthy();
    }, { timeout: 2000 });
  });

  it('reset button clears current state back to idle', async function() {
    primeRequestContext();
    mockSuccessFlow();
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-success')).toBeTruthy();
    }, { timeout: 2000 });
    // Reset button is visible after import
    var resetBtn = screen.getByTestId('reset-button');
    fireEvent.click(resetBtn);
    await waitFor(function() {
      expect(screen.queryByTestId('import-success')).toBeNull();
      expect(screen.queryByTestId('import-phase')).toBeNull();
    });
  });

  it('history table appears after first successful import', async function() {
    primeRequestContext();
    mockSuccessFlow();
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-history')).toBeTruthy();
    }, { timeout: 2000 });
    expect(screen.getByTestId('history-count').textContent).toBe('1');
    expect(screen.getAllByTestId('history-row')).toHaveLength(1);
  });

  it('history persists after reset and shows success status', async function() {
    primeRequestContext();
    mockSuccessFlow();
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-success')).toBeTruthy();
    }, { timeout: 2000 });
    // Reset clears current but history remains
    fireEvent.click(screen.getByTestId('reset-button'));
    await waitFor(function() {
      expect(screen.queryByTestId('import-phase')).toBeNull();
      expect(screen.getByTestId('import-history')).toBeTruthy();
    });
    var rows = screen.getAllByTestId('history-row');
    expect(rows).toHaveLength(1);
    expect(rows[0].textContent).toContain('Erfolg');
  });

  it('history shows error status after failed job', async function() {
    primeRequestContext();
    mockSuccessFlow(JOB_FAILED_OCR);
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-history')).toBeTruthy();
    }, { timeout: 2000 });
    var row = screen.getByTestId('history-row');
    expect(row.textContent).toContain('Fehler');
  });

  it('subtitle updates to show number of imported documents', async function() {
    primeRequestContext();
    mockSuccessFlow();
    renderPage();
    expect(screen.getByTestId('import-subtitle').textContent).toContain('importieren');
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(screen.getByTestId('import-subtitle').textContent).toContain('1 Dokument importiert');
    }, { timeout: 2000 });
  });

  it('sends Authorization header with import request', async function() {
    primeRequestContext();
    var capturedHeaders = null;
    vi.spyOn(globalThis, 'fetch').mockImplementation(function(url, opts) {
      capturedHeaders = opts && opts.headers;
      return Promise.resolve({
        ok: true,
        status: 202,
        headers: jsonHeaders(),
        json: async function() { return JOB_QUEUED; },
      });
    });
    // Mock job poll to avoid hanging
    var callCount = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(function(url, opts) {
      if (String(url).includes('/documents/import')) {
        capturedHeaders = opts && opts.headers;
        return Promise.resolve({
          ok: true,
          status: 202,
          headers: jsonHeaders(),
          json: async function() { return JOB_QUEUED; },
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        headers: jsonHeaders(),
        json: async function() { return JOB_COMPLETED; },
      });
    });
    renderPage();
    setFile(MOCK_FILE);
    fireEvent.submit(screen.getByTestId('upload-form'));
    await waitFor(function() {
      expect(capturedHeaders).toBeTruthy();
    });
    var authHeader = capturedHeaders instanceof Headers
      ? capturedHeaders.get('authorization')
      : (capturedHeaders && (capturedHeaders['authorization'] || capturedHeaders['Authorization']));
    expect(authHeader).toContain('Bearer test-token');
  });
});
