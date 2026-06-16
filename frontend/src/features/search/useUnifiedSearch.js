import { useCallback, useEffect, useReducer, useRef } from 'react';
import { searchUnified } from '../../api/search.js';
import { createRequestCoordinator } from '../../api/requestCoordinator.js';

var INITIAL_STATE = {
  status: 'idle',          // idle | loading | success | error
  hits: [],
  total: 0,
  nextCursor: null,
  hasMore: false,
  executedQuery: '',
  sort: 'score_desc',
  kindFilter: [],           // [] = all
  error: null,
};

function reducer(state, action) {
  switch (action.type) {
    case 'SEARCH_START':
      return Object.assign({}, state, {
        status: 'loading', hits: [], total: 0, nextCursor: null,
        hasMore: false, error: null, executedQuery: action.query,
        sort: action.sort, kindFilter: action.kindFilter,
      });
    case 'SEARCH_SUCCESS':
      return Object.assign({}, state, {
        status: 'success',
        hits: action.hits,
        total: action.total,
        nextCursor: action.nextCursor,
        hasMore: action.hasMore,
        error: null,
      });
    case 'LOAD_MORE_START':
      return Object.assign({}, state, { status: 'loading-more' });
    case 'LOAD_MORE_SUCCESS':
      return Object.assign({}, state, {
        status: 'success',
        hits: state.hits.concat(action.hits),
        total: action.total,
        nextCursor: action.nextCursor,
        hasMore: action.hasMore,
      });
    case 'SEARCH_ERROR':
      return Object.assign({}, state, { status: 'error', error: action.error });
    case 'RESET':
      return Object.assign({}, INITIAL_STATE, { sort: state.sort, kindFilter: state.kindFilter });
    default:
      return state;
  }
}

function mapError(err) {
  if (err && err.userMessage) return err;
  return { userMessage: (err && err.message) || 'Unbekannter Fehler.', code: 'UNKNOWN' };
}

export function useUnifiedSearch() {
  var [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  var coordRef = useRef(null);
  var queryRef = useRef('');
  var stateRef = useRef(state);
  stateRef.current = state;

  if (!coordRef.current) {
    coordRef.current = createRequestCoordinator({ getContext: function() { return {}; } });
  }

  var execute = useCallback(function(query, sort, kindFilter, cursor) {
    var trimmed = query.trim();
    if (!trimmed) { dispatch({ type: 'RESET' }); return; }

    var isLoadMore = Boolean(cursor);
    var ticket = coordRef.current.begin('search:unified');

    if (isLoadMore) {
      dispatch({ type: 'LOAD_MORE_START' });
    } else {
      dispatch({ type: 'SEARCH_START', query: trimmed, sort: sort, kindFilter: kindFilter });
    }

    searchUnified(
      { query: trimmed, limit: 20, cursor: cursor, sort: sort, kind: kindFilter },
      { signal: ticket.signal, correlationId: ticket.correlationId }
    )
      .then(function(data) {
        if (!coordRef.current.isCurrent(ticket)) return;
        var hits = Array.isArray(data.hits) ? data.hits : [];
        var actionType = isLoadMore ? 'LOAD_MORE_SUCCESS' : 'SEARCH_SUCCESS';
        dispatch({
          type: actionType,
          hits: hits,
          total: data.total || 0,
          nextCursor: data.next_cursor || null,
          hasMore: Boolean(data.has_more),
        });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        dispatch({ type: 'SEARCH_ERROR', error: mapError(err) });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, []);

  function search(query) {
    queryRef.current = query;
    execute(query, stateRef.current.sort, stateRef.current.kindFilter, null);
  }

  function loadMore() {
    if (!stateRef.current.hasMore || !stateRef.current.nextCursor) return;
    execute(queryRef.current, stateRef.current.sort, stateRef.current.kindFilter, stateRef.current.nextCursor);
  }

  function setSort(sort) {
    var q = queryRef.current;
    if (q.trim()) execute(q, sort, stateRef.current.kindFilter, null);
    else dispatch({ type: 'RESET' });
  }

  function setKindFilter(kinds) {
    var q = queryRef.current;
    if (q.trim()) execute(q, stateRef.current.sort, kinds, null);
    else dispatch({ type: 'RESET' });
  }

  function reset() {
    coordRef.current.cancelAll();
    queryRef.current = '';
    dispatch({ type: 'RESET' });
  }

  useEffect(function() {
    return function() { coordRef.current.cancelAll(); };
  }, []);

  return {
    state: state,
    search: search,
    loadMore: loadMore,
    setSort: setSort,
    setKindFilter: setKindFilter,
    reset: reset,
  };
}
