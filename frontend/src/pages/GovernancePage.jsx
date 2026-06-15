import { useEffect, useState } from 'react';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';

function RiskBadge({ level }) {
  return <span className={`status-badge status-badge--${level === 'CRITICAL' ? 'danger' : 'warning'}`}>{level}</span>;
}

export function GovernancePage() {
  const [state, setState] = useState({ status: 'loading', data: null, error: null });
  const [message, setMessage] = useState('');

  async function load() {
    setState({ status: 'loading', data: null, error: null });
    const res = await callApi('/api/v1/governance/status');
    if (!res.ok) setState({ status: 'error', data: null, error: res.error });
    else setState({ status: 'success', data: res.data, error: null });
  }

  useEffect(() => { load(); }, []);

  async function requestPrivacyToggle() {
    const res = await callApi('/api/v1/governance/privacy-mode', {
      method: 'PATCH',
      body: JSON.stringify({ enabled: !state.data?.privacy_mode, reason: 'ui_toggle' }),
    });
    if (!res.ok) setState({ status: 'error', data: null, error: res.error });
    else setMessage(`Approval erforderlich: ${res.data.approval_id}`);
  }

  if (state.status === 'loading') return <LoadingState label="Governance wird geladen..." />;
  if (state.status === 'error') return <ErrorState error={state.error} onAction={load} actionLabel="Erneut laden" />;

  return (
    <div className="page" data-testid="governance-page">
      <h1 className="page__title">Governance</h1>
      <section className="page__section">
        <h2>Privacy Mode</h2>
        <p>Aktueller Status: {state.data?.privacy_mode ? 'aktiv' : 'inaktiv'}</p>
        <p className="state-card__meta">Folge: Schreibende Persistenz wird eingeschraenkt.</p>
        <RiskBadge level="HIGH" />
        <button type="button" onClick={requestPrivacyToggle}>Approval anfordern</button>
        {message ? <p className="state-card__meta">{message}</p> : null}
      </section>
    </div>
  );
}
