import { useDataQuality } from './useDataQuality.js';
import { LoadingState } from '../../components/status/LoadingState.jsx';
import { ErrorState } from '../../components/status/ErrorState.jsx';
import { mapError } from '../../view-models/mappers.js';

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const SEVERITY_TONE = { error: 'danger', warning: 'warning', info: 'info' };
const SEVERITY_LABEL = { error: 'Fehler', warning: 'Warnung', info: 'Info' };

function severityTone(s) {
  return SEVERITY_TONE[s] || 'neutral';
}

function severityLabel(s) {
  return SEVERITY_LABEL[s] || s;
}

function scoreLabel(score) {
  if (score == null) return '—';
  if (score >= 90) return 'Exzellent';
  if (score >= 75) return 'Gut';
  if (score >= 50) return 'Mäßig';
  return 'Kritisch';
}

function scoreTone(score) {
  if (score == null) return 'neutral';
  if (score >= 90) return 'success';
  if (score >= 75) return 'warning';
  return 'danger';
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('de-DE', {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function RunSummaryCard({ summary, latestRun }) {
  const score = summary?.latest_quality_score;
  const tone = scoreTone(score);
  return (
    <article className="diagnostics-card" data-testid="dq-run-summary-card">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Letzter Run</p>
          <h3 data-testid="dq-run-id">
            {summary?.latest_run_id ?? '—'}
          </h3>
        </div>
        <span
          className={`status-badge status-badge--${tone}`}
          data-testid="dq-quality-score-badge"
        >
          {score != null ? `${score.toFixed(1)} — ${scoreLabel(score)}` : '—'}
        </span>
      </div>
      <dl className="meta-grid">
        <div>
          <dt>Status</dt>
          <dd data-testid="dq-run-status">{summary?.latest_run_status ?? '—'}</dd>
        </div>
        <div>
          <dt>Gestartet</dt>
          <dd data-testid="dq-run-started-at">{formatDate(summary?.latest_run_at)}</dd>
        </div>
        <div>
          <dt>Findings gesamt</dt>
          <dd data-testid="dq-total-findings">{summary?.total_findings ?? 0}</dd>
        </div>
        <div>
          <dt>Runs gesamt</dt>
          <dd data-testid="dq-total-runs">{summary?.total_runs ?? 0}</dd>
        </div>
      </dl>
    </article>
  );
}

function SeverityBreakdown({ findingsBySeverity = {} }) {
  const entries = Object.entries(findingsBySeverity).sort((a, b) => {
    const order = ['error', 'warning', 'info'];
    return order.indexOf(a[0]) - order.indexOf(b[0]);
  });

  if (entries.length === 0) {
    return (
      <article className="diagnostics-card" data-testid="dq-severity-breakdown">
        <div className="panel__header">
          <p className="panel__eyebrow">Nach Schweregrad</p>
        </div>
        <p data-testid="dq-severity-empty">Keine Findings.</p>
      </article>
    );
  }

  return (
    <article className="diagnostics-card" data-testid="dq-severity-breakdown">
      <div className="panel__header">
        <p className="panel__eyebrow">Nach Schweregrad</p>
      </div>
      <dl className="meta-grid">
        {entries.map(([sev, count]) => (
          <div key={sev}>
            <dt>
              <span
                className={`status-badge status-badge--${severityTone(sev)}`}
                data-testid={`dq-severity-label-${sev}`}
              >
                {severityLabel(sev)}
              </span>
            </dt>
            <dd data-testid={`dq-severity-count-${sev}`}>{count}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function TypeBreakdown({ findingsByType = {} }) {
  const entries = Object.entries(findingsByType).sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) {
    return (
      <article className="diagnostics-card" data-testid="dq-type-breakdown">
        <div className="panel__header">
          <p className="panel__eyebrow">Nach Typ</p>
        </div>
        <p data-testid="dq-type-empty">Keine Findings.</p>
      </article>
    );
  }

  return (
    <article className="diagnostics-card" data-testid="dq-type-breakdown">
      <div className="panel__header">
        <p className="panel__eyebrow">Nach Typ</p>
      </div>
      <dl className="meta-grid">
        {entries.map(([type, count]) => (
          <div key={type}>
            <dt data-testid={`dq-type-label-${type}`}>{type}</dt>
            <dd data-testid={`dq-type-count-${type}`}>{count}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function FindingsFilters({ filters, onFilterChange }) {
  return (
    <div className="search-bar" data-testid="dq-findings-filters">
      <label htmlFor="dq-filter-severity">Schweregrad</label>
      <select
        id="dq-filter-severity"
        value={filters.severity ?? ''}
        onChange={(e) => onFilterChange('severity', e.target.value)}
        data-testid="dq-filter-severity"
      >
        <option value="">Alle</option>
        <option value="error">Fehler</option>
        <option value="warning">Warnung</option>
        <option value="info">Info</option>
      </select>

      <label htmlFor="dq-filter-type">Typ</label>
      <select
        id="dq-filter-type"
        value={filters.findingType ?? ''}
        onChange={(e) => onFilterChange('findingType', e.target.value)}
        data-testid="dq-filter-finding-type"
      >
        <option value="">Alle</option>
        <option value="DUPLICATE_DOCUMENT">Duplikat</option>
        <option value="ORPHAN_CHUNK">Orphan Chunk</option>
        <option value="INVALID_LIFECYCLE">Ungültiger Lifecycle</option>
        <option value="MISSING_METADATA">Fehlende Metadaten</option>
        <option value="EMPTY_CHUNK">Leerer Chunk</option>
        <option value="EMPTY_DOCUMENT">Leeres Dokument</option>
        <option value="RETRIEVAL_RISK">Retrieval-Risiko</option>
        <option value="ORPHAN_VERSION">Orphan Version</option>
        <option value="DUPLICATE_CONTENT">Duplikat Inhalt</option>
        <option value="INVALID_SOURCE_STATUS">Ungültiger Source-Status</option>
      </select>
    </div>
  );
}

function FindingsTable({ findings, total, offset, pageSize, onPageChange }) {
  if (!findings) {
    return <LoadingState label="Lade Findings..." testId="dq-findings-loading" />;
  }

  if (findings.length === 0) {
    return (
      <p data-testid="dq-findings-empty">
        Keine Findings gefunden.
      </p>
    );
  }

  const currentPage = Math.floor(offset / pageSize) + 1;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <section data-testid="dq-findings-table-section">
      <p data-testid="dq-findings-count" className="panel__eyebrow">
        {total} Finding{total !== 1 ? 's' : ''}
      </p>
      <table data-testid="dq-findings-table">
        <thead>
          <tr>
            <th>Schweregrad</th>
            <th>Typ</th>
            <th>Titel</th>
            <th>Dokument</th>
            <th>Maßnahme</th>
          </tr>
        </thead>
        <tbody>
          {findings.map((f) => (
            <tr key={f.finding_id} data-testid="dq-finding-row">
              <td>
                <span
                  className={`status-badge status-badge--${severityTone(f.severity)}`}
                  data-testid="dq-finding-severity"
                >
                  {severityLabel(f.severity)}
                </span>
              </td>
              <td data-testid="dq-finding-type">{f.finding_type}</td>
              <td data-testid="dq-finding-title">{f.title}</td>
              <td data-testid="dq-finding-document-id">
                {f.document_id ?? '—'}
              </td>
              <td data-testid="dq-finding-remediation">{f.remediation}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {totalPages > 1 && (
        <nav data-testid="dq-findings-pagination">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => onPageChange(Math.max(0, offset - pageSize))}
            data-testid="dq-findings-prev"
          >
            Zurück
          </button>
          <span data-testid="dq-findings-page-info">
            Seite {currentPage} von {totalPages}
          </span>
          <button
            type="button"
            disabled={offset + pageSize >= total}
            onClick={() => onPageChange(offset + pageSize)}
            data-testid="dq-findings-next"
          >
            Weiter
          </button>
        </nav>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export function DataQualityDashboard() {
  const {
    summary,
    latestRun,
    findings,
    findingsTotal,
    findingsOffset,
    filters,
    loading,
    error,
    setFilter,
    setOffset,
    pageSize,
  } = useDataQuality();

  if (loading && !summary) {
    return <LoadingState label="Data Quality wird geladen..." testId="dq-loading" />;
  }

  if (error) {
    return (
      <ErrorState
        error={mapError(error)}
        testId="dq-error"
      />
    );
  }

  return (
    <div data-testid="dq-dashboard">
      <h1>Data Quality</h1>

      <RunSummaryCard summary={summary} latestRun={latestRun} />

      <div className="diagnostics-grid">
        <SeverityBreakdown findingsBySeverity={summary?.findings_by_severity ?? {}} />
        <TypeBreakdown findingsByType={summary?.findings_by_type ?? {}} />
      </div>

      <section data-testid="dq-findings-section">
        <h2>Findings</h2>
        <FindingsFilters filters={filters} onFilterChange={setFilter} />
        <FindingsTable
          findings={findings}
          total={findingsTotal}
          offset={findingsOffset}
          pageSize={pageSize}
          onPageChange={setOffset}
        />
      </section>
    </div>
  );
}
