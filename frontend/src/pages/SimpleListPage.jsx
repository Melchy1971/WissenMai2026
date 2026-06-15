import { useEffect, useState } from 'react';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { EmptyState } from '../components/status/EmptyState.jsx';
import { VirtualizedTable } from '../components/shared/VirtualizedTable.jsx';

export function SimpleListPage({ title, endpoint, testId }) {
  const [state, setState] = useState({ status: 'loading', items: [], error: null });

  async function load() {
    setState({ status: 'loading', items: [], error: null });
    const res = await callApi(endpoint);
    if (!res.ok) {
      setState({ status: 'error', items: [], error: res.error });
      return;
    }
    setState({ status: 'success', items: res.data?.items ?? [], error: null });
  }

  useEffect(() => { load(); }, [endpoint]);

  if (state.status === 'loading') return <LoadingState label={`${title} wird geladen...`} />;
  if (state.status === 'error') return <ErrorState error={state.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid={testId}>
      <h1 className="page__title">{title}</h1>
      {state.items.length === 0 ? (
        <EmptyState title={`Keine ${title}-Daten`} message="Fuer diesen Workspace sind keine Eintraege vorhanden." />
      ) : (
        <VirtualizedTable
          items={state.items}
          columns={[
            { key: 'id', label: 'ID', render: (item) => item.name || item.title || item.id },
            { key: 'status', label: 'Status', render: (item) => item.status || '-' },
          ]}
        />
      )}
    </div>
  );
}
