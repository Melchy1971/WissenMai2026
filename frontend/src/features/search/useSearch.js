import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../../auth/AuthContext.jsx';
import { searchChunks } from '../../api/search.js';
import { mapSearchResult } from '../../view-models/mappers.js';
import { createRequestCoordinator } from '../../api/requestCoordinator.js';

function mapError(err) {
  if (err && err.userMessage) return err;
  return { userMessage: (err && err.message) || 'Unbekannter Fehler.', code: 'UNKNOWN' };
}

function mapRelevanceClass(rank) {
  if (rank >= 0.7) return { label: 'Sehr relevant', tone: 'high', bars: 3 };
  if (rank >= 0.3) return { label: 'Relevant', tone: 'medium', bars: 2 };
  return { label: 'Moeglicherweise relevant', tone: 'low', bars: 1 };
}

function enrichResult(mapped) {
  return Object.assign({}, mapped, { relevance: mapRelevanceClass(mapped.rank) });
}

export function useSearch() {
  var auth = useAuth();
  var token = auth.token;
  var workspaceId = auth.active_workspace_id;
  var isAuthReady = auth.isAuthReady;

  var [query, setQuery] = useState('');
  var [searchState, setSearchState] = useState({ status: 'idle', items: [], error: null, executedQuery: '' });

  var ctxRef = useRef({ authToken: '', workspaceId: '' });
  var coordRef = useRef(null);
  var debounceRef = useRef(null);

  ctxRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!coordRef.current) {
    coordRef.current = createRequestCoordinator({ getContext: function() { return ctxRef.current; } });
  }

  var executeSearch = useCallback(function(q) {
    var trimmed = q.trim();
    if (!trimmed) {
      coordRef.current.cancel('search:chunks');
      setSearchState({ status: 'idle', items: [], error: null, executedQuery: '' });
      return;
    }
    var ticket = coordRef.current.begin('search:chunks');
    setSearchState({ status: 'loading', items: [], error: null, executedQuery: trimmed });
    searchChunks({ query: trimmed, limit: 20, offset: 0 }, { signal: ticket.signal, correlationId: ticket.correlationId })
      .then(function(raw) {
        if (!coordRef.current.isCurrent(ticket)) return;
        var items = Array.isArray(raw) ? raw.map(function(r) { return enrichResult(mapSearchResult(r)); }) : [];
        setSearchState({ status: 'success', items: items, error: null, executedQuery: trimmed });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setSearchState({ status: 'error', items: [], error: mapError(err), executedQuery: trimmed });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, []);

  function handleQueryChange(value) {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(function() { executeSearch(value); }, 300);
  }

  function handleSubmit() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    executeSearch(query);
  }

  function handleReset() {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    coordRef.current.cancel('search:chunks');
    setQuery('');
    setSearchState({ status: 'idle', items: [], error: null, executedQuery: '' });
  }

  useEffect(function() {
    return function() {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      coordRef.current.cancelAll();
    };
  }, []);

  return {
    query: query,
    searchState: searchState,
    isAuthReady: isAuthReady,
    handleQueryChange: handleQueryChange,
    handleSubmit: handleSubmit,
    handleReset: handleReset,
  };
}
