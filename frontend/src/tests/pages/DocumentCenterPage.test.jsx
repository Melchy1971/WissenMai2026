import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AuthProvider } from '../../auth/AuthContext.jsx';
import { setApiRequestContext } from '../../api/client.js';
import { DocumentCenterPage } from '../../pages/DocumentCenterPage.jsx';

const ACTIVE_DOC = {
  id: 'doc-1',
  title: 'Prozesshandbuch Eingang',
  mime_type: 'application/pdf',
  created_at: '2026-05-01T10:00:00',
  updated_at: '2026-05-10T14:00:00',
  latest_version_id: 'ver-1',
  import_status: 'chunked',
  lifecycle_status: 'active',
  version_count: 2,
  chunk_count: 12,
};

const ARCHIVED_DOC = {
  id: 'doc-2',
  title: 'Altlast Handbuch 2020',
  mime_type: 'text/plain',
  created_at: '2020-01-01T00:00:00',
  updated_at: '2020-12-31T00:00:00',
  latest_version_id: 'ver-2',
  import_status: 'chunked',
  lifecycle_status: 'archived',
  version_count: 1,
  chunk_count: 5,
};

function renderPage() {
  return render(
    <AuthProvider
      initialAuthState={{
        token: 'test-token',
        user: { id: 'user-1', login: 'test-user' },
        active_workspace_id: 'workspace-1',
        memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
      }}
    >
      <MemoryRouter initialEntries={['/documents']}>
        <Routes>
          <Route path="/documents" element={<DocumentCenterPage />} />
          <Route path="/documents/:id" element={<div>Dokumentdetail</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  );
}

function primeRequestContext() {
  setApiRequestContext({ authToken: 'test-token', workspaceId: 'workspace-1' });
}

function mockTwoFetchCalls({ active = [ACTIVE_DOC], archived = [] } = {}) {
  vi.spyOn(globalThis, 'fetch').mockImplementation((url) => {
    const u = String(url);
    const json = u.includes('lifecycle_status=archived') ? archived : active;
    return Promise.resolve({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async () => json,
    });
  });
}

describe('DocumentCenterPage', () => {
  afterEach(() => {
    setApiRequestContext({ authToken: '', workspaceId: '' });
    vi.restoreAllMocks();
    cleanup();
  });

  it('renders loading state on mount', () => {
    primeRequestContext();
    mockTwoFetchCalls();

    renderPage();

    expect(screen.getByText(/Wird geladen/i)).toBeInTheDocument();
  });

  it('renders active documents from the API', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [] });

    renderPage();

    expect(await screen.findByText('Prozesshandbuch Eingang')).toBeInTheDocument();
    // Lifecycle badge
    expect(screen.getByText('Aktiv')).toBeInTheDocument();
  });

  it('shows correct document count in header', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [ARCHIVED_DOC] });

    renderPage();

    // Both active + archived loaded, deleted excluded: 2 total
    await waitFor(() => {
      expect(screen.getByText(/2 Dokumente im Bestand/i)).toBeInTheDocument();
    });
  });

  it('renders filter panel with status options', async () => {
    primeRequestContext();
    mockTwoFetchCalls();

    renderPage();

    await screen.findByText('Prozesshandbuch Eingang');

    expect(screen.getByRole('radio', { name: 'Alle' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Aktiv' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Archiviert' })).toBeInTheDocument();
    // Default selection is "Aktiv"
    expect(screen.getByRole('radio', { name: 'Aktiv' })).toBeChecked();
  });

  it('filters to archived when Archiviert is selected', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [ARCHIVED_DOC] });

    renderPage();

    await screen.findByText('Prozesshandbuch Eingang');

    // Initially archived doc should be hidden by active filter
    expect(screen.queryByText('Altlast Handbuch 2020')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('radio', { name: 'Archiviert' }));

    expect(await screen.findByText('Altlast Handbuch 2020')).toBeInTheDocument();
    expect(screen.queryByText('Prozesshandbuch Eingang')).not.toBeInTheDocument();
  });

  it('filters by search text in document title', async () => {
    primeRequestContext();
    mockTwoFetchCalls({
      active: [ACTIVE_DOC, { ...ACTIVE_DOC, id: 'doc-3', title: 'Qualitätsbericht Q1' }],
      archived: [],
    });

    renderPage();

    await screen.findByText('Prozesshandbuch Eingang');
    await screen.findByText('Qualitätsbericht Q1');

    fireEvent.change(screen.getByPlaceholderText(/Titel suchen/i), {
      target: { value: 'Prozess' },
    });

    expect(screen.getByText('Prozesshandbuch Eingang')).toBeInTheDocument();
    expect(screen.queryByText('Qualitätsbericht Q1')).not.toBeInTheDocument();
  });

  it('shows empty state when no documents match the filter', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [] });

    renderPage();

    await screen.findByText('Prozesshandbuch Eingang');

    fireEvent.change(screen.getByPlaceholderText(/Titel suchen/i), {
      target: { value: 'xxxxxxxx' },
    });

    expect(screen.getByText(/Keine Dokumente gefunden/i)).toBeInTheDocument();
  });

  it('shows document detail in preview panel on row click', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [] });

    renderPage();

    const row = await screen.findByText('Prozesshandbuch Eingang');
    fireEvent.click(row);

    // Preview panel should show title and actions
    expect(screen.getByRole('heading', { name: 'Prozesshandbuch Eingang' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Öffnen/i })).toHaveAttribute('href', '/documents/doc-1');
    // Active document can be archived
    expect(screen.getByRole('button', { name: /Archivieren/i })).toBeInTheDocument();
    // Active document cannot be deleted
    expect(screen.queryByRole('button', { name: /Löschen/i })).not.toBeInTheDocument();
  });

  it('shows empty preview panel when no document is selected', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [] });

    renderPage();

    await screen.findByText('Prozesshandbuch Eingang');

    expect(screen.getByText(/Dokument auswählen/i)).toBeInTheDocument();
  });

  it('shows delete action only for archived documents', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [], archived: [ARCHIVED_DOC] });

    renderPage();

    // Switch filter to show all
    fireEvent.click(screen.getByRole('radio', { name: 'Alle' }));

    const row = await screen.findByText('Altlast Handbuch 2020');
    fireEvent.click(row);

    // Archived document can be deleted, cannot be archived again
    expect(screen.getByRole('button', { name: /Löschen/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Archivieren/i })).not.toBeInTheDocument();
  });

  it('shows confirmation dialog before archiving', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [] });

    renderPage();

    const row = await screen.findByText('Prozesshandbuch Eingang');
    fireEvent.click(row);

    fireEvent.click(screen.getByRole('button', { name: /Archivieren/i }));

    // Confirmation message must appear
    expect(screen.getByText(/archivieren\?/i)).toBeInTheDocument();
    // Cancel hides confirm
    fireEvent.click(screen.getByRole('button', { name: /Abbrechen/i }));
    expect(screen.queryByText(/archivieren\?/i)).not.toBeInTheDocument();
  });

  it('shows error state when API returns an error', async () => {
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
      expect(screen.getByText(/Fehler beim Laden/i)).toBeInTheDocument();
    });
  });

  it('sends correct API requests with auth headers', async () => {
    primeRequestContext();
    mockTwoFetchCalls();

    renderPage();

    await screen.findByText('Prozesshandbuch Eingang');

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/documents?limit=200&offset=0&lifecycle_status=active'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
          'X-Workspace-Id': 'workspace-1',
        }),
      }),
    );
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/documents?limit=200&offset=0&lifecycle_status=archived'),
      expect.any(Object),
    );
  });

  it('deselects document on second click of same row', async () => {
    primeRequestContext();
    mockTwoFetchCalls({ active: [ACTIVE_DOC], archived: [] });

    renderPage();

    const row = await screen.findByText('Prozesshandbuch Eingang');
    fireEvent.click(row);
    expect(screen.getByRole('heading', { name: 'Prozesshandbuch Eingang' })).toBeInTheDocument();

    fireEvent.click(row);
    expect(screen.queryByRole('heading', { name: 'Prozesshandbuch Eingang' })).not.toBeInTheDocument();
    expect(screen.getByText(/Dokument auswählen/i)).toBeInTheDocument();
  });
});
