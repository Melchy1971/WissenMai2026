import { requestJson } from './client.js';

export function getAuthSession() {
  return requestJson('/api/v1/auth/me');
}

export function login({ login, password }) {
  return requestJson('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ login, password }),
  });
}