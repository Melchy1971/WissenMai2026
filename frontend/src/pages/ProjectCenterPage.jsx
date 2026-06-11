import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';

export function ProjectCenterPage() {
  const { viewState, setLoading, setSuccess, setError, setEmpty } = useViewState('idle');
  const [projects, setProjects] = useState([]);
  const [selected, setSelected] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', description: '' });

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const res = await callApi('/api/v1/projects');
    if (!res.ok) { setError(res.error); return; }
    const items = res.data?.items ?? [];
    if (!items.length) { setEmpty(); return; }
    setProjects(items);
    setSuccess();
  }

  async function loadDetail(id) {
    const res = await callApi(`/api/v1/projects/${id}`);
    if (!res.ok) { alert(res.error.message); return; }
    setSelected(res.data);
  }

  async function createProject(e) {
    e.preventDefault();
    const res = await callApi('/api/v1/projects', { method: 'POST', body: JSON.stringify(form) });
    if (!res.ok) { alert(res.error.message); return; }
    setForm({ name: '', description: '' });
    setShowForm(false);
    load();
  }

  if (viewState.state === 'loading') return <LoadingState label="Projekte werden geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="project-center-page">
      <div className="page__header-row">
        <h1 className="page__title">Project Center</h1>
        <button type="button" className="button-primary" onClick={() => { setShowForm(v => !v); setSelected(null); }}>
          {showForm ? 'Abbrechen' : '+ Neues Projekt'}
        </button>
      </div>

      {showForm && (
        <form className="form-card" onSubmit={createProject} data-testid="project-create-form">
          <label>Name <input required className="input" value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))} /></label>
          <label>Beschreibung <textarea className="input" value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))} /></label>
          <button type="submit" className="button-primary">Erstellen</button>
        </form>
      )}

      <div className="split-layout">
        <aside className="split-layout__list">
          {viewState.state === 'empty' && projects.length === 0
            ? <EmptyState label="Keine Projekte." />
            : (
              <ul data-testid="projects-list">
                {projects.map(p => (
                  <li key={p.id}
                    className={`list-item list-item--clickable ${selected?.id === p.id ? 'list-item--active' : ''}`}
                    onClick={() => loadDetail(p.id)}
                  >
                    <strong>{p.name}</strong>
                    <small>{p.description}</small>
                  </li>
                ))}
              </ul>
            )}
        </aside>

        <main className="split-layout__detail">
          {selected ? (
            <div data-testid="project-detail">
              <h2>{selected.name}</h2>
              <p>{selected.description}</p>
              {selected.tasks?.length > 0 && (
                <><h3>Tasks</h3><ul>{selected.tasks.map(t => <li key={t.id}>{t.title} — {t.status}</li>)}</ul></>
              )}
              {selected.memories?.length > 0 && (
                <><h3>Memories</h3><ul>{selected.memories.map(m => <li key={m.id}>{m.key}</li>)}</ul></>
              )}
              {selected.documents?.length > 0 && (
                <><h3>Dokumente</h3><ul>{selected.documents.map(d => <li key={d.id}>{d.title}</li>)}</ul></>
              )}
            </div>
          ) : (
            <p className="text-muted">Projekt auswählen.</p>
          )}
        </main>
      </div>
    </div>
  );
}
