import React from 'react';
import { Link } from 'react-router-dom';

var KIND_LABELS = { topic: 'Thema', document: 'Dokument', chunk: 'Absatz' };
var KIND_COLORS = {
  topic:    { bg: '#e3f2fd', text: '#1565c0' },
  document: { bg: '#e8f5e9', text: '#2e7d32' },
  chunk:    { bg: '#fff3e0', text: '#e65100' },
};

function KindBadge({ kind }) {
  var colors = KIND_COLORS[kind] || { bg: '#f5f5f5', text: '#555' };
  return React.createElement('span', {
    className: 'unified-card__kind-badge',
    style: { background: colors.bg, color: colors.text },
  }, KIND_LABELS[kind] || kind);
}

function ScoreBar({ score }) {
  var pct = Math.round(Math.min(Math.max(score, 0), 1) * 100);
  var color = pct >= 70 ? '#2e7d32' : pct >= 40 ? '#f9a825' : '#9e9e9e';
  return React.createElement('div', { className: 'unified-card__score', 'aria-label': 'Relevanzscore ' + pct + '%' },
    React.createElement('div', { className: 'unified-card__score-track' },
      React.createElement('div', {
        className: 'unified-card__score-fill',
        style: { width: pct + '%', background: color },
      })
    ),
    React.createElement('span', { className: 'unified-card__score-label' }, pct + '%')
  );
}

function hitLink(hit) {
  if (hit.kind === 'topic') return '/topics/' + hit.id;
  if (hit.kind === 'document') return '/documents/' + hit.id;
  // chunk: link to parent document via meta
  var docId = (hit.meta && hit.meta.document_id) ? hit.meta.document_id : hit.id;
  return '/documents/' + docId;
}

function Highlight({ html }) {
  return React.createElement('span', { dangerouslySetInnerHTML: { __html: html } });
}

function StatusPill({ status }) {
  if (!status) return null;
  return React.createElement('span', { className: 'unified-card__status badge badge--neutral' }, status);
}

export function UnifiedSearchResultCard({ hit }) {
  var link = hitLink(hit);
  var createdDate = hit.created_at
    ? new Date(hit.created_at).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
    : null;

  return React.createElement('article', { className: 'unified-card' },
    React.createElement('div', { className: 'unified-card__header' },
      React.createElement('div', { className: 'unified-card__title-row' },
        React.createElement(KindBadge, { kind: hit.kind }),
        React.createElement('h3', { className: 'unified-card__title' },
          React.createElement(Link, { to: link, className: 'unified-card__title-link' }, hit.title)
        )
      ),
      React.createElement('div', { className: 'unified-card__meta' },
        hit.status && React.createElement(StatusPill, { status: hit.status }),
        createdDate && React.createElement('span', { className: 'unified-card__date' }, createdDate)
      )
    ),

    hit.highlight && React.createElement('blockquote', { className: 'unified-card__excerpt' },
      React.createElement(Highlight, { html: hit.highlight })
    ),

    React.createElement('div', { className: 'unified-card__footer' },
      React.createElement(ScoreBar, { score: hit.score })
    ),

    React.createElement('style', null, `
      .unified-card {
        background: var(--color-surface, #fff);
        border: 1px solid var(--color-border, #e0e0e0);
        border-radius: 8px;
        padding: 14px 18px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        transition: box-shadow 0.15s;
      }
      .unified-card:hover { box-shadow: 0 2px 10px rgba(0,0,0,0.08); }
      .unified-card__header { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
      .unified-card__title-row { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
      .unified-card__title { margin: 0; font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
      .unified-card__title-link { color: var(--t-magenta, #E20074); text-decoration: none; }
      .unified-card__title-link:hover { text-decoration: underline; }
      .unified-card__kind-badge { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 10px; white-space: nowrap; flex-shrink: 0; text-transform: uppercase; letter-spacing: 0.04em; }
      .unified-card__meta { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
      .unified-card__status { font-size: 11px; }
      .unified-card__date { font-size: 11px; color: var(--color-text-secondary, #888); }
      .unified-card__excerpt {
        margin: 0;
        padding: 8px 12px;
        border-left: 3px solid var(--color-border, #e0e0e0);
        font-size: 13px;
        line-height: 1.6;
        color: var(--color-text, #1c1c1c);
        font-style: italic;
      }
      .unified-card__excerpt mark {
        background: #fff176;
        color: inherit;
        font-style: inherit;
        padding: 0 1px;
        border-radius: 2px;
      }
      .unified-card__footer { display: flex; align-items: center; gap: 12px; }
      .unified-card__score { display: flex; align-items: center; gap: 8px; }
      .unified-card__score-track { width: 80px; height: 5px; background: #e0e0e0; border-radius: 3px; overflow: hidden; }
      .unified-card__score-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
      .unified-card__score-label { font-size: 11px; color: var(--color-text-secondary, #888); }
    `)
  );
}
