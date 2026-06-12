import React from 'react';
import { Link } from 'react-router-dom';

var TONE_COLORS = {
  high:   { bar: '#2e7d32', text: '#1b5e20', bg: '#e8f5e9' },
  medium: { bar: '#f9a825', text: '#7f6000', bg: '#fff8e1' },
  low:    { bar: '#9e9e9e', text: '#555',    bg: '#f5f5f5' },
};

function RelevanceBar({ relevance }) {
  var colors = TONE_COLORS[relevance.tone] || TONE_COLORS.low;
  var segments = [1, 2, 3];
  return React.createElement('div', { className: 'relevance-bar-wrap' },
    React.createElement('div', { className: 'relevance-bar', 'aria-label': relevance.label },
      segments.map(function(n) {
        return React.createElement('span', {
          key: n,
          className: 'relevance-bar__seg',
          style: { background: n <= relevance.bars ? colors.bar : '#e0e0e0' },
        });
      })
    ),
    React.createElement('span', {
      className: 'relevance-label',
      style: { color: colors.text, background: colors.bg },
    }, relevance.label)
  );
}

export function SearchResultCard({ item }) {
  return React.createElement('article', { className: 'search-result-card' },
    React.createElement('div', { className: 'search-result-card__header' },
      React.createElement('h3', { className: 'search-result-card__title' },
        React.createElement(Link, {
          to: '/documents/' + item.documentId,
          className: 'search-result-card__title-link',
        }, item.documentTitle)
      ),
      item.positionLabel && React.createElement('span', { className: 'search-result-card__position badge badge--neutral' },
        item.positionLabel
      )
    ),

    React.createElement('blockquote', { className: 'search-result-card__excerpt' },
      '„', item.textPreview, '“'
    ),

    React.createElement('div', { className: 'search-result-card__footer' },
      React.createElement(RelevanceBar, { relevance: item.relevance }),
      item.sourceAnchorLabel && item.sourceAnchorLabel !== 'Keine Quellenposition verfuegbar' &&
        React.createElement('span', { className: 'search-result-card__anchor' }, item.sourceAnchorLabel)
    ),

    React.createElement('style', null, `
      .search-result-card {
        background: var(--color-surface, #fff);
        border: 1px solid var(--color-border, #e0e0e0);
        border-radius: 8px;
        padding: 16px 20px;
        display: flex;
        flex-direction: column;
        gap: 10px;
        transition: box-shadow 0.15s;
      }
      .search-result-card:hover {
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
      }
      .search-result-card__header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
      }
      .search-result-card__title {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
      }
      .search-result-card__title-link {
        color: var(--t-magenta, #E20074);
        text-decoration: none;
      }
      .search-result-card__title-link:hover {
        text-decoration: underline;
      }
      .search-result-card__position {
        flex-shrink: 0;
        font-size: 11px;
      }
      .search-result-card__excerpt {
        margin: 0;
        padding: 10px 14px;
        border-left: 3px solid var(--color-border, #e0e0e0);
        font-size: 13px;
        line-height: 1.6;
        color: var(--color-text, #1c1c1c);
        font-style: italic;
      }
      .search-result-card__footer {
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      }
      .search-result-card__anchor {
        font-size: 11px;
        color: var(--color-text-secondary, #666);
      }
      .relevance-bar-wrap {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .relevance-bar {
        display: flex;
        gap: 3px;
      }
      .relevance-bar__seg {
        width: 12px;
        height: 8px;
        border-radius: 2px;
      }
      .relevance-label {
        font-size: 11px;
        font-weight: 600;
        padding: 2px 7px;
        border-radius: 10px;
      }
    `)
  );
}
