import React from 'react';
import { useSearch } from '../features/search/useSearch.js';
import { SearchResultCard } from '../features/search/SearchResultCard.jsx';

var PAGE_STYLE = { display: 'flex', flexDirection: 'column', height: '100%' };
var HEADER_STYLE = { padding: '16px 24px 0', flexShrink: 0 };
var FORM_STYLE = { padding: '12px 24px 0', flexShrink: 0 };
var RESULTS_STYLE = { flex: 1, overflowY: 'auto', padding: '16px 24px 24px', display: 'flex', flexDirection: 'column', gap: '12px' };

function EmptyHint() {
  return React.createElement('div', { className: 'search-page__empty' },
    React.createElement('p', null, 'Suchbegriff eingeben, um Dokumente zu durchsuchen.'),
    React.createElement('p', { className: 'search-page__hint' },
      'Die Suche durchsucht alle importierten Dokumente auf Absatzebene.'
    )
  );
}

function NoResults({ query }) {
  return React.createElement('div', { className: 'search-page__empty' },
    React.createElement('p', null,
      'Keine Ergebnisse für „', query, '".'
    ),
    React.createElement('p', { className: 'search-page__hint' },
      'Tipp: Allgemeineren Begriff versuchen oder Schreibweise prüfen.'
    )
  );
}

function ErrorState({ error, onRetry }) {
  return React.createElement('div', { className: 'search-page__error' },
    React.createElement('p', null, (error && error.userMessage) || 'Suche nicht verfügbar.'),
    React.createElement('button', {
      className: 'button-secondary',
      onClick: onRetry,
    }, 'Erneut versuchen')
  );
}

export function SearchPage() {
  var ctx = useSearch();
  var query = ctx.query;
  var searchState = ctx.searchState;
  var handleQueryChange = ctx.handleQueryChange;
  var handleSubmit = ctx.handleSubmit;
  var handleReset = ctx.handleReset;

  function onFormSubmit(e) {
    e.preventDefault();
    handleSubmit();
  }

  var resultLabel = '';
  if (searchState.status === 'success') {
    var n = searchState.items.length;
    resultLabel = n === 0 ? '' : (n + ' Treffer für „' + searchState.executedQuery + '"');
  }

  return React.createElement('div', { className: 'page-stack', style: PAGE_STYLE },
    React.createElement('header', { style: HEADER_STYLE },
      React.createElement('h1', { className: 'page-title' }, 'Suche'),
      resultLabel && React.createElement('p', { className: 'page-subtitle' }, resultLabel)
    ),

    React.createElement('div', { style: FORM_STYLE },
      React.createElement('form', { onSubmit: onFormSubmit, className: 'search-page__form' },
        React.createElement('div', { className: 'search-bar search-bar--lg' },
          React.createElement('input', {
            className: 'search-bar__field',
            type: 'search',
            placeholder: 'Was suchen Sie?',
            value: query,
            onChange: function(e) { handleQueryChange(e.target.value); },
            autoFocus: true,
            'aria-label': 'Suchbegriff',
          }),
          React.createElement('button', {
            type: 'submit',
            className: 'button-primary search-page__submit',
            disabled: searchState.status === 'loading',
          }, searchState.status === 'loading' ? 'Suche läuft …' : 'Suchen'),
          query && React.createElement('button', {
            type: 'button',
            className: 'button-secondary',
            onClick: handleReset,
          }, 'Zurücksetzen')
        )
      )
    ),

    React.createElement('div', { style: RESULTS_STYLE },
      searchState.status === 'idle' && React.createElement(EmptyHint),

      searchState.status === 'loading' && React.createElement('div', { className: 'search-page__loading' },
        'Suche läuft …'
      ),

      searchState.status === 'error' && React.createElement(ErrorState, {
        error: searchState.error,
        onRetry: handleSubmit,
      }),

      searchState.status === 'success' && searchState.items.length === 0 &&
        React.createElement(NoResults, { query: searchState.executedQuery }),

      searchState.status === 'success' && searchState.items.map(function(item) {
        return React.createElement(SearchResultCard, { key: item.chunkId || item.documentId + '-' + item.position, item: item });
      })
    ),

    React.createElement('style', null, `
      .search-page__form { display: flex; flex-direction: column; }
      .search-bar--lg { display: flex; gap: 8px; align-items: center; }
      .search-bar--lg .search-bar__field {
        flex: 1;
        padding: 10px 14px;
        font-size: 15px;
        border: 1px solid var(--color-border, #ccc);
        border-radius: 6px;
        background: var(--color-surface, #fff);
        color: var(--color-text, #1c1c1c);
      }
      .search-bar--lg .search-bar__field:focus {
        outline: 2px solid var(--t-magenta, #E20074);
        border-color: var(--t-magenta, #E20074);
      }
      .search-page__submit {
        white-space: nowrap;
        flex-shrink: 0;
      }
      .button-primary {
        padding: 9px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        border: none;
        background: var(--t-magenta, #E20074);
        color: #fff;
      }
      .button-primary:disabled { opacity: 0.6; cursor: not-allowed; }
      .search-page__empty,
      .search-page__loading,
      .search-page__error {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 48px 24px;
        color: var(--color-text-secondary, #666);
        font-size: 14px;
        text-align: center;
      }
      .search-page__empty p, .search-page__error p { margin: 0; }
      .search-page__hint { font-size: 12px; }
      .search-page__error { color: var(--color-danger, #880e4f); }
    `)
  );
}
