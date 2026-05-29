export function LoadingState({ label = 'Lade Daten...', testId = null }) {
  return <div className="state-card" {...(testId ? { 'data-testid': testId } : {})}>{label}</div>;
}
