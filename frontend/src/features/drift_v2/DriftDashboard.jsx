import { useEffect, useMemo, useState } from 'react';

import { getDriftSummary, listDriftFindings } from './driftApi.js';
import { ErrorState } from '../../components/status/ErrorState.jsx';
import { LoadingState } from '../../components/status/LoadingState.jsx';
import { mapError } from '../../view-models/mappers.js';

const SEVERITIES = ['critical', 'error', 'warning', 'info'];
const FINDING_TYPES = [
  'DOCUMENT_DRIFT',
  'METADATA_DRIFT',
  'LIFECYCLE_DRIFT',
  'SOURCE_STATUS_DRIFT',
];

function formatDate(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('de-DE', {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

function normalizeError(error) {
  if (!error) return null;
  if (typeof error === 'string') {
    return { code: 'DRIFT_ERROR', message: error, details: {}, status: null };
  }
  return error;
}

function useApiDriftData(filters) {
  const [state, setState] = useState({
    summary: null,
    findings: [],
    loading: true,
    error: null,
  });

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setState((current) => ({ ...current, loading: true, error: null }));
      try {
        const [summary, findingsResponse] = await Promise.all([
          getDriftSummary({ signal: controller.signal }),
          listDriftFindings(filters, { signal: controller.signal }),
        ]);
        setState({
          summary,
          findings: findingsResponse?.items ?? [],
          loading: false,
          error: null,
        });
      } catch (error) {
        if (error?.name === 'AbortError') return;
        setState({
          summary: null,
          findings: [],
          loading: false,
          error,
        });
      }
    }

    load();
    return () => controller.abort();
  }, [filters.severityFilter, filters.typeFilter]);

  return state;
}

function LastRunWidget({ summary }) {
  const hasRun = Boolean(summary?.latest_run_id);

  return (
    <article className="diagnostics-card" data-testid="drift-last-run-widget">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Letzter Drift Run</p>
          {hasRun ? (
            <h3 data-testid="drift-last-run-id">{summary.latest_run_id}</h3>
          ) : (
            <h3 data-testid="drift-no-run-message">Kein Drift Run vorhanden.</h3>
          )}
        </div>
        <span className="status-badge status-badge--neutral">
          {summary?.latest_run_status ?? '-'}
        </span>
      </div>
      <dl className="meta-grid">
        <div>
          <dt>Abgeschlossen</dt>
          <dd>{formatDate(summary?.latest_run_completed_at)}</dd>
        </div>
        <div>
          <dt>Runs</dt>
          <dd>{summary?.total_runs ?? 0}</dd>
        </div>
        <div>
          <dt>Findings</dt>
          <dd>{summary?.total_findings ?? 0}</dd>
        </div>
      </dl>
    </article>
  );
}

function SeverityBreakdown({ findingsBySeverity = {} }) {
  return (
    <article className="diagnostics-card" data-testid="drift-severity-breakdown-widget">
      <div className="panel__header">
        <p className="panel__eyebrow">Severity</p>
      </div>
      <dl className="meta-grid">
        {SEVERITIES.map((severity) => (
          <div key={severity} data-testid={`drift-severity-${severity}`}>
            <dt>{severity}</dt>
            <dd>{findingsBySeverity[severity] ?? 0}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function TypeBreakdown({ findingsByType = {} }) {
  return (
    <article className="diagnostics-card" data-testid="drift-type-breakdown-widget">
      <div className="panel__header">
        <p className="panel__eyebrow">Typen</p>
      </div>
      <dl className="meta-grid">
        {FINDING_TYPES.map((type) => (
          <div key={type} data-testid={`drift-type-${type}`}>
            <dt>{type}</dt>
            <dd>{findingsByType[type] ?? 0}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function DriftFilters({ severityFilter, typeFilter, onSeverityChange, onTypeChange }) {
  return (
    <div className="search-bar">
      <label htmlFor="drift-filter-severity">Severity</label>
      <select
        id="drift-filter-severity"
        value={severityFilter}
        onChange={(event) => onSeverityChange(event.target.value)}
        data-testid="drift-filter-severity"
      >
        <option value="">Alle</option>
        {SEVERITIES.map((severity) => (
          <option key={severity} value={severity}>{severity}</option>
        ))}
      </select>

      <label htmlFor="drift-filter-type">Typ</label>
      <select
        id="drift-filter-type"
        value={typeFilter}
        onChange={(event) => onTypeChange(event.target.value)}
        data-testid="drift-filter-type"
      >
        <option value="">Alle</option>
        {FINDING_TYPES.map((type) => (
          <option key={type} value={type}>{type}</option>
        ))}
      </select>
    </div>
  );
}

function FindingsTable({ findings = [] }) {
  if (findings.length === 0) {
    return <p data-testid="drift-no-findings-message">Keine Drift Findings vorhanden.</p>;
  }

  return (
    <table data-testid="drift-findings-table">
      <thead>
        <tr>
          <th>Severity</th>
          <th>Typ</th>
          <th>Entity</th>
          <th>Erstellt</th>
        </tr>
      </thead>
      <tbody>
        {findings.map((finding) => (
          <tr key={finding.finding_id} data-testid="drift-finding-row">
            <td>{finding.severity}</td>
            <td>{finding.finding_type}</td>
            <td>{finding.entity_id ?? '-'}</td>
            <td>{formatDate(finding.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function DriftDashboard({ useDriftData = useApiDriftData }) {
  const [severityFilter, setSeverityFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const query = useMemo(
    () => ({
      severityFilter: severityFilter || null,
      typeFilter: typeFilter || null,
    }),
    [severityFilter, typeFilter],
  );
  const { summary, findings = [], loading = false, error = null } = useDriftData(query);
  const normalizedError = normalizeError(error);

  if (loading && !summary) {
    return <LoadingState label="Drift wird geladen..." testId="drift-loading" />;
  }

  if (normalizedError) {
    const mappedError = mapError(normalizedError);
    return (
      <section data-testid="drift-dashboard">
        <section role="alert" data-testid="drift-api-error">
          <p>{normalizedError.message || mappedError.message}</p>
          <ErrorState error={mappedError} />
        </section>
      </section>
    );
  }

  return (
    <div data-testid="drift-dashboard">
      <h1>Drift</h1>
      <LastRunWidget summary={summary} />

      <div className="diagnostics-grid">
        <SeverityBreakdown findingsBySeverity={summary?.findings_by_severity ?? {}} />
        <TypeBreakdown findingsByType={summary?.findings_by_type ?? {}} />
      </div>

      <section>
        <h2>Findings</h2>
        <DriftFilters
          severityFilter={severityFilter}
          typeFilter={typeFilter}
          onSeverityChange={setSeverityFilter}
          onTypeChange={setTypeFilter}
        />
        <FindingsTable findings={findings} />
      </section>
    </div>
  );
}
