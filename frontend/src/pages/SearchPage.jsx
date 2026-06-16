import React, { useState, useRef } from 'react';
import { useUnifiedSearch } from '../features/search/useUnifiedSearch.js';
import { UnifiedSearchResultCard } from '../features/search/UnifiedSearchResultCard.jsx';

var KIND_TABS = [
  { value: [], label: 'Alle' },
  { value: ['topic'], label: 'Themen' },
  { value: ['document'], label: 'Dokumente' },
  { value: ['chunk'], label: 'Absätze' },
];

var SORT_OPTIONS = [
  { value: 'score_desc', label: 'Relevanz' },
  { value: 'created_at_desc', label: 'Neueste zuerst' },
  { value: 'created_at_asc', label: 'Älteste zuerst' },
  { value: 'title_asc', label: 'Titel A–Z' },
];

function KindTabs({ activeKinds, onChange }) {
  return React.createElement('div', { className: 'search-kind-tabs', role: 'tablist' },
    KIND_TABS.map(function(tab) {
      var isActive = JSON.stringify(tab.value) === JSON.stringify(activeKinds);
      return React.createElement('button', {
        key: tab.label,
        role: 'tab',
        'aria-selected': String(isActive),
        className: 'search-kind-tab' + (isActive ? ' search-kind-tab--active' : ''),
        onClick: function() { onChange(tab.value); },
      }, tab.label);
    })
  );
}

function SortDropdown({ value, onChange }) {
  return React.createElement('div', { className: 'search-sort' },
    React.createElement('label', { className: 'search-sort__label', htmlFor: 'search-sort-select' }, 'Sortierung'),
    React.createElement('select', {
      id: 'search-sort-select',
      className: 'search-sort__select',
      value: value,
      onChange: function(e) { onChange(e.target.value); },
    },
      SORT_OPTIONS.map(function(opt) {
        return React.createElement('option', { key: opt.value, value: opt.value }, opt.label);
      })
    )
  );
}

function ResultCount({ total, hits, executedQuery }) {
  if (!executedQuery || !total) return null;
  return React.createElement('p', { className: 'search-result-count' },
    total + ' Treffer für „' + executedQuery + '"',
    hits < total ? ' (zeige ' + hits + ')' : ''
  );
}

function EmptyHint() {
  return React.createElement('div', { className: 'search-page__empty' },
    React.createElement('p', null, 'Suchbegriff eingeben'),
    React.createElement('p', { className: 'search-hint' },
      'Suche über Themen, Dokumente und Absätze — mit Relevanzscore und Trefferhervorhebung.'
    )
  );
}

function NoResults({ query }) {
  return React.createElement('div', { className: 'search-page__empty' },
    React.createElement('p', null, 'Keine Ergebnisse für „' + query + '"'),
    React.createElement('p', { className: 'search-hint' }, 'Allgemeineren Begriff versuchen oder Filter anpassen.')
  );
}

function ErrorState({ error, onRetry }) {
  return React.createElement('div', { className: 'search-page__error' },
    React.createElement('p', null, (error && error.userMessage) || 'Suche nicht verfügbar.'),
    React.createElement('button', { className: 'button-secondary', onClick: onRetry }, 'Erneut versuchen')
  );
}

function SkeletonCard() {
  return React.createElement('div', { className: 'unified-skeleton', 'aria-hidden': 'true' },
    React.createElement('div', { className: 'unified-skeleton__badge' }),
    React.createElement('div', { className: 'unified-skeleton__title' }),
    React.createElement('div', { className: 'unified-skeleton__line' }),
    React.createElement('div', { className: 'unified-skeleton__line unified-skeleton__line--short' })
  );
}

export function SearchPage() {
  var [inputValue, setInputValue] = useState('');
  var debounceRef = useRef(null);
  var ctx = useUnifiedSearch();
  var state = ctx.state;

  function triggerSearch(q) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(function() { ctx.search(q); }, 300);
  }

  function handleInputChange(e) {
    var v = e.target.value;
    setInputValue(v);
    triggerSearch(v);
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    ctx.search(inputValue);
  }

  function handleReset() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setInputValue('');
    ctx.reset();
  }

  var isLoading = state.status === 'loading';
  var isLoadingMore = state.status === 'loading-more';
  var isSuccess = state.status === 'success';
  var isError = state.status === 'error';
  var isIdle = state.status === 'idle';
  var showSkeleton = isLoading;

  return React.createElement('div', { className: 'page-stack search-page' },

    React.createElement('header', { className: 'search-page__header' },
      React.createElement('h1', { className: 'page-title' }, 'Suche')
    ),

    React.createElement('form', { className: 'search-page__form', onSubmit: handleSubmit },
      React.createElement('div', { className: 'search-bar search-bar--lg' },
        React.createElement('input', {
          className: 'search-bar__field',
          type: 'search',
          placeholder: 'Themen, Dokumente, Absätze durchsuchen …',
          value: inputValue,
          onChange: handleInputChange,
          autoFocus: true,
          'aria-label': 'Suchbegriff',
        }),
        React.createElement('button', {
          type: 'submit',
          className: 'button-primary',
          disabled: isLoading || isLoadingMore,
        }, isLoading ? 'Suche …' : 'Suchen'),
        inputValue && React.createElement('button', {
          type: 'button',
          className: 'button-secondary',
          onClick: handleReset,
        }, 'Zurücksetzen')
      )
    ),

    !isIdle && React.createElement('div', { className: 'search-page__controls' },
      React.createElement(KindTabs, {
        activeKinds: state.kindFilter,
        onChange: ctx.setKindFilter,
      }),
      React.createElement(SortDropdown, {
        value: state.sort,
        onChange: ctx.setSort,
      })
    ),

    React.createElement('div', { className: 'search-page__results' },

      isIdle && React.createElement(EmptyHint),

      isError && React.createElement(ErrorState, {
        error: state.error,
        onRetry: function() { ctx.search(inputValue); },
      }),

      showSkeleton && [1, 2, 3, 4].map(function(n) {
        return React.createElement(SkeletonCard, { key: n });
      }),

      isSuccess && state.executedQuery && React.createElement(ResultCount, {
        total: state.total,
        hits: state.hits.length,
        executedQuery: state.executedQuery,
      }),

      isSuccess && state.hits.length === 0 &&
        React.createElement(NoResults, { query: state.executedQuery }),

      isSuccess && state.hits.map(function(hit) {
        return React.createElement(UnifiedSearchResultCard, { key: hit.kind + ':' + hit.id, hit: hit });
      }),

      isLoadingMore && [1, 2].map(function(n) {
        return React.createElement(SkeletonCard, { key: 'more-' + n });
      }),

      isSuccess && state.hasMore && !isLoadingMore &&
        React.createElement('div', { className: 'search-page__load-more' },
          React.createElement('button', {
            className: 'button-secondary',
            onClick: ctx.loadMore,
          }, 'Weitere laden')
        )
    ),

    React.createElement('style', null, `
      .search-page { display: flex; flex-direction: column; height: 100%; }
      .search-page__header { padding: 16px 24px 0; flex-shrink: 0; }
      .search-page__form { padding: 12px 24px 0; flex-shrink: 0; }
      .search-page__controls {
        padding: 12px 24px 0;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
      }
      .search-page__results {
        flex: 1;
        overflow-y: auto;
        padding: 12px 24px 24px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
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
      .button-primary {
        padding: 9px 20px; border-radius: 6px; font-size: 14px; font-weight: 600;
        cursor: pointer; border: none;
        background: var(--t-magenta, #E20074); color: #fff; white-space: nowrap;
      }
      .button-primary:disabled { opacity: 0.6; cursor: not-allowed; }
      .button-secondary {
        padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 500;
        cursor: pointer; border: 1px solid var(--color-border, #ccc);
        background: var(--color-surface, #fff); color: var(--color-text, #1c1c1c);
        white-space: nowrap;
      }
      .button-secondary:hover { background: var(--color-surface-alt, #f5f5f5); }

      /* Kind tabs */
      .search-kind-tabs { display: flex; gap: 4px; flex-wrap: wrap; }
      .search-kind-tab {
        padding: 5px 14px; border-radius: 20px; border: 1px solid var(--color-border, #ccc);
        font-size: 13px; cursor: pointer; background: var(--color-surface, #fff);
        color: var(--color-text, #1c1c1c);
      }
      .search-kind-tab--active {
        background: var(--t-magenta, #E20074); color: #fff; border-color: var(--t-magenta, #E20074);
        font-weight: 600;
      }

      /* Sort */
      .search-sort { display: flex; align-items: center; gap: 8px; }
      .search-sort__label { font-size: 12px; color: var(--color-text-secondary, #888); }
      .search-sort__select {
        padding: 5px 10px; font-size: 13px; border-radius: 6px;
        border: 1px solid var(--color-border, #ccc);
        background: var(--color-surface, #fff); color: var(--color-text, #1c1c1c);
        cursor: pointer;
      }

      /* Result count */
      .search-result-count {
        margin: 0; font-size: 12px; color: var(--color-text-secondary, #888);
      }

      /* Empty / error states */
      .search-page__empty, .search-page__error {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 8px; padding: 48px 24px;
        color: var(--color-text-secondary, #666); font-size: 14px; text-align: center;
      }
      .search-page__empty p, .search-page__error p { margin: 0; }
      .search-hint { font-size: 12px; }
      .search-page__error { color: var(--color-danger, #880e4f); }

      /* Load more */
      .search-page__load-more { display: flex; justify-content: center; padding: 16px 0 4px; }

      /* Skeleton */
      @keyframes skeleton-pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
      .unified-skeleton {
        background: var(--color-surface, #fff);
        border: 1px solid var(--color-border, #e0e0e0);
        border-radius: 8px;
        padding: 14px 18px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        animation: skeleton-pulse 1.4s ease-in-out infinite;
      }
      .unified-skeleton__badge { width: 60px; height: 16px; background: #e0e0e0; border-radius: 10px; }
      .unified-skeleton__title { width: 55%; height: 14px; background: #e0e0e0; border-radius: 4px; }
      .unified-skeleton__line { height: 12px; background: #e0e0e0; border-radius: 4px; }
      .unified-skeleton__line--short { width: 70%; }
    `)
  );
}
