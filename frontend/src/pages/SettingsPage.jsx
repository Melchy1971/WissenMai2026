import { useEffect, useState } from 'react';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { SettingsSection } from '../components/shared/SettingsSection.jsx';
import { SecretInput } from '../components/shared/SecretInput.jsx';

// Validation helpers
function clamp(val, min, max) { const n = Number(val); return n >= min && n <= max; }

export function SettingsPage() {
  const { viewState, setLoading, setSuccess, setError } = useViewState('idle');
  const [settings, setSettings] = useState(null);
  const [dirty, setDirty] = useState({});
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState({});

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const res = await callApi('/api/v1/settings');
    if (!res.ok) { setError(res.error); return; }
    setSettings(res.data);
    setSuccess();
  }

  function update(section, key, value) {
    setSettings(s => ({ ...s, [section]: { ...s[section], [key]: value } }));
    setDirty(d => ({ ...d, [section]: true }));
    setErrors(e => ({ ...e, [`${section}.${key}`]: null }));
  }

  function validate(section, data) {
    const errs = {};
    if (section === 'provider') {
      if (!clamp(data.timeout_seconds, 1, 300)) errs['provider.timeout_seconds'] = '1–300 s';
      if (!clamp(data.max_retries, 0, 5)) errs['provider.max_retries'] = '0–5';
    }
    if (section === 'rag') {
      if (!clamp(data.chunk_size, 100, 2000)) errs['rag.chunk_size'] = '100–2000';
      if (Number(data.chunk_overlap) >= Number(data.chunk_size)) errs['rag.chunk_overlap'] = 'Overlap < chunk_size';
      if (!clamp(data.min_score, 0.0, 1.0)) errs['rag.min_score'] = '0.0–1.0';
      if (!clamp(data.max_chunks, 1, 20)) errs['rag.max_chunks'] = '1–20';
    }
    if (section === 'agents') {
      if (!clamp(data.max_steps, 1, 100)) errs['agents.max_steps'] = '1–100';
      if (!clamp(data.max_tool_calls, 0, 50)) errs['agents.max_tool_calls'] = '0–50';
      if (!clamp(data.max_runtime_seconds, 1, 3600)) errs['agents.max_runtime_seconds'] = '1–3600 s';
    }
    if (section === 'collaboration') {
      if (!clamp(data.max_agents, 1, 10)) errs['collaboration.max_agents'] = '1–10';
      if (!clamp(data.revision_cycles, 0, 10)) errs['collaboration.revision_cycles'] = '0–10';
    }
    if (section === 'governance') {
      if (!clamp(data.approval_expiry_minutes, 1, 1440)) errs['governance.approval_expiry_minutes'] = '1–1440 min';
    }
    return errs;
  }

  async function save(section) {
    const data = settings[section];
    const errs = validate(section, data);
    if (Object.keys(errs).length) { setErrors(e => ({ ...e, ...errs })); return; }
    setSaving(s => ({ ...s, [section]: true }));
    const res = await callApi('/api/v1/settings', {
      method: 'PATCH',
      body: JSON.stringify({ [section]: data }),
    });
    setSaving(s => ({ ...s, [section]: false }));
    if (!res.ok) { setErrors(e => ({ ...e, [`${section}._save`]: res.error.message })); return; }
    setDirty(d => ({ ...d, [section]: false }));
  }

  if (viewState.state === 'loading') return <LoadingState label="Einstellungen werden geladen…" />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;
  if (!settings) return null;

  const field = (section, key, type = 'text', props = {}) => {
    const errKey = `${section}.${key}`;
    return (
      <div className="settings-field" key={errKey}>
        <label className="settings-field__label">{key}
          <input
            type={type}
            className={`input ${errors[errKey] ? 'input--error' : ''}`}
            value={settings[section]?.[key] ?? ''}
            onChange={e => update(section, key, type === 'number' ? e.target.value : e.target.value)}
            {...props}
          />
          {errors[errKey] && <span className="validation-error">{errors[errKey]}</span>}
        </label>
      </div>
    );
  };

  const toggle = (section, key, label) => (
    <div className="settings-field" key={`${section}.${key}`}>
      <label className="toggle-label">
        <input type="checkbox"
          checked={!!settings[section]?.[key]}
          onChange={e => update(section, key, e.target.checked)} />
        {label}
      </label>
    </div>
  );

  return (
    <div className="page" data-testid="settings-page">
      <h1 className="page__title">Einstellungen</h1>

      {/* Provider */}
      <SettingsSection title="Provider" isDirty={dirty.provider} isSaving={saving.provider}
        onSave={() => save('provider')} saveError={errors['provider._save']} requiresRestart={false}>
        <div className="settings-grid">
          {field('provider', 'model', 'text')}
          {field('provider', 'base_url', 'text')}
          {field('provider', 'timeout_seconds', 'number', { min: 1, max: 300 })}
          {field('provider', 'max_retries', 'number', { min: 0, max: 5 })}
        </div>
        {/* API-Key: Secret – nie im Klartext anzeigen */}
        <div className="settings-field">
          <label className="settings-field__label">api_key</label>
          <SecretInput
            fieldKey="provider.api_key"
            onUpdate={async (val) => {
              const res = await callApi('/api/v1/settings/secrets', {
                method: 'PATCH',
                body: JSON.stringify({ key: 'provider.api_key', value: val }),
              });
              if (!res.ok) alert(res.error.message);
            }}
          />
        </div>
      </SettingsSection>

      {/* Voice */}
      <SettingsSection title="Voice" isDirty={dirty.voice} isSaving={saving.voice}
        onSave={() => save('voice')} saveError={errors['voice._save']} requiresRestart={false}>
        {toggle('voice', 'enabled', 'Voice aktiviert')}
        {field('voice', 'provider', 'text')}
        {field('voice', 'language', 'text')}
      </SettingsSection>

      {/* Security */}
      <SettingsSection title="Security" isDirty={dirty.security} isSaving={saving.security}
        onSave={() => save('security')} saveError={errors['security._save']} requiresRestart={true}>
        {toggle('security', 'require_approval_for_high', 'Approval für HIGH-Aktionen')}
        {toggle('security', 'block_critical_by_default', 'CRITICAL-Aktionen blockieren')}
        {toggle('security', 'audit_all_actions', 'Alle Aktionen auditieren')}
      </SettingsSection>

      {/* Governance */}
      <SettingsSection title="Governance" isDirty={dirty.governance} isSaving={saving.governance}
        onSave={() => save('governance')} saveError={errors['governance._save']} requiresRestart={false}>
        {field('governance', 'approval_expiry_minutes', 'number', { min: 1, max: 1440 })}
        {toggle('governance', 'require_two_approvers', 'Zwei Genehmiger erforderlich')}
      </SettingsSection>

      {/* RAG */}
      <SettingsSection title="RAG" isDirty={dirty.rag} isSaving={saving.rag}
        onSave={() => save('rag')} saveError={errors['rag._save']} requiresRestart={false}>
        {field('rag', 'chunk_size', 'number', { min: 100, max: 2000 })}
        {field('rag', 'chunk_overlap', 'number', { min: 0 })}
        {field('rag', 'min_score', 'number', { min: 0, max: 1, step: 0.01 })}
        {field('rag', 'max_chunks', 'number', { min: 1, max: 20 })}
      </SettingsSection>

      {/* Memory */}
      <SettingsSection title="Memory" isDirty={dirty.memory} isSaving={saving.memory}
        onSave={() => save('memory')} saveError={errors['memory._save']} requiresRestart={false}>
        {field('memory', 'max_entries', 'number')}
        {field('memory', 'decay_rate', 'number', { min: 0, max: 1, step: 0.01 })}
        {toggle('memory', 'auto_review', 'Automatische Review-Queue')}
      </SettingsSection>

      {/* Agents */}
      <SettingsSection title="Agents" isDirty={dirty.agents} isSaving={saving.agents}
        onSave={() => save('agents')} saveError={errors['agents._save']} requiresRestart={false}>
        {field('agents', 'max_steps', 'number', { min: 1, max: 100 })}
        {field('agents', 'max_tool_calls', 'number', { min: 0, max: 50 })}
        {field('agents', 'max_runtime_seconds', 'number', { min: 1, max: 3600 })}
      </SettingsSection>

      {/* Collaboration */}
      <SettingsSection title="Collaboration" isDirty={dirty.collaboration} isSaving={saving.collaboration}
        onSave={() => save('collaboration')} saveError={errors['collaboration._save']} requiresRestart={false}>
        {field('collaboration', 'max_agents', 'number', { min: 1, max: 10 })}
        {field('collaboration', 'revision_cycles', 'number', { min: 0, max: 10 })}
      </SettingsSection>

      {/* UI */}
      <SettingsSection title="UI" isDirty={dirty.ui} isSaving={saving.ui}
        onSave={() => save('ui')} saveError={errors['ui._save']} requiresRestart={false}>
        {toggle('ui', 'dark_mode', 'Dark Mode')}
        {toggle('ui', 'compact_view', 'Kompaktansicht')}
        <div className="settings-field">
          <label>Sprache
            <select className="input"
              value={settings.ui?.language ?? 'de'}
              onChange={e => update('ui', 'language', e.target.value)}>
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
      </SettingsSection>
    </div>
  );
}
