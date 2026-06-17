import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '../../auth/AuthContext.jsx';
import {
  listExportJobs,
  getExportJob,
  startExportJob,
  cancelExportJob,
  retryExportJob,
  downloadExportFile,
  deleteExportFile,
  listExportTemplates,
  createExportTemplate,
  updateExportTemplate,
  deleteExportTemplate,
} from '../../api/export.js';
import { createRequestCoordinator } from '../../api/requestCoordinator.js';

function mapError(err) {
  if (!err) return { userMessage: 'Unbekannter Fehler.', code: 'UNKNOWN' };
  if (err.userMessage) return err;
  return { userMessage: err.message || 'Unbekannter Fehler.', code: err.code || 'UNKNOWN' };
}

function mapJob(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    workspaceId: raw.workspace_id || null,
    status: raw.status || 'QUEUED',
    sourceType: raw.source_type || null,
    sourceIds: raw.source_ids || null,
    exportFormat: raw.export_format || null,
    fileName: raw.file_name || '',
    filePath: raw.file_path || null,
    errorMessage: raw.error_message || null,
    createdBy: raw.created_by || null,
    createdAt: raw.created_at || null,
    startedAt: raw.started_at || null,
    finishedAt: raw.finished_at || null,
  };
}

function mapTemplate(raw) {
  if (!raw) return null;
  return {
    id: raw.id,
    name: raw.name || '',
    exportFormat: raw.export_format || null,
    layoutConfig: raw.layout_config || null,
    isDefault: raw.is_default || false,
    createdAt: raw.created_at || null,
    updatedAt: raw.updated_at || null,
  };
}

var LIMIT = 20;

export function useExport() {
  var auth = useAuth();
  var token = auth.token;
  var workspaceId = auth.active_workspace_id;
  var isAuthReady = auth.isAuthReady;

  var [listState, setListState] = useState({ status: 'loading', items: [], total: 0, error: null });
  var [detailState, setDetailState] = useState({ status: 'idle', data: null, error: null });
  var [selectedId, setSelectedId] = useState(null);
  var [actionState, setActionState] = useState({ status: 'idle', error: null });
  var [statusFilter, setStatusFilter] = useState(null);
  var [formatFilter, setFormatFilter] = useState(null);
  var [page, setPage] = useState(0);
  var [newExportDialogOpen, setNewExportDialogOpen] = useState(false);

  var [templateState, setTemplateState] = useState({ status: 'loading', items: [], error: null });
  var [templateActionState, setTemplateActionState] = useState({ status: 'idle', error: null });

  var ctxRef = useRef({ authToken: '', workspaceId: '' });
  var coordRef = useRef(null);
  ctxRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!coordRef.current) {
    coordRef.current = createRequestCoordinator({ getContext: function() { return ctxRef.current; } });
  }

  var loadList = useCallback(function(opts) {
    var o = opts || {};
    var ticket = coordRef.current.begin('export:list');
    setListState(function(prev) { return { status: 'loading', items: prev.items, total: prev.total, error: null }; });
    listExportJobs(
      {
        limit: LIMIT,
        offset: o.offset != null ? o.offset : 0,
        status: o.statusFilter !== undefined ? o.statusFilter : statusFilter,
        format: o.formatFilter !== undefined ? o.formatFilter : formatFilter,
      },
      { signal: ticket.signal, correlationId: ticket.correlationId },
    )
      .then(function(raw) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setListState({ status: 'success', items: (raw.items || []).map(mapJob), total: raw.total || 0, error: null });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setListState({ status: 'error', items: [], total: 0, error: mapError(err) });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, [statusFilter, formatFilter]);

  var loadDetail = useCallback(function(id) {
    if (!id) { setDetailState({ status: 'idle', data: null, error: null }); return; }
    var ticket = coordRef.current.begin('export:detail');
    setDetailState({ status: 'loading', data: null, error: null });
    getExportJob(id, { signal: ticket.signal, correlationId: ticket.correlationId })
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

  var loadTemplates = useCallback(function() {
    var ticket = coordRef.current.begin('export:templates');
    setTemplateState(function(prev) { return { status: 'loading', items: prev.items, error: null }; });
    listExportTemplates({}, { signal: ticket.signal })
      .then(function(raw) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setTemplateState({ status: 'success', items: (raw.items || []).map(mapTemplate), error: null });
      })
      .catch(function(err) {
        if (!coordRef.current.isCurrent(ticket)) return;
        setTemplateState({ status: 'error', items: [], error: mapError(err) });
      })
      .finally(function() { coordRef.current.complete(ticket); });
  }, []);

  useEffect(function() {
    if (!isAuthReady || !token) return;
    loadList({ offset: page * LIMIT });
  }, [isAuthReady, token, workspaceId, statusFilter, formatFilter, page, loadList]);

  useEffect(function() {
    if (!isAuthReady || !token) return;
    loadTemplates();
  }, [isAuthReady, token, loadTemplates]);

  var handleSelect = useCallback(function(id) {
    setSelectedId(id);
    loadDetail(id);
  }, [loadDetail]);

  var handleRefresh = useCallback(function() {
    loadList({ offset: page * LIMIT });
    if (selectedId) loadDetail(selectedId);
  }, [loadList, loadDetail, selectedId, page]);

  var handleStart = useCallback(function(jobId) {
    setActionState({ status: 'loading', error: null });
    startExportJob(jobId)
      .then(function(raw) {
        setActionState({ status: 'idle', error: null });
        setDetailState({ status: 'success', data: mapJob(raw), error: null });
        loadList({ offset: page * LIMIT });
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [loadList, page]);

  var handleCancel = useCallback(function(jobId) {
    setActionState({ status: 'loading', error: null });
    cancelExportJob(jobId)
      .then(function(raw) {
        setActionState({ status: 'idle', error: null });
        setDetailState({ status: 'success', data: mapJob(raw), error: null });
        loadList({ offset: page * LIMIT });
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [loadList, page]);

  var handleRetry = useCallback(function(jobId) {
    setActionState({ status: 'loading', error: null });
    retryExportJob(jobId)
      .then(function(raw) {
        setActionState({ status: 'idle', error: null });
        handleRefresh();
        handleSelect(raw.id);
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [handleRefresh, handleSelect]);

  var handleDownload = useCallback(function(jobId) {
    setActionState({ status: 'loading', error: null });
    downloadExportFile(jobId)
      .then(function(result) {
        setActionState({ status: 'idle', error: null });
        var url = URL.createObjectURL(result.blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = result.fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, []);

  var handleDeleteFile = useCallback(function(jobId) {
    setActionState({ status: 'loading', error: null });
    deleteExportFile(jobId)
      .then(function() {
        setActionState({ status: 'idle', error: null });
        handleRefresh();
        if (selectedId === jobId) loadDetail(jobId);
      })
      .catch(function(err) {
        setActionState({ status: 'error', error: mapError(err) });
      });
  }, [handleRefresh, loadDetail, selectedId]);

  var handleStatusFilterChange = useCallback(function(value) {
    setStatusFilter(value || null);
    setPage(0);
  }, []);

  var handleFormatFilterChange = useCallback(function(value) {
    setFormatFilter(value || null);
    setPage(0);
  }, []);

  var openNewExportDialog  = useCallback(function() { setNewExportDialogOpen(true); }, []);
  var closeNewExportDialog = useCallback(function() { setNewExportDialogOpen(false); }, []);

  var handleExportCreated = useCallback(function(job) {
    loadList({ offset: 0 });
    if (job && job.id) handleSelect(job.id);
  }, [loadList, handleSelect]);

  // Template handlers
  var handleCreateTemplate = useCallback(function(fields) {
    setTemplateActionState({ status: 'loading', error: null });
    return createExportTemplate(fields)
      .then(function() {
        setTemplateActionState({ status: 'idle', error: null });
        loadTemplates();
      })
      .catch(function(err) {
        var mapped = mapError(err);
        setTemplateActionState({ status: 'error', error: mapped });
        throw mapped;
      });
  }, [loadTemplates]);

  var handleUpdateTemplate = useCallback(function(templateId, fields) {
    setTemplateActionState({ status: 'loading', error: null });
    return updateExportTemplate(templateId, fields)
      .then(function() {
        setTemplateActionState({ status: 'idle', error: null });
        loadTemplates();
      })
      .catch(function(err) {
        var mapped = mapError(err);
        setTemplateActionState({ status: 'error', error: mapped });
        throw mapped;
      });
  }, [loadTemplates]);

  var handleDeleteTemplate = useCallback(function(templateId) {
    setTemplateActionState({ status: 'loading', error: null });
    deleteExportTemplate(templateId)
      .then(function() {
        setTemplateActionState({ status: 'idle', error: null });
        loadTemplates();
      })
      .catch(function(err) {
        setTemplateActionState({ status: 'error', error: mapError(err) });
      });
  }, [loadTemplates]);

  return {
    listState: listState,
    detailState: detailState,
    selectedId: selectedId,
    actionState: actionState,
    statusFilter: statusFilter,
    formatFilter: formatFilter,
    page: page,
    limit: LIMIT,
    newExportDialogOpen: newExportDialogOpen,
    templateState: templateState,
    templateActionState: templateActionState,
    handleSelect: handleSelect,
    handleRefresh: handleRefresh,
    handleStart: handleStart,
    handleCancel: handleCancel,
    handleRetry: handleRetry,
    handleDownload: handleDownload,
    handleDeleteFile: handleDeleteFile,
    handleStatusFilterChange: handleStatusFilterChange,
    handleFormatFilterChange: handleFormatFilterChange,
    setPage: setPage,
    openNewExportDialog: openNewExportDialog,
    closeNewExportDialog: closeNewExportDialog,
    handleExportCreated: handleExportCreated,
    handleCreateTemplate: handleCreateTemplate,
    handleUpdateTemplate: handleUpdateTemplate,
    handleDeleteTemplate: handleDeleteTemplate,
  };
}
