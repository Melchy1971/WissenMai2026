export function ErrorState({ error, actionLabel = '', onAction = null, testId = null }) {
  const visibleAction = actionLabel || error.allowedAction || '';
  return (
    <section
      className="state-card state-card--error"
      {...(testId ? { 'data-testid': testId } : {})}
      data-error-code={error.code}
      data-technical-code={error.technicalCode || error.classification || error.code}
      data-retry={error.retry ? 'true' : 'false'}
      data-log-event={error.logging?.event || ''}
    >
      <h2>{error.title}</h2>
      <p>{error.message}</p>
      <p className="state-card__meta">Fehlercode: {error.code}</p>
      <p className="state-card__meta">Technischer Code: {error.technicalCode || error.classification || error.code}</p>
      {visibleAction ? (
        <p className="state-card__meta">Aktion: {visibleAction}</p>
      ) : null}
      {actionLabel && typeof onAction === 'function' ? (
        <div className="search-bar__actions">
          <button type="button" onClick={onAction}>{actionLabel}</button>
        </div>
      ) : null}
    </section>
  );
}
