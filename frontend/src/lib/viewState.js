import { useState } from 'react';

// States: idle | loading | streaming | success | warning | error | blocked | unauthorized | empty
export function useViewState(initial = 'idle') {
  const [viewState, setViewState] = useState({ state: initial, error: null, data: null });

  return {
    viewState,
    setLoading: () => setViewState({ state: 'loading', error: null, data: null }),
    setSuccess: (data = null) => setViewState({ state: 'success', error: null, data }),
    setError: (error) => setViewState({ state: 'error', error: error || { code: 'UNKNOWN_ERROR', message: 'Unbekannter Fehler' }, data: null }),
    setEmpty: () => setViewState({ state: 'empty', error: null, data: null }),
    setBlocked: (reason) => setViewState({ state: 'blocked', error: { code: 'BLOCKED', message: reason || 'Aktion blockiert' }, data: null }),
    setStreaming: () => setViewState({ state: 'streaming', error: null, data: null }),
    setWarning: (msg) => setViewState({ state: 'warning', error: null, data: msg }),
    setUnauthorized: () => setViewState({ state: 'unauthorized', error: { code: 'AUTH_REQUIRED', message: 'Nicht autorisiert' }, data: null }),
    reset: () => setViewState({ state: initial, error: null, data: null }),
  };
}
