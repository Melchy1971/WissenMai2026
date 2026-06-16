import React, { useEffect, useReducer } from 'react';
import { getDashboardTopicsWidgets } from '../../api/dashboard.js';

// ── State management ──────────────────────────────────────────────────────────

var INIT = { status: 'idle', data: null, error: null };

function reducer(state, action) {
  if (action.type === 'LOAD') return { status: 'loading', data: null, error: null };
  if (action.type === 'OK')   return { status: 'success', data: action.data, error: null };
  if (action.type === 'ERR')  return { status: 'error', data: null, error: action.error };
  return state;
}

// ── Chart components (pure SVG, no dependencies) ──────────────────────────────

var STATUS_COLORS = {
  draft:    '#90a4ae',
  review:   '#ffb74d',
  approved: '#66bb6a',
  archived: '#bdbdbd',
};
var STATUS_LABELS = { draft: 'Entwurf', review: 'Review', approved: 'Genehmigt', archived: 'Archiviert' };

function DonutChart({ byStatus }) {
  var total = Object.values(byStatus).reduce(function(a, b) { return a + b; }, 0);
  if (total === 0) return React.createElement('div', { className: 'widget-chart__empty' }, 'Keine Daten');

  var W = 120, R = 44, cx = 60, cy = 60;
  var circumference = 2 * Math.PI * R;

  var segments = [];
  var offset = 0;
  ['approved', 'review', 'draft', 'archived'].forEach(function(status) {
    var count = byStatus[status] || 0;
    if (count === 0) return;
    var frac = count / total;
    var dash = frac * circumference;
    segments.push({ status, count, dash, offset });
    offset += dash;
  });

  return React.createElement('svg', { width: W, height: W, viewBox: '0 0 120 120', role: 'img', 'aria-label': 'Statusverteilung' },
    React.createElement('circle', { cx, cy, r: R, fill: 'none', stroke: '#e0e0e0', strokeWidth: 16 }),
    segments.map(function(seg) {
      return React.createElement('circle', {
        key: seg.status,
        cx, cy, r: R,
        fill: 'none',
        stroke: STATUS_COLORS[seg.status] || '#ccc',
        strokeWidth: 16,
        strokeDasharray: seg.dash + ' ' + circumference,
        strokeDashoffset: -seg.offset,
        transform: 'rotate(-90 60 60)',
      });
    }),
    React.createElement('text', { x: 60, y: 56, textAnchor: 'middle', fontSize: 18, fontWeight: 700, fill: 'var(--color-text, #1c1c1c)' }, total),
    React.createElement('text', { x: 60, y: 70, textAnchor: 'middle', fontSize: 10, fill: 'var(--color-text-secondary, #888)' }, 'Gesamt')
  );
}

function BarChart({ byStatus }) {
  var max = Math.max(...Object.values(byStatus), 1);
  var statuses = ['draft', 'review', 'approved', 'archived'];

  return React.createElement('div', { className: 'bar-chart' },
    statuses.map(function(status) {
      var count = byStatus[status] || 0;
      var pct = Math.round((count / max) * 100);
      return React.createElement('div', { key: status, className: 'bar-chart__row' },
        React.createElement('span', { className: 'bar-chart__label' }, STATUS_LABELS[status]),
        React.createElement('div', { className: 'bar-chart__track' },
          React.createElement('div', {
            className: 'bar-chart__fill',
            style: { width: pct + '%', background: STATUS_COLORS[status] },
            role: 'meter', 'aria-valuenow': count, 'aria-valuemax': max,
          })
        ),
        React.createElement('span', { className: 'bar-chart__value' }, count)
      );
    })
  );
}

function TrendChart({ newPerDay }) {
  if (!newPerDay || newPerDay.length === 0) return null;
  var W = 280, H = 70, PAD = 10;
  var counts = newPerDay.map(function(d) { return d.count; });
  var max = Math.max(...counts, 1);
  var n = counts.length;
  var stepX = (W - PAD * 2) / Math.max(n - 1, 1);

  var points = counts.map(function(c, i) {
    return [PAD + i * stepX, H - PAD - ((c / max) * (H - PAD * 2))];
  });

  var polyline = points.map(function(p) { return p[0] + ',' + p[1]; }).join(' ');

  // area fill path
  var areaPath = 'M ' + points[0][0] + ' ' + (H - PAD)
    + ' L ' + points.map(function(p) { return p[0] + ' ' + p[1]; }).join(' L ')
    + ' L ' + points[points.length - 1][0] + ' ' + (H - PAD) + ' Z';

  return React.createElement('div', { className: 'trend-chart' },
    React.createElement('svg', { width: '100%', viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'Neue Themen letzte 7 Tage' },
      React.createElement('path', { d: areaPath, fill: 'rgba(226,0,116,0.1)' }),
      React.createElement('polyline', { points: polyline, fill: 'none', stroke: 'var(--t-magenta, #E20074)', strokeWidth: 2, strokeLinejoin: 'round' }),
      points.map(function(p, i) {
        return React.createElement('circle', { key: i, cx: p[0], cy: p[1], r: 3, fill: 'var(--t-magenta, #E20074)' });
      })
    ),
    React.createElement('div', { className: 'trend-chart__labels' },
      newPerDay.map(function(d) {
        var label = d.date.slice(5); // "MM-DD"
        return React.createElement('span', { key: d.date, className: 'trend-chart__day' }, label);
      })
    )
  );
}

// ── Skeleton components ───────────────────────────────────────────────────────

function SkeletonWidget() {
  return React.createElement('div', { className: 'topics-widget topics-widget--skeleton', 'aria-hidden': 'true' },
    React.createElement('div', { className: 'skel skel--label' }),
    React.createElement('div', { className: 'skel skel--value' })
  );
}

function SkeletonChart() {
  return React.createElement('div', { className: 'topics-chart-card topics-chart-card--skeleton', 'aria-hidden': 'true' },
    React.createElement('div', { className: 'skel skel--title' }),
    React.createElement('div', { className: 'skel skel--chart' })
  );
}

// ── Stat widget ───────────────────────────────────────────────────────────────

function StatWidget({ label, value, accent }) {
  return React.createElement('div', { className: 'topics-widget' + (accent ? ' topics-widget--accent' : '') },
    React.createElement('span', { className: 'topics-widget__label' }, label),
    React.createElement('span', { className: 'topics-widget__value' }, value)
  );
}

function TagCloud({ tags }) {
  if (!tags || tags.length === 0) {
    return React.createElement('p', { className: 'widget-chart__empty' }, 'Keine Tags vorhanden');
  }
  var max = tags[0].count || 1;
  return React.createElement('div', { className: 'tag-cloud' },
    tags.map(function(tag) {
      var size = 11 + Math.round((tag.count / max) * 8);
      return React.createElement('span', {
        key: tag.name,
        className: 'tag-cloud__item',
        style: { fontSize: size + 'px' },
        title: tag.count + ' Themen',
      }, tag.name);
    })
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export function TopicsWidgetPanel() {
  var [state, dispatch] = useReducer(reducer, INIT);

  useEffect(function() {
    var aborted = false;
    var ctrl = new AbortController();
    dispatch({ type: 'LOAD' });
    getDashboardTopicsWidgets({ signal: ctrl.signal })
      .then(function(data) {
        if (!aborted) dispatch({ type: 'OK', data: data });
      })
      .catch(function(err) {
        if (!aborted) dispatch({ type: 'ERR', error: err });
      });
    return function() { aborted = true; ctrl.abort(); };
  }, []);

  var isLoading = state.status === 'loading' || state.status === 'idle';

  return React.createElement('section', { className: 'topics-widget-panel' },
    React.createElement('h2', { className: 'topics-widget-panel__title' }, 'Themen-Übersicht'),

    // ── 6 stat widgets ──
    React.createElement('div', { className: 'topics-widget-grid' },
      isLoading
        ? [1,2,3,4,5,6].map(function(n) { return React.createElement(SkeletonWidget, { key: n }); })
        : state.status === 'success'
          ? [
              React.createElement(StatWidget, { key: 'total', label: 'Themen gesamt', value: state.data.total }),
              React.createElement(StatWidget, { key: 'draft', label: 'Entwurf', value: state.data.by_status.draft || 0 }),
              React.createElement(StatWidget, { key: 'review', label: 'In Review', value: state.data.by_status.review || 0 }),
              React.createElement(StatWidget, { key: 'approved', label: 'Genehmigt', value: state.data.by_status.approved || 0, accent: true }),
              React.createElement(StatWidget, { key: 'new7', label: 'Neue (7 Tage)', value: state.data.new_last_7_days }),
              React.createElement(StatWidget, { key: 'unreviewed', label: 'Unbearbeitet', value: state.data.unreviewed }),
            ]
          : React.createElement('div', { className: 'topics-widget-panel__error' }, 'Daten konnten nicht geladen werden.')
    ),

    // ── 3 charts ──
    state.status === 'success' && React.createElement('div', { className: 'topics-chart-row' },

      React.createElement('div', { className: 'topics-chart-card' },
        React.createElement('h3', { className: 'topics-chart-card__title' }, 'Status (Donut)'),
        React.createElement('div', { className: 'topics-chart-card__body topics-chart-card__body--center' },
          React.createElement(DonutChart, { byStatus: state.data.by_status }),
          React.createElement('div', { className: 'donut-legend' },
            ['approved','review','draft','archived'].map(function(s) {
              return React.createElement('div', { key: s, className: 'donut-legend__item' },
                React.createElement('span', { className: 'donut-legend__dot', style: { background: STATUS_COLORS[s] } }),
                React.createElement('span', null, STATUS_LABELS[s], ' (', state.data.by_status[s] || 0, ')')
              );
            })
          )
        )
      ),

      React.createElement('div', { className: 'topics-chart-card' },
        React.createElement('h3', { className: 'topics-chart-card__title' }, 'Status (Balken)'),
        React.createElement('div', { className: 'topics-chart-card__body' },
          React.createElement(BarChart, { byStatus: state.data.by_status })
        )
      ),

      React.createElement('div', { className: 'topics-chart-card' },
        React.createElement('h3', { className: 'topics-chart-card__title' }, 'Neue Themen (7 Tage)'),
        React.createElement('div', { className: 'topics-chart-card__body' },
          React.createElement(TrendChart, { newPerDay: state.data.new_per_day })
        )
      )
    ),

    isLoading && React.createElement('div', { className: 'topics-chart-row' },
      [1,2,3].map(function(n) { return React.createElement(SkeletonChart, { key: n }); })
    ),

    // ── Tag cloud ──
    state.status === 'success' && React.createElement('div', { className: 'topics-chart-card topics-tag-card' },
      React.createElement('h3', { className: 'topics-chart-card__title' }, 'Häufig verwendete Tags'),
      React.createElement('div', { className: 'topics-chart-card__body' },
        React.createElement(TagCloud, { tags: state.data.top_tags })
      )
    ),

    React.createElement('style', null, `
      .topics-widget-panel { display: flex; flex-direction: column; gap: 20px; }
      .topics-widget-panel__title { margin: 0 0 4px; font-size: 18px; font-weight: 700; color: var(--color-text, #1c1c1c); }
      .topics-widget-panel__error { color: var(--color-danger, #c62828); font-size: 13px; }

      /* Stat widgets */
      .topics-widget-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
      .topics-widget {
        background: var(--color-surface, #fff);
        border: 1px solid var(--color-border, #e0e0e0);
        border-radius: 8px;
        padding: 14px 16px;
        display: flex; flex-direction: column; gap: 6px;
      }
      .topics-widget--accent { border-color: #66bb6a; background: #f1f8f1; }
      .topics-widget__label { font-size: 11px; color: var(--color-text-secondary, #888); text-transform: uppercase; letter-spacing: 0.04em; }
      .topics-widget__value { font-size: 26px; font-weight: 700; color: var(--color-text, #1c1c1c); line-height: 1; }

      /* Charts row */
      .topics-chart-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
      .topics-chart-card {
        background: var(--color-surface, #fff);
        border: 1px solid var(--color-border, #e0e0e0);
        border-radius: 8px;
        padding: 16px;
        display: flex; flex-direction: column; gap: 12px;
      }
      .topics-chart-card__title { margin: 0; font-size: 13px; font-weight: 600; color: var(--color-text-secondary, #555); text-transform: uppercase; letter-spacing: 0.04em; }
      .topics-chart-card__body { display: flex; flex-direction: column; gap: 10px; }
      .topics-chart-card__body--center { align-items: center; }
      .topics-tag-card { grid-column: 1 / -1; }

      /* Donut legend */
      .donut-legend { display: flex; flex-direction: column; gap: 5px; font-size: 12px; }
      .donut-legend__item { display: flex; align-items: center; gap: 6px; }
      .donut-legend__dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

      /* Bar chart */
      .bar-chart { display: flex; flex-direction: column; gap: 8px; }
      .bar-chart__row { display: flex; align-items: center; gap: 8px; }
      .bar-chart__label { width: 72px; font-size: 11px; color: var(--color-text-secondary, #888); flex-shrink: 0; }
      .bar-chart__track { flex: 1; height: 10px; background: #e0e0e0; border-radius: 5px; overflow: hidden; }
      .bar-chart__fill { height: 100%; border-radius: 5px; transition: width 0.4s ease; }
      .bar-chart__value { width: 24px; text-align: right; font-size: 12px; font-weight: 600; color: var(--color-text, #1c1c1c); }

      /* Trend chart */
      .trend-chart { display: flex; flex-direction: column; gap: 4px; }
      .trend-chart__labels { display: flex; justify-content: space-between; }
      .trend-chart__day { font-size: 9px; color: var(--color-text-secondary, #aaa); }

      /* Tag cloud */
      .tag-cloud { display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 0; }
      .tag-cloud__item {
        background: var(--color-surface-alt, #f5f5f5);
        border: 1px solid var(--color-border, #e0e0e0);
        border-radius: 12px;
        padding: 3px 10px;
        color: var(--color-text, #1c1c1c);
        cursor: default;
        transition: background 0.15s;
      }
      .tag-cloud__item:hover { background: #ffe0f0; border-color: var(--t-magenta, #E20074); }

      /* Empty state */
      .widget-chart__empty { font-size: 12px; color: var(--color-text-secondary, #aaa); text-align: center; padding: 16px 0; }

      /* Skeleton */
      @keyframes skel-pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
      .topics-widget--skeleton, .topics-chart-card--skeleton { animation: skel-pulse 1.4s ease-in-out infinite; }
      .skel { background: #e0e0e0; border-radius: 4px; }
      .skel--label { width: 60%; height: 11px; }
      .skel--value { width: 40%; height: 26px; margin-top: 4px; }
      .skel--title { width: 50%; height: 13px; }
      .skel--chart { width: 100%; height: 80px; margin-top: 8px; border-radius: 6px; }
    `)
  );
}
