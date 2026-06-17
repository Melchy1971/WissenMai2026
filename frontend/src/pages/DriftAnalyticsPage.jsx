/**
 * DriftAnalyticsPage — Detailansicht für einen Snapshot-Typ.
 *
 * URL: /drift-analytics/:snapshotType
 *
 * 4 Sektionen:
 *   1. Übersicht (Status, Score, letzte Aktualisierung)
 *   2. Metriken-Tabelle (aus aktuellstem Snapshot)
 *   3. Payload (collapsible JSON-Viewer)
 *   4. Score-Verlauf (letzte 10 Snapshots)
 */
import { useEffect, useReducer, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  getDriftOverview,
  getDriftSnapshots,
  getDriftSnapshotMetrics,
} from '../api/drift_analytics.js';

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_META = {
  PASS:    { color: '#2e7d32', bg: '#f1f8f1', border: '#66bb6a', icon: '✓' },
  WARNING: { color: '#e65100', bg: '#fff8f1', border: '#ffb74d', icon: '⚠' },
  FAIL:    { color: '#c62828', bg: '#fff5f5', border: '#ef5350', icon: '✗' },
  BLOCKED: { color: '#6a1a6a', bg: '#fdf0fd', border: '#ab47bc', icon: '⊘' },
  UNKNOWN: { color: '#78909c', bg: '#f5f7f8', border: '#90a4ae', icon: '?' },
};

const LABEL_MAP = {
  PRODUCT_MATURITY: 'Produktreife',
  GOLD_PATH:        'Gold Path',
  RELEASE_GATE:     'Release Gate',
  TEST_COVERAGE:    'Test Coverage',
  ID_LEAK_AUDIT:    'Technische ID Prüfung',
  SECURITY_AUDIT:   'Sicherheitsaudit',
};

function statusMeta(status) {
  return STATUS_META[status] || STATUS_META.UNKNOWN;
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

// ── Data reducer ──────────────────────────────────────────────────────────────

const INIT = { phase: 'idle', overview: null, snapshots: null, metrics: null, error: null };

function reducer(state, action) {
  switch (action.type) {
    case 'LOAD':     return { ...INIT, phase: 'loading' };
    case 'OK':       return { ...state, phase: 'success', ...action.payload };
    case 'ERR':      return { ...state, phase: 'error', error: action.error };
    case 'METRICS':  return { ...state, metrics: action.metrics };
    default:         return state;
  }
}

// ── Overview card ─────────────────────────────────────────────────────────────

function OverviewCard({ widget, snapshotType }) {
  const status = widget?.status ?? 'UNKNOWN';
  const meta = statusMeta(status);
  const label = LABEL_MAP[snapshotType] || snapshotType;

  return (
    <div
      className="dap-overview-card"
      style={{ borderColor: meta.border, background: meta.bg }}
    >
      <div className="dap-overview-card__left">
        <div
          className="dap-overview-card__icon"
          style={{ color: meta.color }}
          aria-hidden="true"
        >
          {meta.icon}
        </div>
        <div>
          <div className="dap-overview-card__type">{label}</div>
          <div
            className="dap-overview-card__status"
            style={{ color: meta.color }}
          >
            {status}
          </div>
        </div>
      </div>
      <div className="dap-overview-card__right">
        {widget?.score != null && (
          <div className="dap-overview-card__score" style={{ color: meta.color }}>
            {widget.score.toFixed(1)}
            <span className="dap-overview-card__score-unit"> / 100</span>
          </div>
        )}
        <div className="dap-overview-card__date">
          {widget?.last_updated ? `Stand: ${fmtDate(widget.last_updated)}` : 'Keine Daten'}
        </div>
      </div>
    </div>
  );
}

// ── Metrics table ─────────────────────────────────────────────────────────────

function MetricStatusChip({ status }) {
  const meta = statusMeta(status);
  return (
    <span
      className="dap-metric-chip"
      style={{ background: meta.color, color: '#fff' }}
    >
      {status}
    </span>
  );
}

function MetricsTable({ metrics }) {
  if (!metrics || metrics.length === 0) {
    return (
      <div className="dap-empty">Keine Metriken für diesen Snapshot vorhanden.</div>
    );
  }

  return (
    <div className="dap-table-wrapper" role="region" aria-label="Metriken">
      <table className="dap-table">
        <thead>
          <tr>
            <th>Metrik</th>
            <th>Wert</th>
            <th>Einheit</th>
            <th>Grenzwert W</th>
            <th>Grenzwert F</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.metric_key}>
              <td>
                <span className="dap-metric-label">{m.metric_label}</span>
              </td>
              <td>
                <code className="dap-code">{m.metric_value}</code>
              </td>
              <td>{m.metric_unit || '—'}</td>
              <td>{m.threshold_warning != null ? m.threshold_warning : '—'}</td>
              <td>{m.threshold_fail != null ? m.threshold_fail : '—'}</td>
              <td>
                <MetricStatusChip status={m.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Payload viewer (collapsible) ──────────────────────────────────────────────

function PayloadViewer({ payload }) {
  const [open, setOpen] = useState(false);

  if (payload == null) {
    return <div className="dap-empty">Kein Payload vorhanden.</div>;
  }

  const json = typeof payload === 'string'
    ? payload
    : JSON.stringify(payload, null, 2);

  return (
    <div className="dap-payload">
      <button
        type="button"
        className="dap-payload__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="dap-payload__arrow">{open ? '▾' : '▸'}</span>
        {open ? 'Payload verbergen' : 'Payload anzeigen'}
        <span className="dap-payload__size">
          ({json.length.toLocaleString('de-DE')} Zeichen)
        </span>
      </button>
      {open && (
        <pre className="dap-payload__code">
          <code>{json}</code>
        </pre>
      )}
    </div>
  );
}

// ── Score history / trend ─────────────────────────────────────────────────────

function HistoryTrendChart({ items }) {
  if (!items || items.length === 0) return null;

  // Only items with a score
  const scored = items.filter((s) => s.score != null).slice(0, 20).reverse();
  if (scored.length < 2) return null;

  const W = 400, H = 80, PAD = 10;
  const scores = scored.map((s) => s.score);
  const min = Math.min(...scores);
  const max = Math.max(...scores, min + 1);
  const n = scored.length;
  const stepX = (W - PAD * 2) / Math.max(n - 1, 1);

  const pts = scores.map((v, i) => [
    PAD + i * stepX,
    H - PAD - ((v - min) / (max - min + 0.001)) * (H - PAD * 2),
  ]);
  const polyline = pts.map((p) => `${p[0]},${p[1]}`).join(' ');
  const area =
    `M ${pts[0][0]} ${H - PAD} ` +
    pts.map((p) => `L ${p[0]} ${p[1]}`).join(' ') +
    ` L ${pts[pts.length - 1][0]} ${H - PAD} Z`;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      style={{ display: 'block', overflow: 'visible' }}
      role="img"
      aria-label="Score-Verlauf"
    >
      <path d={area} fill="rgba(226,0,116,0.08)" />
      <polyline
        points={polyline}
        fill="none"
        stroke="var(--t-magenta, #E20074)"
        strokeWidth="2"
        strokeLinejoin="round"
      />
      {pts.map((p, i) => (
        <circle
          key={i}
          cx={p[0]}
          cy={p[1]}
          r={3}
          fill="var(--t-magenta, #E20074)"
        >
          <title>{`${scored[i].score?.toFixed(1)} — ${fmtDate(scored[i].created_at)}`}</title>
        </circle>
      ))}
    </svg>
  );
}

function HistoryList({ items, onSelectMetrics, selectedId }) {
  if (!items || items.length === 0) {
    return <div className="dap-empty">Kein Verlauf vorhanden.</div>;
  }

  return (
    <div className="dap-history-list">
      {items.map((snap) => {
        const meta = statusMeta(snap.status);
        const isSelected = snap.id === selectedId;
        return (
          <button
            key={snap.id}
            type="button"
            className={`dap-history-item ${isSelected ? 'dap-history-item--active' : ''}`}
            style={isSelected ? { borderColor: meta.border, background: meta.bg } : {}}
            onClick={() => onSelectMetrics(snap)}
          >
            <span
              className="dap-history-item__badge"
              style={{ background: meta.color, color: '#fff' }}
            >
              {snap.status}
            </span>
            {snap.score != null && (
              <span className="dap-history-item__score">{snap.score.toFixed(1)}</span>
            )}
            <span className="dap-history-item__date">{fmtDate(snap.created_at)}</span>
            {snap.created_by && (
              <span className="dap-history-item__by">{snap.created_by}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, children }) {
  return (
    <section className="dap-section">
      <h2 className="dap-section__title">{title}</h2>
      {children}
    </section>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function DriftAnalyticsPage() {
  const { snapshotType } = useParams();
  const navigate = useNavigate();
  const [state, dispatch] = useReducer(reducer, INIT);
  const [selectedSnap, setSelectedSnap] = useState(null);

  useEffect(() => {
    if (!snapshotType) return;
    const ctrl = new AbortController();
    dispatch({ type: 'LOAD' });

    Promise.all([
      getDriftOverview({ signal: ctrl.signal }),
      getDriftSnapshots({ type: snapshotType, page: 1, pageSize: 20 }, { signal: ctrl.signal }),
    ])
      .then(([overview, snapPage]) => {
        dispatch({ type: 'OK', payload: { overview, snapshots: snapPage } });
        // Auto-load metrics for the latest snapshot
        const items = snapPage?.items || [];
        if (items.length > 0) {
          loadMetrics(items[0], ctrl.signal);
        }
      })
      .catch((err) => {
        if (err?.name !== 'AbortError') dispatch({ type: 'ERR', error: err });
      });

    return () => ctrl.abort();
  }, [snapshotType]);

  function loadMetrics(snap, signal) {
    setSelectedSnap(snap);
    dispatch({ type: 'METRICS', metrics: null }); // clear while loading
    getDriftSnapshotMetrics(snap.id, signal ? { signal } : {})
      .then((data) => dispatch({ type: 'METRICS', metrics: data.metrics || [] }))
      .catch((err) => {
        if (err?.name !== 'AbortError') {
          dispatch({ type: 'METRICS', metrics: [] });
        }
      });
  }

  const widget = state.overview
    ? state.overview[snapshotType?.toLowerCase().replace(/_/g, '_')]
    : null;

  // Map overview by snake_case key derived from snapshot_type
  const typeToKey = {
    PRODUCT_MATURITY: 'product_maturity',
    GOLD_PATH: 'gold_path',
    RELEASE_GATE: 'release_gate',
    TEST_COVERAGE: 'test_coverage',
    ID_LEAK_AUDIT: 'id_leak_audit',
    SECURITY_AUDIT: 'security_audit',
  };
  const overviewWidget = state.overview?.[typeToKey[snapshotType]];
  const snapItems = state.snapshots?.items || [];

  return (
    <div className="dap-page" data-testid="drift-analytics-page">
      <header className="dap-header">
        <button
          type="button"
          className="dap-back-btn"
          onClick={() => navigate('/dashboard')}
          aria-label="Zurück zum Dashboard"
        >
          ← Dashboard
        </button>
        <h1 className="dap-page-title">
          {LABEL_MAP[snapshotType] || snapshotType || 'Drift Analytics'}
        </h1>
      </header>

      {state.phase === 'loading' || state.phase === 'idle' ? (
        <div className="dap-loading">Wird geladen…</div>
      ) : state.phase === 'error' ? (
        <div className="dap-error" role="alert">
          Fehler beim Laden: {state.error?.message || 'Unbekannter Fehler'}
        </div>
      ) : (
        <>
          {/* 1. Übersicht */}
          <Section title="Übersicht">
            <OverviewCard widget={overviewWidget} snapshotType={snapshotType} />
          </Section>

          {/* 2. Metriken */}
          <Section title="Metriken">
            {selectedSnap && (
              <p className="dap-section__sub">
                Snapshot vom {fmtDate(selectedSnap.created_at)}
                {selectedSnap.created_by && ` · ${selectedSnap.created_by}`}
              </p>
            )}
            {state.metrics === null ? (
              <div className="dap-loading">Metriken werden geladen…</div>
            ) : (
              <MetricsTable metrics={state.metrics} />
            )}
          </Section>

          {/* 3. Payload */}
          {selectedSnap && (
            <Section title="Payload (Rohdaten)">
              <PayloadViewer payload={selectedSnap.payload} />
            </Section>
          )}

          {/* 4. Verlauf */}
          <Section title="Score-Verlauf (letzte 20 Snapshots)">
            <HistoryTrendChart items={snapItems} />
            <HistoryList
              items={snapItems}
              selectedId={selectedSnap?.id}
              onSelectMetrics={(snap) => loadMetrics(snap)}
            />
          </Section>
        </>
      )}

      <style>{`
        /* Page layout */
        .dap-page {
          display: flex; flex-direction: column;
          gap: 0; overflow-y: auto; min-height: 100%;
        }
        .dap-header {
          display: flex; align-items: center; gap: 16px;
          padding: 16px 24px 0;
        }
        .dap-page-title {
          margin: 0; font-size: 22px; font-weight: 700;
          color: var(--color-text, #1c1c1c);
        }
        .dap-back-btn {
          background: none; border: none; padding: 0;
          color: var(--t-magenta, #E20074); font-size: 13px;
          font-weight: 600; cursor: pointer; font-family: inherit;
          text-decoration: underline;
        }
        .dap-back-btn:hover { opacity: 0.8; }

        /* Sections */
        .dap-section {
          padding: 18px 24px;
          border-bottom: 1px solid var(--color-border, #e0e0e0);
          display: flex; flex-direction: column; gap: 12px;
        }
        .dap-section:last-child { border-bottom: none; }
        .dap-section__title {
          margin: 0; font-size: 14px; font-weight: 600;
          color: var(--color-text-secondary, #666);
          text-transform: uppercase; letter-spacing: 0.05em;
        }
        .dap-section__sub { margin: -4px 0 0; font-size: 12px; color: var(--color-text-secondary, #999); }

        /* Overview card */
        .dap-overview-card {
          display: flex; align-items: center; justify-content: space-between;
          border: 1.5px solid; border-radius: 10px;
          padding: 16px 20px; gap: 16px;
        }
        .dap-overview-card__left { display: flex; align-items: center; gap: 14px; }
        .dap-overview-card__icon { font-size: 28px; line-height: 1; width: 36px; text-align: center; }
        .dap-overview-card__type { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-secondary, #777); }
        .dap-overview-card__status { font-size: 20px; font-weight: 700; line-height: 1.2; }
        .dap-overview-card__right { text-align: right; }
        .dap-overview-card__score { font-size: 32px; font-weight: 700; line-height: 1; }
        .dap-overview-card__score-unit { font-size: 14px; font-weight: 400; opacity: 0.65; }
        .dap-overview-card__date { font-size: 11px; color: var(--color-text-secondary, #999); margin-top: 4px; }

        /* Metrics table */
        .dap-table-wrapper { overflow-x: auto; }
        .dap-table {
          width: 100%; border-collapse: collapse; font-size: 13px;
        }
        .dap-table th, .dap-table td {
          padding: 8px 12px; border-bottom: 1px solid var(--color-border, #e0e0e0);
          text-align: left;
        }
        .dap-table th {
          font-size: 11px; font-weight: 600; text-transform: uppercase;
          letter-spacing: 0.04em; color: var(--color-text-secondary, #777);
          white-space: nowrap; background: var(--color-surface-alt, #f9f9f9);
        }
        .dap-table tbody tr:hover { background: var(--color-surface-alt, #f9f9f9); }
        .dap-metric-label { font-weight: 500; }
        .dap-metric-chip {
          padding: 2px 8px; border-radius: 10px;
          font-size: 10px; font-weight: 700; text-transform: uppercase;
          letter-spacing: 0.04em; white-space: nowrap;
        }
        .dap-code { font-family: 'Courier New', monospace; font-size: 12px; }

        /* Payload viewer */
        .dap-payload { display: flex; flex-direction: column; gap: 8px; }
        .dap-payload__toggle {
          display: flex; align-items: center; gap: 6px;
          background: none; border: none; padding: 0;
          color: var(--t-magenta, #E20074); font-size: 13px;
          font-weight: 600; cursor: pointer; font-family: inherit;
        }
        .dap-payload__toggle:hover { opacity: 0.8; }
        .dap-payload__arrow { font-size: 12px; }
        .dap-payload__size { font-size: 11px; font-weight: 400; color: var(--color-text-secondary, #999); }
        .dap-payload__code {
          background: var(--color-surface-alt, #f5f5f5);
          border: 1px solid var(--color-border, #e0e0e0);
          border-radius: 6px; padding: 14px 16px;
          font-family: 'Courier New', monospace; font-size: 12px;
          overflow-x: auto; max-height: 400px; white-space: pre-wrap;
          word-break: break-all; margin: 0;
          color: var(--color-text, #1c1c1c);
        }

        /* History */
        .dap-history-list {
          display: flex; flex-direction: column; gap: 6px;
          max-height: 320px; overflow-y: auto;
        }
        .dap-history-item {
          display: flex; align-items: center; gap: 10px;
          padding: 8px 12px; border-radius: 6px;
          border: 1px solid var(--color-border, #e0e0e0);
          background: var(--color-surface, #fff);
          cursor: pointer; font-family: inherit; font-size: 13px;
          text-align: left; transition: border-color 0.1s;
        }
        .dap-history-item:hover { border-color: var(--t-magenta, #E20074); }
        .dap-history-item--active { font-weight: 600; }
        .dap-history-item__badge {
          padding: 2px 7px; border-radius: 10px;
          font-size: 10px; font-weight: 700; text-transform: uppercase;
          flex-shrink: 0;
        }
        .dap-history-item__score {
          font-size: 14px; font-weight: 700;
          color: var(--color-text, #1c1c1c); flex-shrink: 0;
        }
        .dap-history-item__date { flex: 1; color: var(--color-text-secondary, #666); }
        .dap-history-item__by { font-size: 11px; color: var(--color-text-secondary, #999); }

        /* Utility */
        .dap-loading { padding: 16px 0; font-size: 13px; color: var(--color-text-secondary, #888); }
        .dap-error { padding: 16px; font-size: 13px; color: #c62828; }
        .dap-empty { font-size: 13px; color: var(--color-text-secondary, #aaa); padding: 8px 0; }
      `}</style>
    </div>
  );
}
