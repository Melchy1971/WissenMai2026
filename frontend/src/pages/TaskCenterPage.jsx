import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';

const STATUS_OPTIONS = ['pending', 'in_progress', 'completed', 'cancelled'];
const PRIORITY_OPTIONS = ['low', 'medium', 'high', 'critical'];

export function TaskCenterPage() {
  const { viewState, setLoading, setSuccess, setError, setEmpty } = useViewState('idle');
  const [tasks, setTasks] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ title: '', description: '', priority: 'medium', assigned_agent: '' });

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const res = await callApi('/api/v1/tasks');
    if (!res.ok) { setError(res.error); return; }
    const items = res.data?.items ?? [];
    if (!items.length) { setEmpty(); return; }
    setTasks(items);
    setSuccess();
  }

  async function createTask(e) {
    e.preventDefault();
    const res = await callApi('/api/v1/tasks', { method: 'POST', body: JSON.stringify(form) });
    if (!res.ok) { alert(res.error.message); return; }
    setForm({ title: '', description: '', priority: 'medium', assigned_agent: '' });
    setShowForm(false);
    load();
  }

  async function updateStatus(taskId, status) {
    const res = await callApi(`/api/v1/tasks/${taskId}`, { method: 'PATCH', body: JSON.stringify({ status }) });
    if (!res.ok) { alert(res.error.message); return; }
    load();
  }

  if (viewState.state === 'loading') return <LoadingState label="Tasks werden geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="task-center-page">
      <div className="page__header-row">
        <h1 className="page__title">Task Center</h1>
        <button type="button" className="button-primary" onClick={() => setShowForm(v => !v)}>
          {showForm ? 'Abbrechen' : '+ Neuer Task'}
        </button>
      </div>

      {showForm && (
        <form className="form-card" onSubmit={createTask} data-testid="task-create-form">
          <div className="form-row">
            <label>Titel
              <input required className="input" value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
            </label>
          </div>
          <div className="form-row">
            <label>Beschreibung
              <textarea className="input" value={form.description}
                onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </label>
          </div>
          <div className="form-row form-row--inline">
            <label>Priorität
              <select className="input" value={form.priority}
                onChange={e => setForm(f => ({ ...f, priority: e.target.value }))}>
                {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </label>
            <label>Agent
              <input className="input" value={form.assigned_agent}
                onChange={e => setForm(f => ({ ...f, assigned_agent: e.target.value }))} />
            </label>
          </div>
          <button type="submit" className="button-primary">Task erstellen</button>
        </form>
      )}

      {viewState.state === 'empty' && tasks.length === 0
        ? <EmptyState label="Keine Tasks vorhanden." />
        : (
          <section className="page__section">
            <table className="data-table" data-testid="tasks-table">
              <thead>
                <tr><th>Titel</th><th>Priorität</th><th>Agent</th><th>Status</th><th>Aktion</th></tr>
              </thead>
              <tbody>
                {tasks.map(t => (
                  <tr key={t.id}>
                    <td><strong>{t.title}</strong><br /><small>{t.description}</small></td>
                    <td><span className={`badge badge--${t.priority === 'critical' ? 'danger' : t.priority === 'high' ? 'warning' : 'neutral'}`}>{t.priority}</span></td>
                    <td>{t.assigned_agent || '—'}</td>
                    <td>{t.status}</td>
                    <td>
                      <select className="input input--sm" value={t.status}
                        onChange={e => updateStatus(t.id, e.target.value)}>
                        {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
    </div>
  );
}
