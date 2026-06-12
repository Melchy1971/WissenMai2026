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

      {/* KI Provider */}
      <SettingsSection title="KI Provider" isDirty={dirty.provider} isSaving={saving.provider}
        onSave={() => save('provider')} saveError={errors['provider._save']} requiresRestart={false}>
        <div className="settings-grid">
          {field('provider', 'model', 'text')}
          {field('provider', 'base_url', 'text')}
          {field('provider', 'timeout_seconds', 'number', { min: 1, max: 300 })}
          {field('provider', 'max_retries', 'number', { min: 0, max: 5 })}
        </div>
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

      {/* Import / Sucheinstellungen */}
      <SettingsSection title="Import / Sucheinstellungen" isDirty={dirty.rag} isSaving={saving.rag}
        onSave={() => save('rag')} saveError={errors['rag._save']} requiresRestart={false}>
        {field('rag', 'chunk_size', 'number', { min: 100, max: 2000 })}
        {field('rag', 'chunk_overlap', 'number', { min: 0 })}
        {field('rag', 'min_score', 'number', { min: 0, max: 1, step: 0.01 })}
        {field('rag', 'max_chunks', 'number', { min: 1, max: 20 })}
      </SettingsSection>

      {/* Benutzerprofil / Darstellung */}
      <SettingsSection title="Benutzerprofil / Darstellung" isDirty={dirty.ui} isSaving={saving.ui}
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
