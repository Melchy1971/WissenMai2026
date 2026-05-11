const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const AUTH_TOKEN_STORAGE_KEY = 'wissen.authToken';
const WORKSPACE_ID_STORAGE_KEY = 'wissen.workspaceId';
const DEFAULT_TIMEOUT_MS = 15000;
const memoryRequestContext = new Map();

function getStorage() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null;
  }

  const storage = window.localStorage;
  if (typeof storage.getItem !== 'function' || typeof storage.setItem !== 'function' || typeof storage.removeItem !== 'function') {
    return null;
  }

  return storage;
}

function readStoredValue(key, fallback = '') {
  const storage = getStorage();
  if (storage) {
    return storage.getItem(key) || fallback;
  }

  return memoryRequestContext.get(key) || fallback;
}

export function getApiRequestContext() {
  const authToken = readStoredValue(AUTH_TOKEN_STORAGE_KEY, import.meta.env.VITE_AUTH_TOKEN || '');
  const workspaceId = readStoredValue(WORKSPACE_ID_STORAGE_KEY);

  return {
    authToken: authToken.trim(),
    workspaceId: workspaceId.trim(),
  };
}

export function setApiRequestContext({ authToken = '', workspaceId = '' }) {
  const storage = getStorage();

  if (authToken.trim()) {
    if (storage) {
      storage.setItem(AUTH_TOKEN_STORAGE_KEY, authToken.trim());
    }
    memoryRequestContext.set(AUTH_TOKEN_STORAGE_KEY, authToken.trim());
  } else {
    if (storage) {
      storage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    }
    memoryRequestContext.delete(AUTH_TOKEN_STORAGE_KEY);
  }

  if (workspaceId.trim()) {
    if (storage) {
      storage.setItem(WORKSPACE_ID_STORAGE_KEY, workspaceId.trim());
    }
    memoryRequestContext.set(WORKSPACE_ID_STORAGE_KEY, workspaceId.trim());
  } else {
    if (storage) {
      storage.removeItem(WORKSPACE_ID_STORAGE_KEY);
    }
    memoryRequestContext.delete(WORKSPACE_ID_STORAGE_KEY);
  }
}

function buildRequestHeaders(optionsHeaders = {}) {
  const requestContext = getApiRequestContext();
  const headers = {
    Accept: 'application/json',
    ...optionsHeaders,
  };

  if (requestContext.authToken && !headers.Authorization) {
    headers.Authorization = `Bearer ${requestContext.authToken}`;
  }
  if (requestContext.workspaceId && !headers['X-Workspace-Id']) {
    headers['X-Workspace-Id'] = requestContext.workspaceId;
  }

  return headers;
}

export class ApiClientError extends Error {
  constructor({ code, message, details, status }) {
    super(message || 'API request failed');
    this.name = 'ApiClientError';
    this.code = code || 'UNKNOWN_ERROR';
    this.details = details || {};
    this.status = status ?? null;
  }
}

function classifyFetchFailure(error, { timedOut = false } = {}) {
  const message = error instanceof Error ? error.message : String(error);
  const normalizedMessage = message.toLowerCase();

  if (timedOut || error?.name === 'AbortError' || normalizedMessage.includes('timeout')) {
    return {
      code: 'TIMEOUT',
      message: 'Die Anfrage hat zu lange gedauert.',
    };
  }

  if (normalizedMessage.includes('cors') || normalizedMessage.includes('access-control')) {
    return {
      code: 'CORS_ERROR',
      message: 'Der Browser hat die Anfrage wegen CORS blockiert.',
    };
  }

  return {
    code: 'API_UNREACHABLE',
    message: 'Backend nicht erreichbar oder Netzwerkfehler.',
  };
}

function classifyHttpFailure(response, errorPayload) {
  if (response.status === 401) {
    return {
      code: 'AUTH_REQUIRED',
      message: errorPayload?.message || 'Authentifizierung erforderlich.',
    };
  }

  if (errorPayload?.code === 'WORKSPACE_REQUIRED' || errorPayload?.code === 'WORKSPACE_NOT_CONFIGURED') {
    return {
      code: 'WORKSPACE_NOT_CONFIGURED',
      message: errorPayload?.message || 'Kein aktiver Workspace konfiguriert.',
    };
  }

  if (errorPayload?.code === 'WORKSPACE_ACCESS_FORBIDDEN') {
    return {
      code: 'FORBIDDEN',
      message: errorPayload?.message || 'Workspace-Zugriff verweigert.',
    };
  }

  if (response.status === 403) {
    return {
      code: 'FORBIDDEN',
      message: errorPayload?.message || 'Zugriff verweigert.',
    };
  }

  return {
    code: errorPayload?.code || (response.status === 503 ? 'SERVICE_UNAVAILABLE' : 'HTTP_ERROR'),
    message: errorPayload?.message || response.statusText || 'API request failed',
  };
}

export async function requestJson(path, options = {}) {
  let response;
  const {
    headers: optionHeaders = {},
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal: optionSignal,
    ...requestOptions
  } = options;
  const controller = typeof AbortController !== 'undefined' && !optionSignal ? new AbortController() : null;
  let timedOut = false;
  const timeoutId = controller && timeoutMs > 0
    ? setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, timeoutMs)
    : null;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      headers: buildRequestHeaders(optionHeaders),
      signal: optionSignal || controller?.signal,
    });
  } catch (error) {
    const classified = classifyFetchFailure(error, { timedOut });
    throw new ApiClientError({
      code: classified.code,
      message: classified.message,
      details: { cause: error instanceof Error ? error.message : String(error) },
      status: null,
    });
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    const errorPayload = payload?.error;
    const classified = classifyHttpFailure(response, errorPayload);
    throw new ApiClientError({
      code: classified.code,
      message: classified.message,
      details: errorPayload?.details || {},
      status: response.status,
    });
  }

  return payload;
}
