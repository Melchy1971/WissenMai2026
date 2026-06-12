import React from 'react';
import { useTopics } from '../features/topics/useTopics.js';
import { TopicListPanel } from '../features/topics/TopicListPanel.jsx';
import { TopicDetailPanel } from '../features/topics/TopicDetailPanel.jsx';

var PAGE_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  gap: '0',
};

var HEADER_STYLE = {
  padding: '16px 24px 0',
  flexShrink: 0,
};

var CONTENT_STYLE = {
  flex: 1,
  display: 'flex',
  gap: '16px',
  padding: '16px 24px 24px',
  minHeight: 0,
  position: 'relative',
};

export function TopicsPage() {
  var ctx = useTopics();
  var listState = ctx.listState;
  var filteredItems = ctx.filteredItems;
  var detailState = ctx.detailState;
  var selectedId = ctx.selectedId;
  var handleSelect = ctx.handleSelect;
  var search = ctx.search;
  var setSearch = ctx.setSearch;
  var actionState = ctx.actionState;
  var handleDelete = ctx.handleDelete;

  var isNotFound = listState.status === 'error' && listState.error && listState.error.code === 'NOT_FOUND';
  var subtitle = isNotFound ? 'Backend nicht verfügbar' : (listState.status === 'loading' ? 'Wird geladen …' : '');

  return React.createElement('div', { className: 'page-stack', style: PAGE_STYLE },
    React.createElement('header', { style: HEADER_STYLE },
      React.createElement('h1', { className: 'page-title' }, 'Themenzentrum'),
      subtitle && React.createElement('p', { className: 'page-subtitle' }, subtitle)
    ),
    React.createElement('div', { style: CONTENT_STYLE },
      React.createElement(TopicListPanel, {
        items: filteredItems,
        selectedId: selectedId,
        onSelect: handleSelect,
        search: search,
        onSearch: setSearch,
        listState: listState,
      }),
      React.createElement(TopicDetailPanel, {
        detailState: detailState,
        selectedId: selectedId,
        actionState: actionState,
        onDelete: handleDelete,
      })
    )
  );
}
