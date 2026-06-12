import { useEffect, useRef, useState } from 'react';
import { useAuth } from '../../auth/AuthContext.jsx';
import { importDocument } from '../../api/documents.js';
import { getJob } from '../../api/jobs.js';
import { createRequestCoordinator } from '../../api/requestCoordinator.js';
import { mapError, mapImportOutcome, mapJobStatus } from '../../view-models/mappers.js';

const POLL_INTERVAL_MS = 250;
const POLL_MAX_ATTEMPTS = 120;
const POLL_MAX_NETWORK_ERRORS = 3;

var IDLE_STATE = { phase: 'idle', fileName: '', job: null, jobStatus: null, outcome: null, error: null };

// phase: 'idle' | 'uploading' | 'polling' | 'done' | 'error'
export function useImport() {
  var auth = useAuth();
  var token = auth.token;
  var workspaceId = auth.active_workspace_id;

  var currentState = useState(IDLE_STATE);
  var current = currentState[0];
  var setCurrent = currentState[1];

  var historyState = useState([]);
  var history = historyState[0];
  var setHistory = historyState[1];

  var ctxRef = useRef({ authToken: '', workspaceId: '' });
  var coordRef = useRef(null);
  var pollTimerRef = useRef(null);
  var pollAttemptsRef = useRef(0);
  var pollNetErrRef = useRef(0);
  var inFlightRef = useRef(false);

  ctxRef.current = { authToken: token || '', workspaceId: workspaceId || '' };
  if (!coordRef.current) {
    coordRef.current = createRequestCoordinator({ getContext: function() { return ctxRef.current; } });
  }

  useEffect(function() {
    return function() {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      coordRef.current.cancelAll();
    };
  }, []);

  function addHistory(entry) {
    setHistory(function(prev) {
      return [Object.assign({}, entry, { uid: entry.jobId + '-' + Date.now() }), ...prev];
    });
  }

  function pollJob(jobId, fileName, ticket) {
    if (!coordRef.current.isCurrent(ticket)) { inFlightRef.current = false; return; }
    if (pollAttemptsRef.current >= POLL_MAX_ATTEMPTS) {
      inFlightRef.current = false;
      var timeoutErr = mapError({ code: 'JOB_TIMEOUT', message: 'Der Import-Job hat zu lange gedauert.', details: {} });
      setCurrent({ phase: 'error', fileName: fileName, job: null, jobStatus: null, outcome: null, error: timeoutErr });
      addHistory({ jobId: jobId, fileName: fileName, status: 'error', label: 'Timeout' });
      return;
    }
    pollAttemptsRef.current += 1;

    getJob(jobId, { signal: ticket.signal, correlationId: ticket.correlationId }).then(function(job) {
      if (!coordRef.current.isCurrent(ticket)) return;
      pollNetErrRef.current = 0;
      var jobStatus = mapJobStatus(job);

      if (job.status === 'completed') {
        inFlightRef.current = false;
        var outcome = mapImportOutcome(job.result, { fileName: fileName });
        setCurrent({ phase: 'done', fileName: fileName, job: job, jobStatus: jobStatus, outcome: outcome, error: null });
        addHistory({
          jobId: jobId,
          fileName: fileName,
          status: 'success',
          label: outcome.title,
          documentId: job.result && job.result.document_id,
          chunks: job.result && job.result.chunk_count != null ? job.result.chunk_count : 0,
        });
        coordRef.current.complete(ticket);
        return;
      }
      if (job.status === 'failed') {
        inFlightRef.current = false;
        var failErr = mapError({ code: job.error_code, message: job.error_message, details: {} });
        setCurrent({ phase: 'error', fileName: fileName, job: job, jobStatus: jobStatus, outcome: null, error: failErr });
        addHistory({ jobId: jobId, fileName: fileName, status: 'error', label: job.error_code || 'Fehlgeschlagen' });
        coordRef.current.complete(ticket);
        return;
      }

      setCurrent(function(prev) { return Object.assign({}, prev, { job: job, jobStatus: jobStatus }); });
      pollTimerRef.current = setTimeout(function() { pollJob(jobId, fileName, ticket); }, POLL_INTERVAL_MS);
    }).catch(function(err) {
      if (!coordRef.current.isCurrent(ticket)) return;
      pollNetErrRef.current += 1;
      if (pollNetErrRef.current <= POLL_MAX_NETWORK_ERRORS) {
        pollTimerRef.current = setTimeout(function() { pollJob(jobId, fileName, ticket); }, 1000 * pollNetErrRef.current);
      } else {
        inFlightRef.current = false;
        var netErr = mapError(err);
        setCurrent({ phase: 'error', fileName: fileName, job: null, jobStatus: null, outcome: null, error: netErr });
        addHistory({ jobId: jobId, fileName: fileName, status: 'error', label: 'Netzwerkfehler' });
        coordRef.current.complete(ticket);
      }
    });
  }

  function handleUpload(file) {
    if (inFlightRef.current) return;
    if (!file) {
      setCurrent(Object.assign({}, IDLE_STATE, {
        phase: 'error',
        error: mapError({ code: 'FILE_REQUIRED', message: 'Bitte waehle eine Datei aus.', details: {} }),
      }));
      return;
    }
    pollAttemptsRef.current = 0;
    pollNetErrRef.current = 0;
    inFlightRef.current = true;
    var ticket = coordRef.current.begin('import:upload');
    setCurrent({ phase: 'uploading', fileName: file.name, job: null, jobStatus: null, outcome: null, error: null });

    importDocument(file, { signal: ticket.signal, correlationId: ticket.correlationId }).then(function(job) {
      if (!coordRef.current.isCurrent(ticket)) return;
      setCurrent(function(prev) { return Object.assign({}, prev, { phase: 'polling', job: job, jobStatus: mapJobStatus(job) }); });
      pollJob(job.id, file.name, ticket);
    }).catch(function(err) {
      if (!coordRef.current.isCurrent(ticket)) return;
      inFlightRef.current = false;
      var uploadErr = mapError(err);
      setCurrent({ phase: 'error', fileName: file.name, job: null, jobStatus: null, outcome: null, error: uploadErr });
      coordRef.current.complete(ticket);
    });
  }

  function handleReset() {
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    coordRef.current.cancel('import:upload');
    inFlightRef.current = false;
    setCurrent(Object.assign({}, IDLE_STATE));
  }

  var isLoading = current.phase === 'uploading' || current.phase === 'polling';

  return { current: current, history: history, handleUpload: handleUpload, handleReset: handleReset, isLoading: isLoading };
}
