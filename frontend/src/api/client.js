const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const AUTH_TOKEN_STORAGE_KEY = 'wissen.authToken';
const WORKSPACE_ID_STORAGE_KEY = 'wissen.workspaceId';
const DEFAULT_TIMEOUT_MS = 15000;
const memoryRequestContext = new Map();
const CENTRAL_HEADER_NAMES = new Set(['authorization', 'x-workspace-id']);

let _onAuthRequired = null;

export function setOnAuthRequired(callback) {
  _onAuthRequired = typeof callback === 'function' ? callback : null;
}

function getStorage() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return null;
  }
  const storage = window.localStorage;
  if (
    typeof storage.getItem !== 'function' ||
    typeof storage.setItem !== 'function' ||
    typeof storage.removeItem !== 'function'
  ) {
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
    if (storage) storage.setItem(AUTH_TOKEN_STORAGE_KEY, authToken.trim());
    memoryRequestContext.set(AUTH_TOKEN_STORAGE_KEY, authToken.trim());
  } else {
    if (storage) storage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    memoryRequestContext.delete(AUTH_TOKEN_STORAGE_KEY);
  }

  if (workspaceId.trim()) {
    if (storage) storage.setItem(WORKSPACE_ID_STORAGE_KEY, workspaceId.trim());
    memoryRequestContext.set(WORKSPACE_ID_STORAGE_KEY, workspaceId.trim());
  } else {
    if (storage) storage.removeItem(WORKSPACE_ID_STORAGE_KEY);
    memoryRequestContext.delete(WORKSPACE_ID_STORAGE_KEY);
  }
}

/**
 * Builds final request headers.
 * - Authorization and X-Workspace-Id are always sourced from central context.
 *   Any caller-provided values for these two keys are silently discarded.
 * - Content-Type is auto-inferred as application/json when body is a string
 *   and the caller has not set Content-Type explicitly.
 * - correlationId is injected as X-Correlation-Id when provided.
 */
function normalizeHeaders(headersInit = {}) {
  if (headersInit instanceof Headers) {
    return Object.fromEntries(headersInit.entries());
  }
  if (Array.isArray(headersInit)) {
    return Object.fromEntries(headersInit);
  }
  return { ...headersInit };
}

function removeCentralHeaders(headers) {
  for (const headerName of Object.keys(headers)) {
    if (CENTRAL_HEADER_NAMES.has(headerName.toLowerCase())) {
      delete headers[headerName];
    }
  }
}

function hasHeader(headers, name) {
  const normalizedName = name.toLowerCase();
  return Object.keys(headers).some((headerName) => headerName.toLowerCase() === normalizedName);
}

function buildRequestHeaders(optionsHeaders = {}, body, correlationId) {
  const requestContext = getApiRequestContext();

  const headers = {
    Accept: 'application/json',
    ...normalizeHeaders(optionsHeaders),
  };

  // Remove caller-provided auth/workspace headers — they must come from context only.
  removeCentralHeaders(headers);

  // Auto-infer Content-Type for JSON string bodies.
  if (typeof body === 'string' && !hasHeader(headers, 'Content-Type')) {
    headers['Content-Type'] = 'application/json';
  }

  // Inject from central context.
  if (requestContext.authToken) {
    headers.Authorization = `Bearer ${requestContext.authToken}`;
  }
  if (requestContext.workspaceId) {
    headers['X-Workspace-Id'] = requestContext.workspaceId;
  }

  // Optional correlation id for distributed tracing.
  if (correlationId != null && correlationId !== '') {
    headers['X-Correlation-Id'] = String(correlationId);
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
    return { code: 'TIMEOUT', message: 'Die Anfrage hat zu lange gedauert.' };
  }

  return { code: 'API_UNREACHABLE', message: 'Backend nicht erreichbar oder Netzwerkfehler.' };
}

function classifyHttpFailure(response, errorPayload) {
  if (response.status === 401) {
    return { code: 'AUTH_REQUIRED', message: errorPayload?.message || 'Authentifizierung erforderlich.' };
  }

  if (
    errorPayload?.code === 'WORKSPACE_REQUIRED' ||
    errorPayload?.code === 'WORKSPACE_NOT_CONFIGURED'
  ) {
    return {
      code: 'WORKSPACE_NOT_CONFIGURED',
      message: errorPayload?.message || 'Kein aktiver Workspace konfiguriert.',
    };
  }

  if (errorPayload?.code === 'WORKSPACE_ACCESS_FORBIDDEN') {
    return { code: 'FORBIDDEN', message: errorPayload?.message || 'Workspace-Zugriff verweigert.' };
  }

  if (response.status === 403) {
    return { code: 'FORBIDDEN', message: errorPayload?.message || 'Zugriff verweigert.' };
  }

  if (
    response.status === 422 ||
    (response.status === 400 &&
      (errorPayload?.code === 'VALIDATION_ERROR' || errorPayload?.code === 'INVALID_INPUT'))
  ) {
    return { code: 'VALIDATION_ERROR', message: errorPayload?.message || 'Validierungsfehler.' };
  }

  if (response.status >= 500) {
    return { code: 'SERVER_ERROR', message: errorPayload?.message || 'Interner Serverfehler.' };
  }

  return {
    code: errorPayload?.code || 'HTTP_ERROR',
    message: errorPayload?.message || response.statusText || 'API request failed',
  };
}

/**
 * Central HTTP function. All API modules must route through this.
 *
 * @param {string} path - API path (e.g. '/api/v1/documents')
 * @param {object} options
 * @param {number} [options.timeoutMs=15000] - Abort after this many ms.
 * @param {string} [options.correlationId] - Forwarded as X-Correlation-Id.
 * @param {AbortSignal} [options.signal] - External abort signal.
 */
export async function requestJson(path, options = {}) {
  const {
    headers: optionHeaders = {},
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal: optionSignal,
    correlationId,
    ...requestOptions
  } = options;

  const builtHeaders = buildRequestHeaders(optionHeaders, requestOptions.body, correlationId);

  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  let removeOptionAbortListener = null;
  let timedOut = false;

  if (controller && optionSignal) {
    const abortFromOptionSignal = () => controller.abort();
    if (optionSignal.aborted) {
      controller.abort();
    } else {
      optionSignal.addEventListener('abort', abortFromOptionSignal, { once: true });
      removeOptionAbortListener = () =>
        optionSignal.removeEventListener('abort', abortFromOptionSignal);
    }
  }

  const timeoutId =
    controller && timeoutMs > 0
      ? setTimeout(() => {
          timedOut = true;
          controller.abort();
        }, timeoutMs)
      : null;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...requestOptions,
      headers: builtHeaders,
      signal: controller?.signal || optionSignal,
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
    if (timeoutId) clearTimeout(timeoutId);
    if (removeOptionAbortListener) removeOptionAbortListener();
  }

  const contentType = response.headers.get('content-type') || '';
  const isJson = contentType.includes('application/json');
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    const errorPayload = payload?.error;
    const classified = classifyHttpFailure(response, errorPayload);
    if (response.status === 401 && _onAuthRequired) {
      _onAuthRequired();
    }
    throw new ApiClientError({
      code: classified.code,
      message: classified.message,
      details: {
        ...(errorPayload?.details || {}),
        backendCode: errorPayload?.code || null,
        classification: classified.code,
      },
      status: response.status,
    });
  }

  return payload;
}
