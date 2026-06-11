export function PrivacyModeBanner({ enabled, onToggle }) {
  if (!enabled) return null;
  return (
    <div
      data-testid="privacy-mode-banner"
      style={{ background: 'var(--t-magenta)', color: '#fff', padding: '8px 16px',
               textAlign: 'center', fontWeight: '600', fontSize: '0.875rem' }}
    >
      🔒 PRIVACY MODE AKTIV – Keine Persistenz
      {onToggle && (
        <button
          type="button"
          onClick={onToggle}
          style={{ marginLeft: 16, background: 'rgba(255,255,255,0.2)', border: 'none',
                   color: '#fff', cursor: 'pointer', padding: '2px 10px', borderRadius: 4 }}
        >
          Deaktivieren
        </button>
      )}
    </div>
  );
}
