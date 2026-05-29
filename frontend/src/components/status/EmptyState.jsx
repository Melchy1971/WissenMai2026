export function EmptyState({ title, message, testId = null }) {
  return (
    <section className="state-card" {...(testId ? { 'data-testid': testId } : {})}>
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}
