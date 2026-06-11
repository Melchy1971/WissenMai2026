export function SettingsSection({ title, description, children, dirty, onSave, saving, saveError, saveSuccess, requiresRestart }) {
  return (
    <section style={{ marginBottom: 32, padding: 24, background: 'var(--color-surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: '700' }}>{title}</h2>
          {description && <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>{description}</p>}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {requiresRestart && <span style={{ background: 'var(--color-warning-bg)', color: 'var(--color-warning-fg)', fontSize: '0.75rem', padding: '2px 8px', borderRadius: 'var(--radius-pill)', fontWeight: '600' }}>⟳ Neustart erforderlich</span>}
          {dirty && <span style={{ background: 'var(--color-info-bg)', color: 'var(--color-info-fg)', fontSize: '0.75rem', padding: '2px 8px', borderRadius: 'var(--radius-pill)' }}>● Nicht gespeichert</span>}
        </div>
      </div>
      <div style={{ marginBottom: 20 }}>{children}</div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button type="button" onClick={onSave} disabled={saving || !dirty}
          style={{ background: dirty ? 'var(--t-magenta)' : 'var(--t-gray-20)', color: dirty ? '#fff' : 'var(--color-text-tertiary)', border: 'none', borderRadius: 4, padding: '8px 20px', cursor: dirty ? 'pointer' : 'default', fontWeight: '600' }}>
          {saving ? 'Wird gespeichert…' : 'Speichern'}
        </button>
        {saveSuccess && <span style={{ color: 'var(--color-success-fg)', fontSize: '0.875rem' }}>✓ Gespeichert</span>}
        {saveError && <span style={{ color: 'var(--color-danger-fg)', fontSize: '0.875rem' }}>✗ {saveError}</span>}
      </div>
    </section>
  );
}
