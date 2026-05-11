export function ErrorState({ error, actionLabel = '', onAction = null }) {
  return (
    <section className="state-card state-card--error">
      <h2>{error.title}</h2>
      <p>{error.message}</p>
      <p className="state-card__meta">Fehlercode: {error.code}</p>
      {actionLabel && typeof onAction === 'function' ? (
        <div className="search-bar__actions">
          <button type="button" onClick={onAction}>{actionLabel}</button>
        </div>
      ) : null}
    </section>
  );
}