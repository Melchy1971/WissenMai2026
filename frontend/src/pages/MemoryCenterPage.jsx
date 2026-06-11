import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { MemoryScoreCard } from '../components/shared/MemoryScoreCard.jsx';

export function MemoryCenterPage() {
  const { viewState, setLoading, setSuccess, setError, setEmpty } = useViewState('idle');
  const [memories, setMemories] = useState([]);
  const [reviewQueue, setReviewQueue] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const [memRes, revRes, conRes] = await Promise.all([
      callApi('/api/v1/memory'),
      callApi('/api/v1/memory/review-queue'),
      callApi('/api/v1/memory/conflicts'),
    ]);
    if (!memRes.ok) { setError(memRes.error); return; }
    const items = memRes.data?.items ?? [];
    if (!items.length) { setEmpty(); return; }
    setMemories(items);
    setReviewQueue(revRes.ok ? (revRes.data?.items ?? []) : []);
    setConflicts(conRes.ok ? (conRes.data?.items ?? []) : []);
    setSuccess();
  }

  async function handleSearch(e) {
    e.preventDefault();
    if (!search.trim()) return;
    const res = await callApi(`/api/v1/memory/search?q=${encodeURIComponent(search)}`);
    if (!res.ok) { alert(res.error.message); return; }
    setMemories(res.data?.items ?? []);
  }

  // Secrets werden niemals angezeigt – Filterung auf API-Seite; hier nur Anzeige
  const visibleMemories = memories.filter(m => m.classification !== 'SECRET');

  if (viewState.state === 'loading') return <LoadingState label="Memory wird geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;
  if (viewState.state === 'empty') return <EmptyState label="Keine Memory-Einträge vorhanden." />;

  return (
    <div className="page" data-testid="memory-center-page">
      <h1 className="page__title">Memory Center</h1>

      <section className="page__section">
        <form className="search-bar" onSubmit={handleSearch}>
          <input
            type="text"
            placeholder="Memory durchsuchen…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input"
            data-testid="memory-search-input"
          />
          <button type="submit" className="button-primary">Suchen</button>
        </form>
      </section>

      {conflicts.length > 0 && (
        <section className="page__section">
          <h2>Konflikte ({conflicts.length})</h2>
          <ul data-testid="memory-conflicts">
            {conflicts.map(c => (
              <li key={c.id} className="list-item list-item--warning">
                <strong>{c.key}</strong>: {c.description}
              </li>
            ))}
          </ul>
        </section>
      )}

      {reviewQueue.length > 0 && (
        <section className="page__section">
          <h2>Review-Queue ({reviewQueue.length})</h2>
          <ul data-testid="memory-review-queue">
            {reviewQueue.map(m => (
              <li key={m.id} className="list-item">
                <MemoryScoreCard memory={m} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="page__section">
        <h2>Memory-Einträge ({visibleMemories.length})</h2>
        <ul data-testid="memory-list">
          {visibleMemories.map(m => (
            <li key={m.id} className="list-item">
              <MemoryScoreCard memory={m} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
