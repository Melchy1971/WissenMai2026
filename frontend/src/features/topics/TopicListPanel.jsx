import React from 'react';

function EmptyState({ hasSearch }) {
  if (hasSearch) {
    return React.createElement('div', { className: 'topic-list__empty' },
      React.createElement('span', null, 'Keine Themen gefunden.'),
      React.createElement('span', { className: 'topic-list__empty-hint' }, 'Suchbegriff anpassen.')
    );
  }
  return React.createElement('div', { className: 'topic-list__empty' },
    React.createElement('span', null, 'Keine Themen vorhanden.'),
    React.createElement('span', { className: 'topic-list__empty-hint' }, 'Themen werden automatisch aus importierten Dokumenten extrahiert.')
  );
}

function TopicRow({ item, selected, onSelect }) {
  function handleClick() { onSelect(item.id); }
  function handleKey(e) { if (e.key === 'Enter' || e.key === ' ') onSelect(item.id); }
  var cls = 'topic-list-row' + (selected ? ' topic-list-row--selected' : '');
  return React.createElement('div', {
    className: cls,
    role: 'row',
    tabIndex: 0,
    'aria-selected': selected,
    onClick: handleClick,
    onKeyDown: handleKey,
  },
    React.createElement('div', { className: 'topic-row__name' }, item.name),
    React.createElement('div', { className: 'topic-row__meta' },
      React.createElement('span', { className: 'topic-row__count' }, item.documentCount, ' Dok.'),
      item.tagCount > 0 && React.createElement('span', { className: 'topic-row__count' }, item.tagCount, ' Tags')
    )
  );
}

export function TopicListPanel({ items, selectedId, onSelect, search, onSearch, listState }) {
  if (listState.status === 'loading') {
    return React.createElement('div', { className: 'topic-list-panel panel topic-list-panel--loading' },
      React.createElement('div', { className: 'topic-list__info' }, 'Themen werden geladen …')
    );
  }

  var isNotFound = listState.status === 'error' && listState.error && listState.error.code === 'NOT_FOUND';

  if (listState.status === 'error' && !isNotFound) {
    return React.createElement('div', { className: 'topic-list-panel panel topic-list-panel--error' },
      React.createElement('div', { className: 'topic-list__info topic-list__info--error' },
        React.createElement('strong', null, 'Fehler beim Laden'),
        React.createElement('span', null, (listState.error && listState.error.userMessage) || 'Themen konnten nicht geladen werden.')
      )
    );
  }

  var headerCount = isNotFound ? '—' : items.length;
  var headerLabel = isNotFound ? 'Backend nicht verfügbar' : (items.length === 1 ? '1 Thema' : items.length + ' Themen');

  return React.createElement('div', { className: 'topic-list-panel panel' },
    React.createElement('div', { className: 'panel__header topic-list-panel__header' },
      React.createElement('span', { className: 'panel__eyebrow' }, headerLabel),
      React.createElement('div', { className: 'search-bar search-bar--sm topic-list__search' },
        React.createElement('input', {
          className: 'search-bar__field',
          type: 'search',
          placeholder: 'Thema suchen …',
          value: search,
          onChange: function(e) { onSearch(e.target.value); },
          'aria-label': 'Thema suchen',
        })
      )
    ),

    isNotFound
      ? React.createElement('div', { className: 'topic-list__placeholder' },
          React.createElement('p', { className: 'topic-list__placeholder-title' }, 'Themen-API nicht verfügbar'),
          React.createElement('p', { className: 'topic-list__placeholder-hint' },
            'GET /topics ist noch nicht implementiert. Die UI ist bereit — sobald das Backend verfügbar ist, werden Themen hier angezeigt.'
          )
        )
      : items.length === 0
        ? React.createElement(EmptyState, { hasSearch: search.length > 0 })
        : React.createElement('div', { className: 'topic-list-panel__scroll' },
            items.map(function(item) {
              return React.createElement(TopicRow, {
                key: item.id,
                item: item,
                selected: selectedId === item.id,
                onSelect: onSelect,
              });
            })
          ),

    React.createElement('style', null, `
      .topic-list-panel {
        width: 300px;
        min-width: 240px;
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .topic-list-panel--loading,
      .topic-list-panel--error { justify-content: center; align-items: center; }
      .topic-list-panel__header {
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
      }
      .topic-list__search { width: 100%; }
      .topic-list-panel__scroll { flex: 1; overflow-y: auto; }
      .topic-list-row {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 12px 16px;
        cursor: pointer;
        border-bottom: 1px solid var(--color-border, #eee);
        transition: background 0.1s;
      }
      .topic-list-row:hover { background: var(--color-hover, #f5f5f5); }
      .topic-list-row--selected { background: var(--color-accent-light, #fce4ec) !important; }
      .topic-row__name { font-size: 14px; font-weight: 500; color: var(--color-text, #1c1c1c); }
      .topic-row__meta { display: flex; gap: 12px; }
      .topic-row__count { font-size: 11px; color: var(--color-text-secondary, #666); }
      .topic-list__empty,
      .topic-list__info {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 8px; padding: 48px 24px;
        color: var(--color-text-secondary, #666); font-size: 14px; text-align: center;
      }
      .topic-list__info--error { color: var(--color-danger, #880e4f); }
      .topic-list__empty-hint { font-size: 12px; }
      .topic-list__placeholder {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 32px 24px;
        text-align: center;
        gap: 12px;
      }
      .topic-list__placeholder-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--color-text, #1c1c1c);
        margin: 0;
      }
      .topic-list__placeholder-hint {
        font-size: 12px;
        color: var(--color-text-secondary, #666);
        line-height: 1.5;
        margin: 0;
      }
    `)
  );
}
