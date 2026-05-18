import { requestJson } from './client.js';

export async function getJob(jobId, { signal, correlationId } = {}) {
  return requestJson(`/api/v1/jobs/${jobId}`, { signal, correlationId });
}
