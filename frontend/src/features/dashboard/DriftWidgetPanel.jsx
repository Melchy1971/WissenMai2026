import { useEffect, useReducer, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getDriftOverview, postDriftRecalculate } from '../../api/drift_analytics.js';

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_META = {
  PASS:    { color: '#2e7d32', bg: '#f1f8f1', border: '#66bb6a', label: 'PASS' },
  WARNING: { color: '#e65100', bg: '#fff8f1', border: '#ffb74d', label: 'WARNING' },
  FAIL:    { color: '#c62828', bg: '#fff5f5', border: '#ef5350', label: 'FAIL' },
  BLOCKED: { color: '#6a1a6a', bg: '#fdf0fd', border: '#ab47bc', label: 'BLOCKED' },
  UNKNOWN: { color: '#78909c', bg: '#f5f7f8', border: '#90a4ae', label: '—' },
};

function statusMeta(status) {
  return STATUS_META[status] || STATUS_META.UNKNOWN;
}

// ── Data reducer ──────────────────────────────────────────────────────────────

const INIT = { phase: 'idle', data: null, error: null };

function reducer(state, action) {
  switch (action.type) {
    case 'LOAD':   return { phase: 'loading', data: null, error: null };
    case 'OK':     return { phase: 'success', data: action.data, error: null };
    case 'ERR':    return { phase: 'error', data: null, error: action.error };
    case 'RELOAD': return { ...state, phase: 'reloading' };
    default:       return state;
  }
}

// ── Recalculate dialog ────────────────────────────────────────────────────────

function RecalcDialog({ onConfirm, onCancel, busy, result }) {
  return (
    <div className="drift-recalc-overlay" role="dialog" aria-modal="true"
      aria-label="Drift neu berechnen">
      <div className="drift-recalc-dialog">
        <h2 className="drift-recalc-dialog__title">Drift neu berechnen?</h2>
        <p className="drift-recalc-dialog__body">
          Alle 6 Analyse-Snapshots werden aus den aktuellen Report-Dateien neu erstellt.
          Bestehende Snapshots bleiben erhalten (append-only).
        </p>

        {result && (
          <div className={`drift-recalc-result drift-recalc-result--${result.type}`}>
            <strong>{result.type === 'success' ? 'Abgeschlossen' : 'Teilweise fehlgeschlagen'}</strong>
            <span>{result.message}</span>
            {result.failed && result.failed.length > 0 && (
              <span className="drift-recalc-result__failed">
                Fehlgeschlagen: {result.failed.join(', ')}
              </span>
            )}
          </div>
        )}

        <div className="drift-recalc-dialog__actions">
          {!result && (
            <>
              <button
                type="button"
                className="drift-btn drift-btn--primary"
                onClick={onConfirm}
                disabled={busy}
                aria-busy={busy}
              >
                {busy ? 'Wird berechnet…' : 'Neu berechnen'}
              </button>
              <button type="button" className="drift-btn drift-btn--secondary"
                onClick={onCancel} disabled={busy}>
                Abbrechen
              </button>
            </>
          )}
          {result && (
            <button type="button" className="drift-btn drift-btn--secondary"
              onClick={onCancel}>
              Schließen
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Single drift card ─────────────────────────────────────────────────────────

function DriftCard({ widget, onClick }) {
  // status=null means no data → show as WARNING
  const effectiveStatus = widget.status ?? 'WARNING';
  const meta = statusMeta(effectiveStatus);
  const hasNoData = widget.status === null;

  const formattedScore = widget.score != null
    ? widget.score.toFixed(1)
    : null;

  const formattedDate = widget.last_updated
    ? new Date(widget.last_updated).toLocaleDateString('de-DE', {
        day: '2-digit', month: '2-digit', year: 'numeric',
      })
    : null;

  return (
    <button
      type="button"
      className="drift-card"
      style={{
        background: meta.bg,
        borderColor: meta.border,
        cursor: 'pointer',
      }}
      onClick={() => onClick(widget.snapshot_type)}
      aria-label={`${widget.label}: ${meta.label}`}
    >
      <div className="drift-card__header">
        <span className="drift-card__label">{widget.label}</span>
        <span
          className="drift-card__badge"
          style={{ background: meta.color, color: '#fff' }}
        >
          {meta.label}
        </span>
      </div>

      {formattedScore != null && (
        <div className="drift-card__score" style={{ color: meta.color }}>
          {formattedScore}
          <span className="drift-card__score-unit"> / 100</span>
        </div>
      )}

      {hasNoData && (
        <div className="drift-card__no-data">Noch keine Daten</div>
      )}

      {formattedDate && (
        <div className="drift-card__date">Stand: {formattedDate}</div>
      )}
    </button>
  );
}

function DriftCardSkeleton() {
  return (
    <div className="drift-card drift-card--skeleton" aria-hidden="true">
      <div className="skel skel--label" />
      <div className="skel skel--badge" />
      <div className="skel skel--score" />
    </div>
  );
}

// ── Global status bar ─────────────────────────────────────────────────────────

function GlobalStatusBar({ globalStatus, missingData }) {
  const meta = statusMeta(globalStatus || 'UNKNOWN');
  return (
    <div className="drift-global-status" style={{ borderColor: meta.border }}>
      <span className="drift-global-status__label">Gesamtstatus:</span>
      <span
        className="drift-global-status__badge"
        style={{ background: meta.color, color: '#fff' }}
      >
        {meta.label}
      </span>
      {missingData && missingData.length > 0 && (
        <span className="drift-global-status__missing">
          Fehlende Daten: {missingData.join(', ')}
        </span>
      )}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

const WIDGET_ORDER = [
  'product_maturity',
  'gold_path',
  'release_gate',
  'test_coverage',
  'id_leak_audit',
  'security_audit',
];

export function DriftWidgetPanel() {
  const [state, dispatch] = useReducer(reducer, INIT);
  const [showDialog, setShowDialog] = useState(false);
  const [recalcBusy, setRecalcBusy] = useState(false);
  const [recalcResult, setRecalcResult] = useState(null);
  const navigate = useNavigate();
  const abortRef = useRef(null);

  function load() {
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    dispatch({ type: 'LOAD' });
    getDriftOverview({ signal: ctrl.signal })
      .then((data) => dispatch({ type: 'OK', data }))
      .catch((err) => {
        if (err?.name !== 'AbortError') dispatch({ type: 'ERR', error: err });
      });
  }

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, []);

  function handleCardClick(snapshotType) {
    navigate(`/drift-analytics/${encodeURIComponent(snapshotType)}`);
  }

  async function handleRecalc() {
    setRecalcBusy(true);
    setRecalcResult(null);
    try {
      const result = await postDriftRecalculate();
      const hasFailures = result.snapshots_failed && result.snapshots_failed.length > 0;
      setRecalcResult({
        type: hasFailures ? 'warning' : 'success',
        message: result.message,
        failed: result.snapshots_failed,
      });
      // Reload overview after recalculate
      load();
    } catch (err) {
      setRecalcResult({
        type: 'error',
        message: err?.message || 'Berechnung fehlgeschlagen.',
        failed: [],
      });
    } finally {
      setRecalcBusy(false);
    }
  }

  function closeDialog() {
    setShowDialog(false);
    setRecalcResult(null);
  }

  const isLoading = state.phase === 'idle' || state.phase === 'loading';
  const data = state.data;

  // Build ordered widget list
  const widgets = data
    ? WIDGET_ORDER.map((key) => data[key]).filter(Boolean)
    : [];

  return (
    <section className="drift-widget-panel" data-testid="drift-widget-panel">
      <div className="drift-widget-panel__head">
        <h2 className="drift-widget-panel__title">Produktqualität (Drift Analytics)</h2>
        <button
          type="button"
          className="drift-btn drift-btn--ghost"
          onClick={() => setShowDialog(true)}
          disabled={isLoading}
          title="Alle Drift-Snapshots aus aktuellen Reports neu berechnen"
        >
          Neu berechnen
        </button>
      </div>

      {data && (
        <GlobalStatusBar
          globalStatus={data.global_status}
          missingData={data.missing_data}
        />
      )}

      <div className="drift-card-grid">
        {isLoading
          ? WIDGET_ORDER.map((k) => <DriftCardSkeleton key={k} />)
          : state.phase === 'error'
            ? (
              <div className="drift-error" role="alert">
                Daten konnten nicht geladen werden.{' '}
                <button type="button" className="drift-link" onClick={load}>
                  Erneut versuchen
                </button>
              </div>
            )
            : widgets.map((w) => (
              <DriftCard key={w.snapshot_type} widget={w} onClick={handleCardClick} />
            ))
        }
      </div>

      {showDialog && (
        <RecalcDialog
          onConfirm={handleRecalc}
          onCancel={closeDialog}
          busy={recalcBusy}
          result={recalcResult}
        />
      )}

      <style>{`
        /* Panel layout */
        .drift-widget-panel { display: flex; flex-direction: column; gap: 14px; }
        .drift-widget-panel__head {
          display: flex; align-items: center; justify-content: space-between; gap: 12px;
        }
        .drift-widget-panel__title {
          margin: 0;
          font-size: 18px;
          font-weight: 700;
          color: var(--color-text, #1c1c1c);
        }

        /* Global status bar */
        .drift-global-status {
          display: flex; align-items: center; gap: 10px;
          padding: 8px 14px;
          border: 1px solid;
          border-radius: 6px;
          background: var(--color-surface, #fff);
          font-size: 13px;
        }
        .drift-global-status__label { color: var(--color-text-secondary, #666); }
        .drift-global-status__badge {
          padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.04em;
        }
        .drift-global-status__missing {
          font-size: 11px; color: var(--color-text-secondary, #999); margin-left: auto;
        }

        /* Card grid */
        .drift-card-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 12px;
        }

        /* Individual card */
        .drift-card {
          background: var(--color-surface, #fff);
          border: 1.5px solid var(--color-border, #e0e0e0);
          border-radius: 10px;
          padding: 14px 16px;
          display: flex; flex-direction: column; gap: 8px;
          text-align: left;
          transition: box-shadow 0.15s, transform 0.1s;
          font-family: inherit;
        }
        .drift-card:hover {
          box-shadow: 0 4px 16px rgba(0,0,0,0.10);
          transform: translateY(-1px);
        }
        .drift-card:focus-visible {
          outline: 2px solid var(--t-magenta, #E20074);
          outline-offset: 2px;
        }
        .drift-card--skeleton { animation: skel-pulse 1.4s ease-in-out infinite; }

        .drift-card__header {
          display: flex; align-items: flex-start; justify-content: space-between; gap: 8px;
        }
        .drift-card__label {
          font-size: 12px; font-weight: 600;
          color: var(--color-text-secondary, #555);
          text-transform: uppercase; letter-spacing: 0.04em;
          line-height: 1.3;
        }
        .drift-card__badge {
          padding: 2px 8px; border-radius: 10px;
          font-size: 10px; font-weight: 700;
          text-transform: uppercase; letter-spacing: 0.04em;
          flex-shrink: 0;
          white-space: nowrap;
        }
        .drift-card__score {
          font-size: 28px; font-weight: 700; line-height: 1;
        }
        .drift-card__score-unit {
          font-size: 13px; font-weight: 400; opacity: 0.7;
        }
        .drift-card__no-data {
          font-size: 11px; color: #e65100; font-style: italic;
        }
        .drift-card__date {
          font-size: 11px; color: var(--color-text-secondary, #999);
        }

        /* Skeleton */
        @keyframes skel-pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        .skel { background: #e0e0e0; border-radius: 4px; }
        .skel--label { width: 60%; height: 12px; }
        .skel--badge { width: 40%; height: 10px; }
        .skel--score { width: 35%; height: 28px; margin-top: 4px; }

        /* Error */
        .drift-error {
          grid-column: 1 / -1; font-size: 13px;
          color: var(--color-danger, #c62828); padding: 8px 0;
        }
        .drift-link {
          background: none; border: none; padding: 0;
          color: var(--t-magenta, #E20074); text-decoration: underline;
          cursor: pointer; font-size: 13px; font-family: inherit;
        }

        /* Buttons */
        .drift-btn {
          border: none; border-radius: 6px; padding: 7px 14px;
          font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
          transition: opacity 0.15s;
        }
        .drift-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .drift-btn--primary {
          background: var(--t-magenta, #E20074); color: #fff;
        }
        .drift-btn--primary:hover:not(:disabled) { opacity: 0.88; }
        .drift-btn--secondary {
          background: var(--color-surface, #fff);
          border: 1.5px solid var(--color-border, #ccc); color: var(--color-text, #1c1c1c);
        }
        .drift-btn--secondary:hover:not(:disabled) { background: #f5f5f5; }
        .drift-btn--ghost {
          background: transparent;
          border: 1.5px solid var(--color-border, #ccc); color: var(--color-text-secondary, #666);
          padding: 5px 12px; font-size: 12px;
        }
        .drift-btn--ghost:hover:not(:disabled) { border-color: var(--t-magenta, #E20074); color: var(--t-magenta, #E20074); }

        /* Recalculate dialog overlay */
        .drift-recalc-overlay {
          position: fixed; inset: 0;
          background: rgba(0,0,0,0.45);
          display: flex; align-items: center; justify-content: center;
          z-index: 1000;
        }
        .drift-recalc-dialog {
          background: var(--color-surface, #fff);
          border-radius: 10px;
          padding: 28px 32px;
          width: min(460px, 90vw);
          display: flex; flex-direction: column; gap: 16px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.18);
        }
        .drift-recalc-dialog__title { margin: 0; font-size: 18px; font-weight: 700; }
        .drift-recalc-dialog__body { margin: 0; font-size: 14px; color: var(--color-text-secondary, #555); line-height: 1.5; }
        .drift-recalc-dialog__actions { display: flex; gap: 10px; margin-top: 4px; }

        /* Recalculate result */
        .drift-recalc-result {
          display: flex; flex-direction: column; gap: 4px;
          padding: 12px 14px; border-radius: 6px; font-size: 13px;
          border: 1px solid;
        }
        .drift-recalc-result--success { background: #f1f8f1; border-color: #66bb6a; color: #2e7d32; }
        .drift-recalc-result--warning { background: #fff8f1; border-color: #ffb74d; color: #e65100; }
        .drift-recalc-result--error   { background: #fff5f5; border-color: #ef5350; color: #c62828; }
        .drift-recalc-result__failed  { font-size: 11px; opacity: 0.8; }
      `}</style>
    </section>
  );
}
