import { Link } from 'react-router-dom';

export function SearchResultList({ items, query }) {
  return (
    <section className="panel" data-testid="search-results">
      <div className="panel__header search-results__header">
        <div>
          <p className="panel__eyebrow">Suche</p>
          <h3>Treffer fuer &quot;{query}&quot;</h3>
        </div>
        <span className="pill">{items.length} Treffer</span>
      </div>
      <ul className="stack-list">
        {items.map((item) => (
          <li key={item.chunkId} className="stack-list__item stack-list__item--block search-result-card">
            <div className="search-result-card__header">
              <div>
                <Link to={`/documents/${item.documentId}`}>
                  {item.documentTitle}
                </Link>
                <p className="state-card__meta">Version {item.versionNumber} | {item.positionLabel}</p>
              </div>
              <span className="pill">Rank {item.rankLabel}</span>
            </div>
            <p className="search-result-card__preview">{item.textPreview}</p>
            <p className="state-card__meta">Quelle: {item.sourceAnchorLabel}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
