import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { setApiRequestContext } from '../../api/client.js';
import { AuthProvider } from '../../auth/AuthContext.jsx';
import { DocumentDetailPage } from '../../pages/DocumentDetailPage.jsx';

function renderPage() {
  setApiRequestContext({ authToken: 'test-token', workspaceId: 'workspace-1' });
  return render(
    <AuthProvider initialAuthState={{
      token: 'test-token',
      user: { id: 'user-1', login: 'admin' },
      active_workspace_id: 'workspace-1',
      memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
    }}>
      <MemoryRouter initialEntries={['/documents/doc-1?workspace_id=workspace-1']}>
        <Routes>
          <Route path="/documents/:id" element={<DocumentDetailPage />} />
          <Route path="/documents" element={<div>Dokumentliste</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe('DocumentDetailPage', () => {
  afterEach(() => {
    setApiRequestContext({ authToken: '', workspaceId: '' });
    vi.restoreAllMocks();
    cleanup();
  });

  it('renders metadata, versions and chunk previews', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'doc-1',
          workspace_id: 'workspace-1',
          owner_user_id: 'user-1',
          title: 'Dokument A',
          source_type: 'upload',
          mime_type: 'text/plain',
          content_hash: 'hash-1',
          created_at: '2026-05-01T10:00:00',
          updated_at: '2026-05-01T10:10:00',
          latest_version_id: 'ver-1',
          lifecycle_status: 'active',
          archived_at: null,
          deleted_at: null,
          parser_metadata: { parser_version: '1.0', ocr_used: false, ki_provider: null, ki_model: null, metadata: {} },
          import_status: 'chunked',
          chunk_summary: { chunk_count: 1, total_chars: 120, first_chunk_id: 'chunk-1', last_chunk_id: 'chunk-1' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ id: 'ver-1', version_number: 1, created_at: '2026-05-01T10:00:00', content_hash: 'hash-v1' }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ chunk_id: 'chunk-1', position: 0, text_preview: 'Preview', source_anchor: { type: 'text', char_start: 0, char_end: 50 } }]),
      });

    renderPage();

    expect(await screen.findAllByText('Dokument A')).toHaveLength(2);
    expect(screen.getByText('v1')).toBeInTheDocument();
    expect(screen.getByText('Preview')).toBeInTheDocument();
    expect(screen.getAllByText('active').length).toBeGreaterThan(0);
    expect(screen.getByText(/Archivieren blendet das Dokument aus Suche und Chat aus/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Dokument archivieren' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Dokument loeschen' })).toBeInTheDocument();
  });

  it('renders API errors visibly', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => ({ error: { code: 'DOCUMENT_NOT_FOUND', message: 'Document not found', details: {} } }),
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Serverfehler')).toBeInTheDocument();
    });
    expect(screen.getByText(/Fehlercode: DOCUMENT_NOT_FOUND/i)).toBeInTheDocument();
  });

  it('archives an active document and reloads the detail state', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'doc-1',
          workspace_id: 'workspace-1',
          owner_user_id: 'user-1',
          title: 'Dokument A',
          source_type: 'upload',
          mime_type: 'text/plain',
          content_hash: 'hash-1',
          created_at: '2026-05-01T10:00:00',
          updated_at: '2026-05-01T10:10:00',
          latest_version_id: 'ver-1',
          lifecycle_status: 'active',
          archived_at: null,
          deleted_at: null,
          parser_metadata: { parser_version: '1.0', ocr_used: false, ki_provider: null, ki_model: null, metadata: {} },
          import_status: 'chunked',
          chunk_summary: { chunk_count: 1, total_chars: 120, first_chunk_id: 'chunk-1', last_chunk_id: 'chunk-1' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ id: 'ver-1', version_number: 1, created_at: '2026-05-01T10:00:00', content_hash: 'hash-v1' }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ chunk_id: 'chunk-1', position: 0, text_preview: 'Preview', source_anchor: { type: 'text', char_start: 0, char_end: 50 } }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ document_id: 'doc-1', lifecycle_status: 'archived', archived_at: '2026-05-06T10:00:00Z', deleted_at: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'doc-1',
          workspace_id: 'workspace-1',
          owner_user_id: 'user-1',
          title: 'Dokument A',
          source_type: 'upload',
          mime_type: 'text/plain',
          content_hash: 'hash-1',
          created_at: '2026-05-01T10:00:00',
          updated_at: '2026-05-06T10:00:00',
          latest_version_id: 'ver-1',
          lifecycle_status: 'archived',
          archived_at: '2026-05-06T10:00:00Z',
          deleted_at: null,
          parser_metadata: { parser_version: '1.0', ocr_used: false, ki_provider: null, ki_model: null, metadata: {} },
          import_status: 'chunked',
          chunk_summary: { chunk_count: 1, total_chars: 120, first_chunk_id: 'chunk-1', last_chunk_id: 'chunk-1' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ id: 'ver-1', version_number: 1, created_at: '2026-05-01T10:00:00', content_hash: 'hash-v1' }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ chunk_id: 'chunk-1', position: 0, text_preview: 'Preview', source_anchor: { type: 'text', char_start: 0, char_end: 50 } }]),
      });

    renderPage();

    expect(await screen.findByRole('button', { name: 'Dokument archivieren' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Dokument archivieren' }));

    expect((await screen.findAllByText('archived')).length).toBeGreaterThan(0);
    expect(screen.getByText(/Archivierte Dokumente erscheinen nicht in Suche oder Chat/i)).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      4,
      expect.stringContaining('/documents/doc-1/archive'),
      expect.objectContaining({ method: 'PATCH' }),
    );
  });

  it('deletes a document through soft delete and returns to the list', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'doc-1',
          workspace_id: 'workspace-1',
          owner_user_id: 'user-1',
          title: 'Dokument A',
          source_type: 'upload',
          mime_type: 'text/plain',
          content_hash: 'hash-1',
          created_at: '2026-05-01T10:00:00',
          updated_at: '2026-05-01T10:10:00',
          latest_version_id: 'ver-1',
          lifecycle_status: 'active',
          archived_at: null,
          deleted_at: null,
          parser_metadata: { parser_version: '1.0', ocr_used: false, ki_provider: null, ki_model: null, metadata: {} },
          import_status: 'chunked',
          chunk_summary: { chunk_count: 1, total_chars: 120, first_chunk_id: 'chunk-1', last_chunk_id: 'chunk-1' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ id: 'ver-1', version_number: 1, created_at: '2026-05-01T10:00:00', content_hash: 'hash-v1' }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ chunk_id: 'chunk-1', position: 0, text_preview: 'Preview', source_anchor: { type: 'text', char_start: 0, char_end: 50 } }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ document_id: 'doc-1', lifecycle_status: 'deleted', archived_at: null, deleted_at: '2026-05-06T10:00:00Z' }),
      });

    renderPage();

    expect(await screen.findByRole('button', { name: 'Dokument loeschen' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Dokument loeschen' }));

    expect(confirmSpy).toHaveBeenCalled();
    expect(await screen.findByText('Dokumentliste')).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      4,
      expect.stringContaining('/documents/doc-1'),
      expect.objectContaining({ method: 'DELETE' }),
    );
  });

  it('restores an archived document and reloads the detail state', async () => {
    vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'doc-1',
          workspace_id: 'workspace-1',
          owner_user_id: 'user-1',
          title: 'Dokument A',
          source_type: 'upload',
          mime_type: 'text/plain',
          content_hash: 'hash-1',
          created_at: '2026-05-01T10:00:00',
          updated_at: '2026-05-06T10:00:00',
          latest_version_id: 'ver-1',
          lifecycle_status: 'archived',
          archived_at: '2026-05-06T10:00:00Z',
          deleted_at: null,
          parser_metadata: { parser_version: '1.0', ocr_used: false, ki_provider: null, ki_model: null, metadata: {} },
          import_status: 'chunked',
          chunk_summary: { chunk_count: 1, total_chars: 120, first_chunk_id: 'chunk-1', last_chunk_id: 'chunk-1' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ id: 'ver-1', version_number: 1, created_at: '2026-05-01T10:00:00', content_hash: 'hash-v1' }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ chunk_id: 'chunk-1', position: 0, text_preview: 'Preview', source_anchor: { type: 'text', char_start: 0, char_end: 50 } }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({ document_id: 'doc-1', lifecycle_status: 'active', archived_at: null, deleted_at: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ({
          id: 'doc-1',
          workspace_id: 'workspace-1',
          owner_user_id: 'user-1',
          title: 'Dokument A',
          source_type: 'upload',
          mime_type: 'text/plain',
          content_hash: 'hash-1',
          created_at: '2026-05-01T10:00:00',
          updated_at: '2026-05-06T10:05:00',
          latest_version_id: 'ver-1',
          lifecycle_status: 'active',
          archived_at: null,
          deleted_at: null,
          parser_metadata: { parser_version: '1.0', ocr_used: false, ki_provider: null, ki_model: null, metadata: {} },
          import_status: 'chunked',
          chunk_summary: { chunk_count: 1, total_chars: 120, first_chunk_id: 'chunk-1', last_chunk_id: 'chunk-1' },
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ id: 'ver-1', version_number: 1, created_at: '2026-05-01T10:00:00', content_hash: 'hash-v1' }]),
      })
      .mockResolvedValueOnce({
        ok: true,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async () => ([{ chunk_id: 'chunk-1', position: 0, text_preview: 'Preview', source_anchor: { type: 'text', char_start: 0, char_end: 50 } }]),
      });

    renderPage();

    expect(await screen.findByRole('button', { name: 'Dokument wiederherstellen' })).toBeInTheDocument();
    expect(screen.getByText(/koennen aber wiederhergestellt werden/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Dokument wiederherstellen' }));

    expect((await screen.findAllByText('active')).length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: 'Dokument archivieren' })).toBeInTheDocument();
    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      4,
      expect.stringContaining('/documents/doc-1/restore'),
      expect.objectContaining({ method: 'PATCH' }),
    );
  });
});
