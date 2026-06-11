import { requestJson, ApiClientError } from '../api/client.js';

/**
 * Zentrale API-Wrapper-Funktion mit Result-Pattern.
 * Secrets werden NIEMALS geloggt.
 * @returns {Promise<{ok:true, data:any}|{ok:false, error:{code,message,status}}>}
 */
export async function callApi(path, options = {}) {
  try {
    const data = await requestJson(path, options);
    return { ok: true, data };
  } catch (err) {
    if (err instanceof ApiClientError) {
      return { ok: false, error: { code: err.code, message: err.message, status: err.status } };
    }
    return { ok: false, error: { code: 'UNKNOWN_ERROR', message: String(err), status: null } };
  }
}

export function isApiError(result) {
  return result.ok === false;
}
