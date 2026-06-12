import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '../../auth/AuthContext.jsx';
import { setApiRequestContext } from '../../api/client.js';
import { SearchPage } from '../../pages/SearchPage.jsx';

// ── fixtures ──────────────────────────────────────────────────────────────────

var MOCK_RESULTS = [
  {
    document_id: 'doc-1',
    document_title: 'Datenschutzrichtlinie 2026',
    document_version_id: 'ver-1',
    version_number: 1,
    chunk_id: 'chunk-1',
    position: 0,
    text_preview: 'Personenbezogene Daten werden nach DSGVO-Grundsaetzen verarbeitet.',
    source_anchor: null,
    rank: 0.85,
  },
  {
    document_id: 'doc-2',
    document_title: 'Onboarding-Handbuch',
    document_version_id: 'ver-2',
    version_number: 1,
    chunk_id: 'chunk-2',
    position: 2,
    text_preview: 'Neue Mitarbeiter erhalten in der ersten Woche eine Einfuehrung.',
    source_anchor: null,
    rank: 0.45,
  },
  {
    document_id: 'doc-3',
    document_title: 'IT-Sicherheitskonzept',
    document_version_id: 'ver-3',
    version_number: 1,
    chunk_id: 'chunk-3',
    position: 1,
    text_preview: 'Zugriffsrechte werden quartalsweise ueberprueft.',
    source_anchor: null,
    rank: 0.15,
  },
];

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
      React.createElement(MemoryRouter, { initialEntries: ['/search'] },
        React.createElement(Routes, null,
          React.createElement(Route, { path: '/search', element: React.createElement(SearchPage) }),
          React.createElement(Route, { path: '/documents/:id', element: React.createElement('div', null, 'Dokument') })
        )
      )
    )
  );
}

function primeRequestContext() {
  setApiRequestContext({ authToken: 'test-token', workspaceId: 'workspace-1' });
}

function mockFetchResults(results) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async function() { return results; },
  });
}

function mockFetchError() {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue({
    ok: false,
    status: 503,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: async function() { return { detail: 'Service Unavailable' }; },
  });
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('SearchPage', function() {
  afterEach(function() {
    setApiRequestContext({ authToken: '', workspaceId: '' });
    vi.restoreAllMocks();
    cleanup();
  });

  it('renders search input on mount', function() {
    primeRequestContext();
    renderPage();
    expect(screen.getByPlaceholderText(/Was suchen Sie/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /Suchen/i })).toBeTruthy();
  });

  it('shows empty hint before any search', function() {
    primeRequestContext();
    renderPage();
    expect(screen.getByText(/Suchbegriff eingeben/i)).toBeTruthy();
  });

  it('shows loading state while searching', async function() {
    primeRequestContext();
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(function() {}));
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Datenschutz' } });
    await waitFor(function() {
      expect(screen.getByRole('button', { name: /Suche läuft/i })).toBeTruthy();
    });
  });

  it('renders results after search', async function() {
    primeRequestContext();
    mockFetchResults(MOCK_RESULTS);
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Datenschutz' } });
    await waitFor(function() {
      expect(screen.getByText('Datenschutzrichtlinie 2026')).toBeTruthy();
    });
    expect(screen.getByText('Onboarding-Handbuch')).toBeTruthy();
    expect(screen.getByText('IT-Sicherheitskonzept')).toBeTruthy();
  });

  it('shows result count in header', async function() {
    primeRequestContext();
    mockFetchResults(MOCK_RESULTS);
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Datenschutz' } });
    await waitFor(function() {
      expect(screen.getByText(/3 Treffer/i)).toBeTruthy();
    });
  });

  it('shows text preview in card', async function() {
    primeRequestContext();
    mockFetchResults(MOCK_RESULTS);
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Datenschutz' } });
    await waitFor(function() {
      expect(screen.getByText(/Personenbezogene Daten/i)).toBeTruthy();
    });
  });

  it('shows Sehr relevant for high rank result', async function() {
    primeRequestContext();
    mockFetchResults([MOCK_RESULTS[0]]); // rank 0.85
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Datenschutz' } });
    await waitFor(function() {
      expect(screen.getByText('Sehr relevant')).toBeTruthy();
    });
  });

  it('shows Relevant for medium rank result', async function() {
    primeRequestContext();
    mockFetchResults([MOCK_RESULTS[1]]); // rank 0.45
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Onboarding' } });
    await waitFor(function() {
      expect(screen.getByText('Relevant')).toBeTruthy();
    });
  });

  it('shows Moeglicherweise relevant for low rank result', async function() {
    primeRequestContext();
    mockFetchResults([MOCK_RESULTS[2]]); // rank 0.15
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Zugriff' } });
    await waitFor(function() {
      expect(screen.getByText('Moeglicherweise relevant')).toBeTruthy();
    });
  });

  it('shows no-results message when empty array returned', async function() {
    primeRequestContext();
    mockFetchResults([]);
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'xyzNichtVorhanden' } });
    await waitFor(function() {
      expect(screen.getByText(/Keine Ergebnisse/i)).toBeTruthy();
    });
  });

  it('shows error state on API failure', async function() {
    primeRequestContext();
    mockFetchError();
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Fehler' } });
    await waitFor(function() {
      expect(screen.getByRole('button', { name: /Erneut versuchen/i })).toBeTruthy();
    });
  });

  it('clears results on reset', async function() {
    primeRequestContext();
    mockFetchResults(MOCK_RESULTS);
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Datenschutz' } });
    await waitFor(function() { expect(screen.getByText('Datenschutzrichtlinie 2026')).toBeTruthy(); });

    var resetBtn = screen.getByRole('button', { name: /Zurücksetzen/i });
    fireEvent.click(resetBtn);
    expect(screen.queryByText('Datenschutzrichtlinie 2026')).toBeNull();
    expect(screen.getByText(/Suchbegriff eingeben/i)).toBeTruthy();
  });

  it('document title links to document detail', async function() {
    primeRequestContext();
    mockFetchResults([MOCK_RESULTS[0]]);
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'Datenschutz' } });
    await waitFor(function() { expect(screen.getByText('Datenschutzrichtlinie 2026')).toBeTruthy(); });

    var link = screen.getByRole('link', { name: 'Datenschutzrichtlinie 2026' });
    expect(link.getAttribute('href')).toBe('/documents/doc-1');
  });

  it('sends auth header in search request', async function() {
    primeRequestContext();
    mockFetchResults(MOCK_RESULTS);
    renderPage();
    var input = screen.getByPlaceholderText(/Was suchen Sie/i);
    fireEvent.change(input, { target: { value: 'test' } });
    await waitFor(function() { expect(globalThis.fetch).toHaveBeenCalled(); });
    var opts = globalThis.fetch.mock.calls[0][1];
    expect(opts && opts.headers && opts.headers.Authorization).toBeTruthy();
  });
});
