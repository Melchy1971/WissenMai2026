import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../../auth/AuthContext.jsx';
import { setApiRequestContext } from '../../api/client.js';
import { TopicsPage } from '../../pages/TopicsPage.jsx';

// ── fixtures ──────────────────────────────────────────────────────────────────

const MOCK_TOPICS = [
  { id: 'topic-1', name: 'Datenschutz', summary: 'DSGVO-Anforderungen', document_count: 3, tag_count: 2, updated_at: '2026-01-10T00:00:00Z' },
  { id: 'topic-2', name: 'Onboarding',  summary: 'Einarbeitung neuer Mitarbeiter', document_count: 1, tag_count: 0, updated_at: '2026-01-05T00:00:00Z' },
];

const MOCK_DETAIL = {
  id: 'topic-1',
  name: 'Datenschutz',
  summary: 'DSGVO-Anforderungen fuer die Telekom',
  sources: [{ doc_id: 'doc-a', title: 'DSGVO Leitfaden', excerpt: 'Personenbezogene Daten ...' }],
  documents: [{ id: 'doc-a', title: 'DSGVO Leitfaden', lifecycle_status: 'active', updated_at: '2026-01-10T00:00:00Z' }],
  tags: ['DSGVO', 'Compliance'],
  linked_topics: [{ id: 'topic-3', name: 'Compliance Grundlagen' }],
};

// ── helpers ──────────────────────────────────────────────────────────────────

var INITIAL_AUTH = {
  token: 'test-token',
  user: { id: 'user-1', login: 'test-user' },
  active_workspace_id: 'workspace-1',
  memberships: [{ workspace_id: 'workspace-1', role: 'owner' }],
};

function renderPage() {
  return render(
    React.createElement(AuthProvider, { initialAuthState: INITIAL_AUTH },
      React.createElement(MemoryRouter, { initialEntries: ['/topics'] },
        React.createElement(Routes, null,
          React.createElement(Route, { path: '/topics', element: React.createElement(TopicsPage) })
        )
      )
    )
  );
}

function primeRequestContext() {
  setApiRequestContext({ authToken: 'test-token', workspaceId: 'workspace-1' });
}

function mockFetchList(topics) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(function(url) {
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async function() { return topics; },
    });
  });
}

function mockFetchListAndDetail(topics, detail) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(function(url) {
    var u = String(url);
    if (u.includes('/topics/' + detail.id)) {
      return Promise.resolve({
        ok: true, status: 200,
        headers: new Headers({ 'content-type': 'application/json' }),
        json: async function() { return detail; },
      });
    }
    return Promise.resolve({
      ok: true, status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: async function() { return topics; },
    });
  });
}

function mock404() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: false,
    status: 404,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async function() { return { detail: 'Not Found' }; },
  });
}

function mock500() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: false,
    status: 500,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async function() { return { detail: 'Internal Server Error' }; },
  });
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('TopicsPage', function() {
  afterEach(function() {
    setApiRequestContext({ authToken: '', workspaceId: '' });
    vi.restoreAllMocks();
    cleanup();
  });

  it('shows loading state initially', function() {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(function() {}));
    renderPage();
    expect(screen.getByText(/Themen werden geladen/i)).toBeTruthy();
  });

  it('renders topic list when API responds', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });
    expect(screen.getByText('Onboarding')).toBeTruthy();
  });

  it('shows document count per topic', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });
    expect(screen.getByText(/3 Dok\./i)).toBeTruthy();
  });

  it('shows topic count in header', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(screen.getByText(/2 Themen/i)).toBeTruthy(); });
  });

  it('filters topics by search input', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });

    var input = screen.getByPlaceholderText(/Thema suchen/i);
    fireEvent.change(input, { target: { value: 'onboarding' } });

    expect(screen.getByText('Onboarding')).toBeTruthy();
    expect(screen.queryByText('Datenschutz')).toBeNull();
  });

  it('shows empty state when search finds nothing', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });

    var input = screen.getByPlaceholderText(/Thema suchen/i);
    fireEvent.change(input, { target: { value: 'xyz-nicht-vorhanden' } });

    expect(screen.getByText(/Keine Themen gefunden/i)).toBeTruthy();
  });

  it('shows placeholder panel when no topic selected', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });
    expect(screen.getByText(/Thema auswählen/i)).toBeTruthy();
  });

  it('loads detail when topic row is clicked', async function() {
    primeRequestContext();
    mockFetchListAndDetail(MOCK_TOPICS, MOCK_DETAIL);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });

    fireEvent.click(screen.getByText('Datenschutz'));

    await waitFor(function() {
      expect(screen.getByText('DSGVO-Anforderungen fuer die Telekom')).toBeTruthy();
    });
  });

  it('shows tags in detail panel', async function() {
    primeRequestContext();
    mockFetchListAndDetail(MOCK_TOPICS, MOCK_DETAIL);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });
    fireEvent.click(screen.getByText('Datenschutz'));
    await waitFor(function() { expect(screen.getByText('DSGVO')).toBeTruthy(); });
    expect(screen.getByText('Compliance')).toBeTruthy();
  });

  it('deselects topic on second click', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });

    fireEvent.click(screen.getByText('Datenschutz'));
    await waitFor(function() {
      var rows = screen.getAllByRole('row');
      var row = rows.find(function(r) { return r.textContent && r.textContent.includes('Datenschutz'); });
      expect(row).toBeTruthy();
      expect(row.getAttribute('aria-selected')).toBe('true');
    });

    fireEvent.click(screen.getByText('Datenschutz'));
    await waitFor(function() {
      expect(screen.getByText(/Thema auswählen/i)).toBeTruthy();
    });
  });

  it('shows 404 placeholder when backend not available', async function() {
    primeRequestContext();
    mock404();
    renderPage();
    await waitFor(function() {
      expect(screen.getByText(/Themen-API nicht verfügbar/i)).toBeTruthy();
    });
  });

  it('shows error state on 500', async function() {
    primeRequestContext();
    mock500();
    renderPage();
    await waitFor(function() {
      expect(screen.getByText(/Fehler beim Laden/i)).toBeTruthy();
    });
  });

  it('shows delete button in detail panel', async function() {
    primeRequestContext();
    mockFetchListAndDetail(MOCK_TOPICS, MOCK_DETAIL);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });
    fireEvent.click(screen.getByText('Datenschutz'));
    await waitFor(function() { expect(screen.getByText('Thema löschen')).toBeTruthy(); });
  });

  it('shows confirmation dialog on delete click', async function() {
    primeRequestContext();
    mockFetchListAndDetail(MOCK_TOPICS, MOCK_DETAIL);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });
    fireEvent.click(screen.getByText('Datenschutz'));
    await waitFor(function() { expect(screen.getByText('Thema löschen')).toBeTruthy(); });
    fireEvent.click(screen.getByText('Thema löschen'));
    expect(screen.getByText(/Endgültig löschen/i)).toBeTruthy();
    expect(screen.getByText(/Abbrechen/i)).toBeTruthy();
  });

  it('cancels delete dialog without calling API', async function() {
    primeRequestContext();
    mockFetchListAndDetail(MOCK_TOPICS, MOCK_DETAIL);
    renderPage();
    await waitFor(function() { expect(screen.getByText('Datenschutz')).toBeTruthy(); });
    fireEvent.click(screen.getByText('Datenschutz'));
    await waitFor(function() { expect(screen.getByText('Thema löschen')).toBeTruthy(); });
    fireEvent.click(screen.getByText('Thema löschen'));
    fireEvent.click(screen.getByText('Abbrechen'));
    expect(screen.queryByText(/Endgültig löschen/i)).toBeNull();
    expect(screen.getByText('Thema löschen')).toBeTruthy();
  });

  it('sends auth header in API call', async function() {
    primeRequestContext();
    mockFetchList(MOCK_TOPICS);
    renderPage();
    await waitFor(function() { expect(globalThis.fetch).toHaveBeenCalled(); });
    var call = globalThis.fetch.mock.calls[0];
    var opts = call[1];
    expect(opts && opts.headers && opts.headers.Authorization).toBeTruthy();
  });
});
