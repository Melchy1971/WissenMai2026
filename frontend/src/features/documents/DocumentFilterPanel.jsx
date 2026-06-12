import React from 'react';

const STATUS_OPTIONS = [
  { value: 'all', label: 'Alle' },
  { value: 'active', label: 'Aktiv' },
  { value: 'archived', label: 'Archiviert' },
];

export function DocumentFilterPanel({ filters, setFilters, categories, allTags }) {
  function set(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  function toggleTag(tag) {
    setFilters((prev) => {
      const has = prev.tags.includes(tag);
      return { ...prev, tags: has ? prev.tags.filter((t) => t !== tag) : [...prev.tags, tag] };
    });
  }

  function reset() {
    setFilters({ search: '', status: 'active', category: '', tags: [], topic: '' });
  }

  const hasActiveFilter =
    filters.search !== '' ||
    filters.status !== 'active' ||
    filters.category !== '' ||
    filters.tags.length > 0 ||
    filters.topic !== '';

  return (
    <aside className="doc-filter-panel panel">
      <div className="panel__header">
        <span className="panel__eyebrow">Filter</span>
        {hasActiveFilter && (
          <button className="button-secondary button-secondary--xs" onClick={reset}>
            Zurücksetzen
          </button>
        )}
      </div>

      <div className="doc-filter-panel__body">
        {/* Suche */}
        <section className="doc-filter-section">
          <label className="doc-filter-label" htmlFor="doc-filter-search">
            Dokumentsuche
          </label>
          <div className="search-bar search-bar--sm">
            <input
              id="doc-filter-search"
              className="search-bar__field"
              type="search"
              placeholder="Titel suchen …"
              value={filters.search}
              onChange={(e) => set('search', e.target.value)}
            />
          </div>
        </section>

        {/* Status */}
        <section className="doc-filter-section">
          <span className="doc-filter-label">Status</span>
          <div className="doc-filter-radios" role="group" aria-label="Lifecycle-Status">
            {STATUS_OPTIONS.map((opt) => (
              <label key={opt.value} className="doc-filter-radio">
                <input
                  type="radio"
                  name="doc-status"
                  value={opt.value}
                  checked={filters.status === opt.value}
                  onChange={() => set('status', opt.value)}
                />
                <span>{opt.label}</span>
              </label>
            ))}
          </div>
        </section>

        {/* Kategorie */}
        {categories.length > 0 && (
          <section className="doc-filter-section">
            <label className="doc-filter-label" htmlFor="doc-filter-category">
              Kategorie
            </label>
            <select
              id="doc-filter-category"
              className="doc-filter-select"
              value={filters.category}
              onChange={(e) => set('category', e.target.value)}
            >
              <option value="">Alle Kategorien</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </section>
        )}

        {/* Tags */}
        {allTags.length > 0 && (
          <section className="doc-filter-section">
            <span className="doc-filter-label">Tags</span>
            <div className="doc-filter-tags">
              {allTags.map((tag) => {
                const active = filters.tags.includes(tag);
                return (
                  <button
                    key={tag}
                    className={`badge ${active ? 'badge--active' : ''}`}
                    onClick={() => toggleTag(tag)}
                    aria-pressed={active}
                  >
                    {tag}
                  </button>
                );
              })}
            </div>
          </section>
        )}
      </div>

      <style>{`
        .doc-filter-panel {
          width: 220px;
          min-width: 180px;
          flex-shrink: 0;
          display: flex;
          flex-direction: column;
          gap: 0;
        }
        .doc-filter-panel__body {
          display: flex;
          flex-direction: column;
          gap: 20px;
          padding: 16px;
          overflow-y: auto;
        }
        .doc-filter-section {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .doc-filter-label {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          color: var(--color-text-secondary, #666);
        }
        .doc-filter-radios {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .doc-filter-radio {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          cursor: pointer;
        }
        .doc-filter-select {
          width: 100%;
          padding: 6px 8px;
          font-size: 13px;
          border: 1px solid var(--color-border, #ddd);
          border-radius: 4px;
          background: var(--color-surface, #fff);
          color: var(--color-text, #1c1c1c);
        }
        .doc-filter-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .badge--active {
          background: var(--t-magenta, #E20074);
          color: #fff;
          border-color: var(--t-magenta, #E20074);
        }
        .button-secondary--xs {
          font-size: 11px;
          padding: 2px 8px;
        }
      `}</style>
    </aside>
  );
}
