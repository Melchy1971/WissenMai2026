import { useState } from 'react';

export function SecretInput({ label, status, onUpdate, testId }) {
  const [editing, setEditing] = useState(false);
  const [newValue, setNewValue] = useState('');

  function handleSubmit() {
    if (newValue.trim()) {
      onUpdate?.(newValue.trim());
    }
    setNewValue('');
    setEditing(false);
  }

  return (
    <div data-testid={testId || 'secret-input'} style={{ fontSize: '0.875rem' }}>
      <label style={{ fontWeight: '600', display: 'block', marginBottom: 6 }}>{label}</label>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <span style={{ fontFamily: 'monospace', color: status === 'present' ? 'var(--color-success-fg)' : 'var(--color-text-tertiary)', userSelect: 'none' }}>
          {status === 'present' ? '●●●●●●●●' : '[nicht gesetzt]'}
        </span>
        <span style={{ fontSize: '0.75rem', padding: '2px 8px', borderRadius: 'var(--radius-pill)',
                       background: status === 'present' ? 'var(--color-success-bg)' : 'var(--color-neutral-bg)',
                       color: status === 'present' ? 'var(--color-success-fg)' : 'var(--color-text-secondary)' }}>
          {status === 'present' ? 'vorhanden' : 'nicht gesetzt'}
        </span>
        {!editing && <button type="button" onClick={() => setEditing(true)} style={{ background: 'none', border: '1px solid var(--color-border)', borderRadius: 4, padding: '2px 10px', cursor: 'pointer', fontSize: '0.8rem' }}>Aktualisieren</button>}
      </div>
      {editing && (
        <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
          <input
            type="password"
            value={newValue}
            onChange={e => setNewValue(e.target.value)}
            placeholder="Neuen Wert eingeben..."
            autoComplete="new-password"
            style={{ flex: 1, border: '1px solid var(--color-border)', borderRadius: 4, padding: '4px 8px', fontFamily: 'monospace' }}
          />
          <button type="button" onClick={handleSubmit} style={{ background: 'var(--t-magenta)', color: '#fff', border: 'none', borderRadius: 4, padding: '4px 12px', cursor: 'pointer' }}>Senden</button>
          <button type="button" onClick={() => { setEditing(false); setNewValue(''); }} style={{ background: 'none', border: '1px solid var(--color-border)', borderRadius: 4, padding: '4px 8px', cursor: 'pointer' }}>Abbrechen</button>
        </div>
      )}
    </div>
  );
}
