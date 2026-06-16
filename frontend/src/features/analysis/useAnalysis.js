import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  listAnalysisJobs,
  getAnalysisJob,
  cancelAnalysisJob,
  retryAnalysisJob,
  markResultForReview,
  approveAnalysisResult,
  rejectAnalysisResult,
  importAnalysisResult,
} from '../../api/analysis.js';
import { createRequestCoordinator } from '../../api/requestCoordinator.js';

function mapError(err) {
  if (!err) return { userMessage: 'Unbekannter Fehler.', code: 'UNKNOWN' };
  if (err.status === 404 || err.code === 'NOT_FOUND') {
    return { userMessage: 'Analyse-API nicht erreichbar.', code: 'NOT_FOUND' };
  }
  if (err.userMessage) return err;
  return { userMessage: err.message || 'Unbekannter Fehler.', code: err.code || 'UNKNOWN' };
}

function mapJob(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    status: raw.status || 'queued',
    analysisType: raw.analysis_type || '',
    sourceType: raw.source_type || null,
    sourceDocumentIds: raw.source_document_ids || [],
    prompt: raw.prompt || '',
    provider: raw.provider || null,
    model: raw.model || null,
    resultId: raw.result_id || null,
    createdBy: raw.created_by || null,
    createdAt: raw.created_at || null,
    startedAt: raw.started_at || null,
    finishedAt: raw.finished_at || null,
    errorCode: raw.error_code || null,
    errorMessage: raw.error_message || null,
    result: raw.result ? mapResult(raw.result) : null,
    suggestions: (raw.suggestions || []).map(mapSuggestion),
  };
}

function mapResult(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    jobId: raw.job_id,
    title: raw.title || null,
    summary: raw.summary || '',
    contentMarkdown: raw.content_markdown || null,
    keyPoints: raw.key_points || [],
    suggestedTags: raw.suggested_tags || [],
    suggestedTopics: raw.suggested_topics || [],
    sources: raw.sources || null,
    confidence: raw.confidence != null ? raw.confidence : null,
    status: raw.status || 'draft',
    approvedAt: raw.approved_at || null,
    approvedBy: raw.approved_by || null,
    updatedAt: raw.updated_at || null,
    createdAt: raw.created_at || null,
  };
}

function mapSuggestion(raw) {
  return {
    id: raw.id,
    suggestionType: raw.suggestion_type,
    payload: raw.payload || {},
    status: raw.status || 'pending',
  };
}

function mapListItem(raw) {
  return {
    id: raw.id,
    status: raw.status || 'queued',
    analysisType: raw.analysis_type || '',
    sourceType: raw.source_type || null,
    prompt: raw.prompt || '',
    provider: raw.provider || null,
    model: raw.model || null,
    resultId: raw.result_id || null,
    createdAt: raw.created_at || null,
    finishedAt: raw.finished_at || null,
    errorCode: raw.error_code || null,
  };
}

export function useAnalysis() {
  var auth = useAuth();
  var token = auth.token;
  var workspaceId = auth.active_workspace_id;
  var isAuthReady = auth.isAuthReady;

  var [listState, setListState] = useState({ status: 'loading', items: [], total: 0, error: null });
  var [detailState, setDetailState] = useState({ status: 'idle', data: null, error: null });
  var [selectedId, setSelectedId] = useState(null);
  var [actionState, setActionState] = useState({ status: 'idle', error: null });
  var [statusFilter, setStatusFilter] = useState(null);
  var [page, setPage] = useState(0);
  var [newJobDialogOpen, setNewJobDialogOpen] = useState(false);
  var LIMIT = 20;

  var ctxRef = useRef({ authToken: '', workspaceId: '' });
  var coordRef = useRef(null);
  ctxRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!coordRef.current) {
    coordRef.current = createRequestCoordinator({ getContext: function() { return ctxRef.current; } });
  }

  var loadList = useCallback(function(opts) {
    var o = opts || {};
    var ticket = coordRef.current.begin('analysis:list');
    setListState(function(prev) { return { status: 'loading', items: prev.items, total: prev.total, error: null }; });
    listAnalysisJobs(
      { limit: LIMIT, offset: o.offset != null ? o.offset : 0, status: o.statusFilter !== undefined ? o.statusFilter : statusFilter },
      { signal: ticket.signal, correlationId: ticket.correlationId },
    )
      .then(function(raw) {
        if (!coordRef.current.isCurrent(ticket)) return;
        var items = (raw.items || []).map(mapListItem);
        setListState({ status: 'success', items: items, total: raw.total || 0, error: null });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setListState({ status: 'error', items: [], total: 0, error: mapError(err) });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, [statusFilter]);

  var loadDetail = useCallback(function(id) {
    if (!id) { setDetailState({ status: 'idle', data: null, error: null }); return; }
    var ticket = coordRef.current.begin('analysis:detail');
    setDetailState({ status: 'loading', data: null, error: null });
    getAnalysisJob(id, { signal: ticket.signal, correlationId: ticket.correlationId })
      .then(function(raw) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setDetailState({ status: 'success', data: mapJob(raw), error: null });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setDetailState({ status: 'error', data: null, error: mapError(err) });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, []);

  useEffect(function() {
    if (!isAuthReady || !token) return;
    loadList({ offset: page * LIMIT });
  }, [isAuthReady, token, workspaceId, statusFilter, page, loadList]);

  var handleSelect = useCallback(function(id) {
    setSelectedId(id);
    loadDetail(id);
  }, [loadDetail]);

  var handleRefresh = useCallback(function() {
    loadList({ offset: page * LIMIT });
    if (selectedId) loadDetail(selectedId);
  }, [loadList, loadDetail, selectedId, page]);

  var handleCancel = useCallback(function(jobId) {
    setActionState({ status: 'loading', error: null });
    cancelAnalysisJob(jobId)
      .then(function() {
        setActionState({ status: 'idle', error: null });
        handleRefresh();
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [handleRefresh]);

  var handleRetry = useCallback(function(jobId) {
    setActionState({ status: 'loading', error: null });
    retryAnalysisJob(jobId)
      .then(function(raw) {
        setActionState({ status: 'idle', error: null });
        handleRefresh();
        handleSelect(raw.id);
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [handleRefresh, handleSelect]);

  var handleMarkForReview = useCallback(function(resultId) {
    setActionState({ status: 'loading', error: null });
    markResultForReview(resultId, null)
      .then(function() {
        setActionState({ status: 'idle', error: null });
        if (selectedId) loadDetail(selectedId);
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [selectedId, loadDetail]);

  var handleApprove = useCallback(function(resultId, note) {
    setActionState({ status: 'loading', error: null });
    approveAnalysisResult(resultId, note || null)
      .then(function() {
        setActionState({ status: 'idle', error: null });
        if (selectedId) loadDetail(selectedId);
        handleRefresh();
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [selectedId, loadDetail, handleRefresh]);

  var handleReject = useCallback(function(resultId, reason) {
    setActionState({ status: 'loading', error: null });
    rejectAnalysisResult(resultId, reason)
      .then(function() {
        setActionState({ status: 'idle', error: null });
        if (selectedId) loadDetail(selectedId);
        handleRefresh();
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [selectedId, loadDetail, handleRefresh]);

  var handleImport = useCallback(function(resultId) {
    // IMPORT GUARD CONTRACT: called only when result.status === 'approved'.
    // The btn-import button in AnalysisResultPanel is not rendered for any other status.
    setActionState({ status: 'loading', error: null });
    importAnalysisResult(resultId)
      .then(function() {
        setActionState({ status: 'idle', error: null });
        if (selectedId) loadDetail(selectedId);
        handleRefresh();
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [selectedId, loadDetail, handleRefresh]);

  var handleFilterChange = useCallback(function(value) {
    setStatusFilter(value || null);
    setPage(0);
  }, []);

  var openNewJobDialog  = useCallback(function() { setNewJobDialogOpen(true); }, []);
  var closeNewJobDialog = useCallback(function() { setNewJobDialogOpen(false); }, []);

  var handleJobCreated = useCallback(function(job) {
    loadList({ offset: 0 });
    if (job && job.id) { handleSelect(job.id); }
  }, [loadList, handleSelect]);

  return {
    listState: listState,
    detailState: detailState,
    selectedId: selectedId,
    actionState: actionState,
    statusFilter: statusFilter,
    page: page,
    limit: LIMIT,
    newJobDialogOpen: newJobDialogOpen,
    handleSelect: handleSelect,
    handleRefresh: handleRefresh,
    handleCancel: handleCancel,
    handleRetry: handleRetry,
    handleMarkForReview: handleMarkForReview,
    handleApprove: handleApprove,
    handleReject: handleReject,
    handleImport: handleImport,
    handleFilterChange: handleFilterChange,
    setPage: setPage,
    openNewJobDialog: openNewJobDialog,
    closeNewJobDialog: closeNewJobDialog,
    handleJobCreated: handleJobCreated,
  };
}
