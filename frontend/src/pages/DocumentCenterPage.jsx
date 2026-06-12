import React from 'react';
import { DocumentFilterPanel } from '../features/documents/DocumentFilterPanel.jsx';
import { DocumentListPanel } from '../features/documents/DocumentListPanel.jsx';
import { DocumentPreviewPanel } from '../features/documents/DocumentPreviewPanel.jsx';
import { useDocumentCenter } from '../features/documents/useDocumentCenter.js';

const LAYOUT_STYLES = {
  page: { height: '100%', display: 'flex', flexDirection: 'column' },
  layout: { display: 'flex', flex: 1, gap: 12, minHeight: 0, overflow: 'hidden', paddingBottom: 16 },
};

function headerSubtitle(listState) {
  if (listState.status !== 'success') return 'Wird geladen';
  var n = listState.items.length;
  return n + ' Dokument' + (n !== 1 ? 'e' : '') + ' im Bestand';
}

export function DocumentCenterPage() {
  var ctx = useDocumentCenter();
  var listState = ctx.listState;
  var sortedItems = ctx.sortedItems;
  var filters = ctx.filters;
  var setFilters = ctx.setFilters;
  var sort = ctx.sort;
  var setSort = ctx.setSort;
  var selectedItem = ctx.selectedItem;
  var selectedId = ctx.selectedId;
  var setSelectedId = ctx.setSelectedId;
  var actionState = ctx.actionState;
  var handleArchive = ctx.handleArchive;
  var handleDelete = ctx.handleDelete;
  var categories = ctx.categories;
  var allTags = ctx.allTags;

  var hasActiveFilter =
    filters.search !== '' ||
    filters.status !== 'active' ||
    filters.category !== '' ||
    filters.tags.length > 0 ||
    filters.topic !== '';

  return (
    React.createElement('div', { className: 'page-stack', style: LAYOUT_STYLES.page },
      React.createElement('div', { className: 'page-header' },
        React.createElement('h1', { className: 'page-header__title' }, 'Dokumente'),
        React.createElement('span', { className: 'page-header__subtitle' }, headerSubtitle(listState))
      ),
      React.createElement('div', { className: 'doc-center-layout', style: LAYOUT_STYLES.layout },
        React.createElement(DocumentFilterPanel, {
          filters: filters,
          setFilters: setFilters,
          categories: categories,
          allTags: allTags,
        }),
        React.createElement(DocumentListPanel, {
          items: sortedItems,
          selectedId: selectedId,
          onSelect: setSelectedId,
          sort: sort,
          onSort: setSort,
          listState: listState,
          hasFilter: hasActiveFilter,
        }),
        React.createElement(DocumentPreviewPanel, {
          item: selectedItem,
          actionState: actionState,
          onArchive: handleArchive,
          onDelete: handleDelete,
        })
      )
    )
  );
}
