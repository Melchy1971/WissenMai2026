import { useCallback, useEffect, useReducer } from 'react';

import {
  getDataQualitySummary,
  getDataQualityRun,
  listDataQualityFindings,
} from '../../api/dataQuality.js';

const FINDINGS_PAGE_SIZE = 50;

function init() {
  return {
    summary: null,
    latestRun: null,
    findings: null,
    findingsTotal: 0,
    findingsOffset: 0,
    filters: { severity: null, findingType: null },
    loading: true,
    error: null,
  };
}

function reducer(state, action) {
  switch (action.type) {
    case 'LOAD_START':
      return { ...state, loading: true, error: null };
    case 'SUMMARY_OK':
      return { ...state, summary: action.summary, loading: false };
    case 'RUN_OK':
      return { ...state, latestRun: action.run };
    case 'FINDINGS_OK':
      return {
        ...state,
        findings: action.findings,
        findingsTotal: action.total,
        findingsOffset: action.offset,
      };
    case 'ERROR':
      return { ...state, loading: false, error: action.error };
    case 'SET_FILTER':
      return {
        ...state,
        filters: { ...state.filters, [action.key]: action.value },
        findingsOffset: 0,
      };
    case 'SET_OFFSET':
      return { ...state, findingsOffset: action.offset };
    default:
      return state;
  }
}

export function useDataQuality() {
  const [state, dispatch] = useReducer(reducer, undefined, init);

  const loadSummary = useCallback(async () => {
    dispatch({ type: 'LOAD_START' });
    try {
      const summary = await getDataQualitySummary();
      dispatch({ type: 'SUMMARY_OK', summary });

      if (summary.latest_run_id) {
        const run = await getDataQualityRun(summary.latest_run_id);
        dispatch({ type: 'RUN_OK', run });
      }
    } catch (err) {
      dispatch({ type: 'ERROR', error: err });
    }
  }, []);

  const loadFindings = useCallback(
    async (offset = 0) => {
      try {
        const result = await listDataQualityFindings({
          severity: state.filters.severity,
          findingType: state.filters.findingType,
          limit: FINDINGS_PAGE_SIZE,
          offset,
        });
        dispatch({ type: 'FINDINGS_OK', findings: result.items, total: result.total, offset });
      } catch (err) {
        dispatch({ type: 'ERROR', error: err });
      }
    },
    [state.filters],
  );

  const setFilter = useCallback((key, value) => {
    dispatch({ type: 'SET_FILTER', key, value: value === '' ? null : value });
  }, []);

  const setOffset = useCallback((offset) => {
    dispatch({ type: 'SET_OFFSET', offset });
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    loadFindings(state.findingsOffset);
  }, [loadFindings, state.findingsOffset]);

  return { ...state, reload: loadSummary, setFilter, setOffset, pageSize: FINDINGS_PAGE_SIZE };
}
