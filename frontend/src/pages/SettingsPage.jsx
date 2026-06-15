import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { useViewState } from '../lib/viewState.js';
import { callApi } from '../lib/apiClient.js';
import { LoadingState } from '../components/status/LoadingState.jsx';
import { ErrorState } from '../components/status/ErrorState.jsx';
import { SettingsSection } from '../components/shared/SettingsSection.jsx';
import { SecretInput } from '../components/shared/SecretInput.jsx';
import { diffSettingsSection, validateSettingsPatch } from '../lib/settingsValidation.ts';

const SECTION_DEFS = [
  { key: 'provider', title: 'Provider', fields: [
    ['model', 'text'], ['base_url', 'text'], ['timeout_seconds', 'number'], ['max_retries', 'number'],
  ] },
  { key: 'voice', title: 'Voice', fields: [['enabled', 'checkbox'], ['provider', 'text'], ['language', 'select']] },
  { key: 'security', title: 'Security', fields: [
    ['require_approval_for_high', 'checkbox'], ['block_critical_by_default', 'checkbox'],
    ['audit_all_actions', 'checkbox'], ['source_required', 'checkbox'],
    ['review_queue_required', 'checkbox'], ['validation_pipeline_enabled', 'checkbox'],
    ['rollback_enabled', 'checkbox'], ['plugin_sandbox_enabled', 'checkbox'], ['plugins_enabled', 'checkbox'],
  ] },
  { key: 'governance', title: 'Governance', fields: [
    ['approval_expiry_minutes', 'number'], ['require_two_approvers', 'checkbox'], ['changesets_enabled', 'checkbox'],
  ] },
  { key: 'rag', title: 'RAG', fields: [
    ['chunk_size', 'number'], ['chunk_overlap', 'number'], ['min_score', 'number'], ['max_chunks', 'number'],
  ] },
  { key: 'memory', title: 'Memory', fields: [
    ['max_entries', 'number'], ['decay_rate', 'number'], ['auto_review', 'checkbox'], ['memory_extraction_enabled', 'checkbox'],
  ] },
  { key: 'agents', title: 'Agents', fields: [
    ['max_steps', 'number'], ['max_tool_calls', 'number'], ['max_runtime_seconds', 'number'], ['agents_enabled', 'checkbox'],
  ] },
  { key: 'collaboration', title: 'Collaboration', fields: [
    ['max_agents', 'number'], ['revision_cycles', 'number'], ['collaboration_enabled', 'checkbox'], ['arbitration_enabled', 'checkbox'],
  ] },
  { key: 'ui', title: 'UI', fields: [['dark_mode', 'checkbox'], ['compact_view', 'checkbox'], ['language', 'select']] },
];

function activeRole(auth) {
  return auth.memberships?.find((m) => m.workspace_id === auth.active_workspace_id)?.role || auth.user?.role || 'member';
}

export function SettingsPage() {
  const auth = useAuth();
  const { viewState, setLoading, setSuccess, setError } = useViewState('idle');
  const [settings, setSettings] = useState(null);
  const [original, setOriginal] = useState(null);
  const [dirty, setDirty] = useState({});
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState({});

  const isAdmin = useMemo(() => ['owner', 'admin'].includes(activeRole(auth)), [auth]);

  useEffect(() => { load(); }, []);

  async function load() {
    setLoading();
    const res = await callApi('/api/v1/settings');
    if (!res.ok) { setError(res.error); return; }
    setSettings(res.data);
    setOriginal(JSON.parse(JSON.stringify(res.data)));
    setDirty({});
    setErrors({});
    setSuccess();
  }

  function update(section, key, value) {
    const nextSettings = { ...settings, [section]: { ...(settings[section] || {}), [key]: value } };
    const patch = { [section]: diffSettingsSection(original?.[section] || {}, nextSettings[section]) };
    setSettings(nextSettings);
    setDirty((d) => ({ ...d, [section]: Object.keys(patch[section]).length > 0 }));
    setErrors((current) => {
      const validation = validateSettingsPatch(nextSettings, patch, { isAdmin });
      return { ...current, [`${section}.${key}`]: null, ...validation };
    });
  }

  async function save(section) {
    const sectionPatch = diffSettingsSection(original?.[section] || {}, settings?.[section] || {});
    if (Object.keys(sectionPatch).length === 0) return;
    const patch = { [section]: sectionPatch };
    const validation = validateSettingsPatch(settings, patch, { isAdmin });
    if (Object.keys(validation).length > 0) {
      setErrors((current) => ({ ...current, ...validation }));
      return;
    }
    setSaving((s) => ({ ...s, [section]: true }));
    const res = await callApi('/api/v1/settings', { method: 'PATCH', body: JSON.stringify(patch) });
    setSaving((s) => ({ ...s, [section]: false }));
    if (!res.ok) {
      setErrors((current) => ({ ...current, [`${section}._save`]: res.error.message }));
      return;
    }
    setSettings(res.data);
    setOriginal(JSON.parse(JSON.stringify(res.data)));
    setDirty((d) => ({ ...d, [section]: false }));
  }

  if (viewState.state === 'loading') return <LoadingState label="Einstellungen werden geladen..." />;
  if (viewState.state === 'error') return <ErrorState error={viewState.error} onAction={load} actionLabel="Erneut laden" />;
  if (!settings) return null;

  function field(section, key, type) {
    const value = settings[section]?.[key];
    const err = errors[`${section}.${key}`];
    if (type === 'checkbox') {
      return (
        <label key={key} className="toggle-label">
          <input type="checkbox" checked={!!value} onChange={(e) => update(section, key, e.target.checked)} />
          {key}
          {err ? <span className="validation-error">{err}</span> : null}
        </label>
      );
    }
    if (type === 'select') {
      return (
        <label key={key} className="settings-field__label">{key}
          <select className={`input ${err ? 'input--error' : ''}`} value={value ?? 'de'} onChange={(e) => update(section, key, e.target.value)}>
            <option value="de">Deutsch</option>
            <option value="en">English</option>
          </select>
          {err ? <span className="validation-error">{err}</span> : null}
        </label>
      );
    }
    return (
      <label key={key} className="settings-field__label">{key}
        <input
          type={type}
          className={`input ${err ? 'input--error' : ''}`}
          value={value ?? ''}
          onChange={(e) => update(section, key, type === 'number' ? Number(e.target.value) : e.target.value)}
        />
        {err ? <span className="validation-error">{err}</span> : null}
      </label>
    );
  }

  return (
    <div className="page" data-testid="settings-page">
      <h1 className="page__title">Einstellungen</h1>

      {SECTION_DEFS.map((section) => (
        <SettingsSection
          key={section.key}
          title={section.title}
          isDirty={dirty[section.key]}
          isSaving={saving[section.key]}
          onSave={() => save(section.key)}
          saveError={errors[`${section.key}._save`]}
          requiresRestart={false}
        >
          <div className="settings-grid">
            {section.fields.map(([key, type]) => field(section.key, key, type))}
          </div>
          {section.key === 'provider' ? (
            <div className="settings-field">
              <label className="settings-field__label">Provider Secret</label>
              <SecretInput
                fieldKey="provider.api_key"
                onUpdate={async (val) => {
                  const res = await callApi('/api/v1/settings/secrets', {
                    method: 'PATCH',
                    body: JSON.stringify({ key: 'provider.api_key', value: val }),
                  });
                  if (!res.ok) setErrors((current) => ({ ...current, 'provider._save': res.error.message }));
                }}
              />
            </div>
          ) : null}
        </SettingsSection>
      ))}
    </div>
  );
}
