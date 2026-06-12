import React, { useRef } from 'react';
import { Link } from 'react-router-dom';
import { useImport } from '../features/import/useImport.js';

var ACCEPTED = '.txt,.md,.docx,.doc,.pdf';

var STEPS = [
  { key: 'uploading', label: '1 Hochladen' },
  { key: 'polling',   label: '2 Verarbeiten' },
  { key: 'result',    label: '3 Ergebnis' },
];

function stepIndex(phase) {
  if (phase === 'uploading') return 0;
  if (phase === 'polling')   return 1;
  if (phase === 'done' || phase === 'error') return 2;
  return -1;
}

function StepIndicator(props) {
  var active = stepIndex(props.phase);
  if (active < 0) return null;
  return React.createElement('div', { className: 'import-steps', 'data-testid': 'import-steps' },
    STEPS.map(function(step, i) {
      var cls = 'import-step';
      if (i === active) cls += ' import-step--active';
      else if (i < active) cls += ' import-step--done';
      return React.createElement('span', { key: step.key, className: cls }, step.label);
    })
  );
}

function PhaseStatus(props) {
  var current = props.current;
  var phase = current.phase;
  var fileName = current.fileName;
  var jobStatus = current.jobStatus;
  var outcome = current.outcome;
  var error = current.error;
  var job = current.job;

  if (phase === 'uploading') {
    return React.createElement('div', { className: 'panel', 'data-testid': 'import-phase' },
      React.createElement('p', { className: 'panel__eyebrow' }, 'Hochladen'),
      React.createElement('p', null,
        'Datei wird hochgeladen: ',
        React.createElement('strong', { 'data-testid': 'import-filename' }, fileName)
      )
    );
  }

  if (phase === 'polling') {
    return React.createElement('div', { className: 'panel', 'data-testid': 'import-phase' },
      React.createElement('p', { className: 'panel__eyebrow' }, 'Verarbeitung'),
      React.createElement('p', null,
        'Dokument wird verarbeitet: ',
        React.createElement('strong', { 'data-testid': 'import-filename' }, fileName)
      ),
      jobStatus
        ? React.createElement('p', { 'data-testid': 'job-status' },
            jobStatus.label + ' — ' + jobStatus.message
          )
        : null
    );
  }

  if (phase === 'done' && outcome) {
    var docId = job && job.result && job.result.document_id;
    var chunks = job && job.result && job.result.chunk_count != null ? job.result.chunk_count : null;
    return React.createElement('div', { className: 'panel', 'data-testid': 'import-success' },
      React.createElement('p', { className: 'panel__eyebrow' }, 'Abgeschlossen'),
      React.createElement('p', null, React.createElement('strong', null, outcome.title)),
      React.createElement('p', null, outcome.message),
      docId
        ? React.createElement('p', null,
            'Dokument: ',
            React.createElement(Link, {
              to: '/documents/' + docId,
              'data-testid': 'import-document-link',
            },
              React.createElement('span', { 'data-testid': 'import-document-id' }, docId)
            )
          )
        : null,
      chunks != null
        ? React.createElement('p', { 'data-testid': 'import-chunks' }, 'Chunks: ' + chunks)
        : null
    );
  }

  if (phase === 'error' && error) {
    return React.createElement('div', { className: 'panel', 'data-testid': 'import-error' },
      React.createElement('p', { className: 'panel__eyebrow' }, 'Fehler'),
      React.createElement('p', { className: 'error-text' },
        error.message || 'Import fehlgeschlagen'
      ),
      error.code
        ? React.createElement('p', { 'data-testid': 'import-error-code' }, 'Code: ' + error.code)
        : null
    );
  }

  return null;
}

function HistoryRow(props) {
  var entry = props.entry;
  return React.createElement('tr', { 'data-testid': 'history-row' },
    React.createElement('td', null, entry.fileName),
    React.createElement('td', null, entry.status === 'success' ? 'Erfolg' : 'Fehler'),
    React.createElement('td', null, entry.label || ''),
    entry.documentId
      ? React.createElement('td', null,
          React.createElement(Link, {
            to: '/documents/' + entry.documentId,
            'data-testid': 'history-doc-link',
          }, entry.documentId)
        )
      : React.createElement('td', null, '—')
  );
}

export function ImportCenterPage() {
  var imported = useImport();
  var current = imported.current;
  var history = imported.history;
  var handleUpload = imported.handleUpload;
  var handleReset = imported.handleReset;
  var isLoading = imported.isLoading;

  var formRef = useRef(null);
  var fileInputRef = useRef(null);

  function handleSubmit(event) {
    event.preventDefault();
    var file = fileInputRef.current && fileInputRef.current.files && fileInputRef.current.files[0]
      ? fileInputRef.current.files[0]
      : null;
    handleUpload(file);
  }

  function handleResetClick() {
    if (formRef.current) formRef.current.reset();
    handleReset();
  }

  var showStatus = current.phase !== 'idle';
  var showHistory = history.length > 0;
  var successCount = history.filter(function(h) { return h.status === 'success'; }).length;
  var subtitle = successCount === 0
    ? 'Dokumente importieren und verarbeiten lassen'
    : successCount === 1
      ? '1 Dokument importiert'
      : successCount + ' Dokumente importiert';

  return React.createElement('section', {
    className: 'page-stack',
    'data-testid': 'import-center-page',
  },

    React.createElement('div', { className: 'page-header' },
      React.createElement('div', null,
        React.createElement('p', { className: 'panel__eyebrow' }, 'Import'),
        React.createElement('h2', null, 'Importcenter')
      ),
      React.createElement('p', { className: 'page-header__meta', 'data-testid': 'import-subtitle' }, subtitle)
    ),

    React.createElement('section', { className: 'panel', 'data-testid': 'upload-panel' },
      React.createElement('div', { className: 'panel__header' },
        React.createElement('div', null,
          React.createElement('p', { className: 'panel__eyebrow' }, 'Schritt 1'),
          React.createElement('h3', null, 'Datei auswählen')
        )
      ),
      React.createElement('form', {
        ref: formRef,
        className: 'search-bar',
        'data-testid': 'upload-form',
        onSubmit: handleSubmit,
      },
        React.createElement('label', { className: 'search-bar__field' },
          React.createElement('span', { className: 'search-bar__label' },
            'Datei (PDF, DOCX, TXT, MD)'
          ),
          React.createElement('input', {
            ref: fileInputRef,
            type: 'file',
            name: 'file',
            accept: ACCEPTED,
            'data-testid': 'file-input',
            disabled: isLoading,
          })
        ),
        React.createElement('div', { className: 'search-bar__actions' },
          React.createElement('button', {
            type: 'submit',
            'data-testid': 'upload-submit',
            disabled: isLoading,
          }, isLoading ? 'Import läuft …' : 'Importieren'),
          showStatus
            ? React.createElement('button', {
                type: 'button',
                className: 'button-secondary',
                'data-testid': 'reset-button',
                onClick: handleResetClick,
                disabled: isLoading,
              }, 'Zurücksetzen')
            : null
        )
      )
    ),

    showStatus ? React.createElement(StepIndicator, { phase: current.phase }) : null,
    showStatus ? React.createElement(PhaseStatus, { current: current }) : null,

    showHistory
      ? React.createElement('section', {
          className: 'panel',
          'data-testid': 'import-history',
        },
          React.createElement('div', { className: 'panel__header' },
            React.createElement('div', null,
              React.createElement('p', { className: 'panel__eyebrow' }, 'Sitzungsverlauf'),
              React.createElement('h3', null,
                React.createElement('span', { 'data-testid': 'history-count' }, String(history.length)),
                ' Import',
                history.length !== 1 ? 'e' : ''
              )
            )
          ),
          React.createElement('table', { className: 'document-table' },
            React.createElement('thead', null,
              React.createElement('tr', null,
                React.createElement('th', null, 'Datei'),
                React.createElement('th', null, 'Status'),
                React.createElement('th', null, 'Ergebnis'),
                React.createElement('th', null, 'Dokument-ID')
              )
            ),
            React.createElement('tbody', null,
              history.map(function(entry, i) {
                return React.createElement(HistoryRow, { key: entry.uid || String(i), entry: entry });
              })
            )
          )
        )
      : null
  );
}
