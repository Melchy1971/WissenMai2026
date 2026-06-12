import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../../auth/AuthContext.jsx';
import { getTopics, getTopicDetail, createTopic, deleteTopic } from '../../api/topics.js';
import { createRequestCoordinator } from '../../api/requestCoordinator.js';

function mapError(err) {
  if (err && (err.status === 404 || err.code === 'NOT_FOUND')) {
    return { userMessage: 'Backend noch nicht verfuegbar. /topics-API fehlt.', code: 'NOT_FOUND' };
  }
  if (err && err.userMessage) return err;
  return { userMessage: (err && err.message) || 'Unbekannter Fehler.', code: 'UNKNOWN' };
}

function mapTopicItem(raw) {
  return {
    id: raw.id,
    name: raw.name || '(ohne Name)',
    summary: raw.summary || '',
    documentCount: raw.document_count != null ? raw.document_count : 0,
    tagCount: raw.tag_count != null ? raw.tag_count : 0,
    updatedAt: raw.updated_at || '',
  };
}

function mapTopicDetail(raw) {
  return {
    id: raw.id,
    name: raw.name || '(ohne Name)',
    summary: raw.summary || '',
    sources: (raw.sources || []).map(function(s) {
      return { docId: s.doc_id, title: s.title || '', excerpt: s.excerpt || '' };
    }),
    documents: (raw.documents || []).map(function(d) {
      return { id: d.id, title: d.title || '', lifecycleStatus: d.lifecycle_status || 'active', updatedAt: d.updated_at || '' };
    }),
    tags: raw.tags || [],
    linkedTopics: (raw.linked_topics || []).map(function(t) {
      return { id: t.id, name: t.name || '' };
    }),
  };
}

export function useTopics() {
  var auth = useAuth();
  var token = auth.token;
  var workspaceId = auth.active_workspace_id;
  var isAuthReady = auth.isAuthReady;

  var [listState, setListState] = useState({ status: 'loading', items: [], error: null });
  var [detailState, setDetailState] = useState({ status: 'idle', data: null, error: null });
  var [selectedId, setSelectedId] = useState(null);
  var [search, setSearch] = useState('');
  var [actionState, setActionState] = useState({ status: 'idle', error: null });

  var ctxRef = useRef({ authToken: '', workspaceId: '' });
  var coordRef = useRef(null);
  ctxRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!coordRef.current) {
    coordRef.current = createRequestCoordinator({ getContext: function() { return ctxRef.current; } });
  }

  var loadList = useCallback(function() {
    var ticket = coordRef.current.begin('topics:list');
    setListState({ status: 'loading', items: [], error: null });
    getTopics({}, { signal: ticket.signal, correlationId: ticket.correlationId })
      .then(function(raw) {
        if (!coordRef.current.isCurrent(ticket)) return;
        var items = Array.isArray(raw) ? raw.map(mapTopicItem) : [];
        setListState({ status: 'success', items: items, error: null });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setListState({ status: 'error', items: [], error: mapError(err) });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, []);

  var loadDetail = useCallback(function(id) {
    if (!id) { setDetailState({ status: 'idle', data: null, error: null }); return; }
    var ticket = coordRef.current.begin('topics:detail');
    setDetailState({ status: 'loading', data: null, error: null });
    getTopicDetail(id, { signal: ticket.signal, correlationId: ticket.correlationId })
      .then(function(raw) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setDetailState({ status: 'success', data: mapTopicDetail(raw), error: null });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setDetailState({ status: 'error', data: null, error: mapError(err) });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, []);

  useEffect(function() {
    if (!isAuthReady) return function() { coordRef.current.cancel('topics:list'); };
    loadList();
    return function() { coordRef.current.cancel('topics:list'); };
  }, [isAuthReady, workspaceId, loadList]);

  useEffect(function() {
    coordRef.current.cancel('topics:detail');
    loadDetail(selectedId);
  }, [selectedId, loadDetail]);

  useEffect(function() {
    return function() { coordRef.current.cancelAll(); };
  }, []);

  var filteredItems = listState.items.filter(function(item) {
    if (!search) return true;
    return item.name.toLowerCase().includes(search.toLowerCase());
  });

  function handleSelect(id) {
    setSelectedId(id === selectedId ? null : id);
  }

  function handleCreate(payload) {
    setActionState({ status: 'loading', error: null });
    createTopic(payload)
      .then(function() {
        loadList();
        setActionState({ status: 'idle', error: null });
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }

  function handleDelete(id) {
    setActionState({ status: 'loading', error: null });
    deleteTopic(id)
      .then(function() {
        if (selectedId === id) setSelectedId(null);
        loadList();
        setActionState({ status: 'idle', error: null });
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }

  return {
    listState: listState,
    filteredItems: filteredItems,
    detailState: detailState,
    selectedId: selectedId,
    handleSelect: handleSelect,
    search: search,
    setSearch: setSearch,
    actionState: actionState,
    handleCreate: handleCreate,
    handleDelete: handleDelete,
    reload: loadList,
  };
}
