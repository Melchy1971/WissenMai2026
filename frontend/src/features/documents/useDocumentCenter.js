import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../../auth/AuthContext.jsx';
import { getDocuments, archiveDocument, deleteDocument } from '../../api/documents.js';
import { createRequestCoordinator } from '../../api/requestCoordinator.js';
import { mapDocumentListItem, mapError } from '../../view-models/mappers.js';

// Local mock for categories/tags until backend provides them
function extractFiltersFromItems(items) {
  const cats = new Set();
  const tags = new Set();
  items.forEach((item) => {
    if (item.category) cats.add(item.category);
    if (Array.isArray(item.tags)) item.tags.forEach((t) => tags.add(t));
  });
  return { categories: [...cats].sort(), tags: [...tags].sort() };
}

function applyLocalFilters(items, { search, status, category, tags, topic }) {
  return items.filter((item) => {
    if (search) {
      const q = search.toLowerCase();
      if (!item.title.toLowerCase().includes(q)) return false;
    }
    if (status && status !== 'all') {
      if (item.lifecycleStatus.kind !== status) return false;
    }
    if (category) {
      if (item.category !== category) return false;
    }
    if (tags.length > 0) {
      if (!tags.every((t) => (item.tags || []).includes(t))) return false;
    }
    if (topic) {
      if (!(item.topics || []).includes(topic)) return false;
    }
    return true;
  });
}

export function useDocumentCenter() {
  const { token, active_workspace_id: workspaceId, isAuthReady } = useAuth();
  const [listState, setListState] = useState({ status: 'loading', items: [], error: null });
  const [filters, setFilters] = useState({ search: '', status: 'active', category: '', tags: [], topic: '' });
  const [selectedId, setSelectedId] = useState(null);
  const [actionState, setActionState] = useState({ status: 'idle', error: null });
  const [sort, setSort] = useState({ field: 'updatedAtLabel', dir: 'desc' });

  const ctxRef = useRef({ authToken: '', workspaceId: '' });
  const coordRef = useRef(null);
  ctxRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!coordRef.current) {
    coordRef.current = createRequestCoordinator({ getContext: () => ctxRef.current });
  }

  const load = useCallback(async () => {
    const ticket = coordRef.current.begin('docCenter:list');
    setListState({ status: 'loading', items: [], error: null });
    try {
      const raw = await getDocuments(
        { limit: 200, offset: 0, lifecycleStatus: 'active' },
        { signal: ticket.signal, correlationId: ticket.correlationId },
      );
      if (!coordRef.current.isCurrent(ticket)) return;
      const archived = await getDocuments(
        { limit: 200, offset: 0, lifecycleStatus: 'archived' },
        { signal: ticket.signal, correlationId: ticket.correlationId },
      ).catch(() => []);
      if (!coordRef.current.isCurrent(ticket)) return;
      const items = [...raw, ...archived]
        .map(mapDocumentListItem)
        .filter((i) => i.lifecycleStatus.kind !== 'deleted');
      setListState({ status: 'success', items, error: null });
    } catch (err) {
      if (!coordRef.current.isCurrent(ticket)) return;
      setListState({ status: 'error', items: [], error: mapError(err) });
    } finally {
      coordRef.current.complete(ticket);
    }
  }, []);

  useEffect(() => {
    if (!isAuthReady) return () => coordRef.current.cancel('docCenter:list');
    void load();
    return () => coordRef.current.cancel('docCenter:list');
  }, [isAuthReady, workspaceId, load]);

  useEffect(() => () => coordRef.current.cancelAll(), []);

  const allItems = listState.items;
  const { categories, tags: allTags } = extractFiltersFromItems(allItems);
  const filteredItems = applyLocalFilters(allItems, filters);

  // Sort
  const sortedItems = [...filteredItems].sort((a, b) => {
    const va = a[sort.field] ?? '';
    const vb = b[sort.field] ?? '';
    const cmp = typeof va === 'string' ? va.localeCompare(vb, 'de') : va - vb;
    return sort.dir === 'asc' ? cmp : -cmp;
  });

  const selectedItem = sortedItems.find((i) => i.id === selectedId) || null;

  async function handleArchive(id) {
    setActionState({ status: 'loading', error: null });
    try {
      await archiveDocument(id);
      await load();
      if (selectedId === id) setSelectedId(null);
      setActionState({ status: 'idle', error: null });
    } catch (err) {
      setActionState({ status: 'error', error: mapError(err) });
    }
  }

  async function handleDelete(id) {
    setActionState({ status: 'loading', error: null });
    try {
      await deleteDocument(id);
      await load();
      if (selectedId === id) setSelectedId(null);
      setActionState({ status: 'idle', error: null });
    } catch (err) {
      setActionState({ status: 'error', error: mapError(err) });
    }
  }

  return {
    listState,
    sortedItems,
    filters,
    setFilters,
    sort,
    setSort,
    selectedItem,
    selectedId,
    setSelectedId,
    actionState,
    handleArchive,
    handleDelete,
    categories,
    allTags,
    reload: load,
  };
}
