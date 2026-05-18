import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../auth/AuthContext.jsx';
import { setApiRequestContext } from '../../api/client.js';
import { DocumentsPage } from '../../pages/DocumentsPage.jsx';

function renderPage(initialEntry = '/documents') {
  return render(
    <AuthProvider
      initialAuthState={{
        token: 'test-token',
        user: { id: 'user-1', login: 'test-user' },
        active_workspace_id: 'workspace-1',
        memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      }}
    >
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/documents" element={<DocumentsPage />} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

describe('DocumentsPage', () => {
  afterEach(() => {
    setApiRequestContext({ authToken: '', workspaceId: '' });
    vi.restoreAllMocks();
    cleanup();
  });

  function primeRequestContext() {
    setApiRequestContext({ authToken: 'test-token', workspaceId: 'workspace-1' });
  }

  it('renders documents from the API', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ([
        {
          id: 'doc-1',
          title: 'Vertragsentwurf',
          mime_type: 'text/plain',
          created_at: '2026-05-01T10:00:00',
          updated_at: '2026-05-01T10:10:00',
          latest_version_id: 'ver-1',
          import_status: 'chunked',
          lifecycle_status: 'active',
          version_count: 1,
          chunk_count: 2,
        },
      ]),
    });

    renderPage();

    expect(screen.getByText(/Dokumente werden geladen/i)).toBeInTheDocument();
    expect(await screen.findByText('Vertragsentwurf')).toBeInTheDocument();
    expect(screen.getByText('Lesbar')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/documents?limit=20&offset=0&lifecycle_status=active'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
          'X-Workspace-Id': 'workspace-1',
        }),
      }),
    );
  });

  it('renders empty state for an empty list', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ([]),
    });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();
  });

  it('renders visible error code on API errors', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ error: { code: 'SERVICE_UNAVAILABLE', message: 'Service unavailable', details: {} } }),
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Serverfehler')).toBeInTheDocument();
    });
    expect(screen.getByText(/Fehlercode: SERVICE_UNAVAILABLE/i)).toBeInTheDocument();
  });

  it('renders search results with preview and source anchor', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([
          {
            id: 'doc-1',
            title: 'Vertragsentwurf',
            mime_type: 'text/plain',
            created_at: '2026-05-01T10:00:00',
            updated_at: '2026-05-01T10:10:00',
            latest_version_id: 'ver-1',
            import_status: 'chunked',
            lifecycle_status: 'active',
            version_count: 1,
            chunk_count: 2,
          },
        ]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([
          {
            document_id: 'doc-1',
            document_title: 'Vertragsentwurf',
            document_version_id: 'ver-1',
            version_number: 1,
            chunk_id: 'chunk-1',
            position: 0,
            text_preview: 'Abschnitt mit Suchtreffer',
            source_anchor: {
              type: 'text',
              page: null,
              paragraph: null,
              char_start: 10,
              char_end: 42,
            },
            rank: 0.91,
          },
        ]),
      });

    renderPage();

    expect(await screen.findByText('Vertragsentwurf')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/vertragsentwurf oder paragraph 5/i), {
      target: { value: 'vertragsentwurf' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));

    expect(await screen.findByText(/Treffer fuer/i)).toBeInTheDocument();
    expect(screen.getByText('Abschnitt mit Suchtreffer')).toBeInTheDocument();
    expect(screen.getByText(/Quelle: text \| Zeichen 10-42/i)).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Vertragsentwurf' })[0]).toHaveAttribute(
      'href',
      '/documents/doc-1',
    );
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/api/v1/search/chunks?q=vertragsentwurf&limit=10&offset=0'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
          'X-Workspace-Id': 'workspace-1',
        }),
      }),
    );
  });

  it('renders empty search state when no results are found', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/vertragsentwurf oder paragraph 5/i), {
      target: { value: 'foo' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));

    expect(await screen.findByText('Keine Treffer gefunden')).toBeInTheDocument();
  });

  it('renders search error state when search api fails', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ error: { code: 'INVALID_QUERY', message: 'Invalid search query', details: {} } }),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText(/vertragsentwurf oder paragraph 5/i), {
      target: { value: '***' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Suchen' }));

    expect(await screen.findByText('Validierungsfehler')).toBeInTheDocument();
    expect(screen.getByText(/Fehlercode: INVALID_QUERY/i)).toBeInTheDocument();
  });

  it('uploads a document through the queued import flow and refreshes the list', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-1',
          job_type: 'document_import',
          status: 'queued',
          workspace_id: 'workspace-1',
          requested_by_user_id: null,
          filename: 'notes.txt',
          created_at: '2026-05-05T00:00:00Z',
          started_at: null,
          finished_at: null,
          progress_current: 0,
          progress_total: 1,
          progress_message: 'Import ist in Warteschlange',
          error_code: null,
          error_message: null,
          result: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-1',
          job_type: 'document_import',
          status: 'completed',
          workspace_id: 'workspace-1',
          requested_by_user_id: null,
          filename: 'notes.txt',
          created_at: '2026-05-05T00:00:00Z',
          started_at: '2026-05-05T00:00:01Z',
          finished_at: '2026-05-05T00:00:02Z',
          progress_current: 1,
          progress_total: 1,
          progress_message: 'Import abgeschlossen',
          error_code: null,
          error_message: null,
          result: {
            document_id: 'doc-2',
            version_id: 'ver-2',
            import_status: 'chunked',
            duplicate_of_document_id: null,
            chunk_count: 4,
            parser_type: 'txt-parser',
            warnings: [],
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([
          {
            id: 'doc-2',
            title: 'notes',
            mime_type: 'text/plain',
            created_at: '2026-05-05T00:00:02Z',
            updated_at: '2026-05-05T00:00:02Z',
            latest_version_id: 'ver-2',
            import_status: 'chunked',
            lifecycle_status: 'active',
            version_count: 1,
            chunk_count: 4,
          },
        ]),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(screen.getByLabelText('Datei'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: 'Dokument importieren' }));

    expect(await screen.findByText(/notes.txt erfolgreich verarbeitet/i)).toBeInTheDocument();
    expect(screen.getByText('doc-2')).toBeInTheDocument();
    expect(screen.getByText('chunked')).toBeInTheDocument();
    expect(await screen.findByText('notes')).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenCalledTimes(4);
  });

  it('renders normalized queued upload job status labels', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-queued',
          job_type: 'document_import',
          status: 'queued',
          workspace_id: 'workspace-1',
          requested_by_user_id: null,
          filename: 'notes.txt',
          created_at: '2026-05-05T00:00:00Z',
          started_at: null,
          finished_at: null,
          progress_current: 0,
          progress_total: 1,
          progress_message: null,
          error_code: null,
          error_message: null,
          result: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-queued',
          job_type: 'document_import',
          status: 'queued',
          workspace_id: 'workspace-1',
          requested_by_user_id: null,
          filename: 'notes.txt',
          created_at: '2026-05-05T00:00:00Z',
          started_at: null,
          finished_at: null,
          progress_current: 0,
          progress_total: 1,
          progress_message: null,
          error_code: null,
          error_message: null,
          result: null,
        }),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(screen.getByLabelText('Datei'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: 'Dokument importieren' }));

    expect(await screen.findByText('In Warteschlange')).toBeInTheDocument();
    expect(screen.getByText('Import wartet auf Ausfuehrung.')).toBeInTheDocument();
  });

  it('shows duplicate imports as existing documents instead of generic success', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-dup',
          job_type: 'document_import',
          status: 'queued',
          workspace_id: 'workspace-1',
          requested_by_user_id: 'user-1',
          filename: 'notes.txt',
          created_at: '2026-05-05T00:00:00Z',
          started_at: null,
          finished_at: null,
          progress_current: 0,
          progress_total: 1,
          progress_message: 'Import ist in Warteschlange',
          error_code: null,
          error_message: null,
          result: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-dup',
          job_type: 'document_import',
          status: 'completed',
          workspace_id: 'workspace-1',
          requested_by_user_id: 'user-1',
          filename: 'notes.txt',
          created_at: '2026-05-05T00:00:00Z',
          started_at: '2026-05-05T00:00:01Z',
          finished_at: '2026-05-05T00:00:02Z',
          progress_current: 1,
          progress_total: 1,
          progress_message: 'Import abgeschlossen',
          error_code: null,
          error_message: null,
          result: {
            document_id: 'doc-2',
            version_id: 'ver-2',
            import_status: 'duplicate',
            duplicate_of_document_id: 'doc-2',
            chunk_count: 4,
            parser_type: 'txt-parser',
            warnings: [],
          },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(screen.getByLabelText('Datei'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: 'Dokument importieren' }));

    expect(await screen.findByText('Duplicate erkannt')).toBeInTheDocument();
    expect(screen.getByText(/notes.txt ist bereits vorhanden/i)).toBeInTheDocument();
    expect(screen.getByText('DUPLICATE_DOCUMENT')).toBeInTheDocument();
    expect(screen.getByText('duplicate')).toBeInTheDocument();
    expect(screen.getByText('txt-parser')).toBeInTheDocument();
    expect(screen.getAllByText('doc-2')).toHaveLength(2);
  });

  it('maps ocr-required upload failures to a specific error title', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-ocr',
          job_type: 'document_import',
          status: 'queued',
          workspace_id: 'workspace-1',
          requested_by_user_id: 'user-1',
          filename: 'scan.pdf',
          created_at: '2026-05-05T00:00:00Z',
          started_at: null,
          finished_at: null,
          progress_current: 0,
          progress_total: 1,
          progress_message: 'Import ist in Warteschlange',
          error_code: null,
          error_message: null,
          result: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-ocr',
          job_type: 'document_import',
          status: 'failed',
          workspace_id: 'workspace-1',
          requested_by_user_id: 'user-1',
          filename: 'scan.pdf',
          created_at: '2026-05-05T00:00:00Z',
          started_at: '2026-05-05T00:00:01Z',
          finished_at: '2026-05-05T00:00:02Z',
          progress_current: 1,
          progress_total: 1,
          progress_message: 'Import fehlgeschlagen',
          error_code: 'OCR_REQUIRED',
          error_message: 'OCR required but no OCR engine is configured',
          result: null,
        }),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    const file = new File(['fake'], 'scan.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByLabelText('Datei'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: 'Dokument importieren' }));

    expect(await screen.findByText('OCR erforderlich')).toBeInTheDocument();
    expect(screen.getByText(/Fehlercode: OCR_REQUIRED/i)).toBeInTheDocument();
  });

  it('maps parser failures to a specific error title', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-parser',
          job_type: 'document_import',
          status: 'queued',
          workspace_id: 'workspace-1',
          requested_by_user_id: 'user-1',
          filename: 'broken.pdf',
          created_at: '2026-05-05T00:00:00Z',
          started_at: null,
          finished_at: null,
          progress_current: 0,
          progress_total: 1,
          progress_message: 'Import ist in Warteschlange',
          error_code: null,
          error_message: null,
          result: null,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'job-parser',
          job_type: 'document_import',
          status: 'failed',
          workspace_id: 'workspace-1',
          requested_by_user_id: 'user-1',
          filename: 'broken.pdf',
          created_at: '2026-05-05T00:00:00Z',
          started_at: '2026-05-05T00:00:01Z',
          finished_at: '2026-05-05T00:00:02Z',
          progress_current: 1,
          progress_total: 1,
          progress_message: 'Import fehlgeschlagen',
          error_code: 'PARSER_FAILED',
          error_message: 'PDF file could not be opened',
          result: null,
        }),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    const file = new File(['fake'], 'broken.pdf', { type: 'application/pdf' });
    fireEvent.change(screen.getByLabelText('Datei'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: 'Dokument importieren' }));

    expect(await screen.findByText('Import fehlgeschlagen')).toBeInTheDocument();
    expect(screen.getByText(/Fehlercode: PARSER_FAILED/i)).toBeInTheDocument();
  });

  it('maps upload validation errors from the backend with specific titles', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([]),
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 413,
        statusText: 'Request Entity Too Large',
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ error: { code: 'FILE_TOO_LARGE', message: 'Uploaded file exceeds the configured maximum size', details: {} } }),
      });

    renderPage();

    expect(await screen.findByText('Keine Dokumente vorhanden')).toBeInTheDocument();

    const file = new File(['hello'], 'notes.txt', { type: 'text/plain' });
    fireEvent.change(screen.getByLabelText('Datei'), { target: { files: [file] } });
    fireEvent.click(screen.getByRole('button', { name: 'Dokument importieren' }));

    expect(await screen.findByText('Validierungsfehler')).toBeInTheDocument();
    expect(screen.getByText(/Fehlercode: FILE_TOO_LARGE/i)).toBeInTheDocument();
  });

  it('filters archived documents explicitly and does not expose a deleted filter', async () => {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([
          {
            id: 'doc-1',
            title: 'Aktives Dokument',
            mime_type: 'text/plain',
            created_at: '2026-05-01T10:00:00',
            updated_at: '2026-05-01T10:10:00',
            latest_version_id: 'ver-1',
            import_status: 'chunked',
            lifecycle_status: 'active',
            version_count: 1,
            chunk_count: 2,
          },
        ]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([
          {
            id: 'doc-2',
            title: 'Archiviertes Dokument',
            mime_type: 'text/plain',
            created_at: '2026-05-01T10:00:00',
            updated_at: '2026-05-01T10:10:00',
            latest_version_id: 'ver-2',
            import_status: 'chunked',
            lifecycle_status: 'archived',
            version_count: 1,
            chunk_count: 2,
          },
        ]),
      });

    renderPage();

    expect(await screen.findByText('Aktives Dokument')).toBeInTheDocument();
    expect(screen.getByText(/Archivierte Dokumente erscheinen nicht in Suche oder Chat/i)).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /deleted/i })).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Statusfilter'), { target: { value: 'archived' } });

    expect(await screen.findByText('Archiviertes Dokument')).toBeInTheDocument();
    expect(screen.getByText('archived')).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/documents?limit=20&offset=0&lifecycle_status=archived'),
      expect.any(Object),
    );
  });
});
