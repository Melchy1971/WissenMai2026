import { useDataQuality } from './useDataQuality.js';
import { LoadingState } from '../../components/status/LoadingState.jsx';
import { ErrorState } from '../../components/status/ErrorState.jsx';
import { mapError } from '../../view-models/mappers.js';

// ---------------------------------------------------------------------------
// Severity helpers
// ---------------------------------------------------------------------------

const SEVERITY_TONE = { error: 'danger', warning: 'warning', info: 'info' };
const SEVERITY_LABEL = { error: 'Fehler', warning: 'Warnung', info: 'Info' };
const SCORE_CATEGORY_WEIGHTS = {
  duplicate: 25,
  metadata: 15,
  lifecycle: 25,
  source_status: 20,
  orphan: 15,
};
const SCORE_CATEGORY_LABELS = {
  duplicate: 'Duplicate',
  metadata: 'Metadata',
  lifecycle: 'Lifecycle',
  source_status: 'Source Status',
  orphan: 'Orphan Objects',
};
const FINDING_TYPE_CATEGORY = {
  DUPLICATE_DOCUMENT: 'duplicate',
  DUPLICATE_CONTENT: 'duplicate',
  MISSING_METADATA: 'metadata',
  EMPTY_DOCUMENT: 'metadata',
  EMPTY_CHUNK: 'metadata',
  INVALID_LIFECYCLE: 'lifecycle',
  RETRIEVAL_RISK: 'lifecycle',
  INVALID_SOURCE_STATUS: 'source_status',
  ORPHAN_CHUNK: 'orphan',
  ORPHAN_VERSION: 'orphan',
  ORPHAN_CITATION: 'orphan',
  ORPHAN_FINDING: 'orphan',
};
const LIFECYCLE_TYPES = ['INVALID_LIFECYCLE', 'RETRIEVAL_RISK'];
const SOURCE_STATUS_TYPES = ['INVALID_SOURCE_STATUS'];
const ORPHAN_TYPES = ['ORPHAN_CHUNK', 'ORPHAN_VERSION', 'ORPHAN_CITATION', 'ORPHAN_FINDING'];

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

function countTypes(findingsByType = {}, types = []) {
  return types.reduce((total, type) => total + (Number(findingsByType[type]) || 0), 0);
}

function scoreBreakdown(findingsByType = {}) {
  const counts = Object.fromEntries(
    Object.keys(SCORE_CATEGORY_WEIGHTS).map((category) => [category, 0]),
  );

  Object.entries(findingsByType).forEach(([type, count]) => {
    const category = FINDING_TYPE_CATEGORY[type];
    if (category) {
      counts[category] += Number(count) || 0;
    }
  });

  return Object.entries(SCORE_CATEGORY_WEIGHTS).map(([category, weight]) => {
    const count = counts[category];
    return {
      category,
      label: SCORE_CATEGORY_LABELS[category],
      count,
      weight,
      penalty: Number(((weight * Math.min(count, 10)) / 10).toFixed(1)),
    };
  });
}

function RunSummaryCard({ summary }) {
  const score = summary?.latest_quality_score;
  const tone = scoreTone(score);
  return (
    <article className="diagnostics-card" data-testid="dq-run-summary-card">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Letzter Run</p>
          <h3 data-testid="dq-run-status">
            {summary?.latest_run_status ?? '—'}
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

function FindingCategoryCard({ testId, title, findingsByType, types }) {
  const total = countTypes(findingsByType, types);
  return (
    <article className="diagnostics-card" data-testid={testId}>
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">{title}</p>
          <h3 data-testid={`${testId}-total`}>{total}</h3>
        </div>
      </div>
      <dl className="meta-grid">
        {types.map((type) => (
          <div key={type}>
            <dt data-testid={`${testId}-label-${type}`}>{type}</dt>
            <dd data-testid={`${testId}-count-${type}`}>{findingsByType[type] ?? 0}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function QualityScoreBreakdown({ findingsByType = {} }) {
  const rows = scoreBreakdown(findingsByType);
  const totalPenalty = rows.reduce((sum, row) => sum + row.penalty, 0);
  return (
    <article className="diagnostics-card" data-testid="dq-score-breakdown">
      <div className="panel__header">
        <div>
          <p className="panel__eyebrow">Quality Score Breakdown</p>
          <h3 data-testid="dq-score-breakdown-penalty">{totalPenalty.toFixed(1)} Punkte Abzug</h3>
        </div>
      </div>
      <dl className="meta-grid">
        {rows.map((row) => (
          <div key={row.category} data-testid={`dq-score-breakdown-${row.category}`}>
            <dt>{row.label}</dt>
            <dd>
              <span data-testid={`dq-score-breakdown-count-${row.category}`}>{row.count}</span>
              {' / '}
              <span data-testid={`dq-score-breakdown-weight-${row.category}`}>{row.weight}%</span>
            </dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

function RunsTrend({ runs = [] }) {
  if (runs.length === 0) {
    return (
      <article className="diagnostics-card" data-testid="dq-runs-trend">
        <div className="panel__header">
          <p className="panel__eyebrow">Trend letzte Runs</p>
        </div>
        <p data-testid="dq-runs-trend-empty">Keine Runs.</p>
      </article>
    );
  }

  return (
    <article className="diagnostics-card" data-testid="dq-runs-trend">
      <div className="panel__header">
        <p className="panel__eyebrow">Trend letzte Runs</p>
      </div>
      <dl className="meta-grid">
        {runs.map((run, index) => (
          <div key={run.run_id} data-testid="dq-runs-trend-item">
            <dt data-testid={`dq-runs-trend-date-${index}`}>{formatDate(run.started_at)}</dt>
            <dd data-testid={`dq-runs-trend-score-${index}`}>
              {run.quality_score != null ? run.quality_score.toFixed(1) : '-'}
            </dd>
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
        <option value="ORPHAN_CITATION">Orphan Citation</option>
        <option value="ORPHAN_FINDING">Orphan Finding</option>
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
    recentRuns,
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

      <RunSummaryCard summary={summary} />

      <div className="diagnostics-grid">
        <SeverityBreakdown findingsBySeverity={summary?.findings_by_severity ?? {}} />
        <TypeBreakdown findingsByType={summary?.findings_by_type ?? {}} />
      </div>

      <div className="diagnostics-grid" data-testid="dq-specialized-widgets">
        <FindingCategoryCard
          testId="dq-lifecycle-findings"
          title="Lifecycle Findings"
          findingsByType={summary?.findings_by_type ?? {}}
          types={LIFECYCLE_TYPES}
        />
        <FindingCategoryCard
          testId="dq-source-status-findings"
          title="Source Status Findings"
          findingsByType={summary?.findings_by_type ?? {}}
          types={SOURCE_STATUS_TYPES}
        />
        <FindingCategoryCard
          testId="dq-orphan-findings"
          title="Orphan Findings"
          findingsByType={summary?.findings_by_type ?? {}}
          types={ORPHAN_TYPES}
        />
        <QualityScoreBreakdown findingsByType={summary?.findings_by_type ?? {}} />
        <RunsTrend runs={recentRuns} />
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
