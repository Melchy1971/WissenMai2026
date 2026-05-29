export function StatusBadge({ status, testId }) {
  return (
    <span
      className={`status-badge status-badge--${status.tone}`}
      {...(testId ? { 'data-testid': testId } : {})}
    >
      {status.label}
    </span>
  );
}